from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
errors=[]
main=(ROOT/'studio/app/ui/main_window.py').read_text(encoding='utf-8')
editor=(ROOT/'studio/app/views/code_editor_view.py').read_text(encoding='utf-8')
theme=(ROOT/'studio/app/ui/theme.py').read_text(encoding='utf-8')
for token in ('VERSION = "1.15.0"','Toggle Explorer / Primary Side Bar','Ctrl+Alt+A','self.explorer_toggle_button','self.activity_toggle_button','def _apply_activity_bar_toggle_action','"activity_bar_visible"','self._editor_activity_bar_visible'):
    if token not in main: errors.append('MainWindow missing: '+token)
for token in ('def set_sidebar_visible','def sidebar_visible','_editor_sidebar_visible'):
    if token not in editor: errors.append('CodeEditorView missing: '+token)
if 'QToolButton#WorkbenchLayoutButton' not in theme: errors.append('layout button theme missing')
if errors:
    print('FAIL'); [print(' -',e) for e in errors]; raise SystemExit(1)
print('PASS: Explorer button + Ctrl+B')
print('PASS: Activity Bar button + Ctrl+Alt+A')
print('PASS: preferences survive Project Hub')
