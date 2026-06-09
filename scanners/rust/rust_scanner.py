"""
Rust Scanner — regex-based
"""
import os, re, sys, json
from dataclasses import dataclass
from typing import List

@dataclass
class EnvReference:
    variable: str; file: str; line: int; method: str
    has_default: bool = False; is_dynamic: bool = False

RE_VAR_STATIC  = re.compile(r'(?:std::)?env::var(?:_os)?\(\s*"([A-Za-z_][A-Za-z0-9_]*)"\s*\)')
RE_VAR_DYNAMIC = re.compile(r'(?:std::)?env::var(?:_os)?\(\s*(?!"[A-Za-z_])')
RE_ENV_MACRO   = re.compile(r'\benv!\(\s*"([A-Za-z_][A-Za-z0-9_]*)"\s*\)')
RE_OPTION_ENV  = re.compile(r'\boption_env!\(\s*"([A-Za-z_][A-Za-z0-9_]*)"\s*\)')
RE_VARS_DYN    = re.compile(r'(?:std::)?env::vars(?:_os)?\(\s*\)')

def scan_file(filepath):
    results = []
    try:
        lines = open(filepath, 'r', encoding='utf-8', errors='ignore').readlines()
    except: return []
    for lineno, line in enumerate(lines, 1):
        s = line.strip()
        if s.startswith('//') or s.startswith('*'): continue
        for m in RE_VAR_STATIC.finditer(line):
            results.append(EnvReference(m.group(1), filepath, lineno, 'env::var()'))
        if RE_VAR_DYNAMIC.search(line) and not RE_VAR_STATIC.search(line) and 'env::var' in line:
            results.append(EnvReference('<dynamic>', filepath, lineno, 'env::var(expr)', is_dynamic=True))
        for m in RE_ENV_MACRO.finditer(line):
            results.append(EnvReference(m.group(1), filepath, lineno, 'env!()'))
        for m in RE_OPTION_ENV.finditer(line):
            results.append(EnvReference(m.group(1), filepath, lineno, 'option_env!()', has_default=True))
        if RE_VARS_DYN.search(line):
            results.append(EnvReference('<dynamic>', filepath, lineno, 'env::vars()', is_dynamic=True))
    return results

def scan_directory(directory):
    results = []
    skip = {'.git','target','node_modules','__pycache__','test','tests','benches','examples'}
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in skip]
        for f in files:
            if f.endswith('.rs'): results.extend(scan_file(os.path.join(root, f)))
    return results

if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else '.'
    refs = scan_directory(path) if os.path.isdir(path) else scan_file(path)
    static = [r for r in refs if not r.is_dynamic]
    dynamic = [r for r in refs if r.is_dynamic]
    print(json.dumps({
        'static':  [{'variable':r.variable,'file':r.file,'line':r.line,'method':r.method,'has_default':r.has_default} for r in static],
        'dynamic': [{'file':r.file,'line':r.line,'method':r.method} for r in dynamic],
    }, indent=2))