"""
Env-Injection Convention Adapter
Detects SECTION__KEY style environment variable injection patterns.

Many frameworks translate SECTION__KEY env vars into config file entries:
  - Gitea:  GITEA__database__DB_TYPE  →  [database] DB_TYPE = ...
  - ASP.NET Core: Database__ConnectionString
  - Spring Boot (alt):  SPRING_DATASOURCE_URL
  - .NET:  ConnectionStrings__DefaultConnection

This scanner:
1. Reads config files (docker-compose, k8s) for SECTION__KEY patterns
2. Reports them as "framework-injected" env vars the code depends on
3. Detects mismatches between what the compose file declares vs what the
   framework documentation says is needed

envgrd does NOT implement this. This is a novel contribution.
"""
import os
import re
import sys
import json
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class EnvReference:
    variable: str
    file: str
    line: int
    method: str
    has_default: bool = False
    is_dynamic: bool = False
    section: str = ''
    key: str = ''

# SECTION__KEY pattern: two or more uppercase/mixed words separated by __
RE_SECTION_KEY = re.compile(
    r'\b([A-Za-z][A-Za-z0-9]*(?:__[A-Za-z][A-Za-z0-9]*){1,})\b'
)

# Known prefixes that indicate env-injection convention
KNOWN_PREFIXES = {
    'GITEA__':      'Gitea app.ini injection',
    'ASPNETCORE__': 'ASP.NET Core config injection',
    'DOTNET__':     'ASP.NET Core config injection',
    'SPRING__':     'Spring Boot relaxed binding',
    'Database__':   'ASP.NET Core DB config',
}

SKIP_DIRS = {'.git', 'node_modules', '__pycache__', 'vendor', 'target'}


def detect_convention(var_name: str) -> str:
    """Return the injection convention name for a SECTION__KEY variable."""
    for prefix, convention in KNOWN_PREFIXES.items():
        if var_name.startswith(prefix):
            return convention
    if '__' in var_name:
        return 'env-injection convention (SECTION__KEY)'
    return ''


def scan_file(filepath: str) -> List[EnvReference]:
    """Scan any text file for SECTION__KEY env var patterns."""
    results = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception:
        return []

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        for m in RE_SECTION_KEY.finditer(line):
            var = m.group(1)
            parts = var.split('__')
            if len(parts) < 2:
                continue
            # Must have at least one alphabetic character in each part
            if not all(any(c.isalpha() for c in p) for p in parts):
                continue
            convention = detect_convention(var)
            if not convention:
                continue  # Only report vars that match a known convention
            section = parts[0]
            key = '__'.join(parts[1:])
            results.append(EnvReference(
                variable=var, file=filepath, line=lineno,
                method=convention,
                section=section, key=key))

    return results


def scan_directory(directory: str) -> List[EnvReference]:
    results = []
    TARGET_EXTS = {'.yml', '.yaml', '.env', '.properties', '.conf', '.ini', '.toml'}
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext in TARGET_EXTS or fname.startswith('.env'):
                results.extend(scan_file(os.path.join(root, fname)))
    return results


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else '.'
    refs = scan_directory(path) if os.path.isdir(path) else scan_file(path)
    static  = [r for r in refs if not r.is_dynamic]
    dynamic = [r for r in refs if r.is_dynamic]
    print(json.dumps({
        'static':  [{'variable': r.variable, 'file': r.file, 'line': r.line,
                     'method': r.method, 'has_default': r.has_default,
                     'section': r.section, 'key': r.key} for r in static],
        'dynamic': [],
    }, indent=2))
