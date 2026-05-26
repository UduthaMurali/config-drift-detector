"""
Pydantic BaseSettings Adapter
Extracts environment variable names from Pydantic v1 and v2 Settings classes.

Patterns detected:
  class Settings(BaseSettings):
      DATABASE_URL: str           → env var DATABASE_URL
      db_host: str                → env var DB_HOST  (uppercased)
      api_key: str = Field(env="MY_API_KEY")  → env var MY_API_KEY
      model_config = SettingsConfigDict(env_prefix="APP_")  → prefix applied

Also handles:
  class Config:
      env_prefix = "APP_"

envgrd does NOT implement this. This is a novel contribution.
"""
import os
import re
import sys
import json
import ast
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class EnvReference:
    variable: str
    file: str
    line: int
    method: str
    has_default: bool = False
    is_dynamic: bool = False

SKIP_DIRS = {'.git', '__pycache__', '.venv', 'venv', 'node_modules',
             'build', 'dist', '.tox', 'site-packages'}

# Quick pre-scan: only process files that mention BaseSettings
RE_BASESETTINGS = re.compile(r'BaseSettings|pydantic_settings|pydantic\.BaseSettings')


def _get_env_prefix(class_node: ast.ClassDef) -> str:
    """Extract env_prefix from inner Config class or model_config."""
    for node in ast.walk(class_node):
        # Pydantic v1: class Config: env_prefix = "APP_"
        if isinstance(node, ast.ClassDef) and node.name == 'Config':
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for t in item.targets:
                        if isinstance(t, ast.Name) and t.id == 'env_prefix':
                            if isinstance(item.value, ast.Constant):
                                return str(item.value.value)
        # Pydantic v2: model_config = SettingsConfigDict(env_prefix="APP_")
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == 'model_config':
                    if isinstance(node.value, ast.Call):
                        for kw in node.value.keywords:
                            if kw.arg == 'env_prefix' and isinstance(kw.value, ast.Constant):
                                return str(kw.value.value)
    return ''


def _get_field_env_alias(annotation_node) -> Optional[str]:
    """Extract explicit env='NAME' from Field(env='NAME') or alias."""
    if not isinstance(annotation_node, ast.Call):
        return None
    for kw in annotation_node.keywords:
        if kw.arg in ('env', 'alias') and isinstance(kw.value, ast.Constant):
            return str(kw.value.value).upper()
    return None


def scan_file(filepath: str) -> List[EnvReference]:
    results = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
    except Exception:
        return []

    # Quick check — skip files with no BaseSettings reference
    if not RE_BASESETTINGS.search(source):
        return []

    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError:
        return []

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        # Check if this class inherits from BaseSettings
        is_settings = False
        for base in node.bases:
            base_name = ''
            if isinstance(base, ast.Name):
                base_name = base.id
            elif isinstance(base, ast.Attribute):
                base_name = base.attr
            if 'BaseSettings' in base_name or 'Settings' in base_name:
                is_settings = True
                break
        if not is_settings:
            continue

        env_prefix = _get_env_prefix(node)

        # Walk class body for annotated fields
        for item in node.body:
            if not isinstance(item, ast.AnnAssign):
                continue
            if not isinstance(item.target, ast.Name):
                continue

            field_name = item.target.id
            if field_name.startswith('_') or field_name in ('model_config',):
                continue

            has_default = item.value is not None

            # Check for explicit env alias in Field(...)
            env_alias = None
            if item.value and isinstance(item.value, ast.Call):
                env_alias = _get_field_env_alias(item.value)

            var_name = env_alias if env_alias else (env_prefix + field_name).upper()

            results.append(EnvReference(
                variable=var_name,
                file=filepath,
                line=item.target.col_offset and node.lineno or item.col_offset,
                method=f'Pydantic BaseSettings field ({node.name})',
                has_default=has_default))

    return results


def scan_directory(directory: str) -> List[EnvReference]:
    results = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            if fname.endswith('.py'):
                results.extend(scan_file(os.path.join(root, fname)))
    return results


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else '.'
    refs = scan_directory(path) if os.path.isdir(path) else scan_file(path)
    static  = [r for r in refs if not r.is_dynamic]
    dynamic = [r for r in refs if r.is_dynamic]
    print(json.dumps({
        'static':  [{'variable': r.variable, 'file': r.file,
                     'line': r.line, 'method': r.method,
                     'has_default': r.has_default} for r in static],
        'dynamic': [{'file': r.file, 'line': r.line,
                     'method': r.method} for r in dynamic],
    }, indent=2))
