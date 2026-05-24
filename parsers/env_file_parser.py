"""
.env File Parser
Parses KEY=VALUE lines from .env, .env.example, .env.template, .env.*, etc.
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

LINE_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=")


@dataclass
class ConfigVar:
    variable: str
    file: str
    source: str


def parse_file(filepath: str) -> List[ConfigVar]:
    results = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                m = LINE_RE.match(line)
                if m:
                    results.append(ConfigVar(
                        variable=m.group(1),
                        file=filepath,
                        source="env_file",
                    ))
    except Exception:
        pass
    return results


def parse_directory(directory: str) -> List[ConfigVar]:
    results = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules"}]
        for fname in files:
            if fname in ENV_FILE_NAMES or fname.startswith(".env."):
                results.extend(parse_file(os.path.join(root, fname)))
    return results
