from __future__ import annotations

import re


# app_public_release_v1_transform removes every visitor counter call. When the
# old header wrapped the compact counter in an admin-only ``if`` block, remove
# that now-empty wrapper as well so the generated application remains valid.
source = re.sub(
  r'\n    if is_admin_authenticated\(\):\n(?=\n*def overview_tab\(\):)',
  '\n',
  source,
  count=1,
)
