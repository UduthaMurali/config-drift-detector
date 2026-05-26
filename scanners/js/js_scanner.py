"""
JavaScript / TypeScript Scanner — regex-based
"""
import os, re, sys, json
from dataclasses import dataclass
from typing import List

@dataclass
class EnvReference:
    variable: str; file: str; line: int; method: str
    has_default: bool = False; is_dynamic: bool = False

RE_DOT_ACCESS     = re.compile(r'process\.env\.([A-Za-z_][A-Za-z0-9_]*)\b')
RE_BRACKET_STATIC = re.compile(r'process\.env\[\s*["\`\'"]([A-Za-z_][A-Za-z0-9_]*)["\`\'"]\s*\]')
RE_BRACKET_DYN    = re.compile(r'process\.env\[\s*(?!["\`\'])[A-Za-z_$]')
RE_VITE_ENV       = re.compile(r'import\.meta\.env\.([A-Za-z_][A-Za-z0-9_]*)\b')
RE_NUXT_ENV       = re.compile(r'\$env\.([A-Za-z_][A-Za-z0-9_]*)\b')

def scan_file(filepath):
    results = []
    try:
        lines = open(filepath, 'r', encoding='utf-8', errors='ignore').readlines()
    except: return []
    for lineno, line in enumerate(lines, 1):
        s = line.strip()
        if s.startswith('//') or s.startswith('*'): continue
        for m in RE_DOT_ACCESS.finditer(line):
            results.append(EnvReference(m.group(1), filepath, lineno, 'process.env.KEY'))
        for m in RE_BRACKET_STATIC.finditer(line):
            results.append(EnvReference(m.group(1), filepath, lineno, 'process.env["KEY"]'))
        if RE_BRACKET_DYN.search(line):
            results.append(EnvReference('<dynamic>', filepath, lineno, 'process.env[expr]', is_dynamic=True))
        for m in RE_VITE_ENV.finditer(line):
            if m.group(1) not in ('MODE','BASE_URL','DEV','PROD','SSR'):
                results.append(EnvReference(m.group(1), filepath, lineno, 'import.meta.env.KEY'))
        for m in RE_NUXT_ENV.finditer(line):
            results.append(EnvReference(m.group(1), filepath, lineno, '$env.KEY'))
    return results

def scan_directory(directory):
    results = []
    EXTS = ('.js','.ts','.jsx','.tsx','.mjs','.cjs')
    skip = {'.git','node_modules','dist','build','.next','.nuxt','coverage','__pycache__','vendor'}
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in skip]
        for f in files:
            if any(f.endswith(e) for e in EXTS): results.extend(scan_file(os.path.join(root, f)))
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