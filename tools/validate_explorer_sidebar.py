from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'studio/app/views/code_editor_view.py').read_text(encoding='utf-8')

checks = {
    'Explorer has a remembered non-zero width': 'DEFAULT_SIDEBAR_WIDTH = 220' in source and 'self._sidebar_width' in source,
    'Explorer splitter pane cannot be permanently collapsed by drag': 'self.workspace.setCollapsible(0, False)' in source,
    'Explorer activation repairs a zero-width splitter': 'QTimer.singleShot(0, self._apply_sidebar_width)' in source and 'def _apply_sidebar_width' in source,
    'Workspace restore sanitizes a saved zero width': 'restored[0] < self.MIN_SIDEBAR_WIDTH' in source,
    'Explorer width is persisted separately from raw splitter sizes': '"preferred_width": int(self._sidebar_width)' in source,
}

failed = False
for label, ok in checks.items():
    print(('PASS' if ok else 'FAIL') + ': ' + label)
    failed |= not ok

raise SystemExit(1 if failed else 0)
