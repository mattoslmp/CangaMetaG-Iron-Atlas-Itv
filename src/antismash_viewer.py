from __future__ import annotations

from io import BytesIO
from pathlib import Path
import base64
import mimetypes
import re
import zipfile
import pandas as pd

from ._helpers import BASE_DIR, zip_directory


def discover_antismash_runs() -> list[dict]:
  roots = [BASE_DIR / 'data' / 'kegg_modules' / 'mags' / 'gbk_antismash', BASE_DIR / 'data' / 'antismash', BASE_DIR / 'outputs' / 'antismash']
  runs = []
  for root in roots:
    if not root.exists():
      continue
    for index in sorted(root.rglob('index.html')):
      run_dir = index.parent
      original = run_dir.name
      match = re.search(r'(?:bin[._-]?|MAG[._-]?)(\d+)', original, flags=re.I)
      mag_id = f'MAG{int(match.group(1))}' if match else ''
      gbks = sorted(run_dir.rglob('*.gbk'))
      fastas = sorted([q for q in run_dir.rglob('*') if q.is_file() and q.suffix.lower() in {'.fa', '.fasta', '.fna'}])
      runs.append({
        'run_name': f'{mag_id} — {original}' if mag_id else original,
        'name': original,
        'original_run_name': original,
        'mag_id': mag_id,
        'run_dir': str(run_dir),
        'index_html': str(index),
        'regions': len([q for q in gbks if 'region' in q.name.lower()]),
        'gbk_path': str(gbks[0]) if gbks else '',
        'fasta_path': str(fastas[0]) if fastas else '',
      })
  return runs


def antismash_inventory() -> pd.DataFrame:
  return pd.DataFrame(discover_antismash_runs())


def antismash_run_zip_bytes(run_dir: Path | str) -> bytes:
  return zip_directory(Path(run_dir))


def self_contained_antismash_html(run_dir: Path) -> str:
  run_dir = Path(run_dir)
  index = run_dir / 'index.html'
  if not index.exists():
    return '<html><body><p>antiSMASH index.html not found.</p></body></html>'
  html = index.read_text(encoding='utf-8', errors='replace')
  # Inline local CSS/JS/image assets to make the viewer portable.
  pattern = re.compile(r'(?P<prefix>(?:src|href)=["\'])(?P<path>[^"\']+)(?P<suffix>["\'])')
  def replace(match):
    relative = match.group('path')
    if relative.startswith(('http://', 'https://', 'data:', '#')):
      return match.group(0)
    asset = (run_dir / relative).resolve()
    try:
      asset.relative_to(run_dir.resolve())
    except Exception:
      return match.group(0)
    if not asset.is_file():
      return match.group(0)
    mime = mimetypes.guess_type(asset.name)[0] or 'application/octet-stream'
    encoded = base64.b64encode(asset.read_bytes()).decode('ascii')
    return f"{match.group('prefix')}data:{mime};base64,{encoded}{match.group('suffix')}"
  return pattern.sub(replace, html)
