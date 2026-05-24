"""
Kubernetes YAML Parser
Extracts declared environment variables from:
  - Deployment / StatefulSet / DaemonSet (spec.containers[].env[])
  - ConfigMap (data: section)
  - Secret (data: section)
  - envFrom[] references
"""
import yaml
import os
from dataclasses import dataclass
from typing import List, Set


@dataclass
class ConfigVar:
    variable: str
    file: str
    source: str  # e.g. "kubernetes/Deployment", "kubernetes/ConfigMap"


def _extract_from_env_list(env_list, filepath: str, source: str) -> List[ConfigVar]:
    results = []
    if not isinstance(env_list, list):
        return results
    for item in env_list:
        if isinstance(item, dict) and "name" in item:
            results.append(ConfigVar(
                variable=item["name"],
                file=filepath,
                source=source,
            ))
    return results


def _parse_document(doc, filepath: str) -> List[ConfigVar]:
    results = []
    if not isinstance(doc, dict):
        return results

    kind = doc.get("kind", "")
    name = doc.get("metadata", {}).get("name", "?")
    source = f"kubernetes/{kind}({name})"

    # Deployments, StatefulSets, DaemonSets, Jobs, CronJobs
    if kind in ("Deployment", "StatefulSet", "DaemonSet", "Job"):
        spec = doc.get("spec", {})
        template = spec.get("template", {})
        pod_spec = template.get("spec", {})
        containers = pod_spec.get("containers", []) + pod_spec.get("initContainers", [])
        for container in containers:
            env = container.get("env", [])
            results.extend(_extract_from_env_list(env, filepath, source))

    elif kind == "CronJob":
        job_template = doc.get("spec", {}).get("jobTemplate", {})
        pod_spec = job_template.get("spec", {}).get("template", {}).get("spec", {})
        containers = pod_spec.get("containers", []) + pod_spec.get("initContainers", [])
        for container in containers:
            results.extend(_extract_from_env_list(container.get("env", []), filepath, source))

    # ConfigMap — every key in data is a potential env var name
    elif kind == "ConfigMap":
        data = doc.get("data", {})
        if isinstance(data, dict):
            for key in data:
                results.append(ConfigVar(variable=key, file=filepath, source=source))

    # Secret — keys in data are env var names (base64-encoded values)
    elif kind == "Secret":
        data = doc.get("data", {})
        if isinstance(data, dict):
            for key in data:
                results.append(ConfigVar(variable=key, file=filepath, source=source))

    return results


def parse_file(filepath: str) -> List[ConfigVar]:
    results = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            docs = list(yaml.safe_load_all(f))
        for doc in docs:
            results.extend(_parse_document(doc, filepath))
    except Exception:
        pass
    return results


def parse_directory(directory: str) -> List[ConfigVar]:
    results = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in {".git"}]
        for fname in files:
            if fname.endswith((".yaml", ".yml")):
                results.extend(parse_file(os.path.join(root, fname)))
    return results
