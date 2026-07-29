from pathlib import Path


app_path = Path("app.py")
text = app_path.read_text(encoding="utf-8")

old = '''    st.info(txt(
      "Nenhum index.html do antiSMASH foi encontrado. Extraia cada ZIP em uma pasta própria dentro de data/kegg_modules/mags/gbk_antismash/.",
      "No antiSMASH index.html was found. Extract each ZIP into its own folder under data/kegg_modules/mags/gbk_antismash/."
    ))
'''
new = '''    st.info(txt(
      "Nenhum resultado antiSMASH empacotado está disponível para esta seleção.",
      "No packaged antiSMASH result is available for this selection."
    ))
'''

if old not in text:
  raise RuntimeError("Expected antiSMASH no-results message was not found.")

app_path.write_text(text.replace(old, new, 1), encoding="utf-8")
