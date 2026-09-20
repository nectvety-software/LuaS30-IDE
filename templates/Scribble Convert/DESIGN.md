# DESIGN.md — Scribble Convert (internal)

## Style anchor
Vietnamese student squared-notebook (vở ô ly) physics/math homework page:
pencil-sketched frames, blue ballpoint annotations, red margin, faint handwritten
formulas. Not cute doodles — a real exercise worksheet on 240×320 QVGA.

## Palette
| Role | Hex | RGB |
|------|-----|-----|
| Paper bg | #FAF8EC | 250,248,236 |
| Rule line | #BAD0E4 | 186,208,228 |
| Margin red | #E6A8AC | 230,168,172 |
| Pencil frame | #6C6E78 | 108,110,120 |
| Pencil light | #A0A2AC | 160,162,172 |
| Blue ballpoint | #1E348C | 30,52,140 |
| Blue light | #5470C4 | 84,112,196 |
| Ink black | #161822 | 22,24,34 |
| Red pen | #C6262C | 198,38,44 |
| Shadow fill | #CED8E2 | 206,216,226 |

## Typography
- Title: `set_font(14)`, centered, double hand-underline (pen + pen2)
- Body/labels: `set_font(8)`
- Formulas: font 8, LEAD2, slight slant (handwritten note feel)

## Layout (240×320, 4px rhythm)
```
y=6    Title "DOI DON VI" + double underline
y=28   Category tabs: Do dai | Khoi luong | Tien te
y=48   [FROM pencil box]  --blue pen arrow-->  [TO pencil box]   h=56
y=116  Input sunken box (source value + unit)
y=152  Result sunken box (converted + unit)
y=192  Faint formula notes (2 lines)
y=224  Extra note / rate line (currency) or tip
y=298  Softkeys: Xoa | Thoat
```

## Signature moments
1. Two pencil rectangles + blue ballpoint arrow (core visual)
2. Sunken-ink number fields (inner shadow + hand outline)
3. Faint handwritten conversion formulas under the fields

## Interaction (Nokia keypad)
- OK/5: cycle focus CAT → FROM → TO → INPUT
- CAT: 4/6 switch category
- FROM/TO: 2/8 cycle unit; 4/6 jump between boxes
- INPUT: 0–9 type; clear/back delete one digit
- * or softleft: swap units; # : clear input
- softleft "Xoa" clear; softright "Thoat" exit
- Digit pressed from any focus → jump to INPUT and type

## Conversion model (offline, fixed)
- Length base m; mass base g; currency base VND (fixed local rates)
- factor = to_base[from] / to_base[to]; result = value * factor

## Manifest
- cover: none (single screen app)
- main: converter UI — needs no images (pure primitive sketch)
- Image manifest: no images; color/line only
