"""
Drift Detection Engine
Core set-comparison logic between code-referenced variables and config-declared variables.
Produces a DriftReport with missing, unused, and dynamic warnings.
"""
from dataclasses import dataclass, field
from typing import List, Set, Dict
import json
from datetime import datetime


@dataclass
class EnvRef:
    variable: str
    file: str
    line: int
    method: str
    language: str
    has_default: bool = False
    is_dynamic: bool = False


@dataclass
class ConfigDecl:
    variable: str
    file: str
    source: str


@dataclass
class DriftItem:
    variable: str
    language: str
    file: str
    line: int
    method: str
    severity: str = "critical"  # critical | warning


@dataclass
class DriftReport:
    status: str                        # "CLEAN" | "DRIFT_DETECTED"
    timestamp: str
    languages_scanned: List[str]
    config_files_scanned: List[str]
    code_variables: List[EnvRef]
    config_variables: List[ConfigDecl]
    missing_in_config: List[DriftItem]   # CRITICAL — code needs it, config missing
    unused_in_config: List[ConfigDecl]   # WARNING  — config has it, code doesn't use it
    dynamic_warnings: List[EnvRef]       # INFO     — dynamic patterns detected
    ignored_variables: List[str]

    @property
    def has_critical_drift(self) -> bool:
        return len(self.missing_in_config) > 0

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "timestamp": self.timestamp,
            "languages_scanned": self.languages_scanned,
            "config_files_scanned": self.config_files_scanned,
            "summary": {
                "code_variables": len(self.code_variables),
                "config_variables": len(self.config_variables),
                "missing": len(self.missing_in_config),
                "unused": len(self.unused_in_config),
                "dynamic_warnings": len(self.dynamic_warnings),
                "ignored": len(self.ignored_variables),
            },
            "missing_in_config": [
                {
                    "variable": d.variable, "language": d.language,
                    "file": d.file, "line": d.line,
                    "method": d.method, "severity": d.severity,
                }
                for d in self.missing_in_config
            ],
            "unused_in_config": [
                {"variable": d.variable, "file": d.file, "source": d.source}
                for d in self.unused_in_config
            ],
            "dynamic_patterns": [
                {"file": r.file, "line": r.line, "method": r.method, "language": r.language}
                for r in self.dynamic_warnings
            ],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def to_text_report(self) -> str:
        lines = []
        if self.has_critical_drift:
            lines.append(f"DRIFT DETECTED — {len(self.missing_in_config)} missing variable(s)\n")
            lines.append(f"{'Variable':<30} {'Language':<10} {'File':<45} {'Line':<6} {'Method'}")
            lines.append("-" * 110)
            for d in self.missing_in_config:
                short_file = d.file[-44:] if len(d.file) > 44 else d.file
                lines.append(f"{d.variable:<30} {d.language:<10} {short_file:<45} {d.line:<6} {d.method}")
        else:
            lines.append("OK — No drift detected. All environment variables are declared in config.")

        if self.unused_in_config:
            lines.append(f"\nWARNING: {len(self.unused_in_config)} unused variable(s) in config (not referenced in code):")
            lines.append(f"{'Variable':<30} {'Config File'}")
            lines.append("-" * 70)
            for u in self.unused_in_config:
                lines.append(f"{u.variable:<30} {u.file}")

        if self.dynamic_warnings:
            lines.append(f"\nINFO: {len(self.dynamic_warnings)} dynamic pattern(s) detected (cannot be statically resolved):")
            for d in self.dynamic_warnings:
                lines.append(f"  {d.file}:{d.line} — {d.method} [{d.language}]")

        if self.ignored_variables:
            lines.append(f"\nIgnored: {len(self.ignored_variables)} variable(s) via .driftignore")

        lines.append(f"\nConfig files checked: {', '.join(self.config_files_scanned)}")
        return "\n".join(lines)

    def to_github_pr_comment(self) -> str:
        if self.has_critical_drift:
            lines = [f"## Config Drift Detected — {len(self.missing_in_config)} missing variable(s)\n"]
            lines.append("| Variable | Language | Source File | Line | Detection Method |")
            lines.append("|----------|----------|-------------|------|-----------------|")
            for d in self.missing_in_config:
                fname = d.file.split("/")[-1].split("\\")[-1]
                lines.append(f"| `{d.variable}` | {d.language} | `{fname}` | {d.line} | {d.method} |")
            lines.append(f"\n**Config files checked:** `{', '.join(self.config_files_scanned)}`")
            if self.unused_in_config:
                lines.append(f"\n### Warning: {len(self.unused_in_config)} unused variable(s) in config\n")
                lines.append("| Variable | Config File |")
                lines.append("|----------|-------------|")
                for u in self.unused_in_config:
                    lines.append(f"| `{u.variable}` | `{u.file}` |")
            lines.append("\n**Action Required:** Add the missing variables to your deployment configuration before this PR can be merged.")
        else:
            lines = ["## Config Drift Check Passed\n"]
            lines.append("All environment variables referenced in code are declared in deployment configuration.")
            lines.append(f"\n_Scanned {len(self.code_variables)} code references against {len(self.config_variables)} config declarations._")
        return "\n".join(lines)


def load_driftignore(path: str = ".driftignore") -> Set[str]:
    """Load variable names to ignore from .driftignore file."""
    ignored = set()
    if not os.path.exists(path):
        return ignored
    try:
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    ignored.add(line.upper())
    except Exception:
        pass
    return ignored


import os


def detect_drift(
    code_refs: List[EnvRef],
    config_decls: List[ConfigDecl],
    config_files: List[str],
    languages: List[str],
    driftignore_path: str = ".driftignore",
) -> DriftReport:
    """
    Core drift detection algorithm.
    Returns a DriftReport with all findings.
    """
    ignored = load_driftignore(driftignore_path)

    # Separate static vs dynamic
    static_refs = [r for r in code_refs if not r.is_dynamic]
    dynamic_refs = [r for r in code_refs if r.is_dynamic]

    # Build sets (uppercase for case-insensitive comparison)
    code_vars: Dict[str, EnvRef] = {}
    for ref in static_refs:
        key = ref.variable.upper()
        if key not in ignored:
            if key not in code_vars or not ref.has_default:
                code_vars[key] = ref

    config_var_set: Set[str] = {d.variable.upper() for d in config_decls
                                 if d.variable.upper() not in ignored}

    # CRITICAL: in code but NOT in any config
    missing = []
    for key, ref in code_vars.items():
        if key not in config_var_set:
            severity = "warning" if ref.has_default else "critical"
            missing.append(DriftItem(
                variable=ref.variable,
                language=ref.language,
                file=ref.file,
                line=ref.line,
                method=ref.method,
                severity=severity,
            ))

    # Sort: critical first, then by variable name
    missing.sort(key=lambda d: (0 if d.severity == "critical" else 1, d.variable))

    # WARNING: in config but NOT used in code
    code_var_set = set(code_vars.keys())
    unused = [d for d in config_decls
              if d.variable.upper() not in code_var_set
              and d.variable.upper() not in ignored]

    status = "DRIFT_DETECTED" if any(d.severity == "critical" for d in missing) else "CLEAN"

    return DriftReport(
        status=status,
        timestamp=datetime.utcnow().isoformat() + "Z",
        languages_scanned=languages,
        config_files_scanned=config_files,
        code_variables=static_refs,
        config_variables=config_decls,
        missing_in_config=missing,
        unused_in_config=unused,
        dynamic_warnings=dynamic_refs,
        ignored_variables=list(ignored),
    )
