# -*- coding: utf-8 -*-
"""v1.14.248 — مرحلهٔ ۷a: حذفِ کدِ مرده (manga.py + manga_app.py) با AST + لنگرهای رشته‌ای"""
import ast

# ═════════════════════════ manga.py ═════════════════════════
P = '/home/z/manga-work/manga.py'
src = open(P, encoding='utf-8').read()

DEAD_FUNCS = {
    'k3_schema_json', '_ort_providers', '_gpu_vendor', '_android_heal_model_dir',
    'classify_batch', '_want_english_only', '_dedupe_detections',
    'group_into_regions', '_deduplicate_regions', '_letters_mask_in_crop',
    '_panel_leftover_stats', '_merge_overlap_final_regions', 'test_api_key',
    'process_image_file',
}
DEAD_CONSTS = {'_SPEED_LAB_EP', '_SPEED_LAB_LADDER', 'PUNCTUATION_SET', 'PURE_HANGUL_SFX_RE'}

tree = ast.parse(src)
spans = []
for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in DEAD_FUNCS:
        start = min([node.lineno] + [d.lineno for d in node.decorator_list])
        spans.append((start, node.end_lineno, node.name))
    elif isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id in DEAD_CONSTS:
                spans.append((node.lineno, node.end_lineno, t.id))

found = {s[2] for s in spans}
assert found == DEAD_FUNCS | DEAD_CONSTS, f"missing: {DEAD_FUNCS | DEAD_CONSTS - found}"

lines = src.split('\n')
removed = 0
for start, end, name in sorted(spans, reverse=True):
    removed += end - start + 1
    print(f"  ✓ manga.py: {name} (L{start}-L{end}, {end - start + 1} خط)")
    del lines[start - 1:end]
src = '\n'.join(lines)

# ── زنجیرهٔ مردهٔ _strip_boundaries (نوشته میشود، هرگز خوانده نمیشود) + لولهکشی bounds ──
def rep(old, new, desc):
    global src
    n = src.count(old)
    assert n == 1, f"[{desc}] found {n}"
    src = src.replace(old, new, 1)
    print(f"  ✓ manga.py: {desc}")

rep('        if not hasattr(self, "_strip_boundaries"):\n'
    '            self._strip_boundaries = {}\n'
    '        self._strip_boundaries = {}\n', '', '_strip_boundaries init')
rep('        def _emit_array(arr: np.ndarray, bounds: List[int], label: str = "") -> None:\n',
    '        def _emit_array(arr: np.ndarray, label: str = "") -> None:\n', '_emit_array signature')
rep('            self._write_image(arr, out_path)\n'
    '            if bounds:\n'
    '                kept = [b for b in bounds if 0 < b < arr.shape[0] - 20]\n'
    '                if kept:\n'
    '                    self._strip_boundaries[out_path] = kept\n'
    '            result.append(out_path)\n',
    '            self._write_image(arr, out_path)\n'
    '            result.append(out_path)\n', '_strip_boundaries write')
rep('                bounds = [b - offset for b in current_bounds if offset < b < cut_y]\n'
    '                _emit_array(strip[offset:cut_y], bounds, f"برش بررسی‌شده y={cut_y}")\n',
    '                _emit_array(strip[offset:cut_y], f"برش بررسی‌شده y={cut_y}")\n',
    'cut emit bounds')
rep('            current_h = ih - offset\n'
    '            current_bounds = [b - offset for b in current_bounds if b > offset]\n',
    '            current_h = ih - offset\n', 'current_bounds reassign')
rep('                _emit_array(strip[offset:], current_bounds, label)\n'
    '                current_pages, current_h, current_bounds = [], 0, []\n',
    '                _emit_array(strip[offset:], label)\n'
    '                current_pages, current_h = [], 0\n', 'final emit bounds')
rep('        current_pages: List[np.ndarray] = []\n'
    '        current_h = 0\n'
    '        current_bounds: List[int] = []\n',
    '        current_pages: List[np.ndarray] = []\n'
    '        current_h = 0\n', 'current_bounds init')
rep('            if current_pages:\n'
    '                current_bounds.append(current_h)\n'
    '            current_pages.append(im)\n',
    '            current_pages.append(im)\n', 'current_bounds append')
rep('            nonlocal current_pages, current_h, current_bounds, current_protected, scan_from\n',
    '            nonlocal current_pages, current_h, current_protected, scan_from\n',
    'nonlocal current_bounds')

open(P, 'w', encoding='utf-8').write(src)
print(f"manga.py: {removed} خطِ تابع/ثابت + زنجیرهٔ strip_boundaries حذف شد\n")

# ═════════════════════════ manga_app.py ═════════════════════════
P2 = '/home/z/manga-work/manga_app.py'
src = open(P2, encoding='utf-8').read()
orig = len(src)

DEAD_FUNCS2 = {'_cm_choices', 'system_info', 'history_text', 'open_path'}
DEAD_CONSTS2 = {'HELP_TEXT', 'C_BG', 'C_BG2', 'C_CARD', 'C_LINE', 'C_TXT',
                'C_MUT', 'C_ACC', 'ACCENT', 'C_OK', 'C_ERR'}

tree = ast.parse(src)
spans = []
for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in DEAD_FUNCS2:
        start = min([node.lineno] + [d.lineno for d in node.decorator_list])
        spans.append((start, node.end_lineno, node.name))
    elif isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id in DEAD_CONSTS2:
                spans.append((node.lineno, node.end_lineno, t.id))
found = {s[2] for s in spans}
assert found == DEAD_FUNCS2 | DEAD_CONSTS2, f"missing: {DEAD_FUNCS2 | DEAD_CONSTS2 - found}"

lines = src.split('\n')
removed2 = 0
for start, end, name in sorted(spans, reverse=True):
    removed2 += end - start + 1
    print(f"  ✓ manga_app.py: {name} (L{start}-L{end}, {end - start + 1} خط)")
    del lines[start - 1:end]
src = '\n'.join(lines)

def rep2(old, new, desc):
    global src
    n = src.count(old)
    assert n == 1, f"[{desc}] found {n}"
    src = src.replace(old, new, 1)
    print(f"  ✓ manga_app.py: {desc}")

rep2('import json\nimport os\nimport queue\nimport re\n',
     'import json\nimport os\nimport re\n', 'import queue')
rep2('        browser_form_json = gr.State("")\n\n', '', 'browser_form_json State')

open(P2, 'w', encoding='utf-8').write(src)
print(f"manga_app.py: {removed2} خط + دو موردِ رشته‌ای حذف شد ({orig - len(src)} کاراکتر)")
