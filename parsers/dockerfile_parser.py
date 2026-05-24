"""
Dockerfile Parser
Extracts ENV directives from Dockerfiles.
Handles:
  ENV KEY=VALUE
  ENV KEY VALUE  (legacy form)
  ENV KEY1=VAL1 KEY2=VAL2  (multi-var form)
"""
import os
import re
from dataclasses import dataclass
from typing import List

DOCKERFILE_NAMES = {"Dockerfile", "dockerfile", "Dockerfile.dev",
                    "Dockerfile.prod", "Dockerfile.test"}

@dataclass
class ConfigVar:
    variable: str
    file: str
    source: str


def parse_file(filepath: str) -> List[ConfigVar]:
    results = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line.upper().startswith("ENV "):
                    continue
                rest = line[4:].strip()
                # Multi-var form: KEY1=VAL1 KEY2=VAL2
                if "=" in rest:
                    pairs = re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*=", rest)
                    for key in pairs:
                        results.append(ConfigVar(variable=key, file=filepath, source="dockerfile"))
                else:
                    # Legacy: ENV KEY VALUE
                    key = rest.split()[0] if rest.split() else None
                    if key and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
                        results.append(ConfigVar(variable=key, file=filepath, source="dockerfile"))
    except Exception:
        pass
    return results


def parse_directory(directory: str) -> List[ConfigVar]:
    results = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in {".git"}]
        for fname in files:
            if fname in DOCKERFILE_NAMES or fname.startswith("Dockerfile."):
                results.extend(parse_file(os.path.join(root, fname)))
    return results
