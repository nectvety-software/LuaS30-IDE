# CatBoxMRE Boss Cutscene SVG

This update adds 12 SVG storyboard source files under:

`assets/svg_cutscenes/`

Files:
- moss_intro.svg
- moss_phase2.svg
- moss_victory.svg
- brute_intro.svg
- brute_phase2.svg
- brute_victory.svg
- phantom_intro.svg
- phantom_phase2.svg
- phantom_victory.svg
- warden_intro.svg
- warden_phase2.svg
- warden_victory.svg

The SVG files are production design sources for the 240x320 boss cutscene screens.
The game runtime still uses lightweight in-engine vector drawing for performance on Nokia 225,
but the compositions now match the dedicated SVG storyboard layouts more closely.

Design goals:
- 240x320 portrait safe area
- short text lines only
- large boss silhouette and cat silhouette
- one action badge in the center
- high contrast letterbox UI
- skip prompt on bottom bar

Bosses covered:
- Moss King
- Picnic Brute
- Phantom Keeper
- Sky Warden
