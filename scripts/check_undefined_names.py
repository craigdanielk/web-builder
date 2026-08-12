"""Cheap undefined-name check for the block just added to main().

A NameError on a rarely-taken branch is exactly what shipped `project_name`
into main(); `ast.parse` cannot catch it and there is no compile gate. This
walks main() and reports any Name load that is never assigned in main, never a
parameter, not a module-level binding and not a builtin.
"""
import ast
import builtins
import sys

src = open(sys.argv[1]).read()
tree = ast.parse(src)

module_level = set()
for node in tree.body:
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
            module_level.add(sub.id)
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        module_level.add(node.name)
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        for a in node.names:
            module_level.add((a.asname or a.name).split(".")[0])

func = [n for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == sys.argv[2]][0]

local = set()
for node in ast.walk(func):
    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
        local.add(node.id)
    elif isinstance(node, ast.arg):
        local.add(node.arg)
    elif isinstance(node, (ast.Import, ast.ImportFrom)):
        for a in node.names:
            local.add((a.asname or a.name).split(".")[0])
    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        local.add(node.name)
    elif isinstance(node, ast.ExceptHandler) and node.name:
        local.add(node.name)
    elif isinstance(node, (ast.comprehension,)):
        for sub in ast.walk(node.target):
            if isinstance(sub, ast.Name):
                local.add(sub.id)

known = local | module_level | set(dir(builtins))
lo, hi = int(sys.argv[3]), int(sys.argv[4])
bad = sorted({
    (node.lineno, node.id)
    for node in ast.walk(func)
    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    and node.id not in known and lo <= node.lineno <= hi
})
for line, name in bad:
    print(f"  UNDEFINED {name!r} at line {line}")
print(f"  {len(bad)} undefined name(s) in {sys.argv[2]}() lines {lo}-{hi}")
sys.exit(1 if bad else 0)
