#!/usr/bin/env python3
"""
Config Drift Detector - Main CLI Entrypoint
Usage:
  python main.py --source src/ --config k8s/,docker-compose.yml,.env
  python main.py --source src/ --config k8s/ --languages java,python,cpp --json
"""
import argparse
import os
import sys
import json
import subprocess

from scanners.python.python_scanner import scan_directory as py_scan_dir
from scanners.python.python_scanner import scan_file as py_scan_file
from parsers.kubernetes_parser import parse_directory as k8s_dir, parse_file as k8s_file
from parsers.docker_compose_parser import parse_directory as compose_dir, parse_file as compose_file
from parsers.env_file_parser import parse_directory as env_dir, parse_file as env_file
from parsers.dockerfile_parser import parse_directory as dockerfile_dir, parse_file as dockerfile_file
from engine.drift_engine import detect_drift, EnvRef, ConfigDecl

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init()
    USE_COLOR = True
except ImportError:
    USE_COLOR = False


def log(msg, fore=None):
    """Always prints to stderr - safe in both normal and --json mode."""
    if USE_COLOR and fore:
        print(f"{fore}{msg}{Style.RESET_ALL}", file=sys.stderr)
    else:
        print(msg, file=sys.stderr)


def _to_eng_ref(r, language):
    return EnvRef(
        variable=r.variable, file=r.file, line=r.line,
        method=r.method, language=language,
        has_default=getattr(r, 'has_default', False),
        is_dynamic=getattr(r, 'is_dynamic', False),
    )


# --------------------------------------------------------------------------
# Code scanners
# --------------------------------------------------------------------------

def collect_python_refs(source_paths):
    refs = []
    for path in source_paths:
        if os.path.isdir(path):
            raw = py_scan_dir(path)
        elif path.endswith(".py") and os.path.isfile(path):
            raw = py_scan_file(path)
        else:
            continue
        refs += [_to_eng_ref(r, "python") for r in raw]
    return refs


def collect_java_refs(source_paths):
    """Use Eclipse JDT JAR when built, fall back to Python regex scanner."""
    jar = os.path.join(os.path.dirname(__file__),
                       "scanners", "java", "target", "java-scanner.jar")
    fallback = os.path.join(os.path.dirname(__file__),
                            "scanners", "java", "java_scanner_fallback.py")
    use_jar = os.path.exists(jar)

    if not use_jar:
        log("  [INFO] Java JAR not built - using Python regex fallback scanner.",
            Fore.CYAN if USE_COLOR else None)
        log("         For full AST accuracy: cd scanners/java && mvn package -q",
            Fore.CYAN if USE_COLOR else None)

    refs = []
    for path in source_paths:
        if not (os.path.isdir(path) or path.endswith(".java")):
            continue
        try:
            cmd = (["java", "-jar", jar, path] if use_jar
                   else [sys.executable, fallback, path])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            data = json.loads(result.stdout)
            for item in data.get("static", []):
                refs.append(EnvRef(
                    variable=item["variable"], file=item["file"],
                    line=item["line"], method=item["method"],
                    language="java", has_default=item.get("has_default", False),
                ))
            for item in data.get("dynamic", []):
                refs.append(EnvRef(
                    variable="<dynamic>", file=item["file"],
                    line=item["line"], method=item["method"],
                    language="java", is_dynamic=True,
                ))
        except Exception as e:
            log(f"  [WARN] Java scan failed for {path}: {e}",
                Fore.YELLOW if USE_COLOR else None)
    return refs


def collect_cpp_refs(source_paths):
    scanner = os.path.join(os.path.dirname(__file__),
                           "scanners", "cpp", "cpp_scanner.py")
    cpp_exts = (".cpp", ".cc", ".cxx", ".c", ".h", ".hpp", ".hxx")
    refs = []
    for path in source_paths:
        if not (os.path.isdir(path) or any(path.endswith(e) for e in cpp_exts)):
            continue
        try:
            result = subprocess.run(
                [sys.executable, scanner, path],
                capture_output=True, text=True, timeout=60)
            data = json.loads(result.stdout)
            for item in data.get("static", []):
                refs.append(EnvRef(
                    variable=item["variable"], file=item["file"],
                    line=item["line"], method=item["method"],
                    language="cpp",
                ))
            for item in data.get("dynamic", []):
                refs.append(EnvRef(
                    variable="<dynamic>", file=item["file"],
                    line=item["line"], method=item["method"],
                    language="cpp", is_dynamic=True,
                ))
        except Exception as e:
            log(f"  [WARN] C++ scan failed for {path}: {e}",
                Fore.YELLOW if USE_COLOR else None)
    return refs


# --------------------------------------------------------------------------
# Config parsers
# --------------------------------------------------------------------------

def collect_config_decls(config_paths):
    decls = []
    files_scanned = []

    for path in config_paths:
        path = path.strip()
        if not path:
            continue
        if not os.path.exists(path):
            log(f"  [WARN] Config path not found: {path}",
                Fore.YELLOW if USE_COLOR else None)
            continue

        files_scanned.append(path)

        if os.path.isfile(path):
            fname = os.path.basename(path).lower()
            raw = []
            if fname in ("docker-compose.yml", "docker-compose.yaml",
                         "docker-compose.override.yml", "docker-compose.override.yaml"):
                raw = compose_file(path)
            elif fname.startswith(".env") or fname.endswith(".env"):
                raw = env_file(path)
            elif fname.startswith("dockerfile"):
                raw = dockerfile_file(path)
            elif fname.endswith((".yaml", ".yml")):
                raw = k8s_file(path)
            for v in raw:
                decls.append(ConfigDecl(variable=v.variable,
                                        file=v.file, source=v.source))

        elif os.path.isdir(path):
            for v in k8s_dir(path):
                decls.append(ConfigDecl(variable=v.variable, file=v.file, source=v.source))
            for v in compose_dir(path):
                decls.append(ConfigDecl(variable=v.variable, file=v.file, source=v.source))
            for v in env_dir(path):
                decls.append(ConfigDecl(variable=v.variable, file=v.file, source=v.source))
            for v in dockerfile_dir(path):
                decls.append(ConfigDecl(variable=v.variable, file=v.file, source=v.source))

    return decls, files_scanned


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Config Drift Detector - detects env var drift between code and deployment config"
    )
    parser.add_argument("--source",        required=True,
                        help="Comma-separated source dirs/files to scan")
    parser.add_argument("--config",        required=True,
                        help="Comma-separated config paths (dirs or files)")
    parser.add_argument("--languages",     default="python,java,cpp",
                        help="Languages: python,java,cpp")
    parser.add_argument("--json",          action="store_true",
                        help="Output results as JSON (all logs go to stderr)")
    parser.add_argument("--fail-on-drift", action="store_true",
                        help="Exit 1 if critical drift detected")
    parser.add_argument("--driftignore",   default=".driftignore",
                        help="Path to .driftignore file")
    parser.add_argument("--skip-unused",   action="store_true",
                        help="Do not report unused config variables")
    args = parser.parse_args()

    source_paths = [p.strip() for p in args.source.split(",") if p.strip()]
    config_paths = [p.strip() for p in args.config.split(",") if p.strip()]
    languages    = [l.strip().lower() for l in args.languages.split(",")]

    log("\nConfig Drift Detector", Fore.CYAN if USE_COLOR else None)
    log("=" * 50)

    # Collect code references
    all_refs = []

    if "python" in languages:
        log("  Scanning Python...", Fore.BLUE if USE_COLOR else None)
        refs = collect_python_refs(source_paths)
        all_refs += refs
        log(f"    Found {sum(1 for r in refs if not r.is_dynamic)} static + "
            f"{sum(1 for r in refs if r.is_dynamic)} dynamic references")

    if "java" in languages:
        log("  Scanning Java...", Fore.BLUE if USE_COLOR else None)
        refs = collect_java_refs(source_paths)
        all_refs += refs
        log(f"    Found {sum(1 for r in refs if not r.is_dynamic)} static references")

    if "cpp" in languages:
        log("  Scanning C++...", Fore.BLUE if USE_COLOR else None)
        refs = collect_cpp_refs(source_paths)
        all_refs += refs
        log(f"    Found {sum(1 for r in refs if not r.is_dynamic)} static references")

    # Collect config declarations
    log("  Parsing config files...", Fore.BLUE if USE_COLOR else None)
    config_decls, files_scanned = collect_config_decls(config_paths)
    log(f"    Found {len(config_decls)} declared variables in {len(files_scanned)} path(s)")

    # Run drift detection
    report = detect_drift(
        code_refs=all_refs,
        config_decls=config_decls,
        config_files=files_scanned,
        languages=languages,
        driftignore_path=args.driftignore,
    )

    if args.skip_unused:
        report.unused_in_config = []

    # Output
    if args.json:
        print(report.to_json())   # stdout only - clean JSON
    else:
        text = report.to_text_report()
        if report.has_critical_drift:
            log("\n" + text, Fore.RED if USE_COLOR else None)
        else:
            log("\n" + text, Fore.GREEN if USE_COLOR else None)

    # Exit code
    if args.fail_on_drift and report.has_critical_drift:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
