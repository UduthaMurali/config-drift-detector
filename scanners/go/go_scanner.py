"""
Go Scanner — regex-based
Detects environment variable references in Go source files.
"""
import os, re, sys, json
from dataclasses import dataclass
from typing import List

@dataclass
class EnvReference:
    variable: str; file: str; line: int; method: str
    has_default: bool = False; is_dynamic: bool = False

RE_GETENV_STATIC  = re.compile(r'os\.Getenv\(\s*"([A-Za-z_][A-Za-z0-9_]*)"\s*\)')
RE_GETENV_DYNAMIC = re.compile(r'os\.Getenv\(\s*(?!"[A-Za-z_])')
RE_LOOKUP_STATIC  = re.compile(r'os\.LookupEnv\(\s*"([A-Za-z_][A-Za-z0-9_]*)"\s*\)')
RE_LOOKUP_DYNAMIC = re.compile(r'os\.LookupEnv\(\s*(?!"[A-Za-z_])')
RE_EXPAND_ENV     = re.compile(r'os\.ExpandEnv\(\s*"([^"]*)"\s*\)')
RE_DOLLAR_VAR     = re.compile(r'\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?')

def scan_file(filepath):
    results = []
    try:
        lines = open(filepath, 'r', encoding='utf-8', errors='ignore').readlines()
    except: return []
    for lineno, line in enumerate(lines, 1):
        if line.strip().startswith('//'): continue
        for m in RE_GETENV_STATIC.finditer(line):
            results.append(EnvReference(m.group(1), filepath, lineno, 'os.Getenv()'))
        if RE_GETENV_DYNAMIC.search(line) and not RE_GETENV_STATIC.search(line) and 'os.Getenv' in line:
            results.append(EnvReference('<dynamic>', filepath, lineno, 'os.Getenv(expr)', is_dynamic=True))
        for m in RE_LOOKUP_STATIC.finditer(line):
            results.append(EnvReference(m.group(1), filepath, lineno, 'os.LookupEnv()'))
        if RE_LOOKUP_DYNAMIC.search(line) and not RE_LOOKUP_STATIC.search(line) and 'os.LookupEnv' in line:
            results.append(EnvReference('<dynamic>', filepath, lineno, 'os.LookupEnv(expr)', is_dynamic=True))
        for m in RE_EXPAND_ENV.finditer(line):
            for v in RE_DOLLAR_VAR.finditer(m.group(1)):
                results.append(EnvReference(v.group(1), filepath, lineno, 'os.ExpandEnv()'))
    return results

def scan_directory(directory):
    results = []
    skip = {'.git','vendor','testdata','test','tests','__pycache__','node_modules'}
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in skip]
        for f in files:
            if f.endswith('.go'): results.extend(scan_file(os.path.join(root, f)))
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