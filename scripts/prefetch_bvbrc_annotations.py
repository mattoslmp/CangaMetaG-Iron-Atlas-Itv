#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
  sys.path.insert(0, str(PROJECT_ROOT))

from src.bvbrc_cli_streamlit import (  # noqa: E402
  DEFAULT_WORKSPACE_BASE,
  bvbrc_cli_status,
  ensure_bvbrc_cli,
  sync_mag_annotation,
)


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    description=(
      "Download BV-BRC workspace annotations into Annotation/MAGx so they can "
      "be reviewed and committed to GitHub/Git LFS before deployment."
    )
  )
  parser.add_argument("--start", type=int, default=2, help="First MAG number")
  parser.add_argument("--end", type=int, default=50, help="Last MAG number")
  parser.add_argument(
    "--workspace",
    default=DEFAULT_WORKSPACE_BASE,
    help="BV-BRC Workspace directory containing MAG2, MAG3, ...",
  )
  parser.add_argument(
    "--annotation-dir",
    default=str(PROJECT_ROOT / "Annotation"),
    help="Local output directory inside the repository",
  )
  parser.add_argument("--overwrite", action="store_true")
  parser.add_argument("--timeout", type=int, default=3600)
  parser.add_argument(
    "--force-cli-repair",
    action="store_true",
    help="Rebuild the user-space BV-BRC CLI cache before downloading",
  )
  return parser.parse_args()


def file_inventory(root: Path) -> pd.DataFrame:
  rows = []
  if not root.exists():
    return pd.DataFrame()
  for path in sorted(p for p in root.rglob("*") if p.is_file()):
    size = path.stat().st_size
    rows.append({
      "path": str(path.relative_to(PROJECT_ROOT)),
      "bytes": size,
      "MiB": round(size / 1024**2, 3),
      "over_50_MiB": size > 50 * 1024**2,
      "over_100_MiB": size > 100 * 1024**2,
    })
  return pd.DataFrame(rows)


def main() -> int:
  args = parse_args()
  if args.start < 1 or args.end < args.start:
    raise SystemExit("Invalid MAG interval")

  annotation_dir = Path(args.annotation_dir).expanduser().resolve()
  project_root = PROJECT_ROOT.resolve()
  if not annotation_dir.is_relative_to(project_root):
    raise SystemExit(
      "--annotation-dir must remain inside the repository so the app can read it"
    )
  annotation_dir.mkdir(parents=True, exist_ok=True)

  cli_state = ensure_bvbrc_cli(force=args.force_cli_repair)
  print(bvbrc_cli_status().to_string(index=False))
  if not cli_state.ok:
    print(f"BV-BRC CLI unavailable: {cli_state.status}: {cli_state.message}")
    return 2

  login_command = cli_state.command("p3-login")
  print("\nAuthentication check:")
  print(f"  Run once before this downloader: {login_command} mattoslmp")
  print("  The password/token is entered only in your local terminal, never in Git.\n")

  results = []
  for number in range(args.start, args.end + 1):
    mag = f"MAG{number}"
    print(f"[{mag}] checking/downloading...", flush=True)
    result = sync_mag_annotation(
      mag,
      workspace_base=args.workspace,
      local_annotation_dir=annotation_dir,
      overwrite=args.overwrite,
      timeout=args.timeout,
    )
    row = asdict(result)
    results.append(row)
    print(
      f"[{mag}] ok={result.ok} status={result.status} "
      f"local={result.local_path}",
      flush=True,
    )
    if not result.ok and result.stderr:
      print(result.stderr[-2000:], flush=True)

  result_frame = pd.DataFrame(results)
  result_path = annotation_dir / "bvbrc_download_manifest.csv"
  result_frame.to_csv(result_path, index=False)

  inventory = file_inventory(annotation_dir)
  inventory_path = annotation_dir / "bvbrc_file_size_manifest.csv"
  inventory.to_csv(inventory_path, index=False)

  ok_count = int(result_frame["ok"].fillna(False).astype(bool).sum())
  failed = result_frame.loc[~result_frame["ok"].fillna(False).astype(bool)]
  total_gib = inventory["bytes"].sum() / 1024**3 if not inventory.empty else 0.0
  over_100 = int(inventory["over_100_MiB"].sum()) if not inventory.empty else 0

  print("\nDownload summary")
  print(f"  Successful/reused: {ok_count}/{len(result_frame)}")
  print(f"  Annotation size:   {total_gib:.3f} GiB")
  print(f"  Files >100 MiB:    {over_100}")
  print(f"  Result manifest:   {result_path}")
  print(f"  Size manifest:     {inventory_path}")

  if not failed.empty:
    print("\nFailed MAGs:")
    print(failed[["mag", "status", "stderr"]].to_string(index=False))
    return 1
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
