"""
C++ Scanner (Tree-sitter based)
Detects environment variable references in C++ source files.
Supports: std::getenv("KEY"), getenv("KEY"), macro-wrapped patterns.

Falls back to regex-based scanning if tree-sitter is not installed.
"""
import os
import re
import sys
import json
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class EnvReference:
    variable: str
    file: str
    line: int
    method: str
    has_default: bool = False
    is_dynamic: bool = False


# ── Regex-based fallback scanner ──────────────────────────────────────────────
# Matches: getenv("KEY")  /  std::getenv("KEY")
GETENV_RE = re.compile(
    r'(?:std\s*::\s*)?getenv\s*\(\s*"([A-Za-z_][A-Za-z0-9_]*)"\s*\)',
)
GETENV_DYNAMIC_RE = re.compile(
    r'(?:std\s*::\s*)?getenv\s*\(\s*(?!"[A-Za-z_])',
)


def scan_file_regex(filepath: str) -> List[EnvReference]:
    results = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        for lineno, line in enumerate(lines, 1):
            # Skip comment lines
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            for m in GETENV_RE.finditer(line):
                results.append(EnvReference(
                    variable=m.group(1),
                    file=filepath,
                    line=lineno,
                    method="getenv()",
                ))
            if GETENV_DYNAMIC_RE.search(line) and not GETENV_RE.search(line):
                results.append(EnvReference(
                    variable="<dynamic>",
                    file=filepath,
                    line=lineno,
                    method="getenv(expr)",
                    is_dynamic=True,
                ))
    except Exception:
        pass
    return results


# ── Tree-sitter scanner (if available) ────────────────────────────────────────
def scan_file_treesitter(filepath: str) -> Optional[List[EnvReference]]:
    """
    Use tree-sitter for accurate AST-based C++ scanning.
    Returns None if tree-sitter is not available.
    """
    try:
        import tree_sitter_cpp as tscpp
        from tree_sitter import Language, Parser

        CPP_LANGUAGE = Language(tscpp.language())
        parser = Parser(CPP_LANGUAGE)

        with open(filepath, "rb") as f:
            source = f.read()

        tree = parser.parse(source)
        results = []

        def traverse(node):
            if node.type == "call_expression":
                func = node.child_by_field_name("function")
                args = node.child_by_field_name("arguments")
                if func and args:
                    func_text = source[func.start_byte:func.end_byte].decode("utf-8", errors="ignore").replace(" ", "")
                    if func_text in ("getenv", "std::getenv"):
                        # Get first argument
                        string_nodes = [c for c in args.children if c.type == "string_literal"]
                        if string_nodes:
                            raw = source[string_nodes[0].start_byte:string_nodes[0].end_byte].decode("utf-8", errors="ignore")
                            key = raw.strip('"').strip("'")
                            results.append(EnvReference(
                                variable=key,
                                file=filepath,
                                line=string_nodes[0].start_point[0] + 1,
                                method=f"{func_text}()",
                            ))
                        else:
                            results.append(EnvReference(
                                variable="<dynamic>",
                                file=filepath,
                                line=func.start_point[0] + 1,
                                method=f"{func_text}(expr)",
                                is_dynamic=True,
                            ))
            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return results

    except ImportError:
        return None
    except Exception:
        return None


def scan_file(filepath: str) -> List[EnvReference]:
    result = scan_file_treesitter(filepath)
    if result is not None:
        return result
    return scan_file_regex(filepath)


def scan_directory(directory: str) -> List[EnvReference]:
    results = []
    extensions = {".cpp", ".cc", ".cxx", ".c", ".h", ".hpp", ".hxx"}
    skip_dirs = {".git", "node_modules", "build", "cmake-build-debug",
                 "cmake-build-release", ".cache"}
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for fname in files:
            if any(fname.endswith(ext) for ext in extensions):
                results.extend(scan_file(os.path.join(root, fname)))
    return results


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "."
    refs = scan_directory(path) if os.path.isdir(path) else scan_file(path)
    static = [r for r in refs if not r.is_dynamic]
    dynamic = [r for r in refs if r.is_dynamic]
    output = {
        "static": [
            {"variable": r.variable, "file": r.file,
             "line": r.line, "method": r.method}
            for r in static
        ],
        "dynamic": [
            {"file": r.file, "line": r.line, "method": r.method}
            for r in dynamic
        ],
    }
    print(json.dumps(output, indent=2))
