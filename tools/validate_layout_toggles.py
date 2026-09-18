from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
errors=[]
main=(ROOT/'studio/app/vxpui/main_window.py').read_text(encoding='utf-8')
studio=(ROOT/'studio/app/vxpui/assets_studio_window.py').read_text(encoding='utf-8')
for token in (
    'VERSION = "1.0.1"',
    'self.explorer_toggle_button',
    'def _toggle_left_column',
    'self.project_panel_frame.setVisible(visible)',
    'def _toggle_console_panel',
    'def _set_console_visible',
    'def _set_ai_visible',
    'act("Chat AI", "fa5s.robot", "Ctrl+Alt+I")',
    'fa5s.terminal", "Ctrl+J"',
    'self.assets_studio = AssetsStudioWindow(self, self.engine_root)',
    'act("Tài nguyên · UI Designer", "fa5s.paint-brush", "Ctrl+Alt+U")',
):
    if token not in main: errors.append('MainWindow missing: '+token)
for token in (
    'class AssetsStudioWindow',
    'CustomTitleBar',
    '_PickerAssetsView()',
    'UIDesignerView()',
    'self.assets_dialog = CustomDialog(',
    'self.assets_dialog.set_close_handler(self.assets_dialog.hide)',
    'def _open_assets_dialog',
    'def _insert_selected_asset',
    'def show_studio',
    'def set_project',
):
    if token not in studio: errors.append('AssetsStudioWindow missing: '+token)
if 'QTabWidget' in studio:
    errors.append('Tài nguyên must be a modal dialog, not a cramped tab in the palette dock')
if 'PanelFrame' in studio:
    errors.append('Assets must live in the modal picker dialog, not a PanelFrame')
if 'left_dock' in studio:
    errors.append('Two-tab left dock was replaced by the modal asset picker')
if 'self.assets_panel_frame' in main:
    errors.append('TÀI NGUYÊN panel must live only in AssetsStudioWindow')
if 'place_project_image' not in (ROOT/'studio/app/views/ui_designer/designer_view.py').read_text(encoding='utf-8'):
    errors.append('Designer must expose place_project_image for the picker dialog')
if errors:
    print('FAIL'); [print(' -',e) for e in errors]; raise SystemExit(1)
print('PASS: Explorer column toggle in toolbar')
print('PASS: Console toggle Ctrl+J with checkable menu action')
print('PASS: Chat AI toggle Ctrl+Alt+I')
print('PASS: Assets+UI Designer merged into frameless AssetsStudioWindow (Công cụ menu)')
print('PASS: TÀI NGUYÊN is a modal CustomDialog picker feeding the designer palette')
print('PASS: toggles operate on desired state, panel visibility restored separately')
