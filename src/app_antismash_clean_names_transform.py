from __future__ import annotations


replacements = [
  (
    'file_name=gbk_path.name, mime="text/plain", key=f"download_antismash_gbk_{selected_run_label}"',
    'file_name=str(run.get("gbk_download_name") or gbk_path.name), mime="text/plain", key=f"download_antismash_gbk_{selected_run_label}"',
  ),
  (
    'file_name=fasta_path.name, mime="text/plain", key=f"download_antismash_fasta_{selected_run_label}"',
    'file_name=str(run.get("fasta_download_name") or fasta_path.name), mime="text/plain", key=f"download_antismash_fasta_{selected_run_label}"',
  ),
  (
    '"Os MAGs 2, 5, 20, 32, 44, 47 e 49 são marcados explicitamente como sem clusters BGC identificados no conjunto antiSMASH final. Duplicatas enviadas para o mesmo MAG/bin foram resolvidas mantendo o arquivo selecionado no manifesto, e os nomes originais permanecem rastreáveis.",\n       "MAGs 2, 5, 20, 32, 44, 47 and 49 are explicitly marked as having no BGC clusters identified in the final antiSMASH set. Duplicate uploads for the same MAG/bin were resolved by retaining the selected archive in the manifest, while original names remain traceable."',
    '"Os MAGs 2, 5, 20, 32, 44, 47 e 49 são marcados explicitamente como sem clusters BGC identificados no conjunto antiSMASH final. Duplicatas enviadas para o mesmo MAG/bin foram resolvidas mantendo o arquivo selecionado no manifesto. O marcador técnico de reparo foi ocultado apenas nos nomes públicos; os arquivos internos de cada execução permanecem intactos.",\n       "MAGs 2, 5, 20, 32, 44, 47 and 49 are explicitly marked as having no BGC clusters identified in the final antiSMASH set. Duplicate uploads for the same MAG/bin were resolved by retaining the selected archive in the manifest. The technical repair marker is hidden only from public names; every internal run file remains intact."',
  ),
]

for old, new in replacements:
  if old not in source:
    raise RuntimeError(
      "Could not locate the expected antiSMASH public-name block: " + old[:120]
    )
  source = source.replace(old, new, 1)
