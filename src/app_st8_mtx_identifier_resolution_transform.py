from __future__ import annotations

"""Install identifier-aware ST8 metatranscriptome column resolution.

This layer runs after the final ST8 transform. Existing scientific matrices,
values, row order, and display logic are preserved; only metadata-to-column
resolution is replaced.
"""

MARKER = "CANGAMETAG_ST8_MTX_IDENTIFIER_RESOLUTION_V1 = 1"


if MARKER not in source:
  candidate = source
  dispatch_anchor = "page_handler = page_handlers.get(selected_page)"
  runtime_layer = '''from src.st8_mtx_identifier_resolution import (
  resolve_metatranscriptome_columns as _resolve_st8_mtx_columns_by_identifier,
)


# Functions installed by the preceding ST8 layer resolve this global at call
# time, so replacing it here fixes both the KO and KEGG interactive panels.
_resolve_final_st8_mtx_columns = _resolve_st8_mtx_columns_by_identifier


def _st8_identifier_runtime_resolver(metadata, numeric_columns, data_columns):
  # Excel/CSV dtype inference must not decide whether a sample identifier exists.
  del numeric_columns
  available = list(dict.fromkeys(str(value) for value in data_columns))
  return _resolve_st8_mtx_columns_by_identifier(
    metadata,
    available,
    expected_count=12,
  )


_final_st8_runtime_module.metatranscriptome_matrix_columns = (
  _st8_identifier_runtime_resolver
)


'''
  if dispatch_anchor not in candidate:
    raise RuntimeError("Could not install ST8 MTX identifier resolver")
  candidate = candidate.replace(dispatch_anchor, runtime_layer + dispatch_anchor, 1)
  candidate += f"\n\n{MARKER}\n"
  compile(candidate, "app_core_after_st8_mtx_identifier_resolution.py", "exec")
  source = candidate
