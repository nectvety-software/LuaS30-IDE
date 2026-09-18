from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'studio/app/vxpui/main_window.py').read_text(encoding='utf-8')

checks = {
    'Explorer column has a declared minimum width':
        'LEFT_COLUMN_MIN_WIDTH = 190' in source
        and 'left_column.setMinimumWidth(190)' in source,
    'Explorer splitter pane cannot be permanently collapsed by drag':
        'split.setChildrenCollapsible(False)' in source,
    'Workspace restore repairs a zero-width saved column':
        'def _restore_workspace_layout_state' in source
        and 'if restored and restored[0] < minimum:' in source,
    'Workspace restore sanitizes a saved zero width':
        'restored = [max(0, int(value)) for value in sizes]' in source,
    'Workspace sizes are persisted alongside raw panel state':
        '"sizes": self.workspace_split.sizes()' in source,
    'Splitter drags schedule a workspace session save':
        'pane.splitterMoved.connect' in source,
}

failed = False
for label, ok in checks.items():
    print(('PASS' if ok else 'FAIL') + ': ' + label)
    failed |= not ok

raise SystemExit(1 if failed else 0)
