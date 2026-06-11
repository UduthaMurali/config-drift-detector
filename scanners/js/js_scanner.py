"""
JavaScript / TypeScript Scanner — Tree-sitter AST (with regex fallback)
Detects environment variable references in JS/TS source files.
Uses tree-sitter-javascript for accurate AST parsing; falls back to regex if unavailable.
"""
import os, re, sys, json
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class EnvReference:
    variable: str; file: str; line: int; method: str
    has_default: bool = False; is_dynamic: bool = False

# ── Regex fallback patterns ────────────────────────────────────────────────────
RE_DOT_ACCESS     = re.compile(r'process\.env\.([A-Za-z_][A-Za-z0-9_]*)\b')
RE_BRACKET_STATIC = re.compile(r'process\.env\[\s*["\`\'"]([A-Za-z_][A-Za-z0-9_]*)["\`\'"]\s*\]')
RE_BRACKET_DYN    = re.compile(r'process\.env\[\s*(?!["\`\'])[A-Za-z_$]')
RE_VITE_ENV       = re.compile(r'import\.meta\.env\.([A-Za-z_][A-Za-z0-9_]*)\b')
RE_NUXT_ENV       = re.compile(r'\$env\.([A-Za-z_][A-Za-z0-9_]*)\b')
VITE_SKIP         = {'MODE', 'BASE_URL', 'DEV', 'PROD', 'SSR'}

# ── Tree-sitter scanner ────────────────────────────────────────────────────────
def scan_file_treesitter(filepath: str) -> Optional[List[EnvReference]]:
    """AST-based scan using tree-sitter-javascript. Returns None if unavailable."""
    try:
        import tree_sitter_javascript as tsjs
        from tree_sitter import Language, Parser

        JS_LANGUAGE = Language(tsjs.language())
        parser = Parser(JS_LANGUAGE)

        with open(filepath, "rb") as f:
            source = f.read()

        tree = parser.parse(source)
        results = []

        def get_text(node):
            return source[node.start_byte:node.end_byte].decode("utf-8", errors="ignore")

        def traverse(node):
            # process.env.KEY  →  member_expression { object: member_expression{process.env}, property: KEY }
            if node.type == "member_expression":
                obj  = node.child_by_field_name("object")
                prop = node.child_by_field_name("property")
                if obj and prop:
                    obj_text = get_text(obj)
                    # process.env.KEY
                    if obj_text == "process.env":
                        key = get_text(prop)
                        if node.child_by_field_name("property") and prop.type == "property_identifier":
                            results.append(EnvReference(key, filepath, prop.start_point[0] + 1, "process.env.KEY"))
                    # import.meta.env.KEY
                    elif obj_text == "import.meta.env":
                        key = get_text(prop)
                        if prop.type == "property_identifier" and key not in VITE_SKIP:
                            results.append(EnvReference(key, filepath, prop.start_point[0] + 1, "import.meta.env.KEY"))

            # process.env["KEY"]  →  subscript_expression
            if node.type == "subscript_expression":
                obj   = node.child_by_field_name("object")
                index = node.child_by_field_name("index")
                if obj and index:
                    obj_text = get_text(obj)
                    if obj_text == "process.env":
                        if index.type in ("string", "template_string"):
                            raw = get_text(index).strip('"\'`')
                            if re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', raw):
                                results.append(EnvReference(raw, filepath, index.start_point[0] + 1, 'process.env["KEY"]'))
                            else:
                                results.append(EnvReference("<dynamic>", filepath, index.start_point[0] + 1, "process.env[expr]", is_dynamic=True))
                        else:
                            results.append(EnvReference("<dynamic>", filepath, index.start_point[0] + 1, "process.env[expr]", is_dynamic=True))

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
        for m in RE_DOT_ACCESS.finditer(line):
            results.append(EnvReference(m.group(1), filepath, lineno, 'process.env.KEY'))
        for m in RE_BRACKET_STATIC.finditer(line):
            results.append(EnvReference(m.group(1), filepath, lineno, 'process.env["KEY"]'))
        if RE_BRACKET_DYN.search(line):
            results.append(EnvReference('<dynamic>', filepath, lineno, 'process.env[expr]', is_dynamic=True))
        for m in RE_VITE_ENV.finditer(line):
            if m.group(1) not in VITE_SKIP:
                results.append(EnvReference(m.group(1), filepath, lineno, 'import.meta.env.KEY'))
        for m in RE_NUXT_ENV.finditer(line):
            results.append(EnvReference(m.group(1), filepath, lineno, '$env.KEY'))
    return results

def scan_file(filepath: str) -> List[EnvReference]:
    result = scan_file_treesitter(filepath)
    if result is not None:
        return result
    return scan_file_regex(filepath)

def scan_directory(directory):
    results = []
    EXTS = ('.js','.ts','.jsx','.tsx','.mjs','.cjs')
    skip = {'.git','node_modules','dist','build','.next','.nuxt','coverage','__pycache__','vendor'}
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in skip]
        for f in files:
            if any(f.endswith(e) for e in EXTS): results.extend(scan_file(os.path.join(root, f)))
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