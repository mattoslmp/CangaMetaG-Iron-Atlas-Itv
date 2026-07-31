from __future__ import annotations

"""Final visitor-map placement without redundant author credit."""

MARKER = "CANGAMETAG_VISITOR_FOOTER_FINAL_V2 = 1"

if MARKER not in source:
  # Keep one global visitor map at the true bottom of the application. These
  # inner calls caused the same caption/map to be rendered twice on some pages.
  source = source.replace(
    '    visitor_counter_public_footer("visitor_public_only")\n',
    "",
  )
  source = source.replace(
    '  visitor_counter_public_footer("code_reproducibility_counter")\n',
    "",
  )

  anchor = "def visitor_counter_compact("
  wrapper = r'''
_APP_ORIGINAL_VISITOR_COUNTER_PUBLIC_FOOTER_FINAL = visitor_counter_public_footer


def visitor_counter_public_footer(key: str = "public_footer"):
  _APP_ORIGINAL_VISITOR_COUNTER_PUBLIC_FOOTER_FINAL(key)
  try:
    location = dict(st.session_state.get("_visitor_last_location", {}) or {})
  except Exception:
    location = {}
  location_bits = [
    str(location.get("city", "") or "").strip(),
    str(location.get("region", "") or "").strip(),
    str(location.get("country_name", "") or location.get("country_code", "") or "").strip(),
  ]
  location_bits = [value for value in location_bits if value]
  if location_bits:
    st.caption(txt(
      "Localização aproximada registrada para esta sessão: " + ", ".join(location_bits) + ".",
      "Approximate location recorded for this session: " + ", ".join(location_bits) + ".",
    ))
'''
  if anchor in source and "_APP_ORIGINAL_VISITOR_COUNTER_PUBLIC_FOOTER_FINAL" not in source:
    source = source.replace(anchor, wrapper + "\n\n" + anchor, 1)

  source += f"\n\n{MARKER}\n"
