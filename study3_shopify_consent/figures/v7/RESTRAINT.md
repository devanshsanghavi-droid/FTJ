# RESTRAINT: binding override for v6 (this file wins over DESIGN_V6.md wherever they differ)

## The author's verdicts so far
- **v3 (rounded tinted cards, icons): rejected** as "AI-looking".
- **v5 (K-Dense dense forest tables): rejected.** "Information dense but not unique nor pleasing."
- **The three mockups (editorial, sunflower disc, illustrated isometric system): rejected.** "Horrid, too much going on, to the point where they are almost unlike figures; the graphics start looking like AI."
- **The target:** figures that look like they belong in the author's 10 Nature Computational Science papers (references/ncs_papers; gallery: figures/v6_plan/exemplars_gallery.png).

Those figures are restrained. A panel is a plain, well-made plot or a sparse line drawing, with plenty of white space and almost no text inside the plot. The caption does the explaining.

## Hard rules
1. **It must look like a figure, not an infographic.** No headlines, kickers or standfirsts inside figures. No big "hero numbers". No callout bubbles, no in-figure prose.
2. **No panel titles.** Panels have only the bold lowercase letter (a, b, c). A schematic may carry one or two short section labels, as DIPPER and AlignIF do.
3. **Text inside a data panel is limited to** axis titles, tick labels, one small legend, and at most two short direct labels. Do **not** print "p% · k of n" on every mark. Numbers belong in the caption; the plot shows them by position. One key value may be labelled if it is the panel's point.
4. **Standard chart forms, made well:**
   - scatter or dot with error bars;
   - line or step;
   - thin bars with error bars and optional replicate dots;
   - a raster of ticks;
   - a heatmap with a thin colour bar;
   - a small matrix.

   Prefer the forms these papers use (see the NEP89 Fig 3 and PathSegmentor Fig 4 exemplars). No dumbbell-plus-table hybrids, no forest tables with count columns.
5. **Axes.** A thin full box (0.5 pt, near-black) with outward ticks, as in NEP89, PathSegmentor and MIRACLE. Leave generous plot area. No gridlines.
6. **Colour.** A small, calm palette sampled from the papers, used the same way in every figure:
   - protagonist / "consent lost": a muted brick red, about #c65358;
   - comparison / "consent honoured": slate, about #5d769d;
   - a third series if needed: lavender, about #b788ca;
   - the consent event (banner, Decline click, GPC): amber, about #e8a33a;
   - neutral: grey #a0a0a0.

   The fixed vendor hexes are used only where vendors are the categories. **No tinted background lanes, no pastel fills, no warm-shaded zones**; white backgrounds only. A pale tint is allowed only as an error band.
7. **Markers.** Simple filled circles, squares or diamonds about 4–5 pt, double-coded by shape where a reader must tell series apart. Lines 1.2–1.5 pt.
8. **Schematics** (only Fig 1a, Fig 2b and Supplementary Fig. S1):
   - thin line art in near-black and greys, plus at most one accent colour for the leak path;
   - at most about 12 labelled elements;
   - drawn like the AlignIF Fig 1 or DIPPER Fig 1 flow pieces: plain rectangles, square or slightly rounded (≤ 0.5 mm) corners, thin arrows, short labels;
   - **no** 3D or isometric views, drop shadows, ribbons or Sankey flows, glyph decorations, numbered discs, "zoom rays", tethers, icons or emoji;
   - real text strings (a URL) are allowed if short.
9. **Layout.** Two to four panels per main figure, each with room to breathe; total height about 100–150 mm at 190 mm width. Every panel's point must be clear in five seconds without reading text inside it.
10. **Typography.** Arial. Panel letters 8–9 pt bold lowercase. Axis titles and labels 7 pt; ticks 6–7 pt. Sentence case.
11. **Keep:** every number traceable (trace/QA checks pass), panel letters and contents after the narrative moves (v5 structure), Store C anonymity, honest scales.
12. **The test for every figure.** Put the render next to the exemplar gallery. Would it look at home in those papers? If it looks like a poster, dashboard, magazine graphic or AI illustration, simplify.
