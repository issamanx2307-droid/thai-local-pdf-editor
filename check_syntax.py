import ast, pathlib, sys

root = pathlib.Path(r"D:\PDF editor")
results = []

# 1. Check all COLORS keys referenced in UI files exist in theme.py
import importlib.util, sys
sys.path.insert(0, str(root))
try:
    spec = importlib.util.spec_from_file_location("theme", root / "thai_pdf_editor/app/ui/theme.py")
    theme = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(theme)
    defined_colors = set(theme.COLORS.keys())
    defined_icons  = set(theme.ICON.keys())
    results.append(f"COLORS defined: {sorted(defined_colors)}")
    results.append(f"ICON defined:   {sorted(defined_icons)}")
except Exception as e:
    results.append(f"theme import ERROR: {e}")

# 2. Scan UI files for COLORS["key"] and check they exist
import re
missing_colors = []
for f in (root / "thai_pdf_editor").rglob("*.py"):
    if "__pycache__" in f.parts:
        continue
    src = f.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer(r'COLORS\["(\w+)"\]', src):
        key = m.group(1)
        if key not in defined_colors:
            missing_colors.append(f"  {f.relative_to(root)}: COLORS['{key}']")

if missing_colors:
    results.append(f"\nMissing COLORS keys ({len(missing_colors)}):")
    results += missing_colors
else:
    results.append("\nAll COLORS references OK")

# 3. Check ICON keys
missing_icons = []
for f in (root / "thai_pdf_editor").rglob("*.py"):
    if "__pycache__" in f.parts:
        continue
    src = f.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer(r'icon_label\("(\w+)"', src):
        key = m.group(1)
        if key not in defined_icons:
            missing_icons.append(f"  {f.relative_to(root)}: icon_label('{key}')")

if missing_icons:
    results.append(f"\nMissing ICON keys ({len(missing_icons)}):")
    results += missing_icons
else:
    results.append("All ICON references OK")

pathlib.Path(root / "syntax_result.txt").write_text("\n".join(results), encoding="utf-8")
