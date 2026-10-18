---
name: AssessCraft AI
description: Agentic academic assessment copilot. A quiet ledger for verified exam work.
colors:
  verified-emerald: "#047857"
  verified-emerald-deep: "#065f46"
  verified-emerald-ink: "#064e3b"
  verified-emerald-wash: "#ecfdf5"
  verified-emerald-rule: "#a7f3d0"
  ledger-ink: "#0f172a"
  ledger-ink-soft: "#334155"
  ledger-graphite: "#64748b"
  ledger-pencil: "#94a3b8"
  ledger-rule: "#e2e8f0"
  ledger-rule-strong: "#cbd5e1"
  ledger-paper: "#f8fafc"
  ledger-paper-shade: "#f1f5f9"
  ledger-sheet: "#ffffff"
  caution-amber: "#b45309"
  caution-amber-wash: "#fffbeb"
  caution-amber-rule: "#fde68a"
  defect-rose: "#be123c"
  defect-rose-wash: "#fff1f2"
  defect-rose-rule: "#fecdd3"
  info-sky: "#0369a1"
  info-sky-wash: "#f0f9ff"
  info-sky-rule: "#bae6fd"
typography:
  display:
    fontFamily: "Geist Mono, ui-monospace, SFMono-Regular, Menlo, monospace"
    fontSize: "1.875rem"
    fontWeight: 800
    lineHeight: 1.2
    letterSpacing: "-0.025em"
  headline:
    fontFamily: "Geist, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 800
    lineHeight: 1.33
    letterSpacing: "-0.025em"
  title:
    fontFamily: "Geist, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 600
    lineHeight: 1.43
  body:
    fontFamily: "Geist, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 400
    lineHeight: 1.33
  label:
    fontFamily: "Geist, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "11px"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "0.05em"
  figure:
    fontFamily: "Geist Mono, ui-monospace, SFMono-Regular, Menlo, monospace"
    fontSize: "0.75rem"
    fontWeight: 500
    lineHeight: 1.33
rounded:
  xs: "4px"
  sm: "6px"
  md: "8px"
  lg: "12px"
  full: "9999px"
spacing:
  hair: "2px"
  xs: "6px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "20px"
  2xl: "24px"
components:
  button-primary:
    backgroundColor: "{colors.verified-emerald}"
    textColor: "{colors.ledger-sheet}"
    typography: "{typography.title}"
    rounded: "{rounded.md}"
    padding: "10px 16px"
  button-primary-hover:
    backgroundColor: "{colors.verified-emerald-deep}"
  button-secondary:
    backgroundColor: "{colors.ledger-sheet}"
    textColor: "{colors.ledger-ink-soft}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  button-secondary-hover:
    backgroundColor: "{colors.ledger-paper}"
  input-field:
    backgroundColor: "{colors.ledger-sheet}"
    textColor: "{colors.ledger-ink}"
    rounded: "{rounded.md}"
    padding: "10px 14px"
  card-sheet:
    backgroundColor: "{colors.ledger-sheet}"
    rounded: "{rounded.lg}"
    padding: "20px"
  chip-verified:
    backgroundColor: "{colors.verified-emerald-wash}"
    textColor: "{colors.verified-emerald-deep}"
    rounded: "{rounded.full}"
    padding: "2px 10px"
  chip-caution:
    backgroundColor: "{colors.caution-amber-wash}"
    textColor: "{colors.caution-amber}"
    rounded: "{rounded.full}"
    padding: "2px 10px"
  chip-defect:
    backgroundColor: "{colors.defect-rose-wash}"
    textColor: "{colors.defect-rose}"
    rounded: "{rounded.full}"
    padding: "2px 10px"
  nav-link-active:
    backgroundColor: "{colors.verified-emerald-wash}"
    textColor: "{colors.verified-emerald-ink}"
    rounded: "{rounded.md}"
    padding: "6px 12px"
---

# Design System: AssessCraft AI

## Overview

**Creative North Star: "The Examiner's Ledger"**

AssessCraft reads like a well-kept examinations ledger: white sheets on pale paper, slate ink, hairline rules, and a single green mark that means *this is checked*. The interface is a record of work done by agents and signed off by people, so numbers, statuses and citations are the content, and the chrome stays out of their way.

Density is high and type is small. Most working text sits at 11–12px, with monospace reserved for figures, IDs, marks and codes so they line up and read as data. Surfaces are near-flat. Depth comes from a white sheet against slate paper and a 1px rule, never from dramatic shadow. Colour is semantic first: emerald for action and verification, amber for caution, rose for defects, sky for information. Nothing else competes.

The system is light-mode only today. There is no gradient, glass, or decorative imagery; all styling is Tailwind utilities inline, with `globals.css` holding only tokens, the font wiring, the focus ring, selection and scrollbars.

**Key Characteristics:**
- White sheet cards (12px corners, 1px slate rule, hairline shadow) on slate-50 paper.
- One brand hue, emerald, carrying both primary action and "verified" status.
- Monospace for every figure: marks, counts, IDs, CLO codes, scores.
- Small, dense type (11–12px working size) with uppercase tracked micro-labels.
- Semantic tinted chips (wash background + rule border + deep text) for every status.

## Colors

A cool slate neutral ladder with one emerald voice and three quiet semantic tints.

### Primary
- **Verified Emerald** (#047857): primary buttons, the brand mark tile, active progress, verified/pass dots. The only colour that asks to be clicked.
- **Verified Emerald Deep** (#065f46): primary hover, chip text on emerald wash, emphasised verified figures.
- **Verified Emerald Ink** (#064e3b): active nav text and the strongest verified label.
- **Verified Emerald Wash** (#ecfdf5) and **Verified Emerald Rule** (#a7f3d0): background and border of verified chips, the active nav pill and the selected persona row.

### Neutral
- **Ledger Ink** (#0f172a): headings, primary values.
- **Ledger Ink Soft** (#334155): body copy, secondary button text.
- **Ledger Graphite** (#64748b): metadata, helper text, captions.
- **Ledger Pencil** (#94a3b8): inactive icons, placeholder-level hints.
- **Ledger Rule** (#e2e8f0): every card, input and divider border. **Ledger Rule Strong** (#cbd5e1): hover border.
- **Ledger Paper** (#f8fafc): page background and inset panels. **Ledger Paper Shade** (#f1f5f9): tracks, hover rows, progress backgrounds.
- **Ledger Sheet** (#ffffff): cards, inputs, nav bar, dropdowns.

### Semantic
- **Caution Amber** (#b45309 on #fffbeb, rule #fde68a): warnings, pending moderation, the Moderator persona.
- **Defect Rose** (#be123c on #fff1f2, rule #fecdd3): reviewer defects, key mismatches, failed checks.
- **Info Sky** (#0369a1 on #f0f9ff, rule #bae6fd): neutral information panels and citations.
- Categories that are not statuses (Bloom levels, agent names) stay neutral slate or sky; they never borrow a semantic hue's meaning.

### Named Rules
**The Contrast Floor Rule.** White text only ever sits on emerald-700 or darker; emerald-600 fails 4.5:1. Helper text is slate-500 or darker, never slate-400.

**The One Green Rule.** Emerald means "act" or "verified", and nothing else. Never use it for decoration, illustration, or a category label.

**The Tinted Chip Rule.** Every status is written as wash background + matching rule border + deep text of one semantic hue. Never a solid saturated status pill.

**The Earned Status Rule.** A green chip is computed, never asserted. If the data can't prove it, the chip goes amber or the figure shows an em dash.

## Typography

**Body Font:** Geist (via `next/font`, falling back to the system UI stack)
**Figure Font:** Geist Mono (falling back to ui-monospace, SFMono-Regular, Menlo)

**Character:** A clean, neutral grotesque for reading and its matching mono for anything countable. The pairing reads as a ledger you can trust rather than a brand voice. Both are wired into Tailwind's `--font-sans` / `--font-mono` in `globals.css`.

### Hierarchy
- **Display** (800, 1.875rem / 30px, tight tracking, mono): page-level figures and identifiers such as assessment titles and course codes.
- **Headline** (800, 1.5rem–1.875rem, tight tracking, sans): page headings.
- **Title** (600, 0.875rem / 14px): card titles, primary button labels at large size.
- **Body** (400–500, 0.75rem / 12px): the default working size for content, table cells and controls.
- **Label** (600, 11px, uppercase, 0.05em tracking): field labels, section eyebrows inside cards, dropdown headers. Secondary metadata also sits at 11px; nothing goes smaller.
- **Figure** (500–700, mono, 12px or larger): marks, counts, percentages, item IDs, CLO codes.

### Named Rules
**The Figures Are Mono Rule.** Any number a lecturer might compare (marks, counts, scores, IDs) is set in monospace.

**The 11px Floor Rule.** 11px is the smallest acceptable size.

## Layout

A centred 1280px column (`max-w-7xl`) with responsive gutters of 16 / 24 / 32px (mobile / sm / lg). Pages stack a header row (title + actions) above card grids that go one column on mobile, two at `sm`/`md`, and three or four at `lg`. Within cards, rhythm is tight: 12–16px between blocks, 8px gaps in control rows, 2px vertical padding on chips. The sticky 64px navigation bar collapses its links below `md`. Dense data screens (assessment detail) favour tabs and stacked sheets over side panels.

## Elevation & Depth

Flat by default. Depth is tonal: a white sheet on slate-50 paper, edged by a 1px slate-200 rule. The only shadow at rest is a near-invisible hairline (`shadow-xs`). Hover strengthens the border to slate-300, not the shadow. Real elevation is reserved for floating layers: dropdown menus (`shadow-xl`) and the agent trace drawer.

### Shadow Vocabulary
- **Hairline** (`box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05)`): cards, inputs, buttons at rest.
- **Nav underline** (`box-shadow: 0 1px 2px rgba(0,0,0,0.03)`): sticky header separation.
- **Float** (`box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)`): dropdowns and drawers only.

### Named Rules
**The Border Not Shadow Rule.** Interactive emphasis is a darker rule, not a bigger shadow. Shadows above hairline belong only to things that float over the page.

## Shapes

Gently rounded, never pill-shaped except where meaning demands. 12px corners on cards and sheets, 8px on buttons, inputs and nav pills, 4px on tiny inline tags (the "AI" badge), and full rounding only for status chips, avatars, dots and progress tracks. All containers carry a 1px border; nothing is borderless on white.

## Components

### Buttons
Crisp and restrained: small text, semibold, an 8px corner, no flourish.
- **Shape:** gently rounded (8px).
- **Primary:** emerald-700 fill (white text 5.5:1), white 12px semibold text, 10px × 16px padding, hairline shadow, icon + label with 8px gap.
- **Hover / Active:** emerald-700 on hover, emerald-800 on active; disabled at 50% opacity.
- **Secondary:** white fill, slate-200 rule, slate-700 text; hover to slate-50.
- **Focus:** a global 2px emerald `:focus-visible` outline with 2px offset; inputs use their own 1px emerald ring.

### Chips
- **Style:** full-round, wash background + rule border + deep text in one semantic hue; 12px medium or semibold; often prefixed by a 6px dot or a 12px icon.
- **Variants:** verified (emerald), caution (amber), defect (rose), info (sky), and role badges in the nav.

### Cards / Containers
- **Corner Style:** 12px.
- **Background:** white sheet on slate-50 paper.
- **Shadow Strategy:** hairline at rest; see Elevation.
- **Border:** 1px slate-200 at 90% opacity; slate-300 on hover for clickable cards.
- **Internal Padding:** 20px standard, 24px for primary cards; inner blocks spaced 12–16px.

### Inputs / Fields
- **Style:** white fill, 1px slate-200 rule, 8px corner, 10px × 14px padding, 14px text (12px in compact rows), hairline shadow.
- **Focus:** border shifts to emerald-700 with a 1px emerald ring; no glow.
- **Labels:** 11px uppercase tracked graphite label above the field.

### Navigation
Sticky white bar (95% opacity, backdrop blur) with a slate rule underneath. Left: emerald brand tile + wordmark + tiny "AI" tag. Links are 14px medium slate-600 with a slate-500 icon; hover adds slate-100 fill; active becomes an emerald wash pill with an emerald rule and emerald-700 icon. Right: the persona button (avatar initial, name, email, role chip, chevron) opening a 256px white dropdown with a float shadow.

### Workflow Shell (signature)
The assessment page is organised as three lecturer stages, **Author → Verify → Sign off**, each a white bordered card with a numbered disc (emerald-700 with a check when done, slate-900 when active, slate-100 otherwise) and a one-line status computed from data. The active stage's two steps sit beneath as underline tabs (`role="tab"`, emerald-700 2px underline). The active tab is kept in the URL (`?tab=`).

Directly under it, the **Next-action strip** states the one thing the current role must do next, in amber (action), sky (waiting on someone else) or emerald (done), with at most one primary button. It is the view's primary action; other buttons in the view stay secondary.

### Triage Rows
Long lists (question pool, reviewer flags) are one compact row per question: mono question number, two-line clamped stem, a metadata line of small chips, a "Details"/"Evidence" disclosure, and row actions on the right with accessible names that include the question number. Reviewer flags are grouped per question and sorted by severity; near-duplicates show both stems side by side. Rows support select-all and bulk Keep/Reject.

### Notices and Confirmation
Feedback is an inline toast at the bottom right (`role="status"`, errors `role="alert"`), never `alert()`. Reversible decisions commit after a 6-second Undo window. Irreversible steps (approval) use a confirm dialog that lists exactly what gets locked and who is signing; focus starts on Cancel and Escape closes it.

### Agent Trace Drawer (signature)
The side drawer that exposes each agent step. It is the most direct expression of "show the verification": a floating sheet listing stage, status and output, using the same chip and mono-figure language as the rest of the ledger.

## Do's and Don'ts

### Do:
- **Do** derive every status, badge and "ready" claim from data on the page; when the data can't prove it, say what is missing.
- **Do** use emerald-700 (#047857) for the single primary action in a view and for verified status, and nothing else.
- **Do** set every comparable number in monospace.
- **Do** write status as a tinted chip: wash + rule + deep text of one semantic hue.
- **Do** build containers as white 12px-cornered sheets with a 1px slate-200 rule and hairline shadow on slate-50 paper.
- **Do** signal hover on cards and secondary controls by darkening the rule to slate-300.

### Don't:
- **Don't** present fallback or placeholder text as an agent's judgement; label it.
- **Don't** introduce a second brand hue, purple included.
- **Don't** add gradients, glassmorphism or glow.
- **Don't** set text below 11px.
- **Don't** use shadows above hairline on anything that does not float.
- **Don't** use emoji as icons; use lucide-react at 14–16px, inheriting the text colour.
