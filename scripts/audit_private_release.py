#!/usr/bin/env python3
from __future__ import annotations
import argparse, re, sys
from pathlib import Path
SECRET_NAMES={'.env','secrets.toml','id_rsa','id_ed25519'}
SECRET_SUFFIXES={'.pem','.key','.p12','.pfx'}
TEXT_SUFFIXES={'.py','.md','.txt','.toml','.yaml','.yml','.json','.csv','.tsv','.sh','.bat','.cff','.ini','.cfg'}
PATTERNS=[re.compile(r'(?i)(?:api[_-]?key|client[_-]?secret|private[_-]?key|authorization|bearer)\s*[:=]\s*["\']?[A-Za-z0-9_./+\-=]{16,}'),re.compile(r'gh[pousr]_[A-Za-z0-9]{20,}'),re.compile(r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----')]
PLACEHOLDER_WORDS=('example','replace','placeholder','dummy','test','not available','unavailable')
def main():
  ap=argparse.ArgumentParser(); ap.add_argument('--root',type=Path,default=Path.cwd()); root=ap.parse_args().root.resolve()
  required=['app.py','requirements.txt','src','scripts','data','outputs','tables']; missing=[p for p in required if not (root/p).exists()]
  if missing: print('Missing required paths:',', '.join(missing),file=sys.stderr); return 2
  bad_names=[]; bad_content=[]; oversized=[]
  for path in root.rglob('*'):
    if not path.is_file() or '.git' in path.parts: continue
    rel=path.relative_to(root); low=path.name.lower(); size=path.stat().st_size
    if (low in SECRET_NAMES or path.suffix.lower() in SECRET_SUFFIXES) and str(rel)!='.streamlit/secrets.example.toml': bad_names.append(str(rel))
    if size>=100*1024*1024: oversized.append((size,str(rel)))
    if path.suffix.lower() in TEXT_SUFFIXES and size<=5*1024*1024:
      text=path.read_text(encoding='utf-8',errors='ignore')
      for lineno,line in enumerate(text.splitlines(),1):
        if any(p.search(line) for p in PATTERNS) and not any(w in line.lower() for w in PLACEHOLDER_WORDS):
          if re.search(r'os\.environ|getenv|st\.text_input|runtime_setting|SECRET_NAMES|PATTERNS',line): continue
          bad_content.append(f'{rel}:{lineno}:{line[:160]}')
  if bad_names: print('Potential secret files:',*bad_names,sep='\n  ',file=sys.stderr)
  if bad_content: print('Potential embedded credentials:',*bad_content[:50],sep='\n  ',file=sys.stderr)
  if oversized:
    print('Ordinary files >=100 MiB:',file=sys.stderr)
    for size,rel in oversized: print(f'  {size}\t{rel}',file=sys.stderr)
  if bad_names or bad_content or oversized: return 3
  print('PRIVATE_RELEASE_AUDIT_PASS'); return 0
if __name__=='__main__': raise SystemExit(main())
