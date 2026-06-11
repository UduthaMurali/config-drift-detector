"""
Go Scanner — Tree-sitter AST (with regex fallback)
Detects environment variable references in Go source files.
Uses tree-sitter-go for accurate AST parsing; falls back to regex if unavailable.
"""
import os, re, sys, json
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class EnvReference:
    variable: str; file: str; line: int; method: str
    has_default: bool = False; is_dynamic: bool = False

# ── Regex fallback patterns ────────────────────────────────────────────────────
RE_GETENV_STATIC  = re.compile(r'os\.Getenv\(\s*"([A-Za-z_][A-Za-z0-9_]*)"\s*\)')
RE_GETENV_DYNAMIC = re.compile(r'os\.Getenv\(\s*(?!"[A-Za-z_])')
RE_LOOKUP_STATIC  = re.compile(r'os\.LookupEnv\(\s*"([A-Za-z_][A-Za-z0-9_]*)"\s*\)')
RE_LOOKUP_DYNAMIC = re.compile(r'os\.LookupEnv\(\s*(?!"[A-Za-z_])')
RE_EXPAND_ENV     = re.compile(r'os\.ExpandEnv\(\s*"([^"]*)"\s*\)')
RE_DOLLAR_VAR     = re.compile(r'\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?')

# ── Tree-sitter scanner ────────────────────────────────────────────────────────
def scan_file_treesitter(filepath: str) -> Optional[List[EnvReference]]:
    """AST-based scan using tree-sitter-go. Returns None if unavailable."""
    try:
        import tree_sitter_go as tsgo
        from tree_sitter import Language, Parser

        GO_LANGUAGE = Language(tsgo.language())
        parser = Parser(GO_LANGUAGE)

        with open(filepath, "rb") as f:
            source = f.read()

        tree = parser.parse(source)
        results = []

        # Target functions: os.Getenv, os.LookupEnv, os.ExpandEnv
        TARGET_SELECTORS = {
            ("os", "Getenv"):    ("os.Getenv()",    False),
            ("os", "LookupEnv"): ("os.LookupEnv()", True),   # has_default (ok/err return)
            ("os", "ExpandEnv"): ("os.ExpandEnv()", False),
        }

        def traverse(node):
            if node.type == "call_expression":
                func = node.child_by_field_name("function")
                args = node.child_by_field_name("arguments")
                if func and func.type == "selector_expression" and args:
                    operand = func.child_by_field_name("operand")
                    field   = func.child_by_field_name("field")
                    if operand and field:
                        pkg  = source[operand.start_byte:operand.end_byte].decode("utf-8", errors="ignore")
                        fn   = source[field.start_byte:field.end_byte].decode("utf-8", errors="ignore")
                        key  = (pkg, fn)
                        if key in TARGET_SELECTORS:
                            method, has_default = TARGET_SELECTORS[key]
                            # First string argument
                            str_nodes = [c for c in args.children if c.type == "interpreted_string_literal"]
                            if str_nodes:
                                raw = source[str_nodes[0].start_byte:str_nodes[0].end_byte].decode("utf-8", errors="ignore").strip('"')
                                if fn == "ExpandEnv":
                                    for v in RE_DOLLAR_VAR.finditer(raw):
                                        results.append(EnvReference(v.group(1), filepath, str_nodes[0].start_point[0] + 1, method))
                                else:
                                    results.append(EnvReference(raw, filepath, str_nodes[0].start_point[0] + 1, method, has_default=has_default))
                            else:
                                results.append(EnvReference("<dynamic>", filepath, func.start_point[0] + 1, f"{method[:-1]}expr)", is_dynamic=True))
            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return results

    except ImportError:
        return None
    except Exception:
        return None

# ── Regex fallback ─────────────────────────────────────────────────────────────
def scan_file_regex(filepath: str) -> List[EnvReference]:
    results = []
    try:
        lines = open(filepath, 'r', encoding='utf-8', errors='ignore').readlines()
    except:
        return []
    for lineno, line in enumerate(lines, 1):
        if line.strip().startswith('//'): continue
        for m in RE_GETENV_STATIC.finditer(line):
            results.append(EnvReference(m.group(1), filepath, lineno, 'os.Getenv()'))
        if RE_GETENV_DYNAMIC.search(line) and not RE_GETENV_STATIC.search(line) and 'os.Getenv' in line:
            results.append(EnvReference('<dynamic>', filepath, lineno, 'os.Getenv(expr)', is_dynamic=True))
        for m in RE_LOOKUP_STATIC.finditer(line):
            results.append(EnvReference(m.group(1), filepath, lineno, 'os.LookupEnv()'))
        if RE_LOOKUP_DYNAMIC.search(line) and not RE_LOOKUP_STATIC.search(line) and 'os.LookupEnv' in line:
            results.append(EnvReference('<dynamic>', filepath, lineno, 'os.LookupEnv(expr)', is_dynamic=True))
        for m in RE_EXPAND_ENV.finditer(line):
            for v in RE_DOLLAR_VAR.finditer(m.group(1)):
                results.append(EnvReference(v.group(1), filepath, lineno, 'os.ExpandEnv()'))
    return results

def scan_file(filepath: str) -> List[EnvReference]:
    result = scan_file_treesitter(filepath)
    if result is not None:
        return result
    return scan_file_regex(filepath)

def scan_directory(directory):
    results = []
    skip = {'.git','vendor','testdata','test','tests','__pycache__','node_modules'}
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in skip]
        for f in files:
            if f.endswith('.go'): results.extend(scan_file(os.path.join(root, f)))
    return results

if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else '.'
    refs = scan_directory(path) if os.path.isdir(path) else scan_file(path)
    static = [r for r in refs if not r.is_dynamic]
    dynamic = [r for r in refs if r.is_dynamic]
    print(json.dumps({
        'static':  [{'variable':r.variable,'file':r.file,'line':r.line,'method':r.method,'has_default':r.has_default} for r in static],
        'dynamic': [{'file':r.file,'line':r.line,'method':r.method} for r in dynamic],
    }, indent=2))