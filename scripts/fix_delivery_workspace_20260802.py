#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_generated_combined_script() -> dict[str, object]:
  path = ROOT / "scripts" / "final_publication_figures" / "03_generate_combined_community_figures.py"
  text = path.read_text(encoding="utf-8")
  text = text.replace(
    'ax.boxplot(groups, labels=["AM","TIA","TI","VI"], showfliers=False)',
    'ax.boxplot(groups, tick_labels=["AM","TIA","TI","VI"], showfliers=False)',
  )

  read_otu_block = r'''def _canonical_sample_tokens(text):
  pattern = re.compile(
    r"(?i)(?<![A-Z0-9])(AM|TIA|TI|VI)[._\-\s]*P?0*(\d+)[._\-\s]*(D|R)(?![A-Z0-9])"
  )
  return {
    f"{match.group(1).upper()}.P{int(match.group(2))}.{match.group(3).upper()}"
    for match in pattern.finditer(str(text))
  }


def _discover_jgi_sample_map(jgi_ids):
  from collections import Counter
  import zipfile

  identifiers = [str(value) for value in jgi_ids]
  identifier_set = set(identifiers)
  hits = {identifier: Counter() for identifier in identifiers}
  text_suffixes = {
    ".csv", ".tsv", ".txt", ".tab", ".json", ".yaml", ".yml",
    ".md", ".py", ".r", ".R", ".xml",
  }
  excluded = {
    (ROOT / "data" / "resultado.cds.otu.tab").resolve(),
    Path(__file__).resolve(),
  }

  def register(fragment):
    fragment = str(fragment)
    present = [identifier for identifier in identifiers if identifier in fragment]
    if not present:
      return
    tokens = _canonical_sample_tokens(fragment)
    if len(tokens) != 1:
      return
    token = next(iter(tokens))
    for identifier in present:
      hits[identifier][token] += 1

  roots = [
    ROOT / "data",
    ROOT / "tables",
    ROOT / "metadata",
    ROOT / "reproducibility",
    ROOT / "outputs" / "final_publication_source_tables",
    ROOT / "outputs" / "final_publication_audit_tables",
    ROOT / "reports",
    ROOT / "scripts",
    ROOT / "src",
  ]
  candidates = []
  for base in roots:
    if not base.exists():
      continue
    candidates.extend(path for path in base.rglob("*") if path.is_file())

  for candidate in sorted(set(candidates)):
    try:
      if candidate.resolve() in excluded or candidate.stat().st_size > 60 * 1024 * 1024:
        continue
    except OSError:
      continue
    suffix = candidate.suffix
    try:
      if suffix in text_suffixes:
        content = candidate.read_text(encoding="utf-8", errors="ignore")
        if not identifier_set.intersection(
          identifier for identifier in identifiers if identifier in content
        ):
          continue
        lines = content.splitlines()
        for index, line in enumerate(lines):
          if not any(identifier in line for identifier in identifiers):
            continue
          register(line)
          start = max(0, index - 1)
          end = min(len(lines), index + 2)
          register(" ".join(lines[start:end]))
      elif suffix.lower() in {".xlsx", ".xls"}:
        sheets = pd.read_excel(candidate, sheet_name=None, dtype=str)
        for frame in sheets.values():
          if frame.empty:
            continue
          for row in frame.fillna("").astype(str).itertuples(index=False, name=None):
            register(" | ".join(row))
      elif suffix.lower() == ".docx":
        with zipfile.ZipFile(candidate) as archive:
          for member in archive.namelist():
            if not member.endswith(".xml"):
              continue
            raw = archive.read(member).decode("utf-8", errors="ignore")
            for identifier in identifiers:
              start = 0
              while True:
                position = raw.find(identifier, start)
                if position < 0:
                  break
                register(raw[max(0, position - 500): position + 500])
                start = position + len(identifier)
    except Exception:
      continue

  mapping = {}
  conflicts = {}
  for identifier, counter in hits.items():
    if not counter:
      continue
    ranked = counter.most_common()
    best_count = ranked[0][1]
    best = [token for token, count in ranked if count == best_count]
    if len(best) == 1:
      mapping[identifier] = best[0]
    else:
      conflicts[identifier] = ranked

  reverse = {}
  duplicate_names = {}
  for identifier, sample in mapping.items():
    if sample in reverse:
      duplicate_names.setdefault(sample, [reverse[sample]]).append(identifier)
    else:
      reverse[sample] = identifier
  if duplicate_names:
    for sample, duplicate_ids in duplicate_names.items():
      for identifier in duplicate_ids:
        mapping.pop(identifier, None)

  diagnostic = {
    "requested_jgi_ids": identifiers,
    "resolved_mapping": mapping,
    "candidate_counts": {
      identifier: dict(counter)
      for identifier, counter in hits.items()
      if counter
    },
    "conflicts": conflicts,
    "duplicate_sample_names": duplicate_names,
  }
  report_path = REPORTS / "COMBINED_SAMPLE_ID_MAPPING_20260802.json"
  report_path.write_text(
    json.dumps(diagnostic, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
  )
  return mapping, diagnostic


def read_otu():
  path = ROOT / "data" / "resultado.cds.otu.tab"
  if not path.is_file():
    raise FileNotFoundError(path)
  frame = pd.read_csv(path, sep="\t", low_memory=False)
  jgi_columns = [
    column for column in frame.columns
    if re.fullmatch(r"(?i)Ga\d+", str(column).strip())
  ]
  if len(jgi_columns) != 20:
    numeric_candidates = []
    for column in frame.columns:
      values = pd.to_numeric(frame[column], errors="coerce")
      if values.notna().mean() > 0.95 and float(values.fillna(0).sum()) > 0:
        numeric_candidates.append(column)
    jgi_columns = [
      column for column in numeric_candidates
      if re.fullmatch(r"(?i)Ga\d+", str(column).strip())
    ] or numeric_candidates[:20]
  if len(jgi_columns) != 20:
    raise RuntimeError(
      f"Expected exactly 20 metagenome count columns, found {len(jgi_columns)}: {jgi_columns}"
    )

  mapping, diagnostic = _discover_jgi_sample_map(jgi_columns)
  missing = [str(column) for column in jgi_columns if str(column) not in mapping]
  if missing:
    raise RuntimeError(
      "Could not resolve the canonical sample names for JGI identifiers: "
      f"{missing}. See reports/COMBINED_SAMPLE_ID_MAPPING_20260802.json"
    )

  matrix = frame[jgi_columns].apply(pd.to_numeric, errors="coerce").fillna(0.0).clip(lower=0)
  matrix.columns = [mapping[str(column)] for column in jgi_columns]
  if matrix.columns.nunique() != 20:
    raise RuntimeError(f"Resolved sample names are not unique: {matrix.columns.tolist()}")
  metadata = sample_meta(matrix.columns)
  position_counts = metadata.groupby("Position")["Season"].agg(list)
  invalid_positions = {
    position: seasons
    for position, seasons in position_counts.items()
    if sorted(seasons) != ["Dry", "Rainy"]
  }
  if len(position_counts) != 10 or invalid_positions:
    raise RuntimeError(
      "The canonical mapping must represent ten positions, each with Dry and Rainy samples; "
      f"positions={len(position_counts)}, invalid={invalid_positions}"
    )
  return matrix


'''
  text, replacements = re.subn(
    r"(?ms)^def read_otu\(\):.*?(?=^def savefig)",
    read_otu_block,
    text,
    count=1,
  )
  if replacements != 1:
    raise RuntimeError("Could not replace the combined-analysis sample reader")

  predictor_patch = '''  env=env.fillna(env.median(numeric_only=True)).select_dtypes(include=[np.number])
  expected_predictors = ["loi", "sio2", "al2o3", "tots", "cu", "pb"]
  normalized_columns = {
    column: re.sub(r"[^a-z0-9]+", "", str(column).casefold())
    for column in env.columns
  }
  selected_predictors = []
  for expected in expected_predictors:
    matches = [
      column for column, normalized in normalized_columns.items()
      if normalized == expected or normalized.startswith(expected)
    ]
    if not matches:
      raise RuntimeError(
        f"Combined RDA is missing canonical predictor {expected}; available={list(env.columns)}"
      )
    selected_predictors.append(matches[0])
  env = env[selected_predictors]
  X=StandardScaler().fit_transform(env.to_numpy(float))'''
  text, predictor_replacements = re.subn(
    r'  env=env\.fillna\(env\.median\(numeric_only=True\)\)\.select_dtypes\(include=\[np\.number\]\)\n  X=StandardScaler\(\)\.fit_transform\(env\.to_numpy\(float\)\)',
    predictor_patch,
    text,
    count=1,
  )
  if predictor_replacements != 1:
    raise RuntimeError("Could not enforce the six canonical RDA predictors")

  required_tokens = [
    "COMBINED_SAMPLE_ID_MAPPING_20260802.json",
    "ten positions, each with Dry and Rainy samples",
    'expected_predictors = ["loi", "sio2", "al2o3", "tots", "cu", "pb"]',
    "tick_labels=",
  ]
  missing_tokens = [token for token in required_tokens if token not in text]
  if missing_tokens:
    raise RuntimeError(f"Combined generator patch is incomplete: {missing_tokens}")
  path.write_text(text, encoding="utf-8")
  return {
    "path": str(path.relative_to(ROOT)),
    "matplotlib_tick_labels": True,
    "canonical_sample_mapping": "dynamic evidence-backed JGI ID resolution",
    "required_sample_count": 20,
    "required_position_count": 10,
    "canonical_rda_predictors": ["LOI", "SiO2", "Al2O3", "TOT/S", "Cu", "Pb"],
  }


def patch_existing_percentage_label_transform() -> dict[str, object]:
  path = ROOT / "src" / "app_other_taxa_percentage_label_transform.py"
  text = path.read_text(encoding="utf-8")
  text = text.replace("declared 5% cutoff", "declared 1% cutoff")
  text = text.replace(
    "_OTHER_TAXA_THRESHOLD_PERCENT = 5.0",
    "_OTHER_TAXA_THRESHOLD_PERCENT = 1.0",
  )
  text = text.replace(
    "5% denotes the per-taxon cutoff",
    "1% denotes the per-taxon cutoff",
  )
  path.write_text(text, encoding="utf-8")
  if "_OTHER_TAXA_THRESHOLD_PERCENT = 1.0" not in text:
    raise RuntimeError("Could not update the existing aggregate-label threshold")
  return {
    "path": str(path.relative_to(ROOT)),
    "threshold_percent": 1.0,
  }


def compile_app_transform_chain() -> dict[str, object]:
  app_path = ROOT / "app.py"
  wrapper = app_path.read_text(encoding="utf-8")
  entry = '  Path(__file__).with_name("src") / "app_genus_lt1_transform.py",\n'
  if "app_genus_lt1_transform.py" not in wrapper:
    anchor = "]\n\n\ndef _compile_final_source"
    if anchor not in wrapper:
      raise RuntimeError("Could not locate the end of the app transform list")
    wrapper = wrapper.replace(anchor, entry + anchor, 1)
    app_path.write_text(wrapper, encoding="utf-8")

  source = (ROOT / "app_core.py").read_text(encoding="utf-8")
  transform_files = []
  marker = 'Path(__file__).with_name("src") / "'
  for line in wrapper.splitlines():
    if marker not in line:
      continue
    name = line.split(marker, 1)[1].split('"', 1)[0]
    transform_files.append(ROOT / "src" / name)
  for transform in transform_files:
    namespace = runpy.run_path(str(transform), init_globals={"source": source})
    source = namespace["source"]
  compile(source, str(ROOT / "app_core.py"), "exec")
  required = [
    "CANGAMETAG_GENUS_LT1_CANONICAL_V1",
    "_CANGAMETAG_GENUS_OTHER_THRESHOLD_PERCENT = 1.0",
    "Other taxa (<1% each)",
  ]
  missing = [token for token in required if token not in source]
  if missing:
    raise RuntimeError(f"Final app source lacks genus <1% contract: {missing}")
  return {
    "path": "app.py",
    "transform_count": len(transform_files),
    "last_transform": str(transform_files[-1].relative_to(ROOT)),
    "compiled_final_source": True,
    "contract_tokens": required,
  }


def main() -> int:
  report = {
    "combined_generator": patch_generated_combined_script(),
    "existing_label_transform": patch_existing_percentage_label_transform(),
    "app": compile_app_transform_chain(),
  }
  report_path = ROOT / "reports" / "DELIVERY_20260802_WORKSPACE_FIX_REPORT.json"
  report_path.parent.mkdir(parents=True, exist_ok=True)
  report_path.write_text(
    json.dumps(report, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
  )
  print(json.dumps(report, indent=2, ensure_ascii=False))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
