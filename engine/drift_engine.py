"""
Drift Detection Engine
Core set-comparison logic between code-referenced variables and config-declared variables.
Produces a DriftReport with missing, unused, and dynamic warnings.
"""
from dataclasses import dataclass, field
from typing import List, Set, Dict
import json
import os
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
    missing_in_config: List[DriftItem]   # in code but missing from config
    unused_in_config: List[ConfigDecl]   # in config but unused in code
    dynamic_warnings: List[EnvRef]       # dynamic patterns (cannot statically resolve)
    ignored_variables: List[str]

    @property
    def has_critical_drift(self) -> bool:
        return any(d.severity == "critical" for d in self.missing_in_config)

    @property
    def drift_score(self) -> int:
        """Score = 3 pts per critical + 1 pt per warning missing variable."""
        return sum(3 if d.severity == "critical" else 1 for d in self.missing_in_config)

    @property
    def drift_level(self) -> str:
        """
        Overall drift level based on combined score:
          NONE   = score 0
          LOW    = score 1-3   (e.g. 1 critical or 1-3 warnings)
          MEDIUM = score 4-9   (e.g. 2-3 criticals, or mix)
          HIGH   = score 10+   (e.g. 4+ criticals or many missing vars)
        """
        score = self.drift_score
        if score == 0:
            return "NONE"
        elif score <= 3:
            return "LOW"
        elif score <= 9:
            return "MEDIUM"
        else:
            return "HIGH"

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "drift_level": self.drift_level,
            "drift_score": self.drift_score,
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
        level_icon = {"NONE": "[OK]", "LOW": "[LOW]", "MEDIUM": "[MEDIUM]", "HIGH": "[HIGH]"}
        icon = level_icon.get(self.drift_level, "")

        if self.missing_in_config:
            critical_count = sum(1 for d in self.missing_in_config if d.severity == "critical")
            warning_count  = sum(1 for d in self.missing_in_config if d.severity == "warning")
            lines.append(f"{icon} DRIFT LEVEL: {self.drift_level}  (score={self.drift_score})")
            lines.append(f"     {len(self.missing_in_config)} missing variable(s): "
                         f"{critical_count} critical, {warning_count} warning\n")
            lines.append(f"{'Variable':<30} {'Severity':<10} {'Language':<10} {'File':<45} {'Line':<6} {'Method'}")
            lines.append("-" * 120)
            for d in self.missing_in_config:
                short_file = d.file[-44:] if len(d.file) > 44 else d.file
                sev = d.severity.upper()
                lines.append(f"{d.variable:<30} {sev:<10} {d.language:<10} {short_file:<45} {d.line:<6} {d.method}")
        else:
            lines.append(f"{icon} DRIFT LEVEL: NONE -- All environment variables are declared in config.")

        if self.unused_in_config:
            lines.append(f"\nWARNING: {len(self.unused_in_config)} unused variable(s) in config (not referenced in code):")
            lines.append(f"{'Variable':<30} {'Config File'}")
            lines.append("-" * 70)
            for u in self.unused_in_config:
                lines.append(f"{u.variable:<30} {u.file}")

        if self.dynamic_warnings:
            lines.append(f"\nINFO: {len(self.dynamic_warnings)} dynamic pattern(s) detected (cannot be statically resolved):")
            for d in self.dynamic_warnings:
                lines.append(f"  {d.file}:{d.line} -- {d.method} [{d.language}]")

        if self.ignored_variables:
            lines.append(f"\nIgnored: {len(self.ignored_variables)} variable(s) via .driftignore")

        lines.append(f"\nConfig files checked: {', '.join(self.config_files_scanned)}")
        return "\n".join(lines)

    def to_github_pr_comment(self) -> str:
        if self.has_critical_drift:
            lines = [f"## Config Drift Detected -- {len(self.missing_in_config)} missing variable(s)\n"]
            lines.append("| Variable | Severity | Language | Source File | Line | Detection Method |")
            lines.append("|----------|----------|----------|-------------|------|-----------------|")
            for d in self.missing_in_config:
                fname = d.file.split("/")[-1].split("\\")[-1]
                lines.append(f"| `{d.variable}` | {d.severity} | {d.language} | `{fname}` | {d.line} | {d.method} |")
            lines.append(f"\n**Drift Level:** {self.drift_level} (score={self.drift_score})")
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
            lines.append(f"**Drift Level:** NONE -- All environment variables are declared in deployment configuration.")
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

    # Find variables in code but missing from config
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

    # Sort: critical first, then alphabetically
    missing.sort(key=lambda d: (0 if d.severity == "critical" else 1, d.variable))

    # Find variables in config but not used in code
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
