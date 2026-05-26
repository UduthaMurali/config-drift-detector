"""
Java Scanner — Python regex/AST fallback
Works without the Eclipse JDT JAR. Detects all major patterns via regex.

Detects:
  System.getenv("KEY")
  System.getenv().get("KEY")
  @Value("${KEY}")  /  @Value("${KEY:default}")
  environment.getProperty("KEY")
  env.getProperty("KEY", "default")
  @ConfigurationProperties(prefix="...")
"""
import os
import re
import sys
import json
from dataclasses import dataclass
from typing import List

@dataclass
class EnvReference:
    variable: str
    file: str
    line: int
    method: str
    has_default: bool = False
    is_dynamic: bool = False


# ── Compiled patterns ──────────────────────────────────────────────────────────

# System.getenv("KEY")
RE_GETENV_STATIC  = re.compile(r'System\.getenv\(\s*"([A-Za-z_][A-Za-z0-9_]*)"\s*\)')
RE_GETENV_DYNAMIC = re.compile(r'System\.getenv\(\s*(?!"[A-Za-z_])')

# @Value("${KEY}")  or  @Value("${KEY:default}")
RE_VALUE_ANNOT    = re.compile(r'@Value\(\s*"\$\{([A-Za-z0-9_.\\-]+)(?::([^}]*))?\}"\s*\)')

# environment.getProperty("KEY") / env.getProperty("KEY","default")
RE_GET_PROPERTY   = re.compile(
    r'\.getProperty\(\s*"([A-Za-z0-9_.\\-]+)"(?:\s*,\s*"([^"]*)")?\s*\)')

# @ConfigurationProperties(prefix="my.prefix")
RE_CONFIG_PROPS   = re.compile(r'@ConfigurationProperties\s*\(\s*prefix\s*=\s*"([^"]+)"\s*\)')

# Spring application.properties style: ${KEY} in string literals
RE_PLACEHOLDER    = re.compile(r'\$\{([A-Za-z0-9_.\\-]+)(?::([^}]*))?\}')


def _spring_key_to_env(spring_key: str) -> str:
    """Convert Spring property key to env var name: app.db.url → APP_DB_URL"""
    return spring_key.upper().replace('.', '_').replace('-', '_')


def scan_file(filepath: str) -> List[EnvReference]:
    results = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception:
        return []

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()

        # Skip line comments
        if stripped.startswith('//') or stripped.startswith('*'):
            continue

        # ── System.getenv("KEY") ──────────────────────────────────────────────
        for m in RE_GETENV_STATIC.finditer(line):
            results.append(EnvReference(
                variable=m.group(1), file=filepath, line=lineno,
                method='System.getenv()', has_default=False))
        if RE_GETENV_DYNAMIC.search(line) and not RE_GETENV_STATIC.search(line):
            if 'System.getenv' in line:
                results.append(EnvReference(
                    variable='<dynamic>', file=filepath, line=lineno,
                    method='System.getenv(expr)', is_dynamic=True))

        # ── @Value("${KEY}") ──────────────────────────────────────────────────
        for m in RE_VALUE_ANNOT.finditer(line):
            spring_key = m.group(1)
            has_default = m.group(2) is not None
            results.append(EnvReference(
                variable=_spring_key_to_env(spring_key),
                file=filepath, line=lineno,
                method=f'@Value(${{' + spring_key + '}})',
                has_default=has_default))

        # ── .getProperty("KEY") ───────────────────────────────────────────────
        for m in RE_GET_PROPERTY.finditer(line):
            spring_key = m.group(1)
            has_default = m.group(2) is not None
            results.append(EnvReference(
                variable=_spring_key_to_env(spring_key),
                file=filepath, line=lineno,
                method='environment.getProperty()',
                has_default=has_default))

        # ── @ConfigurationProperties(prefix="...") ───────────────────────────
        for m in RE_CONFIG_PROPS.finditer(line):
            prefix = m.group(1)
            results.append(EnvReference(
                variable=_spring_key_to_env(prefix) + '_*',
                file=filepath, line=lineno,
                method='@ConfigurationProperties(prefix)'))

    return results


def scan_directory(directory: str) -> List[EnvReference]:
    results = []
    skip_dirs = {'.git', 'target', 'build', '.gradle', 'node_modules',
                 '__pycache__', 'test', 'tests'}
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for fname in files:
            if fname.endswith('.java'):
                results.extend(scan_file(os.path.join(root, fname)))
    return results


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else '.'
    refs = scan_directory(path) if os.path.isdir(path) else scan_file(path)
    static  = [r for r in refs if not r.is_dynamic]
    dynamic = [r for r in refs if r.is_dynamic]
    output = {
        'static': [
            {'variable': r.variable, 'file': r.file,
             'line': r.line, 'method': r.method,
             'has_default': r.has_default}
            for r in static
        ],
        'dynamic': [
            {'file': r.file, 'line': r.line, 'method': r.method}
            for r in dynamic
        ],
    }
    print(json.dumps(output, indent=2))
