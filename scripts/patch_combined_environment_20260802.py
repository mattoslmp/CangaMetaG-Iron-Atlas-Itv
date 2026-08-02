#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts" / "final_publication_figures" / "03_generate_combined_community_figures.py"

ENVIRONMENT_BLOCK = r'''def _canonical_position_token(value):
  match = re.search(
    r"(?i)(?<![A-Z0-9])(AM|TIA|TI|VI)[._\-\s]*P?0*(\d+)(?![A-Z0-9])",
    str(value),
  )
  if not match:
    return None
  return f"{match.group(1).upper()}.P{int(match.group(2))}"


def _normalized_predictor_name(value):
  return re.sub(r"[^a-z0-9]+", "", str(value).casefold())


def _resolve_predictor_columns(columns):
  normalized = {
    column: _normalized_predictor_name(column)
    for column in columns
  }
  aliases = {
    "LOI": ("loi", "lossonignition"),
    "SiO2": ("sio2", "silicondioxide", "silica"),
    "Al2O3": ("al2o3", "aluminiumoxide", "aluminumoxide"),
    "TOT/S": ("tots", "totals", "totalsulfur", "totalsulphur"),
    "Cu": ("cu", "copper"),
    "Pb": ("pb", "lead"),
  }
  resolved = {}
  for canonical, prefixes in aliases.items():
    candidates = []
    for column, token in normalized.items():
      if any(token == prefix or token.startswith(prefix) for prefix in prefixes):
        candidates.append(column)
    if not candidates:
      return None
    candidates.sort(key=lambda column: (len(normalized[column]), str(column)))
    resolved[canonical] = candidates[0]
  if len(set(resolved.values())) != len(resolved):
    return None
  return resolved


def find_environment(positions):
  target = list(dict.fromkeys(str(position) for position in positions))
  target_set = set(target)
  if len(target_set) != 10:
    raise RuntimeError(
      f"Combined RDA requires exactly ten canonical positions; got {target}"
    )

  search_roots = [
    ROOT / "reproducibility" / "ordination_reproducibility",
    ROOT / "reproducibility",
    ROOT / "data",
    ROOT / "tables",
    ROOT / "metadata",
    ROOT / "outputs" / "final_publication_source_tables",
    ROOT / "outputs" / "final_publication_audit_tables",
    ROOT / "outputs" / "final_publication_derived",
  ]
  candidates = []
  for search_root in search_roots:
    if not search_root.exists():
      continue
    for candidate in search_root.rglob("*"):
      if not candidate.is_file():
        continue
      if candidate.suffix.casefold() not in {
        ".csv", ".tsv", ".tab", ".txt", ".xlsx", ".xls"
      }:
        continue
      try:
        if candidate.stat().st_size > 80 * 1024 * 1024:
          continue
      except OSError:
        continue
      candidates.append(candidate)

  diagnostics = []
  for candidate in sorted(set(candidates)):
    try:
      if candidate.suffix.casefold() in {".xlsx", ".xls"}:
        tables = pd.read_excel(candidate, sheet_name=None)
      else:
        frame = pd.read_csv(
          candidate,
          sep=None,
          engine="python",
          low_memory=False,
        )
        tables = {"table": frame}
    except Exception as error:
      diagnostics.append({
        "path": str(candidate.relative_to(ROOT)),
        "status": "unreadable",
        "error": str(error),
      })
      continue

    for sheet_name, frame in tables.items():
      if frame is None or frame.empty:
        continue
      best_position_column = None
      best_positions = None
      best_overlap = 0
      for column in frame.columns:
        parsed = frame[column].map(_canonical_position_token)
        overlap = len(target_set.intersection(set(parsed.dropna())))
        if overlap > best_overlap:
          best_position_column = column
          best_positions = parsed
          best_overlap = overlap
      predictors = _resolve_predictor_columns(frame.columns)
      diagnostic = {
        "path": str(candidate.relative_to(ROOT)),
        "sheet": str(sheet_name),
        "matched_positions": int(best_overlap),
        "position_column": (
          None if best_position_column is None else str(best_position_column)
        ),
        "predictors": (
          None if predictors is None else {
            canonical: str(source_column)
            for canonical, source_column in predictors.items()
          }
        ),
      }
      diagnostics.append(diagnostic)
      if best_position_column is None or best_positions is None:
        continue
      if best_overlap != 10 or predictors is None:
        continue

      work = pd.DataFrame({"Position": best_positions})
      canonical_predictors = ["LOI", "SiO2", "Al2O3", "TOT/S", "Cu", "Pb"]
      for canonical, source_column in predictors.items():
        work[canonical] = pd.to_numeric(frame[source_column], errors="coerce")
      work = work.loc[work["Position"].isin(target_set)].copy()
      environment = work.groupby("Position", as_index=False)[
        canonical_predictors
      ].mean()
      environment = environment.set_index("Position").reindex(target).reset_index()
      if len(environment) != 10:
        continue
      if environment[canonical_predictors].notna().sum().min() < 8:
        continue

      report = {
        "status": "PASS",
        "source": str(candidate.relative_to(ROOT)),
        "sheet": str(sheet_name),
        "positions": target,
        "predictor_columns": {
          canonical: str(source_column)
          for canonical, source_column in predictors.items()
        },
        "candidate_diagnostics": diagnostics,
      }
      (REPORTS / "COMBINED_ENVIRONMENT_SOURCE_20260802.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
      )
      return environment, candidate, str(sheet_name)

  failure_report = {
    "status": "FAIL",
    "required_positions": target,
    "required_predictors": ["LOI", "SiO2", "Al2O3", "TOT/S", "Cu", "Pb"],
    "candidate_diagnostics": diagnostics,
  }
  (REPORTS / "COMBINED_ENVIRONMENT_SOURCE_20260802.json").write_text(
    json.dumps(failure_report, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
  )
  raise RuntimeError(
    "Could not resolve a canonical physicochemical table containing all ten "
    "positions and the six official predictors. See "
    "reports/COMBINED_ENVIRONMENT_SOURCE_20260802.json"
  )


'''


def main() -> int:
  if not TARGET.is_file():
    raise FileNotFoundError(TARGET)
  text = TARGET.read_text(encoding="utf-8")
  text, replacements = re.subn(
    r"(?ms)^def find_environment\(positions\):.*?(?=^def rda\(otu\):)",
    lambda _match: ENVIRONMENT_BLOCK,
    text,
    count=1,
  )
  if replacements != 1:
    raise RuntimeError("Could not replace the combined RDA environment resolver")
  required = [
    "COMBINED_ENVIRONMENT_SOURCE_20260802.json",
    "Combined RDA requires exactly ten canonical positions",
    'canonical_predictors = ["LOI", "SiO2", "Al2O3", "TOT/S", "Cu", "Pb"]',
  ]
  missing = [token for token in required if token not in text]
  if missing:
    raise RuntimeError(f"Environment resolver contract incomplete: {missing}")
  compile(text, str(TARGET), "exec")
  TARGET.write_text(text, encoding="utf-8")
  print(f"Canonical combined-RDA environment resolver installed in {TARGET}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
