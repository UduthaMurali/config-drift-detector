"""
.env / .envrc / systemd / shell script Parser
Parses environment variable declarations from:
  - .env files              KEY=VALUE
  - .envrc (direnv)         export KEY=VALUE  /  export KEY
  - systemd .service files  Environment=KEY=VALUE
  - shell scripts           export KEY=VALUE  /  export KEY
"""
import os
import re
from dataclasses import dataclass
from typing import List

ENV_FILE_NAMES = {
    ".env", ".env.example", ".env.template", ".env.sample",
    ".env.local", ".env.development", ".env.staging",
    ".env.production", ".env.test",
}

LINE_RE        = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=")
EXPORT_RE      = re.compile(r"^\s*export\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s*=|$)")
SYSTEMD_ENV_RE = re.compile(r'^\s*Environment\s*=\s*"?([A-Za-z_][A-Za-z0-9_]*)\s*=')


@dataclass
class ConfigVar:
    variable: str
    file: str
    source: str


def parse_file(filepath: str) -> List[ConfigVar]:
    """Parse .env style KEY=VALUE files."""
    results = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                m = LINE_RE.match(line)
                if m:
                    results.append(ConfigVar(variable=m.group(1), file=filepath, source="env_file"))
    except Exception:
        pass
    return results


def parse_envrc(filepath: str) -> List[ConfigVar]:
    """Parse direnv .envrc files — export KEY=value or export KEY."""
    results = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                m = EXPORT_RE.match(line)
                if m:
                    results.append(ConfigVar(variable=m.group(1), file=filepath, source="envrc"))
    except Exception:
        pass
    return results


def parse_systemd_service(filepath: str) -> List[ConfigVar]:
    """Parse systemd .service files — Environment=KEY=value or Environment="KEY=value"."""
    results = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith(";"):
                    continue
                m = SYSTEMD_ENV_RE.match(line)
                if m:
                    results.append(ConfigVar(variable=m.group(1), file=filepath, source="systemd_service"))
    except Exception:
        pass
    return results


def parse_shell_script(filepath: str) -> List[ConfigVar]:
    """Parse shell scripts (.sh, .bash) — export KEY=value or export KEY."""
    results = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                m = EXPORT_RE.match(line)
                if m:
                    results.append(ConfigVar(variable=m.group(1), file=filepath, source="shell_script"))
    except Exception:
        pass
    return results


def parse_directory(directory: str) -> List[ConfigVar]:
    """Recursively parse all supported config files in a directory."""
    results = []
    skip = {".git", "node_modules", "__pycache__"}
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in skip]
        for fname in files:
            fpath = os.path.join(root, fname)
            if fname in ENV_FILE_NAMES or fname.startswith(".env."):
                results.extend(parse_file(fpath))
            elif fname == ".envrc":
                results.extend(parse_envrc(fpath))
            elif fname.endswith(".service"):
                results.extend(parse_systemd_service(fpath))
            elif fname.endswith((".sh", ".bash")):
                results.extend(parse_shell_script(fpath))
    return results
