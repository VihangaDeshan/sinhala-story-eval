# SSEF design system: "Ola"

The interface takes its cues from ola-leaf manuscripts: warm paper, dark ink and one turmeric-ochre accent. It is a reading tool, so the story and the four scores carry the page and the chrome stays quiet. Every value below is a CSS custom property in `app/static/style.css`.

## Principles

1. **Restraint.** Colour carries meaning only. Hierarchy comes from size, weight and space.
2. **No verdict colours.** Scores are always ink-coloured. Red appears only on rejected input and form errors, and green is not used.
3. **Sinhala first.** Sinhala gets a real font (Noto Sans Sinhala), extra line height for vowel signs, and slightly larger small text.
4. **No third parties.** Fonts are served from `/static/fonts`, so the page makes no request to any other server.

## Colour

| Token | Light | Dark | Use |
|---|---|---|---|
| `--paper` | `#F6F2E9` | `#14120F` | Page background |
| `--surface` | `#FFFDF9` | `#1C1915` | Cards, inputs |
| `--surface-2` | `#F0EADD` | `#24201B` | Guides, inner panels, dialogue spans |
| `--surface-3` | `#E7DFCF` | `#2E2922` | Hover, selected segment |
| `--line` | `#E2D9C8` | `#36302A` | Card outlines, dividers |
| `--line-strong` | `#CBBDA5` | `#4C443A` | Input borders, dialogue-span outline |
| `--ink` | `#1C1915` | `#F3EDE2` | Headings, score numbers, primary button |
| `--text` | `#2B2621` | `#E3DCCF` | Body text |
| `--text-2` | `#564E44` | `#B9AFA0` | Secondary text, labels |
| `--text-3` | `#6C6357` | `#9A9083` | Captions, evidence notes, footer |
| `--accent` | `#B9822A` | `#D8A243` | Active nav, focus ring, brand mark, spoken-form highlight |
| `--accent-text` | `#845C17` | `#E4B860` | Links |
| `--accent-tint` | `#F5E5C1` | `#3B2E17` | Spoken-form highlight, length notice |
| `--slate` / `--slate-tint` | `#3F5B74` / `#E1E7EC` | `#A3BACE` / `#1F2933` | Literary-form highlight only |
| `--error` / `--error-tint` | `#A3392A` / `#FBECE7` | `#EC8E7B` / `#3A201B` | Rejected input and form errors only |

Every text/background pair meets WCAG AA. The lowest is `--text-3` on `--surface-2`, at 4.9:1 in light and 5.2:1 in dark.

**Dark theme.** It follows the system setting until the viewer presses the theme button. The choice is then saved in `localStorage` (`ssef-theme`) in that browser only, by `app/static/theme.js`.

## Type

| Role | Family | Notes |
|---|---|---|
| Display: page title, card titles, story text | Abhaya Libre 400/600/700 (Mooniak) | Sinhala and Latin serif, successor to FM Abhaya |
| Interface and body (Latin) | Inter variable | `tabular-nums` on every number |
| Interface and body (Sinhala) | Noto Sans Sinhala variable | Matched to Latin Noto/Inter in height and stroke |

Scale: 12 · 13 · 15 (base) · 16 · 19 · 24 · 32 · 40 px (score).
Line height: 1.55 for the interface, 1.7 for Sinhala interface text, 1.75 for reading, and 1.95 for the story view.

All three fonts are under the SIL Open Font License; the licence files are in `app/static/fonts/`.

## Space, shape, depth

- **Space:** a 4 px grid (`--s-1` … `--s-12`: 4, 8, 12, 16, 20, 24, 32, 40, 48).
- **Radii:** 4 px for tags, 8 px for inputs and buttons, 12 px for cards.
- **Depth:** `--shadow-1` is a hairline lift used on cards; `--shadow-2` is used only on the sign-in card.
- **Motion:** 120 ms colour transitions, and a 260 ms staggered rise when the score cards appear. All motion is switched off under `prefers-reduced-motion`.

## Layout

- **Desktop (above 1080 px):**
  - The story input sits in a left column, and the results in a right column.
  - The right column opens with the input instructions expanded (ochre panel) and "How to read these results" collapsed. After a successful evaluation they swap: the instructions collapse and "How to read" opens above the scores. A rejected input reopens the instructions. Either panel can still be opened or closed by hand.
  - Results show three compact cards (fluency, coherence, lexical diversity), then the register (DARC) card across the full width with its sub-scores beside the score.
  - The composite comes next, in a dashed, quieter box.
  - The annotated story sits below both columns, across the full page width. Its heading, colour key and text are centred in a 900 px reading column.
- **Below 1080 px:** one column, with the input first.
- **Below 640 px:**
  - The nav uses two rows: brand, language and theme on the first; page links on the second.
  - Cards stack in one column, and there is no horizontal scroll at 360 px.

## Story highlights

| Span | Fill | Mark |
|---|---|---|
| Dialogue | `--surface-2` | 1 px `--line-strong` outline |
| Spoken form in narration | `--accent-tint` | 2 px solid `--accent` underline |
| Literary form in dialogue | `--slate-tint` | 2 px dotted `--slate` underline |

The three styles differ in fill, hue and line style, so they stay distinguishable without colour vision.
