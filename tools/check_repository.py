#!/usr/bin/env python3
"""Conservative local publication checks; never sends repository data anywhere."""
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
EXCLUDED={'.git','__pycache__','.test-output','.pytest_cache','.venv'}
PRIVATE_NAMES={'auth.json','session.json','Xauthority','.env','.git-credentials','id_rsa','id_ed25519'}
PATTERNS=[('token-like credential',re.compile(r'\b(?:sk-[A-Za-z0-9_-]{24,}|ghp_[A-Za-z0-9]{24,}|github_pat_[A-Za-z0-9_]{24,})\b')),
          ('private-key header',re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'))]

def scan_text(relative,text):
    findings=[]
    for label,pattern in PATTERNS:
        if pattern.search(text):findings.append({'file':str(relative),'issue':label})
    # Runtime scripts must never contain a publisher's absolute home directory.
    if str(relative).replace('\\','/').startswith(('linux/','windows/')) and Path(relative).suffix.lower() not in ('.md','.json'):
        if re.search(r'/home/[A-Za-z0-9_.-]+|[A-Z]:\\\\?Users\\\\?[A-Za-z0-9_.-]+',text):
            findings.append({'file':str(relative),'issue':'hardcoded user home in runtime'})
    return findings

def main():
    findings=[];count=0
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file() or any(part in EXCLUDED for part in path.relative_to(ROOT).parts):continue
        rel=path.relative_to(ROOT);count+=1
        if path.name in PRIVATE_NAMES or path.suffix.lower() in ('.key','.p12','.pfx'):
            findings.append({'file':str(rel),'issue':'private runtime/credential file must not be published'})
        if path.suffix.lower() in ('.png','.jpg','.jpeg','.ico','.zip'):continue
        try:text=path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            findings.append({'file':str(rel),'issue':'unexpected non-text file'});continue
        findings.extend(scan_text(rel,text))
    print(json.dumps({'files_checked':count,'passed':not findings,'findings':findings},indent=2))
    return 1 if findings else 0

if __name__=='__main__':raise SystemExit(main())
