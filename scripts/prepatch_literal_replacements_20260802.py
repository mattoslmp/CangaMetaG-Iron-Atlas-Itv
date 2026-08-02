#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "scripts" / "fix_delivery_workspace_20260802.py"
text = path.read_text(encoding="utf-8")
replacements = {
  "    read_otu_block,\n    text,": "    lambda _match: read_otu_block,\n    text,",
  "    predictor_patch,\n    text,": "    lambda _match: predictor_patch,\n    text,",
  "  identifiers = [str(value) for value in jgi_ids]\n  identifier_set = set(identifiers)": (
    "  raw_identifiers = [str(value) for value in jgi_ids]\n"
    "  aliases = {}\n"
    "  for raw_identifier in raw_identifiers:\n"
    "    match = re.search(r\"(?i)Ga\\d+\", raw_identifier)\n"
    "    aliases[raw_identifier] = match.group(0) if match else raw_identifier\n"
    "  identifiers = list(dict.fromkeys(aliases.values()))\n"
    "  identifier_set = set(identifiers)"
  ),
  "    \"requested_jgi_ids\": identifiers,\n    \"resolved_mapping\": mapping,": (
    "    \"requested_jgi_ids\": raw_identifiers,\n"
    "    \"normalized_jgi_aliases\": aliases,\n"
    "    \"resolved_mapping\": {\n"
    "      raw_identifier: mapping[alias]\n"
    "      for raw_identifier, alias in aliases.items()\n"
    "      if alias in mapping\n"
    "    },"
  ),
  "  return mapping, diagnostic\n\n\ndef read_otu": (
    "  raw_mapping = {\n"
    "    raw_identifier: mapping[alias]\n"
    "    for raw_identifier, alias in aliases.items()\n"
    "    if alias in mapping\n"
    "  }\n"
    "  return raw_mapping, diagnostic\n\n\ndef read_otu"
  ),
}
for old, new in replacements.items():
  if old in text:
    text = text.replace(old, new, 1)
  elif new not in text:
    raise RuntimeError(f"Expected replacement anchor was not found: {old!r}")

insertion_anchor = '''  if predictor_replacements != 1:
    raise RuntimeError("Could not enforce the six canonical RDA predictors")

  required_tokens = [
'''
environment_patch = r'''  if predictor_replacements != 1:
    raise RuntimeError("Could not enforce the six canonical RDA predictors")

  environment_block = r\'''def _canonical_position_token(value):
  match = re.search(
    r"(?i)(?<![A-Z0-9])(AM|TIA|TI|VI)[._\\-\\s]*P?0*(\\d+)(?![A-Z0-9])",
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
      if candidate.suffix.casefold() not in {".csv", ".tsv", ".tab", ".txt", ".xlsx", ".xls"}:
        continue
      try:
        if candidate.stat().st_size > 80 * 1024 * 1024:
          continue
      except OSError:
        continue
      candidates.append(candidate)

  diagnostics = []
  for candidate in sorted(set(candidates)):
    tables = {}
    try:
      if candidate.suffix.casefold() in {".xlsx", ".xls"}:
        tables = pd.read_excel(candidate, sheet_name=None)
      else:
        frame = pd.read_csv(candidate, sep=None, engine="python", low_memory=False)
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
        "position_column": None if best_position_column is None else str(best_position_column),
        "predictors": predictors,
      }
      diagnostics.append(diagnostic)
      if best_position_column is None or best_positions is None:
        continue
      if best_overlap != 10 or predictors is None:
        continue

      work = pd.DataFrame({"Position": best_positions})
      for canonical, source_column in predictors.items():
        work[canonical] = pd.to_numeric(frame[source_column], errors="coerce")
      work = work.loc[work["Position"].isin(target_set)].copy()
      environment = work.groupby("Position", as_index=False)[
        ["LOI", "SiO2", "Al2O3", "TOT/S", "Cu", "Pb"]
      ].mean()
      environment = environment.set_index("Position").reindex(target).reset_index()
      if len(environment) != 10:
        continue
      if environment[["LOI", "SiO2", "Al2O3", "TOT/S", "Cu", "Pb"]].notna().sum().min() < 8:
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
        json.dumps(report, indent=2, ensure_ascii=False) + "\\n",
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
    json.dumps(failure_report, indent=2, ensure_ascii=False) + "\\n",
    encoding="utf-8",
  )
  raise RuntimeError(
    "Could not resolve a canonical physicochemical table containing all ten "
    "positions and the six official predictors. See "
    "reports/COMBINED_ENVIRONMENT_SOURCE_20260802.json"
  )


\'''
  text, environment_replacements = re.subn(
    r"(?ms)^def find_environment\\(positions\\):.*?(?=^def rda\\(otu\\):)",
    lambda _match: environment_block,
    text,
    count=1,
  )
  if environment_replacements != 1:
    raise RuntimeError("Could not install the canonical environment resolver")

  required_tokens = [
'''
if insertion_anchor in text:
  text = text.replace(insertion_anchor, environment_patch, 1)
elif "COMBINED_ENVIRONMENT_SOURCE_20260802.json" not in text:
  raise RuntimeError("Could not locate the environment resolver insertion point")

path.write_text(text, encoding="utf-8")
print(
  "Literal replacement safeguards, JGI alias normalization, and canonical "
  "environment-table resolution applied."
)
