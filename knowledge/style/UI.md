# UI rules for the shelf

Distilled from UI UX Pro Max (MIT) and unslop (CC BY 4.0); see [README.md](README.md).
The shelf keeps its own character: Manrope, the chalk, graphite and mint palette, no framework,
no build step, no external requests, runtime text through `textContent` only.

## Before shipping a page change

1. Text contrast at least 4.5:1 in light **and** dark mode. Measure, do not eyeball.
   (W17a: a later base rule overrode the dark headline and left it at 1.03:1.)
2. No horizontal overflow at 375, 768, 1024 and 1440 px; controls shrink (`min-width:0`).
3. Visible keyboard focus on every control; clickable things look clickable.
4. Motion is short (about 150 to 300 ms) and honours `prefers-reduced-motion`.
5. Color is never the only signal: a pill says its state in words.

## Unslop passes, in order

6. Spacing: a 4 px grid (8, 12, 16, 24 ...). No 14 or 22 px one-offs.
7. Color: one accent for the moments that matter; no gradients or glows for decoration.
8. Icons: real SVG or the app's own logo; never emoji as icons.
9. Copy: sentence case, no shouting. Labels say what happens.
10. Type: hierarchy from size and color first; body and labels stay at 400 to 700 (the hero
    heading is heavier by design).

## Weight

11. Images: recompress PNGs (pngquant quality 95 to 100) and keep the original when the 40 px
    view drops below 45 dB PSNR; record it in `docs/assets/NOTICE.txt`.
12. Fonts: the page loads the Latin subset first; the full font only for other characters
    (`unicode-range`).
13. `src/etc/page_weight.py` holds the budget. Raise it only on purpose, in the same change.
