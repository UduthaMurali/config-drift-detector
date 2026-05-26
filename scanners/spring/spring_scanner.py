"""
Spring Framework Adapter
Extracts environment variable references from Spring Boot configuration files:
  - application.properties  →  ${VAR_NAME}  /  ${VAR_NAME:default}
  - application.yml         →  ${VAR_NAME}  /  ${VAR_NAME:default}
  - @Value("${VAR_NAME}")   →  detected in Java source files

This catches ALL configuration that Spring PetClinic and similar projects
use — the very cases that the Java AST scanner misses entirely.

envgrd does NOT implement this. This is a novel contribution.
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

# ${VAR_NAME}  or  ${VAR_NAME:default_value}
RE_PLACEHOLDER = re.compile(r'\$\{([A-Za-z_][A-Za-z0-9_.]*)(?::([^}]*))?\}')

# @Value("${VAR_NAME}") or @Value("${VAR_NAME:default}")
RE_AT_VALUE    = re.compile(r'@Value\s*\(\s*["\']?\$\{([A-Za-z_][A-Za-z0-9_.]*)(?::([^}]*))?}')

# Spring profile-specific: spring.config.activate.on-profile
RE_PROFILE     = re.compile(r'spring\.profiles?\.(active|include)\s*[=:]\s*(.+)')

PROPERTIES_EXTENSIONS = {'.properties', '.yml', '.yaml'}
JAVA_EXTENSIONS       = {'.java'}
SKIP_DIRS = {'.git', 'target', 'build', 'node_modules', '__pycache__', '.mvn'}


def scan_properties_file(filepath: str) -> List[EnvReference]:
    """Parse .properties file: key=...${VAR}..."""
    results = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception:
        return []

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#') or not stripped:
            continue
        for m in RE_PLACEHOLDER.finditer(line):
            var  = m.group(1).replace('.', '_').upper()  # spring.datasource.url → SPRING_DATASOURCE_URL
            raw  = m.group(1)
            has_default = m.group(2) is not None
            # Skip vars that look like Spring EL expressions (contain spaces or parens)
            if ' ' in raw or '(' in raw:
                continue
            results.append(EnvReference(
                variable=var, file=filepath, line=lineno,
                method='Spring ${VAR} placeholder',
                has_default=has_default))
    return results


def scan_yaml_file(filepath: str) -> List[EnvReference]:
    """Parse application.yml: value: ${VAR_NAME:default}"""
    results = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception:
        return []

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#') or not stripped:
            continue
        for m in RE_PLACEHOLDER.finditer(line):
            raw  = m.group(1)
            var  = raw.replace('.', '_').upper()
            has_default = m.group(2) is not None
            if ' ' in raw or '(' in raw:
                continue
            results.append(EnvReference(
                variable=var, file=filepath, line=lineno,
                method='Spring ${VAR} in YAML',
                has_default=has_default))
    return results


def scan_java_file(filepath: str) -> List[EnvReference]:
    """Detect @Value('${VAR}') annotations in Java source."""
    results = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception:
        return []

    for lineno, line in enumerate(lines, 1):
        for m in RE_AT_VALUE.finditer(line):
            raw  = m.group(1)
            var  = raw.replace('.', '_').upper()
            has_default = m.group(2) is not None
            if ' ' in raw or '(' in raw:
                continue
            results.append(EnvReference(
                variable=var, file=filepath, line=lineno,
                method='Spring @Value annotation',
                has_default=has_default))
    return results


def scan_directory(directory: str) -> List[EnvReference]:
    results = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            fpath = os.path.join(root, fname)
            ext   = os.path.splitext(fname)[1].lower()
            # Only scan application*.properties / application*.yml
            if ext in PROPERTIES_EXTENSIONS:
                base = fname.lower()
                if base.startswith('application') or base.startswith('bootstrap'):
                    if ext == '.properties':
                        results.extend(scan_properties_file(fpath))
                    else:
                        results.extend(scan_yaml_file(fpath))
            elif ext in JAVA_EXTENSIONS:
                results.extend(scan_java_file(fpath))
    return results


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else '.'
    refs = scan_directory(path) if os.path.isdir(path) else []
    static  = [r for r in refs if not r.is_dynamic]
    dynamic = [r for r in refs if r.is_dynamic]
    print(json.dumps({
        'static':  [{'variable': r.variable, 'file': r.file,
                     'line': r.line, 'method': r.method,
                     'has_default': r.has_default} for r in static],
        'dynamic': [{'file': r.file, 'line': r.line,
                     'method': r.method} for r in dynamic],
    }, indent=2))
