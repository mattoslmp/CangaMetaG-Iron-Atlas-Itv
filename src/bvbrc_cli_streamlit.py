from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

from . import bvbrc_cli_sync as _base


BVBRC_LAYOUT_REVISION = 3
_ORIGINAL_FIND_EXTRACTED_COMMAND = _base._find_extracted_command
_ORIGINAL_ENSURE_BVBRC_CLI = _base.ensure_bvbrc_cli
_ORIGINAL_PERL_LIBRARY_ROOTS = _base._perl_library_roots
_ORIGINAL_BINARY_DIRECTORIES = _base._binary_directories
_ORIGINAL_CREATE_LOCAL_WRAPPERS = _base._create_local_wrappers


def _unique_existing(paths: list[Path]) -> list[Path]:
  result = []
  for path in paths:
    if path.exists() and path not in result:
      result.append(path)
  return result


def _deployment_roots(rootfs: Path) -> list[Path]:
  candidates = [
    rootfs / "usr" / "share" / "bvbrc-cli" / "deployment",
    rootfs / "usr" / "share" / "patric-cli" / "deployment",
    rootfs / "opt" / "bvbrc" / "deployment",
    rootfs / "opt" / "patric" / "deployment",
  ]
  candidates.extend(
    path.parent.parent
    for path in rootfs.rglob("plbin/p3-ls.pl")
    if path.is_file()
  )
  return _unique_existing(candidates)


def _perl_library_roots(rootfs: Path) -> list[Path]:
  candidates = list(_ORIGINAL_PERL_LIBRARY_ROOTS(rootfs))
  for deployment in _deployment_roots(rootfs):
    candidates.extend([
      deployment / "lib",
      deployment / "lib" / "perl5",
      deployment / "site_perl",
    ])
  return _unique_existing(candidates)


def _binary_directories(rootfs: Path) -> list[Path]:
  candidates = list(_ORIGINAL_BINARY_DIRECTORIES(rootfs))
  for deployment in _deployment_roots(rootfs):
    candidates.extend([
      deployment / "bin",
      deployment / "plbin",
    ])
  return _unique_existing(candidates)


def _direct_perl_candidates(rootfs: Path, command_name: str) -> list[Path]:
  """Return packaged Perl entry points before absolute-path launchers."""
  filename = f"{command_name}.pl"
  candidates = [deployment / "plbin" / filename for deployment in _deployment_roots(rootfs)]
  candidates.extend(
    path for path in rootfs.rglob(filename)
    if "share/man" not in path.as_posix()
  )
  return _unique_existing(candidates)


def _find_extracted_command(rootfs: Path, command_name: str) -> Path | None:
  """Resolve the real packaged script instead of /usr/bin's absolute launcher.

  The Debian package's /usr/bin/p3-* launchers refer to paths such as
  /usr/share/bvbrc-cli/deployment/plbin/p3-ls.pl. Those paths only exist after a
  system-wide installation. Streamlit extracts the package into a user cache,
  so invoking the launcher would escape the extracted root and fail.
  """
  for candidate in _direct_perl_candidates(rootfs, command_name):
    if candidate.exists() and candidate.is_file():
      return candidate
  return _ORIGINAL_FIND_EXTRACTED_COMMAND(rootfs, command_name)


def _create_local_wrappers(rootfs: Path) -> dict[str, str]:
  """Create relocatable wrappers for required and auxiliary p3 commands."""
  commands = _ORIGINAL_CREATE_LOCAL_WRAPPERS(rootfs)
  _base.BVBRC_LOCAL_BIN.mkdir(parents=True, exist_ok=True)
  for deployment in _deployment_roots(rootfs):
    plbin = deployment / "plbin"
    if not plbin.exists():
      continue
    for script in sorted(plbin.glob("p3-*.pl")):
      command_name = script.stem
      wrapper = _base.BVBRC_LOCAL_BIN / command_name
      wrapper.write_text(_base._wrapper_text(script, rootfs), encoding="utf-8")
      wrapper.chmod(0o755)
      if command_name in {"p3-ls", "p3-cp", "p3-login"}:
        commands[command_name] = str(wrapper)
  return commands


def _marker_has_current_layout() -> bool:
  marker = _base.BVBRC_INSTALL_MARKER
  if not marker.exists():
    return False
  try:
    payload = json.loads(marker.read_text(encoding="utf-8"))
  except Exception:
    return False
  if int(payload.get("layout_revision", 0) or 0) != BVBRC_LAYOUT_REVISION:
    return False
  commands = dict(payload.get("commands", {}))
  for name in ("p3-ls", "p3-cp", "p3-login"):
    wrapper = Path(str(commands.get(name, "")))
    if not wrapper.exists():
      return False
    try:
      wrapper_text = wrapper.read_text(encoding="utf-8", errors="ignore")
    except Exception:
      return False
    if str(_base.BVBRC_ROOTFS) not in wrapper_text:
      return False
  return True


def _invalidate_legacy_cache() -> None:
  _base.BVBRC_INSTALL_MARKER.unlink(missing_ok=True)
  shutil.rmtree(_base.BVBRC_LOCAL_BIN, ignore_errors=True)


def _record_layout_revision() -> None:
  marker = _base.BVBRC_INSTALL_MARKER
  if not marker.exists():
    return
  try:
    payload = json.loads(marker.read_text(encoding="utf-8"))
  except Exception:
    payload = {}
  payload["layout_revision"] = BVBRC_LAYOUT_REVISION
  payload["launcher_mode"] = "direct_extracted_perl_entrypoints"
  marker.write_text(
    json.dumps(payload, indent=2, sort_keys=True),
    encoding="utf-8",
  )


def _probe_cli(command: str) -> tuple[bool, str]:
  if not command:
    return False, "p3-ls is unavailable after installation."
  try:
    process = subprocess.run(
      [command, "--help"],
      text=True,
      capture_output=True,
      timeout=45,
      check=False,
      env=_base.os.environ.copy(),
    )
  except Exception as exc:
    return False, str(exc)
  output = (process.stdout or "") + "\n" + (process.stderr or "")
  lowered = output.casefold()
  if "can't open perl script" in lowered or "no such file or directory" in lowered:
    return False, output.strip()[-4000:]
  if "can't locate" in lowered and ".pm" in lowered:
    return False, output.strip()[-4000:]
  if process.returncode in {126, 127}:
    return False, output.strip()[-4000:]
  return True, output.strip()


def _activate_relocatable_functions() -> None:
  _base._perl_library_roots = _perl_library_roots
  _base._binary_directories = _binary_directories
  _base._find_extracted_command = _find_extracted_command
  _base._create_local_wrappers = _create_local_wrappers


def ensure_bvbrc_cli(force: bool = False):
  """Install or repair the CLI with relocatable user-space launchers."""
  _activate_relocatable_functions()

  if force or (_base.BVBRC_INSTALL_MARKER.exists() and not _marker_has_current_layout()):
    _invalidate_legacy_cache()

  state = _ORIGINAL_ENSURE_BVBRC_CLI(force=force)
  if not state.ok:
    return state

  if state.status == "installed_local_cache":
    _record_layout_revision()
    ok, detail = _probe_cli(state.command("p3-ls"))
    if not ok:
      _invalidate_legacy_cache()
      repaired = _ORIGINAL_ENSURE_BVBRC_CLI(force=True)
      if repaired.ok and repaired.status == "installed_local_cache":
        _record_layout_revision()
        ok, detail = _probe_cli(repaired.command("p3-ls"))
      if not ok:
        return _base.BvbrcCliInstallState(
          ok=False,
          status="cli_launcher_relocation_failed",
          install_root=str(_base.BVBRC_VERSION_ROOT),
          commands=getattr(repaired, "commands", {}),
          message=detail,
        )
      state = repaired
  return state


# The original public functions resolve ensure_bvbrc_cli from their module at
# runtime. Replacing it here fixes status, listing and download operations.
_activate_relocatable_functions()
_base.ensure_bvbrc_cli = ensure_bvbrc_cli


DEFAULT_WORKSPACE_BASE = _base.DEFAULT_WORKSPACE_BASE
BvbrcSyncResult = _base.BvbrcSyncResult
BvbrcCliInstallState = _base.BvbrcCliInstallState
bvbrc_cli_status = _base.bvbrc_cli_status
install_commands_ubuntu = _base.install_commands_ubuntu
inventory_local_annotations = _base.inventory_local_annotations
local_annotation_status = _base.local_annotation_status
list_remote_path = _base.list_remote_path
sync_mag_annotation = _base.sync_mag_annotation
