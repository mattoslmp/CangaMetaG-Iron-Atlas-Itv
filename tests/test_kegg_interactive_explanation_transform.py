from __future__ import annotations

from pathlib import Path
import runpy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRANSFORM = PROJECT_ROOT / "src" / "app_kegg_interactive_explanation_transform.py"

SOURCE = '''def _display_kegg_completeness_panel(key_prefix):
    st.markdown("##### KEGG module completeness explorer")
    return key_prefix
'''


def apply_transform(source: str) -> str:
  namespace = runpy.run_path(str(TRANSFORM), init_globals={"source": source})
  return str(namespace["source"])


def test_transform_compiles_and_explains_interactive_results() -> None:
  transformed = apply_transform(SOURCE)
  compile(transformed, "generated_kegg_explorer.py", "exec")
  required = [
    "Interactive KEGG module completeness explorer",
    "results not shown in the supplementary figure",
    "Selecting Full matrix makes every module and every original state available",
    "no value is recalculated, imputed or replaced",
  ]
  missing = [value for value in required if value not in transformed]
  assert not missing, missing


def test_transform_maps_figures_to_supplementary_tables() -> None:
  transformed = apply_transform(SOURCE)
  required = [
    '"kegg_mags"',
    '"figure": "37"',
    "Supplementary Table 7",
    '"kegg_lagoon_metagenomes"',
    '"figure": "38"',
    '"kegg_external_iron_rich_environmental_group"',
    '"figure": "40"',
    '"kegg_combined_lagoon_external_original"',
    '"figure": "67"',
    "Supplementary Table 8",
    "Supplementary Table 14",
  ]
  missing = [value for value in required if value not in transformed]
  assert not missing, missing


def test_transform_is_idempotent() -> None:
  once = apply_transform(SOURCE)
  twice = apply_transform(once)
  assert twice == once
