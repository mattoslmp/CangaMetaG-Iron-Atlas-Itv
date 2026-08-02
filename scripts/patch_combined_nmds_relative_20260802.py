#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts" / "final_publication_figures" / "03_generate_combined_community_figures.py"


def main() -> int:
  if not TARGET.is_file():
    raise FileNotFoundError(TARGET)
  text = TARGET.read_text(encoding="utf-8")
  old = "  X=otu.T.to_numpy(float)"
  new = (
    "  relative = otu.div(otu.sum(axis=0).replace(0, np.nan), axis=1).fillna(0.0)\n"
    "  X=relative.T.to_numpy(float)"
  )
  if old in text:
    text = text.replace(old, new, 1)
  elif new not in text:
    raise RuntimeError("Could not locate the combined NMDS input matrix")
  required = [
    "relative = otu.div(otu.sum(axis=0).replace(0, np.nan), axis=1).fillna(0.0)",
    "distances=squareform(pdist(X,metric=\"braycurtis\"))",
  ]
  missing = [token for token in required if token not in text]
  if missing:
    raise RuntimeError(f"Relative-abundance NMDS contract incomplete: {missing}")
  compile(text, str(TARGET), "exec")
  TARGET.write_text(text, encoding="utf-8")
  print("Combined Bray-Curtis NMDS now uses within-sample relative abundances.")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
