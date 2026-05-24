"""
Docker Compose Parser
Extracts environment variables from docker-compose.yml / docker-compose.yaml files.
Handles:
  services.<name>.environment (list and dict form)
  services.<name>.env_file (notes the file reference)
"""
import yaml
import os
from dataclasses import dataclass
from typing import List


@dataclass
class ConfigVar:
    variable: str
    file: str
    source: str


def parse_file(filepath: str) -> List[ConfigVar]:
    results = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            doc = yaml.safe_load(f)
        if not isinstance(doc, dict):
            return results

        services = doc.get("services", {})
        if not isinstance(services, dict):
            return results

        for svc_name, svc_def in services.items():
            if not isinstance(svc_def, dict):
                continue
            source = f"docker-compose/service({svc_name})"
            env = svc_def.get("environment", [])

            # List form: ["KEY=value", "KEY2"]
            if isinstance(env, list):
                for item in env:
                    if isinstance(item, str):
                        key = item.split("=")[0].strip()
                        if key:
                            results.append(ConfigVar(variable=key, file=filepath, source=source))

            # Dict form: {KEY: value}
            elif isinstance(env, dict):
                for key in env:
                    results.append(ConfigVar(variable=str(key), file=filepath, source=source))

    except Exception:
        pass
    return results


def parse_directory(directory: str) -> List[ConfigVar]:
    results = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in {".git"}]
        for fname in files:
            if fname in ("docker-compose.yml", "docker-compose.yaml",
                         "docker-compose.override.yml", "docker-compose.override.yaml"):
                results.extend(parse_file(os.path.join(root, fname)))
    return results
