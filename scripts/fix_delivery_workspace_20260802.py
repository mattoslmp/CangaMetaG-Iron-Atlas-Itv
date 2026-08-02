#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_generated_combined_script() -> dict[str, object]:
  path = ROOT / "scripts" / "final_publication_figures" / "03_generate_combined_community_figures.py"
  text = path.read_text(encoding="utf-8")
  before = text
  text = text.replace(
    'ax.boxplot(groups, labels=["AM","TIA","TI","VI"], showfliers=False)',
    'ax.boxplot(groups, tick_labels=["AM","TIA","TI","VI"], showfliers=False)',
  )
  if text == before and "tick_labels=" not in text:
    raise RuntimeError("Could not patch Matplotlib boxplot compatibility")
  path.write_text(text, encoding="utf-8")
  return {
    "path": str(path.relative_to(ROOT)),
    "matplotlib_tick_labels": "tick_labels=" in text,
  }


def replace_in_function(
  text: str,
  function_name: str,
  transform,
) -> tuple[str, bool]:
  pattern = re.compile(
    rf"(?ms)^def {re.escape(function_name)}\(.*?(?=^def |^class |\Z)"
  )
  match = pattern.search(text)
  if not match:
    return text, False
  old_block = match.group(0)
  new_block = transform(old_block)
  if new_block == old_block:
    return text, False
  return text[: match.start()] + new_block + text[match.end() :], True


def patch_app() -> dict[str, object]:
  path = ROOT / "app.py"
  text = path.read_text(encoding="utf-8")
  changes: list[str] = []

  def matrix_transform(block: str) -> str:
    original = block
    block, n = re.subn(
      r"(?m)^(\s*)ranked\s*=\s*ranked\[ranked\s*>=\s*float\(min_display_pct\)\]\s*$",
      (
        r'\1maximum = agg.groupby("taxon", as_index=True)["abundance"].max()\n'
        r"\1eligible = maximum[maximum >= float(min_display_pct)].index\n"
        r"\1ranked = ranked[ranked.index.isin(eligible)]"
      ),
      block,
      count=1,
    )
    if n:
      changes.append("matrix threshold uses maximum abundance")
    return block if block != original else original

  text, _ = replace_in_function(text, "_taxonomy_matrix_from_profile_final", matrix_transform)

  def heatmap_transform(block: str) -> str:
    original = block
    pattern = re.compile(
      r'(?m)^(\s*)matrix\s*=\s*_taxonomy_matrix_from_profile_final\('
      r'df,\s*value_col=value_col,\s*top_n=top_n\)\s*$'
    )
    replacement = (
      r'\1domain, rank = _taxonomy_selection_parts(level_name)\n'
      r'\1effective_top_n = None if rank == "Genus" else top_n\n'
      r'\1matrix = _taxonomy_matrix_from_profile_final(\n'
      r'\1  df, value_col=value_col, top_n=effective_top_n,\n'
      r'\1  min_display_pct=(1.0 if rank == "Genus" else None),\n'
      r'\1)\n'
      r'\1if rank == "Genus" and "Other taxa" in matrix.columns:\n'
      r'\1  matrix = matrix.rename(columns={"Other taxa": "Other taxa (<1%)"})'
    )
    block, n = pattern.subn(replacement, block, count=1)
    if n:
      changes.append("genus heatmap uses strict <1% aggregate")
    if block != original:
      # Remove a duplicate later assignment, but retain the first assignment inserted above.
      occurrences = [m.start() for m in re.finditer(r"(?m)^\s*domain, rank = _taxonomy_selection_parts\(level_name\)\s*$", block)]
      if len(occurrences) > 1:
        first = True
        lines = []
        for line in block.splitlines(keepends=True):
          if re.match(r"^\s*domain, rank = _taxonomy_selection_parts\(level_name\)\s*$", line):
            if first:
              first = False
              lines.append(line)
            else:
              continue
          else:
            lines.append(line)
        block = "".join(lines)
    return block

  text, _ = replace_in_function(text, "_taxonomy_heatmap_final", heatmap_transform)

  def barplot_transform(block: str) -> str:
    original = block
    pattern = re.compile(
      r'(?m)^(\s*)ranked\s*=\s*agg\.groupby\("taxon"(?:,\s*as_index=True)?\)'
      r'\["abundance"\]\.mean\(\)\.sort_values\(ascending=False\)\s*\n'
      r'\1requested\s*=\s*len\(ranked\) if top_n is None or int\(top_n\) <= 0 else min\(int\(top_n\), len\(ranked\)\)\s*\n'
      r'\1keep\s*=\s*ranked\.index\.tolist\(\)\[:requested\]\s*$'
    )
    replacement = (
      r'\1ranked = agg.groupby("taxon")["abundance"].mean().sort_values(ascending=False)\n'
      r'\1domain, rank = _taxonomy_selection_parts(level_name)\n'
      r'\1if rank == "Genus":\n'
      r'\1  maximum = agg.groupby("taxon")["abundance"].max()\n'
      r'\1  ranked = ranked[ranked.index.isin(maximum[maximum >= 1.0].index)]\n'
      r'\1  requested = len(ranked)\n'
      r'\1else:\n'
      r'\1  requested = len(ranked) if top_n is None or int(top_n) <= 0 else min(int(top_n), len(ranked))\n'
      r'\1keep = ranked.index.tolist()[:requested]'
    )
    block, n = pattern.subn(replacement, block, count=1)
    if n:
      changes.append("genus barplot uses strict <1% aggregate")
    block, n2 = re.subn(
      r'(?m)^(\s*)other\["taxon"\]\s*=\s*"Other taxa"\s*$',
      r'\1other["taxon"] = "Other taxa (<1%)" if rank == "Genus" else "Other taxa"',
      block,
      count=1,
    )
    if n2:
      changes.append("genus barplot aggregate label")
    if block != original:
      # A later domain/rank assignment is harmless but redundant; keep only the first.
      seen = False
      lines = []
      for line in block.splitlines(keepends=True):
        if re.match(r"^\s*domain, rank = _taxonomy_selection_parts\(level_name\)\s*$", line):
          if seen:
            continue
          seen = True
        lines.append(line)
      block = "".join(lines)
    return block

  text, _ = replace_in_function(text, "_taxonomy_barplot_final", barplot_transform)

  text = text.replace("Other taxa (<5%)", "Other taxa (<1%)")
  text = text.replace("Other genera (<5%)", "Other genera (<1%)")
  path.write_text(text, encoding="utf-8")

  required = [
    "maximum >= float(min_display_pct)",
    'rank == "Genus"',
    "Other taxa (<1%)",
  ]
  missing = [token for token in required if token not in text]
  if missing:
    raise RuntimeError(f"app.py correction contract incomplete: {missing}; changes={changes}")
  return {
    "path": "app.py",
    "changes": changes,
    "contract_tokens": required,
    "status": "PASS",
  }


def main() -> int:
  report = {
    "combined_generator": patch_generated_combined_script(),
    "app": patch_app(),
  }
  report_path = ROOT / "reports" / "DELIVERY_20260802_WORKSPACE_FIX_REPORT.json"
  report_path.parent.mkdir(parents=True, exist_ok=True)
  report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
  print(json.dumps(report, indent=2, ensure_ascii=False))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
