# Figure design system v7: binding for Figures 1–6, S1–S10 and the graphical abstract

**Status.** This is the binding spec for every v7 figure. Where it differs from `RESTRAINT.md` or `DESIGN_V6.md`
(both copied here from v6), **this file wins**. Where it is silent, `RESTRAINT.md` still applies.

**Worked example.** `fig1/` is the reference figure. Every rule below is implemented there; §13 maps each rule to its
file.

**Basis.** The bake-off of three figure skills was judged on the author's taste, Nature art direction and clarity.

- **Winner:** "sciplot" (github.com/mmd-ahd/scientific-figure-skill). We use its clean-nature theme with Arial in place
  of Inter, its schematic rules, and its rule "grey for context, colour for signal".
- **From FigGenie:** nested, labelled regions in schematics, and no empty boxes.
- **From nature-figure:** the figure contract (one hero panel, each panel a distinct inferential role), the
  panel-alignment and text-collision QA, and pre-mixed tinted regions that mark the key area of a plot.
- **Implementation:** each skill's text was read and its guidance re-implemented in `style/` and `fig1/`. No skill
  script was ever executed.

**The author's taste.**

- **Target:** refined, crafted, journal-grade figures. They should sit beside the author's Nature Computational Science
  exemplars in `references/ncs_papers/figpages/`:
  - AlignIF, `s43588-026-01029-2-p02`;
  - DIPPER, `s43588-026-01015-8-p02`;
  - MIRACLE, `s43588-026-01030-9-p02`;
  - NEP89, `s43588-026-01009-6-p04`.
- **Rejected:**
  - rounded pastel cards with app icons;
  - 3-D or isometric drawings;
  - ribbons and Sankey flows;
  - magazine headlines and hero numbers;
  - dense number tables.
- **v6 verdict:** "good ideas, thorough, but not aesthetically pleasing, too basic". v7 adds craft (nesting, faint
  grounds, numerals, a filled key area), not volume. **Refined, never busy.**

---

## 0. What changed from v6

| topic | v6 (RESTRAINT) | v7 |
|---|---|---|
| axes | thin full box, 0.5 pt, `#222222` | open L axes (left and bottom spines), 0.6 pt, `SP_AXIS` `#3d434b` |
| type | 7 pt words, 6.5 pt ticks, 8.5 pt letters | 7 pt words, **6 pt** ticks and notes, **8 pt** bold lowercase letters |
| text colour | black | `SP_FG` `#1f2328`; tick labels `SP_AXIS`; secondary text `SP_MUTED` `#6b7280` |
| data strokes and marks | lines 1.3 pt, markers about 4.5 pt | lines 1.0 pt, markers 3.5 pt |
| tints | white only; a tint only as an error band | pre-mixed OKLab tints (§3.3), each with one meaning; never alpha |
| lanes and regions | banned | very faint grounds for regions (schematics) and for the lanes that repeat them (traces) |
| schematic numerals | banned (no numbered discs) | small **outlined** brick rings with a 6 pt digit (§7.4); filled discs stay banned |
| schematic structure | flat line art | nested labelled regions, at most three levels (§7.1) |
| panel style entry | `fs.style_context()` | `fs.v7_context()` |
| QA | trace, qa_check, palette, skill screen | the same, plus the text-collision audit and the colour-aware note rule; one 200 dpi review PNG |

---

## 1. Figure contract (nature-figure)

1. **One claim per figure.** The caption title states it as a sentence with a verb, for example "Consent is lost at
   five points between the cookie banner and Shopify's sandboxed pixels."
2. **One hero panel.** It carries the claim and gets the most area: full width, or about 35–60 % of the figure. The
   other panels are visually quieter.
3. **Each panel has a distinct inferential role.**
   - The roles are: mechanism, one instance, the population, the comparison, the control or robustness.
   - Write the role in the panel script's docstring.
   - If covering a panel would not weaken the argument, merge it or move it to the supplement.
   - In Fig. 1, a is the mechanism (hero), b one instance and c the population.
4. **Five-second test.** Each panel's point must be clear without reading the text inside it.
5. **Kept invariants.**
   - Panel letters and panel contents stay as they are; the paper cites them.
   - Every number is traceable (§11).
   - Store C stays anonymous.
   - Scales are honest.
   - Numbers live mostly in the caption.

## 2. Typography

- **One family: Arial.**
  - matplotlib `font.sans-serif: Arial`, with `pdf.fonttype 42`.
  - TikZ uses `fontspec` Arial, falling back to TeX Gyre Heros.
  - Text stays live and embedded as Type 42. Never outline text.
- **Three sizes only** (`figstyle.FS`, mirrored in `palette_v2.tex` as `\figFs*` and in the TikZ macros):

| size | used for | macro / key |
|---|---|---|
| 8 pt bold | panel letters a, b, c, lowercase; drawn by the composite `\Panel` | `FS['letter']`, `\fsLetter` |
| 7 pt | words: axis titles, row and lane labels, direct labels, the key, schematic box text, region names | `FS['axis'/'label'/'cat'/'legend']`, `\fsLabel` |
| 6 pt | tick labels; muted secondary text (`SP_MUTED` only); the loss numerals | `FS['tick'/'note'/'numeral']`, `\fsTick`, `\fsNote`, `\fsNumeral` |

- **Floor 6 pt.** `qa_check` FAILs anything smaller.
- **Weight makes no hierarchy.** Only the letters are bold. No panel titles, no headlines, no hero numbers.
- **Text colours:**
  - `SP_FG` `#1f2328` for words and the numeral digits;
  - `SP_AXIS` `#3d434b` for tick labels;
  - `SP_MUTED` `#6b7280` for secondary text: region names (7 pt) and qualifiers or lists inside a box (6 pt);
  - the letters are `#000000`;
  - **never** text in LEAK, EVENT, NEUTRAL, a tint or a vendor hue.
- **Sentence case.** Units go in parentheses, e.g. 'Time from banner visible (s)'.
- **Signs and ranges.** Use the typographic minus (U+2212). Times relative to an event get signed ticks (`+2`).
  Ranges use an en dash.
- **Venue note.** Elsevier asks for about 7 pt lettering. 6 pt is the sciplot Nature tick size that v7 adopts. Confirm
  it against the C&S Guide for Authors before submission (the skill screen prints this reminder).

## 3. Colour

### 3.1 Roles (one meaning each, the same in every figure)

| token | hex | meaning | allowed as |
|---|---|---|---|
| `LEAK` brick | `#c65358` | **consent lost**: requests that lost consent, leak paths, loss numerals (ring only), the protagonist series | marks, lines, rings, its tint; never text (4.4:1) |
| `HONOUR` slate | `#5d769d` | **the comparison**: consent honoured, the no-banner group, the comparison series | marks, lines; double-coded by shape |
| `EVENT` amber | `#e8a33a` | **the consent moment**: banner visible, Decline click, GPC, a CMP write | one rule per event, always named or on a labelled tick; the banner box outline and its tint; never text |
| `THIRD` lavender | `#b788ca` | a third series, only if needed | marks |
| vendor hexes (`colors.py`) | fixed | vendor identity, **only where vendors are the categories** | never in a panel with LEAK, HONOUR or EVENT |

### 3.2 Neutrals ("grey for context, colour for signal")

| token | hex | role |
|---|---|---|
| `SP_FG` | `#1f2328` | text, the script-blocker wall and its miniature |
| `SP_AXIS` | `#3d434b` | spines, ticks, tick labels, schematic box outlines, connectors |
| `SP_MUTED` | `#6b7280` | secondary text (4.8:1) |
| `NEUTRAL` | `#a0a0a0` | context lines: region frames, the stopped wire, the dotted cut path, leaders, context series |
| `SP_CONTEXT` | `#b9bec5` | dense context marks (the raster's request ticks) |
| `LIGHT` | `#d9d9d9` | decorative rules, absent cells |
| `SAND` | `#3b4656` | the sandbox: its region outline; a solid fill where the sandbox is a category in bars |

- **Colours per panel.** At most five, neutrals and tints excluded. Draw everything grey first, then colour only what
  the panel's message is about.
- **More series of one family** take shades of one hue, or small multiples, never new hues.

### 3.3 Pre-mixed tints (never alpha)

A tint is its token mixed with white in OKLab. Use `figstyle.TINT`; it is written to `palette_v2.tex` as `TINT*`. A
tint keeps its token's meaning.

| tint | hex | mix | the one use |
|---|---|---|---|
| `TINT['EVENT']` | `#fbeddb` | EVENT, t = 0.80 | the cookie-banner box (the consent UI whose appearance is the amber rule) |
| `TINT['SAND']` | `#e9ebed` | SAND, t = 0.90 | the pixel-sandbox region (schematic) **and** the sandbox lane (trace) |
| `TINT['PAGE']` | `#f4f5f6` | SAND, t = 0.95 | the page (main-thread) region **and** the page lane: one step lighter than SAND |
| `TINT['LEAK']` | `#fbeeed` | LEAK, t = 0.90 | the key area of a plot where consent was lost (Fig. 1c: before the banner) |

**Rules for tints**

- **Grounds are very faint** (L\* ≥ 93) and sit **under** every mark.
  - In plots they are square, with no outline.
  - In schematics they are region fills with a 0.6 pt outline (§7.1).
- **A lane repeats its region.** A trace lane takes exactly the ground of the schematic region it stands for; it never
  takes a new tint.
- **A key area** (nature-figure) follows the drawn data exactly. In Fig. 1c it is a polygon on the line's own vertices,
  bounded by the event rule. Name it in the caption.
- **Error bands** use a tint of the line's colour, at t = 0.80, added to `TINT`. Never use `BAND_ALPHA`.
- **Budget.** At most three grounds per panel. Never a ground behind running text other than a region name or label.
- **Adding a tint** takes three steps:
  1. add it to `figstyle.TINT` with its t and its meaning;
  2. run `python3 style/figstyle.py --write-tex --selftest`;
  3. add a row to the table above.

  `palette_gate` and `qa_check` pick it up through `SKIN`.

## 4. Strokes and line grammar

| element | width | colour / form |
|---|---|---|
| spines, ticks | 0.6 pt; ticks 2.5 pt outward, pad 2 pt | `SP_AXIS` |
| data line | 1.0 pt | its token; round joins |
| the one accent line over dense context | 1.2 pt | LEAK (Fig. 1c first-request line over about 3,200 grey ticks) |
| interval (95 % CI) | 0.75 pt, **uncapped** | the colour of its mark |
| event rule | 0.75 pt, full plot height | EVENT; named once ('banner visible') or sitting on the labelled 0 tick |
| schematic box outline | 0.6 pt | `SP_AXIS` (the banner box: EVENT) |
| region frame | 0.6 pt | outer frame and page region `NEUTRAL`; sandbox region `SAND` |
| connector | 0.6 pt, Stealth head 3.4 × 2.8 bp (inset 0.9), stops 0.6 mm short, 0.8 mm rounded bends | `SP_AXIS` |
| leak path (the one accent of a schematic) | 1.0 pt, Stealth 4.25 × 3.4 bp (inset 1.2) | LEAK |
| stopped wire | 0.8 pt, butt caps, ends at the wall | `NEUTRAL` |
| cut path | 0.6 pt, dotted (on 0.6, off 1.6 bp), round caps, no head | `NEUTRAL`; the **only** broken-line meaning in a schematic |
| leader (label moved > 0.8 mm off its mark) | 0.35 pt | `NEUTRAL` |
| minimum stroke anywhere | 0.25 pt | — |

**Line grammar.**

- Solid lines mean something that flows.
- A dotted line is a path that is cut.
- Dashes are used for at most one other meaning per figure, and never in data panels.
- Every directed edge has a head.
- The main path is the heaviest line.
- No line passes through a label.

## 5. Marks

- **Markers: 3.5 pt** (`fs.V7_LW['marker']`), edge 0.6 pt.
  - The protagonist is filled; the comparison is filled in its token and also differs in shape.
  - An open marker is white with a 0.6–1.2 pt edge in the token.
  - The arm shapes stay as in `colors.ARM` (Default circle, Decline square, GPC triangle, Repeat diamond). Their v6
    ratios are scaled by 3.5 / 4.5, so the Default circle is 3.5 pt.
- **Small n (fewer than about 30 units per group):** show the dots and a summary (a 1.0 pt tick at the mean or median,
  with its CI). Never bars ± SEM. Paired units are joined by `LIGHT` 0.5 pt lines.
- **Ticks as events.**
  - A short tick is a library load; a tall tick is a data beacon. Brick ticks are 1.2 pt, centred on their lane.
  - Requests of one kind less than 50 ms apart are drawn side by side 0.85 mm apart, so every request is drawn.
- **Out of range.** A mark that leaves the axis ends in panel a's Stealth leak head (1.5 × 1.2 mm), inside the frame.
  The count of out-of-range marks goes in the caption.
- **The crossing ring.** An open LEAK ring at 3.5 pt (edge 1.2 pt) marks where a curve meets an event rule.
- **The wall.** The script blocker is a solid `SP_FG` bar: 1.2 mm in schematics, 0.8 mm as a mark in a plot.

## 6. Axes

- **Open L axes.** Left and bottom spines only, from `fs.v7_context()`. An event strip has no value axis: drop its
  left spine and keep its row labels.
- **No gridlines.** Event strips use lane grounds (§3.3), not guides.
- **Ticks.** At most 4–5 per axis, never rotated, never with more decimals than needed. Use signed ticks for times
  relative to an event (`fs.signed_ticks`).
- **Starts and limits.**
  - Bars start at 0.
  - Share axes run 0–100 with '(%)' in the title.
  - Leave 2–2.5 mm of air between the data and an axis end, so a data line never runs along a spine.
- **Compared panels share their scale.** Where scales must differ (Fig. 1b over 1c), keep the zeros aligned, make the
  inset visible, and say so in the caption.
- **Labels.** Label directly at the mark, with at most two short direct labels per panel. A key is a last resort:
  frameless, ordered like the data, in muted 7 pt, placed in empty space.

## 7. Schematic grammar (TikZ; Fig. 1a, Fig. 2b, Fig. S1, Fig. S7c and the graphical abstract)

### 7.1 Regions (FigGenie: nested, labelled)

- **At most three levels:** region > region > box. Containers are never louder than their contents.
  - **Level 1**, the outer context (e.g. 'Shopify store in the browser'): an outline-only frame, 0.6 pt `NEUTRAL`, no
    fill. What lies outside it (e.g. the ad vendors) is visibly outside.
  - **Level 2**, the execution contexts: a very faint ground plus a 0.6 pt outline. The page is TINT PAGE with a NEUTRAL
    outline; the pixel sandboxes are TINT SAND with a SAND outline.
- **Name every region** at its top-left, inside it: 7 pt `SP_MUTED`, 2.4 mm in from the edge, in the headroom above
  its first box. A level-1 name may sit beside a level-2 region's top edge when they do not overlap.
- **Corners** are 0.5 mm. All frames are square-ish; no rounded cards.

### 7.2 Boxes (sciplot `S.box`)

- **Style.** White fill, 0.6 pt `SP_AXIS` outline, 0.5 mm corners.
- **Size.** Sized to the text with **2.4 × 1.6 mm** padding (`inner xsep=2.4mm, inner ysep=1.6mm`), minimum height
  6 mm.
- **Columns.** Boxes in a column share their width (`minimum width`). Boxes in a row share their centre line.
- **Tinted boxes.** One tinted box per meaning: the cookie banner is TINT EVENT with an EVENT outline. Every other box
  is white.
- **Secondary text** inside a box is 6 pt `SP_MUTED`:
  - a qualifier right-aligned on the same row (e.g. 'strict', 'lax');
  - or a second line (e.g. 'Customer Privacy API').
- **No empty boxes** (FigGenie). A box that stands for a population or a store of things lists its members in 6 pt
  `SP_MUTED`. For example, 'Ad vendors' lists the vendor groups in `fs.VENDOR_ORDER`, in grey, never in vendor hues.
  The list is asserted against the registry.

### 7.3 Connectors and paths

- **Connectors** stop 0.6 mm short of the box they enter. They run orthogonally, with 0.8 mm rounded bends. A fork
  leaves one trunk and splits with `|-`.
- **Inputs** enter from the left with their labels at the tails: 7 pt, right-aligned on one x, sharing one tail x and
  one length.
- **One accent path** per schematic (the leak, LEAK 1.0 pt).
- **What a component blocks** is a 0.8 pt `NEUTRAL` wire that ends at the `SP_FG` wall. The path it cuts continues as
  the dotted `NEUTRAL` hairline, with no head.

### 7.4 Loss numerals (outlined, never filled)

- **Macro.** `\lossno{x,y}{n}` draws a ring (2.7 mm, 0.5 pt LEAK, white inside) with a 6 pt `SP_FG` digit.
- **Numbering** follows the caption's points, in reading order, once each. A schematic has at most about five.
- **Placement:**
  - on the edge that is the point (centred on the arrow, interrupting it), or
  - at the top-right corner of the element (overlapping its outline like a badge), or
  - beside a wall, or
  - between two parallel paths.

  Rings sit on white or on a ground, never on text or on another mark.
- **Checks.** The digits are the only numbers in a schematic. `make_panels.check_composite` and `trace_fig1.py`
  require exactly the numerals 1–5, in order and at `FS['numeral']`. The caption must list `(1)~` to `(5)~` in its
  panel text.

### 7.5 Budget and bans

- **Budget.** About 12–14 labelled elements per schematic, plus 6 pt member lists.
- **Banned** everywhere:
  - icons, emoji or mascots;
  - 3-D or isometric views;
  - drop shadows or gradients (sciplot's `shadow=` and `gradient_box` are never used);
  - ribbons or Sankey flows;
  - zoom rays or tethers;
  - filled numbered discs;
  - pastel cards.

## 8. Plot conventions by chart type

1. **Dot + CI** (shares, differences; Figs 3–6, S2–S10)
   - One row per category, with the category labels at the left in 7 pt.
   - The estimate is a 3.5 pt filled marker with an uncapped 0.75 pt 95 % CI in the marker's colour.
   - Group rows with a small gap. A summary row ('All', 'Any vendor') is set apart below a gap, not boxed.
   - Groups of fewer than 10 units are drawn grey, with their names in `SP_MUTED`.
   - Compare two groups by colour **and** shape (LEAK circle, HONOUR square).
   - Shares are on 0–100 %. Value labels go in the caption.
2. **Slope and arm comparisons** (Default → Decline → GPC)
   - The x positions are the arms, labelled by name; the marker shapes come from `colors.ARM`.
   - One series per small multiple, with the multiples sharing y.
   - Lines joining arms are 0.75 pt `LIGHT`; they never carry colour.
   - Never more than four converging lines in one panel.
3. **Raster** (event timing across stores or loads; Figs 1c, 5c, S8d)
   - One row per unit, sorted by the story variable; time is aligned to the consent event at 0 (EVENT rule).
   - Context ticks: `SP_CONTEXT`, marker `|`, 1.4 pt long, 0.5 pt wide.
   - The story is one LEAK line or LEAK ticks.
   - The key area (e.g. before the event) is a TINT LEAK ground under the marks.
   - 2.5 mm of air above row 1 and below row n. Rows and values outside the axis are counted in the caption.
4. **Event strip** (one load, lanes; Figs 1b, S9d)
   - One lane per execution context, each on the ground of its schematic region (§3.3): 3.8 mm lanes at a 4 mm pitch.
   - Lane names sit at the left in 7 pt.
   - Event ticks use the tick-height key (§5). The blocked tag is the wall in miniature with the direct label
     'blocked'.
   - The EVENT rule is named once. A broken time axis is allowed only with one scale and marked cuts.
5. **Timelines** (protocol arms; Fig. 2c)
   - Parallel 0.75 pt `SP_AXIS` lines, one per arm, under one time axis.
   - EVENT ticks with 7 pt names above them.
   - Phases are square brackets below the lines. The arm glyph and name sit at the left.
6. **Step, ECDF and CCDF lines** (S6b, S6e)
   - 1.0 pt steps in the group token. The event or threshold is an EVENT rule or a `NEUTRAL` dotted reference.
   - Points marked on a curve use 3.5 pt dots in the line colour.
   - Direct labels at the line ends; no legend box.
7. **Stacked share bars and unit bars** (S6c, S9c)
   - Thin horizontal bars on 0–100 %.
   - Segments in tier order: the story first (LEAK or SAND), then the mid grey `#6e6e6e`, then `LIGHT`. Thin white gaps
     separate the segments.
   - A key is allowed inside the plot at the top right. Totals go in the caption.
   - Unit grids, one square per store, use the same tiers. Never a pie or a donut.
8. **Matrices** (counts or categorical cells; S7b, S7d)
   - Square cells. Absent cells are `LIGHT` or blank; groups are split by 0.6 pt `SP_AXIS` rules, not borders.
   - Cell numerals are 7 pt `SP_FG`, only when the counts are the point. A glyph matrix uses LEAK = sent and `LIGHT` =
     not sent.
9. **Heatmaps** (rates; S2b)
   - A four-step `GREY_RAMP` (or a LEAK ramp of pre-mixed tints for leak rates), monotone in lightness.
   - The lightest step is a definite grey, never white. 'No estimate' is a dash on white.
   - A thin colour bar on the right with 6 pt ticks.
   - Never rainbow or jet. A diverging map is centred and symmetric.
10. **Flows and ledgers** (sampling, Fig. 2a; nested re-check stages, S7c)
    - A vertical `SP_AXIS` spine with one box per stage; boxes are sized to text, and counts go in the box or in the
      caption.
    - Exclusions branch right with flat ends and the reason in 6 pt `SP_MUTED`.
    - The leak is the one LEAK arrow. Nested stages may use §7.1 regions.
    - No Sankey, no equal-size slide cards.

**Never:**

- dual y-axes;
- bars that do not start at 0;
- lines across unordered categories;
- rotated tick labels;
- significance stars;
- capped error bars;
- boxed legends;
- hatching;
- hidden per-group normalisation;
- a number on every mark.

## 9. Layout and alignment

- **Size.**
  - Figures are 190 mm wide (Elsevier double column).
  - Main figures are about 100–150 mm high; the cap is 230 mm.
  - Gutters are 6 mm, with no outer margin.
- **Exact size.** Each panel is drawn at exactly its cell size: `fs.panel(w, h)` + `fs.axes_mm(...)` for matplotlib,
  `\PanelCanvas{w}{h}` for TikZ. The composite places panels at 100 % with `\Panel`, which checks the size to
  ±0.2 mm and draws the letter.
- **Letters.** The 8 pt letter's cap top sits at the cell's top-left. Keep the 4.5 × 4.5 mm letter zone empty, and
  start labels at least 2 mm from the figure's left edge.
- **The hero panel** spans the full width or the largest cell. Supporting panels are quieter (fewer colours, no
  grounds unless they repeat the hero's).
- **Alignment** (nature-figure gate, implemented as asserts in each `make_panels.py`):
  - Panels on one time base share their zero. Fig. 1 asserts that b's 0 sits exactly above c's 0
    (`c_zero_mm`).
  - Panels in a column share their plot left and right edges; panels in a row share their plot top and baseline.
  - The cells in `figN.tex` must equal the script's constants (`check_composite`).
- **Density.** No empty quadrant larger than about 25 % of a panel. Grow the canvas rather than shrink the type.

## 10. Captions and alt text

- **Generation.** Captions and alt text are generated by `scripts/make_caption*.py`. Every number goes through the
  registry (`fs.N`, `fs.KN`, `DN`, `SEC`); never type a number.
- **Structure.**
  - A bold one-sentence title (the claim), then each panel in turn as '(a)~', with lowercase cross-references
    ('Fig.~5c').
  - Define abbreviations on first use.
  - Give n and the unit, and the interval type and level.
- **Name every encoding once.**
  - Colours: brick = requests that lost consent; amber = the consent moment; grey = context.
  - Every ground: light grey = the page, darker grey = the sandbox, pale brick = the key area.
  - The dotted cut path, the tick heights, the arrowheads that leave the axis, the open crossing ring.
  - The member list of a box.
- **The schematic's numerals** are referred to as '(1)~ … (5)~' in the hero panel's text ('marked in a by outlined
  numerals'). Later panels cite them ('Point (2) in one page load').
- **Alt text** gives the chart type, the variables, the main pattern and the key numbers, through its own registry.
  Numerals are written as words ('one to five').

## 11. QA (a build fails on any failing gate)

**Automatic gates**, run by every `build.sh`:

1. **Trace** (`scripts/trace_figN.py`):
   - Every registry row is re-rendered from the current `stats.json` / `derived_numbers.json`.
   - Every digit in the PDF, the caption and the alt text is a registered rendering or a structural token (an allowed
     tick label, a loss numeral, a figure reference).
   - Panels a figure declares number-free must print none.
2. **`style/qa_check.py figN.pdf --dpi 200 --png-prefix _v7_review`:**
   - one page at 190 mm width and ≤ 230 mm height;
   - Arial only, embedded Type 0/42, nothing below 6 pt, sizes on the v7 scale;
   - panel letters at 8 pt, with shared baselines and x;
   - no panel titles;
   - every colour in the registry, and no semantic token with vendor hues;
   - no raster images;
   - **text-collision audit:** two runs whose ink boxes (Arial outlines at the run's size and matrix) overlap by more
     than 0.1 mm in both directions FAIL;
   - it renders the one review PNG.
3. **`style/palette_gate.py`:** registry classes per panel, plus the dataviz validator when two or more hues of one role
   appear.
4. **Skill screen** (`scripts/skill_qa_figN.py`):
   - WCAG contrast per drawn colour against its role (4.5:1 text, 3:1 graphics; low-contrast context accepted only
     with a written reason);
   - grey-scale L\* separation of the category pairs;
   - fonts and sizes (words ≥ 7 pt; 6 pt allowed for tick labels, numerals, and words only when filled `SP_MUTED`;
     `qa_check.Walker` records each run's fill colour);
   - the export manifest.
5. **`scripts/sp_lint.py`:** the categorical hues drawn must be ≥ 10 CIEDE2000 apart under deutan, protan and tritan
   simulation.

**Threshold policy.** A figure may change its own allowed-tick list or QA thresholds only where this spec requires it.
For example:
- `TEXT_MIN_PT` 6.5 → 6.0 for the v7 tick size;
- the `SP_MUTED` note exception;
- the loss numerals of a schematic.

Never weaken number tracing.

**Visual review.**

- Read `_v7_review-p01.png` at full size. Answer the v7 checklist that `qa_check` prints (§1–§9), and record it in
  `figN/QA.md`.
- Compare the render with the four exemplars named at the top of this file.
- The CVD and grayscale montage is opt-in (`CVD_OUT=/scratch/path.png zsh build.sh`). Read it, then delete it.

**Disk.** Keep one review PNG per figure, at 200 dpi or less. Delete scratch renders.

## 12. How to build

- **Environment.**
  - Prefix every command with `PATH=/opt/anaconda3/bin:$PATH`.
  - Tectonic is `<workspace>/tools/texenv/bin/tectonic`; `build.sh` finds it.
  - Renderer: `paper/tools/pdfpages2png in.pdf outprefix dpi`.
- **Style foundation** (`style/`):
  - `figstyle.py` is the single source. It holds FS, the tokens, `TINT`, `V7_RC`, `v7_context()`, the registry, `panel`
    and `axes_mm`.
  - Run `python3 figstyle.py --write-tex --selftest` after any token change. It regenerates `palette_v2.tex` and checks
    parity with `style_v2.mplstyle`.
  - `tikzstyle_v2.tex` provides the fonts, the size macros, `\PanelCanvas`, `\FigureCanvas` and `\Panel`.
- **Per figure** (copy the shape of `fig1/`):
  - `scripts/derive_figN.py` → `derived_numbers.json` (value, definition, script, inputs, check per record).
  - `scripts/make_panels.py`:
    - draws inside `with fs.v7_context():`;
    - registers drawn values (`mark`), lints each panel (`sp_lint.lint_fig`) and saves it at exact size;
    - asserts the composite cells and the alignment.
  - `figNx_*.tex` (TikZ): `\input{../style/tikzstyle_v2.tex}`, then copy the `tikzset` block and `\lossno` from
    `fig1/fig1a_pipeline.tex`.
  - `figN.tex` composite: `\FigureCanvas{h}` + `\Panel{a}{x}{y}{w}{h}{panels/...pdf}`.
  - `scripts/make_caption.py`, `scripts/trace_figN.py`, `scripts/skill_qa_figN.py`.
  - `build.sh` chains them in the order of §11. Copy `fig1/build.sh`.
- **Migrating a v6 figure to v7:**
  1. Switch `fs.style_context()` → `fs.v7_context()`, and remove anything that assumes the full box (right and top
     spines).
  2. Set the skill screen's `TEXT_MIN_PT` to 6.0 and add the `SP_MUTED` note exception (as in
     `fig1/scripts/skill_qa_fig1.py`).
  3. Point the review PNG to `_v7_review` at 200 dpi.
  4. Apply §3.3 tints only where they repeat a meaning.
  5. Update the caption generator for the new encodings.
  6. Rebuild until every gate passes.

  The v7 type scale (FS) and `palette_v2.tex` are already shared, so a rebuild picks them up.
- **Skills** are read, never run. Their guidance is re-implemented locally (`style/`, `fig1/scripts/sp_lint.py`).

## 13. Worked example: `fig1/`

| rule | where |
|---|---|
| figure contract, panel roles (§1) | `fig1/scripts/make_panels.py` docstring; caption title in `scripts/make_caption.py` |
| type, colours, v7_context (§2–§4) | `style/figstyle.py` (`FS`, `TINT`, `V7_RC`, `v7_context`); `style/palette_v2.tex` |
| nested regions, boxes, connectors, wall, cut path (§7.1–§7.3) | `fig1/fig1a_pipeline.tex` |
| no empty box: the vendor-group list (§7.2) | `fig1a_pipeline.tex` 'Ad vendors' node; asserted in `make_panels.check_composite` |
| loss numerals (§7.4) | `\lossno` in `fig1a_pipeline.tex`; checks in `check_composite` and `scripts/trace_fig1.py` |
| lanes on the regions' grounds (§3.3, §8.4) | `make_panels.panel_b` (`LANE_GROUND`, `LANE_H_MM`) |
| key area: pale brick before the banner (§3.3, §8.3) | `make_panels.panel_c` (TINT LEAK polygon on the line's vertices) |
| alignment: b's 0 above c's 0 (§9) | `make_panels.c_zero_mm`, asserts in `panel_b` |
| caption naming every encoding (§10) | `fig1/scripts/make_caption.py` → `caption_fig1.tex`, `alt_text_fig1.txt` |
| QA gates (§11) | `fig1/build.sh`; `style/qa_check.py` (collision audit, fill-aware runs); `fig1/scripts/skill_qa_fig1.py`; `fig1/QA.md` |

Build: `cd figures/v7/fig1 && PATH=/opt/anaconda3/bin:$PATH zsh build.sh`. It writes `fig1.pdf` (190 × 132 mm), the
caption, the alt text, the reports and `_v7_review-p01.png`.
