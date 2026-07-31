from __future__ import annotations

"""Keep the global publication CSS block as a plain string literal.

Late source transforms must never turn the first application-wide CSS block
into an f-string because CSS braces would then be evaluated as Python
expressions (for example ``gap:.45rem``). This guard runs after localization and
repairs only the uniquely identified publication-style CSS block.
"""

import re


MARKER = "CANGAMETAG_CSS_LITERAL_GUARD_V1 = 1"

if MARKER not in source:
  pattern = re.compile(
    r"(st\.markdown\(\s*)(?:f|fr|rf)(?P<quote>\"\"\"|''')"
    r"(?P<body>\s*<style>\s*/\* Publication-style interface)",
    flags=re.IGNORECASE,
  )
  source, repaired = pattern.subn(
    lambda match: (
      match.group(1)
      + match.group("quote")
      + match.group("body")
    ),
    source,
    count=1,
  )

  # The block may already be a correct ordinary string; that is also valid.
  ordinary = re.search(
    r"st\.markdown\(\s*(?:\"\"\"|''')\s*<style>\s*"
    r"/\* Publication-style interface",
    source,
    flags=re.IGNORECASE,
  )
  if ordinary is None:
    raise RuntimeError(
      "The publication CSS block could not be confirmed as a plain string literal."
    )

  source += f"\n\n{MARKER}\n"
