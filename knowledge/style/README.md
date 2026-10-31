# Style rules (W17a, 31 Oct 2026)

Short house rules for the page and the living docs, distilled in our own words from three
published skills. Dated records under `docs/review/` keep their words; these rules are for new
text and for living files.

- [WRITING.md](WRITING.md): prose in README, guides, security and recovery docs, release notes.
- [UI.md](UI.md): the shelf page (`docs/index.html`, `docs/portal.js`).

Checks that keep them alive (**3. Validate**):

- `python3 src/etc/prose_lint.py`: advisory. It prints warnings and never fails the run.
- `python3 src/etc/page_weight.py --check`: fails when the first page load grows past its budget.
- `python3 src/etc/doclinks.py --check`: fails on a broken relative link in any Markdown file.

## Credits

- [humanizer](https://github.com/blader/humanizer) by blader, MIT: the writing patterns.
- [UI UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) by nextlevelbuilder,
  MIT: the pre-delivery UI checklist.
- [unslop](https://github.com/heydamir/unslop) by Damir Sokolovsky (@heydamir), CC BY 4.0:
  the slop audit and the spacing, color, icon, copy and type passes.

No file from these projects is copied here; the rules below are summaries. Applied in W17a by
Anthropic Claude models, for Govindarajulu K.
