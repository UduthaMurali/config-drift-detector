"""
Rust Scanner — Tree-sitter AST (with regex fallback)
Detects environment variable references in Rust source files.
Uses tree-sitter-rust for accurate AST parsing; falls back to regex if unavailable.
"""
import os, re, sys, json
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class EnvReference:
    variable: str; file: str; line: int; method: str
    has_default: bool = False; is_dynamic: bool = False

# ── Regex fallback patterns ────────────────────────────────────────────────────
RE_VAR_STATIC  = re.compile(r'(?:std::)?env::var(?:_os)?\(\s*"([A-Za-z_][A-Za-z0-9_]*)"\s*\)')
RE_VAR_DYNAMIC = re.compile(r'(?:std::)?env::var(?:_os)?\(\s*(?!"[A-Za-z_])')
RE_ENV_MACRO   = re.compile(r'\benv!\(\s*"([A-Za-z_][A-Za-z0-9_]*)"\s*\)')
RE_OPTION_ENV  = re.compile(r'\boption_env!\(\s*"([A-Za-z_][A-Za-z0-9_]*)"\s*\)')
RE_VARS_DYN    = re.compile(r'(?:std::)?env::vars(?:_os)?\(\s*\)')

# ── Tree-sitter scanner ────────────────────────────────────────────────────────
def scan_file_treesitter(filepath: str) -> Optional[List[EnvReference]]:
    """AST-based scan using tree-sitter-rust. Returns None if unavailable."""
    try:
        import tree_sitter_rust as tsrust
        from tree_sitter import Language, Parser

        RUST_LANGUAGE = Language(tsrust.language())
        parser = Parser(RUST_LANGUAGE)

        with open(filepath, "rb") as f:
            source = f.read()

        tree = parser.parse(source)
        results = []

        def get_text(node):
            return source[node.start_byte:node.end_byte].decode("utf-8", errors="ignore")

        def traverse(node):
            # env::var("KEY") / std::env::var("KEY") / env::var_os("KEY")
            if node.type == "call_expression":
                func = node.child_by_field_name("function")
                args = node.child_by_field_name("arguments")
                if func and args:
                    func_text = get_text(func).replace(" ", "")
                    # env::var / std::env::var / env::var_os / std::env::var_os
                    is_var    = func_text in ("env::var", "std::env::var", "env::var_os", "std::env::var_os")
                    is_vars   = func_text in ("env::vars", "std::env::vars", "env::vars_os", "std::env::vars_os")
                    if is_var:
                        str_nodes = [c for c in args.children if c.type == "string_literal"]
                        if str_nodes:
                            raw = get_text(str_nodes[0]).strip('"')
                            results.append(EnvReference(raw, filepath, str_nodes[0].start_point[0] + 1, "env::var()"))
                        else:
                            results.append(EnvReference("<dynamic>", filepath, func.start_point[0] + 1, "env::var(expr)", is_dynamic=True))
                    elif is_vars:
                        results.append(EnvReference("<dynamic>", filepath, func.start_point[0] + 1, "env::vars()", is_dynamic=True))

            # env!("KEY") macro invocation
            if node.type == "macro_invocation":
                macro_name = node.child_by_field_name("macro")
                if macro_name:
                    name = get_text(macro_name)
                    token_tree = node.child_by_field_name("token_tree") or \
                                 next((c for c in node.children if c.type == "token_tree"), None)
                    if name in ("env", "option_env") and token_tree:
                        str_nodes = [c for c in token_tree.children if c.type == "string_literal"]
                        if str_nodes:
                            raw = get_text(str_nodes[0]).strip('"')
                            has_default = (name == "option_env")
                            results.append(EnvReference(raw, filepath, str_nodes[0].start_point[0] + 1, f"{name}!()", has_default=has_default))

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
        s = line.strip()
        if s.startswith('//') or s.startswith('*'): continue
        for m in RE_VAR_STATIC.finditer(line):
            results.append(EnvReference(m.group(1), filepath, lineno, 'env::var()'))
        if RE_VAR_DYNAMIC.search(line) and not RE_VAR_STATIC.search(line) and 'env::var' in line:
            results.append(EnvReference('<dynamic>', filepath, lineno, 'env::var(expr)', is_dynamic=True))
        for m in RE_ENV_MACRO.finditer(line):
            results.append(EnvReference(m.group(1), filepath, lineno, 'env!()'))
        for m in RE_OPTION_ENV.finditer(line):
            results.append(EnvReference(m.group(1), filepath, lineno, 'option_env!()', has_default=True))
        if RE_VARS_DYN.search(line):
            results.append(EnvReference('<dynamic>', filepath, lineno, 'env::vars()', is_dynamic=True))
    return results

def scan_file(filepath: str) -> List[EnvReference]:
    result = scan_file_treesitter(filepath)
    if result is not None:
        return result
    return scan_file_regex(filepath)

def scan_directory(directory):
    results = []
    skip = {'.git','target','node_modules','__pycache__','test','tests','benches','examples'}
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in skip]
        for f in files:
            if f.endswith('.rs'): results.extend(scan_file(os.path.join(root, f)))
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