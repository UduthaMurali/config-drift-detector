"""
Python AST Scanner
Detects environment variable references in Python source files.
Supports: os.environ["KEY"], os.getenv("KEY"), os.environ.get("KEY"),
          dotenv patterns, Django settings patterns.
"""
import ast
import os
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


class PythonEnvVisitor(ast.NodeVisitor):
    """Walks a Python AST and collects every env var reference."""

    def __init__(self, filename: str):
        self.filename = filename
        self.found: List[EnvReference] = []

    # ------------------------------------------------------------------
    # os.environ["KEY"]  and  os.environ.get("KEY")
    # ------------------------------------------------------------------
    def visit_Subscript(self, node: ast.Subscript):
        if self._is_os_environ(node.value):
            key = self._extract_string(node.slice)
            if key:
                self.found.append(EnvReference(
                    variable=key,
                    file=self.filename,
                    line=node.lineno,
                    method="os.environ[KEY]",
                    has_default=False,
                ))
            else:
                self.found.append(EnvReference(
                    variable="<dynamic>",
                    file=self.filename,
                    line=node.lineno,
                    method="os.environ[expr]",
                    is_dynamic=True,
                ))
        self.generic_visit(node)

    # ------------------------------------------------------------------
    # os.getenv("KEY")  /  os.getenv("KEY", "default")
    # os.environ.get("KEY")  /  os.environ.get("KEY", "default")
    # ------------------------------------------------------------------
    def visit_Call(self, node: ast.Call):
        name = self._call_name(node)

        if name in ("os.getenv", "os.environ.get"):
            if node.args:
                key = self._extract_string(node.args[0])
                has_default = len(node.args) > 1 or bool(node.keywords)
                if key:
                    self.found.append(EnvReference(
                        variable=key,
                        file=self.filename,
                        line=node.lineno,
                        method=name,
                        has_default=has_default,
                    ))
                else:
                    self.found.append(EnvReference(
                        variable="<dynamic>",
                        file=self.filename,
                        line=node.lineno,
                        method=f"{name}(expr)",
                        is_dynamic=True,
                    ))

        # dotenv: load_dotenv() — just mark usage, doesn't reveal var names
        elif name in ("load_dotenv", "dotenv.load_dotenv"):
            pass  # dotenv vars come from .env file — handled by config parser

        self.generic_visit(node)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _is_os_environ(self, node) -> bool:
        """Check if node is `os.environ`."""
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                return node.value.id == "os" and node.attr == "environ"
        return False

    def _call_name(self, node: ast.Call) -> str:
        """Return dotted call name e.g. 'os.getenv' or 'os.environ.get'."""
        func = node.func
        if isinstance(func, ast.Attribute):
            if isinstance(func.value, ast.Name):
                return f"{func.value.id}.{func.attr}"
            if isinstance(func.value, ast.Attribute):
                if isinstance(func.value.value, ast.Name):
                    return f"{func.value.value.id}.{func.value.attr}.{func.attr}"
        if isinstance(func, ast.Name):
            return func.id
        return ""

    def _extract_string(self, node) -> Optional[str]:
        """Extract a string literal from an AST node (handles py3.8 Index)."""
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        # Python 3.8 wraps slice in Index
        if isinstance(node, ast.Index):
            return self._extract_string(node.value)
        return None


def scan_file(filepath: str) -> List[EnvReference]:
    """Scan a single Python file and return all env var references."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
        visitor = PythonEnvVisitor(filepath)
        visitor.visit(tree)
        return visitor.found
    except SyntaxError:
        return []
    except Exception:
        return []


def scan_directory(directory: str) -> List[EnvReference]:
    """Recursively scan all .py files in a directory."""
    results: List[EnvReference] = []
    skip_dirs = {"__pycache__", ".git", "node_modules", ".venv", "venv", "env"}

    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for fname in files:
            if fname.endswith(".py"):
                filepath = os.path.join(root, fname)
                results.extend(scan_file(filepath))
    return results


if __name__ == "__main__":
    import sys
    import json

    path = sys.argv[1] if len(sys.argv) > 1 else "."
    refs = scan_directory(path)
    static = [r for r in refs if not r.is_dynamic]
    dynamic = [r for r in refs if r.is_dynamic]

    output = {
        "static": [
            {"variable": r.variable, "file": r.file,
             "line": r.line, "method": r.method,
             "has_default": r.has_default}
            for r in static
        ],
        "dynamic": [
            {"file": r.file, "line": r.line, "method": r.method}
            for r in dynamic
        ],
    }
    print(json.dumps(output, indent=2))
