from __future__ import annotations


# Final safeguard: the Article Atlas overview must not render the static
# Figure1_sampling_map image, its Study area and sampling design heading, or its
# caption. The interactive map that starts at interactive_study_meta is kept.
static_start = (
  '  figure1_sampling_path = BASE_DIR / "outputs" / "final_publication_figures" '
  '/ "Figure1_sampling_map.png"\n'
)
interactive_start = '  interactive_study_meta = taxonomy_samples_metadata()\n'

start = source.find(static_start)
if start >= 0:
  end = source.find(interactive_start, start)
  if end >= 0:
    source = source[:start] + source[end:]
  else:
    raise RuntimeError(
      "Static study-area map was found, but the interactive-map boundary was missing"
    )

# Remove any residual standalone heading/caption variants without affecting the
# interactive map or the canonical figure in the Final Figures section.
residual_blocks = [
  '  st.markdown("### " + txt("Área de estudo e desenho amostral", "Study area and sampling design"))\n',
  '''  st.caption(txt(
    "Área de estudo e desenho amostral. Localização das lagoas lateríticas amazônicas Amendoim, Violão, Três Irmãs e Três Irmãs Adjacent. O estudo inclui 20 metagenomas de sedimento, compreendendo 10 amostras do período seco e 10 do período chuvoso.",
    "Study area and sampling design. Location of the Amazonian lateritic lakes Amendoim, Violão, Três Irmãs and Três Irmãs Adjacent. The study includes 20 sediment metagenomes, comprising 10 dry-season and 10 rainy-season samples."
  ))
''',
]
for block in residual_blocks:
  source = source.replace(block, "")
