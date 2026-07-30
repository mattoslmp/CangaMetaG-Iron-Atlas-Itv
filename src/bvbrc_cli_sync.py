from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import time
import urllib.request

import pandas as pd

from ._helpers import canonical_mag


DEFAULT_WORKSPACE_BASE = "/mattoslmp@patricbrc.org/Lakes-Canga/metagenomas"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
BVBRC_CLI_VERSION = "1.040"
BVBRC_CLI_DEB_URL = (
  "https://github.com/BV-BRC/BV-BRC-CLI/releases/download/"
  f"{BVBRC_CLI_VERSION}/bvbrc-cli-{BVBRC_CLI_VERSION}.deb"
)
BVBRC_CACHE_ROOT = Path(
  os.environ.get(
    "BVBRC_CLI_CACHE",
    str(Path.home() / ".cache" / "cangametag" / "bvbrc-cli"),
  )
).expanduser()
BVBRC_VERSION_ROOT = BVBRC_CACHE_ROOT / BVBRC_CLI_VERSION
BVBRC_ROOTFS = BVBRC_VERSION_ROOT / "rootfs"
BVBRC_LOCAL_BIN = BVBRC_VERSION_ROOT / "bin"
BVBRC_PACKAGE_PATH = BVBRC_VERSION_ROOT / f"bvbrc-cli-{BVBRC_CLI_VERSION}.deb"
BVBRC_INSTALL_MARKER = BVBRC_VERSION_ROOT / "install.json"


@dataclass
class BvbrcSyncResult:
  mag: str
  ok: bool
  status: str
  command: str = ""
  stdout: str = ""
  stderr: str = ""
  local_path: str = ""
  remote_path: str = ""

  def as_row(self) -> dict:
    return asdict(self)


@dataclass
class BvbrcCliInstallState:
  ok: bool
  status: str
  version: str = BVBRC_CLI_VERSION
  install_root: str = ""
  commands: dict[str, str] = field(default_factory=dict)
  message: str = ""

  def command(self, name: str) -> str:
    value = self.commands.get(name, "")
    return value if value and Path(value).exists() else ""


def _safe_local_root(local_annotation_dir: str | Path = "Annotation") -> Path:
  requested = Path(local_annotation_dir).expanduser()
  root = requested if requested.is_absolute() else PROJECT_ROOT / requested
  try:
    resolved = root.resolve()
    project = PROJECT_ROOT.resolve()
    if not resolved.is_relative_to(project):
      return project / "Annotation"
    return resolved
  except Exception:
    return PROJECT_ROOT / "Annotation"


def _displayable_file_count(folder: Path) -> int:
  if not folder.exists():
    return 0
  suffixes = {
    ".fa", ".faa", ".fasta", ".fna", ".ffn", ".gb", ".gbk", ".genbank",
    ".txt", ".tsv", ".csv", ".xls", ".xlsx", ".html", ".json",
  }
  return sum(
    1 for path in folder.rglob("*")
    if path.is_file() and path.suffix.lower() in suffixes
  )


def _run(
  command: list[str],
  timeout: int,
  env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
  return subprocess.run(
    command,
    text=True,
    capture_output=True,
    timeout=timeout,
    check=False,
    env=env,
  )


def _prepend_env(name: str, values: list[str]) -> None:
  cleaned = []
  for value in values:
    text = str(value).strip()
    if text and text not in cleaned:
      cleaned.append(text)
  current = [part for part in os.environ.get(name, "").split(os.pathsep) if part]
  os.environ[name] = os.pathsep.join(
    cleaned + [part for part in current if part not in cleaned]
  )


def _perl_library_roots(rootfs: Path) -> list[Path]:
  candidates = [
    rootfs / "usr" / "share" / "perl5",
    rootfs / "usr" / "local" / "share" / "perl5",
    rootfs / "usr" / "lib" / "perl5",
    rootfs / "usr" / "local" / "lib" / "perl5",
    rootfs / "opt" / "bvbrc" / "lib",
    rootfs / "opt" / "patric" / "lib",
  ]
  for pattern in (
    "usr/lib/*/perl5",
    "usr/lib/*/perl/*",
    "opt/bvbrc/lib/perl5",
    "opt/patric/lib/perl5",
  ):
    candidates.extend(rootfs.glob(pattern))
  return [path for path in candidates if path.exists()]


def _binary_directories(rootfs: Path) -> list[Path]:
  candidates = [
    rootfs / "usr" / "bin",
    rootfs / "usr" / "local" / "bin",
    rootfs / "opt" / "bvbrc" / "bin",
    rootfs / "opt" / "patric" / "bin",
  ]
  return [path for path in candidates if path.exists()]


def _activate_local_cli_environment(rootfs: Path = BVBRC_ROOTFS) -> None:
  bin_dirs = [BVBRC_LOCAL_BIN] + _binary_directories(rootfs)
  _prepend_env("PATH", [str(path) for path in bin_dirs])
  _prepend_env("PERL5LIB", [str(path) for path in _perl_library_roots(rootfs)])

  library_dirs = [
    rootfs / "usr" / "lib",
    rootfs / "usr" / "lib" / "x86_64-linux-gnu",
    rootfs / "usr" / "local" / "lib",
    rootfs / "opt" / "bvbrc" / "lib",
    rootfs / "opt" / "patric" / "lib",
  ]
  _prepend_env(
    "LD_LIBRARY_PATH",
    [str(path) for path in library_dirs if path.exists()],
  )
  os.environ["BVBRC_CLI_ROOT"] = str(rootfs)


def _resolve_extracted_target(path: Path, rootfs: Path) -> Path:
  if not path.is_symlink():
    return path
  target = os.readlink(path)
  if os.path.isabs(target):
    return rootfs / target.lstrip("/")
  return (path.parent / target).resolve()


def _find_extracted_command(rootfs: Path, command_name: str) -> Path | None:
  preferred = [
    rootfs / "usr" / "bin" / command_name,
    rootfs / "usr" / "local" / "bin" / command_name,
    rootfs / "opt" / "bvbrc" / "bin" / command_name,
    rootfs / "opt" / "patric" / "bin" / command_name,
  ]
  for candidate in preferred:
    if candidate.exists() or candidate.is_symlink():
      resolved = _resolve_extracted_target(candidate, rootfs)
      if resolved.exists():
        return resolved

  for candidate in rootfs.rglob(command_name):
    if "share/man" in candidate.as_posix():
      continue
    resolved = _resolve_extracted_target(candidate, rootfs)
    if resolved.exists() and resolved.is_file():
      return resolved
  return None


def _wrapper_text(actual: Path, rootfs: Path) -> str:
  perl_paths = os.pathsep.join(
    str(path) for path in _perl_library_roots(rootfs)
  )
  bin_paths = os.pathsep.join(
    str(path) for path in [BVBRC_LOCAL_BIN] + _binary_directories(rootfs)
  )
  library_paths = os.pathsep.join(
    str(path)
    for path in [
      rootfs / "usr" / "lib",
      rootfs / "usr" / "lib" / "x86_64-linux-gnu",
      rootfs / "usr" / "local" / "lib",
      rootfs / "opt" / "bvbrc" / "lib",
      rootfs / "opt" / "patric" / "lib",
    ]
    if path.exists()
  )
  try:
    first_line = actual.open("rb").readline(512).decode(
      "utf-8", errors="ignore"
    )
  except Exception:
    first_line = ""
  is_perl = "perl" in first_line.casefold() or actual.suffix.casefold() == ".pl"
  executable = (
    f"/usr/bin/perl {shlex.quote(str(actual))}"
    if is_perl
    else shlex.quote(str(actual))
  )
  return (
    "#!/bin/sh\n"
    f"export BVBRC_CLI_ROOT={shlex.quote(str(rootfs))}\n"
    f"export PERL5LIB={shlex.quote(perl_paths)}:\"${{PERL5LIB:-}}\"\n"
    f"export PATH={shlex.quote(bin_paths)}:\"${{PATH:-}}\"\n"
    f"export LD_LIBRARY_PATH={shlex.quote(library_paths)}:\"${{LD_LIBRARY_PATH:-}}\"\n"
    f"exec {executable} \"$@\"\n"
  )


def _create_local_wrappers(rootfs: Path) -> dict[str, str]:
  BVBRC_LOCAL_BIN.mkdir(parents=True, exist_ok=True)
  commands: dict[str, str] = {}
  missing = []
  for name in ("p3-ls", "p3-cp", "p3-login"):
    actual = _find_extracted_command(rootfs, name)
    if actual is None:
      missing.append(name)
      continue
    wrapper = BVBRC_LOCAL_BIN / name
    wrapper.write_text(_wrapper_text(actual, rootfs), encoding="utf-8")
    wrapper.chmod(0o755)
    commands[name] = str(wrapper)
  if missing:
    raise RuntimeError(
      "The extracted BV-BRC package did not contain: " + ", ".join(missing)
    )
  return commands


def _download_package(destination: Path) -> None:
  destination.parent.mkdir(parents=True, exist_ok=True)
  partial = destination.with_suffix(destination.suffix + ".part")
  partial.unlink(missing_ok=True)
  request = urllib.request.Request(
    BVBRC_CLI_DEB_URL,
    headers={"User-Agent": "CangaMetaG-Iron-Atlas/1.0"},
  )
  with urllib.request.urlopen(request, timeout=180) as response, partial.open(
    "wb"
  ) as handle:
    total = 0
    while True:
      chunk = response.read(1024 * 1024)
      if not chunk:
        break
      total += len(chunk)
      if total > 1024 * 1024 * 1024:
        raise RuntimeError("BV-BRC CLI package exceeded the 1 GiB safety limit.")
      handle.write(chunk)
  if partial.stat().st_size < 100_000:
    raise RuntimeError("Downloaded BV-BRC CLI package is unexpectedly small.")
  partial.replace(destination)


def _read_marker() -> BvbrcCliInstallState | None:
  if not BVBRC_INSTALL_MARKER.exists():
    return None
  try:
    payload = json.loads(BVBRC_INSTALL_MARKER.read_text(encoding="utf-8"))
    commands = {
      str(name): str(path)
      for name, path in dict(payload.get("commands", {})).items()
      if Path(str(path)).exists()
    }
    if all(name in commands for name in ("p3-ls", "p3-cp", "p3-login")):
      return BvbrcCliInstallState(
        ok=True,
        status="installed_local_cache",
        version=str(payload.get("version", BVBRC_CLI_VERSION)),
        install_root=str(BVBRC_VERSION_ROOT),
        commands=commands,
        message="BV-BRC CLI loaded from the application cache.",
      )
  except Exception:
    return None
  return None


def _system_cli_state() -> BvbrcCliInstallState | None:
  commands = {
    name: shutil.which(name) or ""
    for name in ("p3-ls", "p3-cp", "p3-login")
  }
  if commands["p3-ls"] and commands["p3-cp"]:
    return BvbrcCliInstallState(
      ok=True,
      status="installed_system",
      install_root="system",
      commands=commands,
      message="BV-BRC CLI is available from the system PATH.",
    )
  return None


def _acquire_install_lock(timeout: int = 240):
  BVBRC_VERSION_ROOT.mkdir(parents=True, exist_ok=True)
  lock_path = BVBRC_VERSION_ROOT / ".install.lock"
  handle = lock_path.open("a+")
  try:
    import fcntl
  except ImportError:
    return handle
  deadline = time.monotonic() + timeout
  while True:
    try:
      fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
      return handle
    except BlockingIOError:
      if time.monotonic() >= deadline:
        handle.close()
        raise TimeoutError(
          "Timed out waiting for the BV-BRC CLI installation lock."
        )
      time.sleep(0.25)


def ensure_bvbrc_cli(force: bool = False) -> BvbrcCliInstallState:
  system_state = _system_cli_state()
  if system_state and not force:
    return system_state

  marker_state = _read_marker()
  if marker_state and not force:
    _activate_local_cli_environment()
    return marker_state

  lock_handle = None
  try:
    lock_handle = _acquire_install_lock()
    marker_state = _read_marker()
    if marker_state and not force:
      _activate_local_cli_environment()
      return marker_state

    dpkg_deb = shutil.which("dpkg-deb")
    if not dpkg_deb:
      return BvbrcCliInstallState(
        ok=False,
        status="installer_dependency_missing",
        install_root=str(BVBRC_VERSION_ROOT),
        message=(
          "dpkg-deb is unavailable. Add the Debian package 'dpkg' to "
          "packages.txt and reboot the Streamlit app."
        ),
      )

    if force:
      shutil.rmtree(BVBRC_ROOTFS, ignore_errors=True)
      BVBRC_INSTALL_MARKER.unlink(missing_ok=True)

    if not BVBRC_PACKAGE_PATH.exists():
      _download_package(BVBRC_PACKAGE_PATH)

    info = _run([dpkg_deb, "--info", str(BVBRC_PACKAGE_PATH)], timeout=60)
    info_text = (info.stdout + "\n" + info.stderr).casefold()
    if info.returncode != 0 or "bvbrc" not in info_text:
      BVBRC_PACKAGE_PATH.unlink(missing_ok=True)
      raise RuntimeError(
        "The downloaded file was not recognized as the expected BV-BRC "
        "Debian package."
      )

    staging = Path(
      tempfile.mkdtemp(prefix="rootfs-", dir=str(BVBRC_VERSION_ROOT))
    )
    try:
      extracted = _run(
        [dpkg_deb, "--extract", str(BVBRC_PACKAGE_PATH), str(staging)],
        timeout=300,
      )
      if extracted.returncode != 0:
        raise RuntimeError(
          "dpkg-deb extraction failed: "
          + (extracted.stderr or extracted.stdout or "unknown error")[-4000:]
        )
      shutil.rmtree(BVBRC_ROOTFS, ignore_errors=True)
      staging.replace(BVBRC_ROOTFS)
    finally:
      if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)

    commands = _create_local_wrappers(BVBRC_ROOTFS)
    _activate_local_cli_environment(BVBRC_ROOTFS)

    probe = _run(
      [commands["p3-ls"], "--help"],
      timeout=45,
      env=os.environ.copy(),
    )
    probe_text = probe.stdout + "\n" + probe.stderr
    dependency_error = re.search(r"Can't locate\s+([^\s]+\.pm)", probe_text)
    if dependency_error:
      raise RuntimeError(
        "BV-BRC CLI was extracted, but a Perl dependency is missing: "
        + dependency_error.group(1)
      )
    if probe.returncode in {126, 127}:
      raise RuntimeError(
        "BV-BRC CLI wrapper could not be executed: " + probe_text[-4000:]
      )

    payload = {
      "version": BVBRC_CLI_VERSION,
      "source": BVBRC_CLI_DEB_URL,
      "installed_at_epoch": int(time.time()),
      "commands": commands,
    }
    BVBRC_INSTALL_MARKER.write_text(
      json.dumps(payload, indent=2, sort_keys=True),
      encoding="utf-8",
    )
    return BvbrcCliInstallState(
      ok=True,
      status="installed_local_cache",
      install_root=str(BVBRC_VERSION_ROOT),
      commands=commands,
      message="BV-BRC CLI was installed in the application user cache.",
    )
  except Exception as exc:
    return BvbrcCliInstallState(
      ok=False,
      status="cli_install_failed",
      install_root=str(BVBRC_VERSION_ROOT),
      message=str(exc),
    )
  finally:
    if lock_handle is not None:
      try:
        lock_handle.close()
      except Exception:
        pass


def _cli_authentication_status(command: str) -> tuple[bool | None, str]:
  if not command:
    return None, "p3-login unavailable"
  try:
    process = _run(
      [command, "--status"],
      timeout=20,
      env=os.environ.copy(),
    )
  except Exception as exc:
    return None, str(exc)
  text = (process.stdout or process.stderr or "").strip()
  return process.returncode == 0, text


def bvbrc_cli_status() -> pd.DataFrame:
  state = ensure_bvbrc_cli()
  auth_ok, auth_message = _cli_authentication_status(state.command("p3-login"))
  rows = [{
    "component": "BV-BRC CLI",
    "installed": state.ok,
    "path": state.install_root,
    "status": state.status,
    "purpose": state.message,
  }]
  for name, purpose in [
    ("p3-ls", "List BV-BRC workspace entries"),
    ("p3-cp", "Copy BV-BRC workspace results into Annotation/MAGx"),
    ("p3-login", "Manage the server-side BV-BRC login token"),
  ]:
    command_path = state.command(name)
    rows.append({
      "component": name,
      "installed": bool(command_path),
      "path": command_path,
      "status": "available" if command_path else state.status,
      "purpose": purpose,
    })
  rows.append({
    "component": "BV-BRC authentication",
    "installed": bool(auth_ok),
    "path": "",
    "status": "authenticated" if auth_ok else "authentication_required",
    "purpose": auth_message or "Run p3-login once in the deployment environment.",
  })
  return pd.DataFrame(rows)


def install_commands_ubuntu() -> str:
  return (
    "# Official system-wide installation (Ubuntu/Debian)\n"
    f"curl -L -O {BVBRC_CLI_DEB_URL}\n"
    f"sudo apt-get update && sudo apt-get install -y "
    f"./bvbrc-cli-{BVBRC_CLI_VERSION}.deb\n"
    "p3-login mattoslmp\n\n"
    "# This Streamlit repository also installs the same pinned package "
    "automatically\n"
    "# into ~/.cache/cangametag/bvbrc-cli without sudo."
  )


def inventory_local_annotations(
  local_annotation_dir: str | Path = "Annotation",
) -> pd.DataFrame:
  root = _safe_local_root(local_annotation_dir)
  rows = []
  if root.exists():
    for folder in sorted(path for path in root.iterdir() if path.is_dir()):
      status = local_annotation_status(folder.name, root)
      rows.append({
        "MAG": status["MAG"],
        "folder": status["local_path"],
        "files": status["files"],
        "displayable_files": status["displayable_files"],
        "ready_for_app": status["ready_for_app"],
      })
  return pd.DataFrame(rows)


def local_annotation_status(
  mag_id: object,
  local_annotation_dir: str | Path = "Annotation",
) -> dict:
  root = _safe_local_root(local_annotation_dir)
  cid = canonical_mag(mag_id)
  candidates = [root / cid]
  if root.exists():
    candidates.extend(
      path for path in root.iterdir()
      if path.is_dir() and canonical_mag(path.name) == cid
    )
  folder = next((path for path in candidates if path.exists()), root / cid)
  files = (
    sum(1 for path in folder.rglob("*") if path.is_file())
    if folder.exists()
    else 0
  )
  displayable = _displayable_file_count(folder)
  ready = bool(folder.exists() and displayable > 0)
  return {
    "MAG": cid,
    "folder": str(folder),
    "local_path": str(folder),
    "exists": folder.exists(),
    "files": files,
    "displayable_files": displayable,
    "ready_for_app": ready,
    "reason": (
      "local_annotation_available"
      if ready
      else "local_annotation_missing_or_empty"
    ),
  }


def list_remote_path(
  workspace_base: str = DEFAULT_WORKSPACE_BASE,
  timeout: int = 180,
) -> BvbrcSyncResult:
  state = ensure_bvbrc_cli()
  executable = state.command("p3-ls")
  if not executable:
    return BvbrcSyncResult(
      mag="",
      ok=False,
      status=state.status,
      stderr=state.message or "p3-ls could not be installed.",
      remote_path=str(workspace_base),
    )
  command = [executable, str(workspace_base).strip()]
  try:
    process = _run(command, timeout=timeout, env=os.environ.copy())
  except subprocess.TimeoutExpired as exc:
    return BvbrcSyncResult(
      mag="",
      ok=False,
      status="remote_listing_timeout",
      command=" ".join(command),
      stdout=str(exc.stdout or ""),
      stderr=str(exc.stderr or ""),
      remote_path=str(workspace_base),
    )
  except Exception as exc:
    return BvbrcSyncResult(
      mag="",
      ok=False,
      status="remote_listing_error",
      command=" ".join(command),
      stderr=str(exc),
      remote_path=str(workspace_base),
    )
  stderr = process.stderr or ""
  status = (
    "remote_directory_listed"
    if process.returncode == 0
    else "remote_listing_failed"
  )
  if process.returncode != 0 and re.search(
    r"login|auth|token|credential", stderr, re.I
  ):
    status = "authentication_required"
  return BvbrcSyncResult(
    mag="",
    ok=process.returncode == 0,
    status=status,
    command=" ".join(command),
    stdout=process.stdout or "",
    stderr=stderr,
    remote_path=str(workspace_base),
  )


def _remote_entry_for_mag(listing: str, mag: str) -> str:
  for line in str(listing).splitlines():
    tokens = [
      token.strip().strip("'")
      for token in re.split(r"\s+", line.strip())
      if token.strip()
    ]
    for token in reversed(tokens):
      clean = token.rstrip("/")
      basename = clean.rsplit("/", 1)[-1]
      if canonical_mag(basename) == mag:
        return basename
  return mag


def sync_mag_annotation(
  mag_id: object,
  workspace_base: str = DEFAULT_WORKSPACE_BASE,
  local_annotation_dir: str | Path = "Annotation",
  overwrite: bool = False,
  timeout: int = 3600,
) -> BvbrcSyncResult:
  mag = canonical_mag(mag_id)
  root = _safe_local_root(local_annotation_dir)
  local_status = local_annotation_status(mag, root)
  if local_status["ready_for_app"] and not overwrite:
    return BvbrcSyncResult(
      mag=mag,
      ok=True,
      status="already_local_no_download",
      local_path=local_status["local_path"],
      remote_path=str(workspace_base),
    )

  state = ensure_bvbrc_cli()
  p3_cp = state.command("p3-cp")
  if not p3_cp:
    return BvbrcSyncResult(
      mag=mag,
      ok=False,
      status=state.status,
      stderr=state.message or "p3-cp could not be installed.",
      local_path=local_status["local_path"],
      remote_path=str(workspace_base),
    )

  listing = list_remote_path(workspace_base, timeout=min(timeout, 240))
  if not listing.ok:
    return BvbrcSyncResult(
      mag=mag,
      ok=False,
      status=listing.status,
      command=listing.command,
      stdout=listing.stdout,
      stderr=listing.stderr,
      local_path=local_status["local_path"],
      remote_path=str(workspace_base),
    )

  remote_entry = _remote_entry_for_mag(listing.stdout, mag)
  remote_path = (
    f"{str(workspace_base).rstrip('/')}/{remote_entry}".replace("//", "/")
  )
  target = root / mag
  root.mkdir(parents=True, exist_ok=True)
  if overwrite and target.exists():
    shutil.rmtree(target)
  target.mkdir(parents=True, exist_ok=True)

  source = f"ws:{remote_path.rstrip('/')}/"
  command = [p3_cp, "-r"]
  if overwrite:
    command.append("-f")
  command.extend([source, str(target)])

  try:
    process = _run(command, timeout=timeout, env=os.environ.copy())
  except subprocess.TimeoutExpired as exc:
    return BvbrcSyncResult(
      mag=mag,
      ok=False,
      status="download_timeout",
      command=" ".join(command),
      stdout=str(exc.stdout or ""),
      stderr=str(exc.stderr or ""),
      local_path=str(target),
      remote_path=remote_path,
    )
  except Exception as exc:
    return BvbrcSyncResult(
      mag=mag,
      ok=False,
      status="download_error",
      command=" ".join(command),
      stderr=str(exc),
      local_path=str(target),
      remote_path=remote_path,
    )

  refreshed = local_annotation_status(mag, root)
  ok = process.returncode == 0 and refreshed["ready_for_app"]
  stderr = process.stderr or ""
  status = "downloaded" if ok else "download_failed_or_empty"
  if not ok and re.search(r"login|auth|token|credential", stderr, re.I):
    status = "authentication_required"
  return BvbrcSyncResult(
    mag=mag,
    ok=ok,
    status=status,
    command=" ".join(command),
    stdout=process.stdout or "",
    stderr=stderr,
    local_path=str(target),
    remote_path=remote_path,
  )
