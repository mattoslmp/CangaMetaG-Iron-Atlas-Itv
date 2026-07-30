from __future__ import annotations


if 'APP_RELEASE_LABEL_PT =' not in source:
  source = source.replace(
    'APP_RELEASE_LABEL = "30 July 2026"\n',
    'APP_RELEASE_LABEL = "30 July 2026"\nAPP_RELEASE_LABEL_PT = "30 de julho de 2026"\n',
    1,
  )

source = source.replace(
  'Version {APP_VERSION} • {APP_RELEASE_LABEL}</span>',
  'Version {APP_VERSION} • {txt(APP_RELEASE_LABEL_PT, APP_RELEASE_LABEL)}</span>',
)
source = source.replace(
  'Version {APP_VERSION} • {APP_RELEASE_LABEL}</div>',
  'Version {APP_VERSION} • {txt(APP_RELEASE_LABEL_PT, APP_RELEASE_LABEL)}</div>',
)
source = source.replace(
  'st.caption(f"Version {APP_VERSION} — {APP_RELEASE_LABEL}")',
  'st.caption(f"Version {APP_VERSION} — {txt(APP_RELEASE_LABEL_PT, APP_RELEASE_LABEL)}")',
  1,
)
