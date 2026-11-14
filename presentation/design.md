# Tinybird visual identity — reference for the jury deck

Measured on **14 Nov 2026** from the live sites (HTML + CSS bundles downloaded with curl, pages rendered with
headless Chromium). Nothing here is from memory; anything not read directly from a file is marked **inferred**.

Sources, cited below by letter (the hashed bundle names change on every deploy):

| Ref | What | URL |
|---|---|---|
| **M** | tinybird.co main stylesheet: tokens, type scale, utilities | `https://www.tinybird.co/_next/static/immutable/chunks/1h4b13balrum5.css` |
| **F** | tinybird.co fonts + component modules (Button, Code) | `https://www.tinybird.co/_next/static/immutable/chunks/2ifownkhrb_iq.css` |
| **H** | tinybird.co pages, class attributes in the HTML | `/` (home), `/blog`, `/pricing`, `/product/managed-clickhouse`, `/about` |
| **D** | Tinybird docs stylesheets (the only **light** Tinybird theme) | `https://www.tinybird.co/docs/_next/static/chunks/0t23ktw6d7hdx.css` (tokens, article), `…/13t~~bdng__nv.css` (code block) |
| **R** | rawtree.com stylesheet | `https://rawtree.com/vc-ap-28d982/_next/static/chunks/161_1dx67vk.u.css` |
| **S** | Organisers' challenge slides | `docs/sources/slides.html` (repo), `<style>` lines 34–2550 |

## 0. The one thing to know first

**tinybird.co is a dark-only site** (`<html class="… dark">` on every marketing page checked; `--color-bg` resolves to
`--gray-950` `#0a0a0a`). Its accent, mint green `#27f795`, has **1.42:1 contrast on white**: it cannot be used for
text or thin lines on a white slide.

Tinybird's own answer exists in two places, and both agree:

- the **docs** (`tinybird.co/docs`) have a light theme as their `:root` default (dark is the opt-in
  `[data-theme=dark]`): white page, navy text `#25283d`, links in
  `--secondary` `#2d27f7`, active/hover in `--primary-dark` `#008060`, and the green kept **only as a fill**
  (button background, dark text on top) — **D** `:root`;
- the marketing components carry light fallbacks next to every `dark:` class, e.g. the blog card
  `border-gray-300 bg-gray-100 … dark:border-gray-800 dark:bg-gray-900` and the date
  `text-secondary dark:text-primary` — **H** `/blog`.

So "Tinybird on white" = navy ink, Roboto, green fills, dark-green or blue-violet text accents. Section 6 turns
that into slide rules.

## 1. Typography

### Families

| Role | Family | Where declared | What it is | Licence |
|---|---|---|---|---|
| Headings + body | **Roboto** | **M** `--font-sans: var(--font-roboto)`; **F** `--font-roboto:"Roboto","Roboto Fallback"` | Google (Christian Robertson), variable `wght` 100–900 | SIL OFL 1.1 (`googlefonts/roboto-classic`) |
| Nav, buttons, eyebrows, tabs, tags, dates, stats, code | **Roboto Mono** | **M** `--font-mono: var(--font-roboto-mono), monospace` | Google, variable `wght` 100–700 | SIL OFL 1.1 (`googlefonts/RobotoMono`) |
| Declared, unused on the pages fetched | Fira Mono (`.font-tinybird-code`), Geist (`.geist_…__className`) | **M**, **F** | Mozilla / Vercel | OFL 1.1 (not downloaded: no element uses them) |
| Declared, unused on the pages fetched | "sevenSegment" (`.font-seven-segment`) | **F** | "Seven Segment", Krafti Lab / Onur Cem Tan (name table of the served file) | **Not open: do not copy.** Closest open alternative: DSEG7 (OFL). Not needed |

Tinybird's own font files (latin subsets, preloaded in **H**), for reference only — we ship the upstream release instead:
`/_next/static/immutable/media/ce62453a442c7f35-s.p.3l4zvto3p0stf.woff2` (Roboto, v3.015),
`/_next/static/immutable/media/2f13ad8e538108e0-s.p.2opg_g5lzx1nr.woff2` (Roboto Mono, v3.001).

Weights declared: marketing loads Roboto **300, 400** and Roboto Mono **300, 400, 500, 700** (**F** `@font-face`);
docs load Roboto **400, 500, 600, 700** and Roboto Mono **400** (**D**).

### Files saved in `fonts/` (upstream `github.com/google/fonts`, `ofl/…`, subset with `pyftsubset`)

| File | Family | Axis | Size |
|---|---|---|---|
| `fonts/roboto-variable.woff2` | Roboto 3.015 (`wdth` pinned to 100) | `wght` 100–900 | 55 KB |
| `fonts/roboto-mono-variable.woff2` | Roboto Mono 3.001 | `wght` 100–700 | 40 KB |
| `fonts/arrows.woff2` | the four arrows `← ↑ → ↓` of Adwaita Sans (Inter, OFL 1.1), which Roboto lacks | | 3 KB |
| `fonts/OFL-*.txt` | the licence texts (OFL asks for them to travel with the fonts) | | |

Coverage: Basic Latin + Latin-1 (`U+0020–00FF`: á é í ó ú ü ñ ¿ ¡ × · « » § º) plus `€ – — … − ≈ ≤ ≥ ‘ ’ “ ” ™`.
**Gap: Roboto and Roboto Mono have no arrow glyphs** (`← → ↑ ↓`), and the deck uses a few. `arrows.woff2` supplies
just those four, declared with `unicode-range: U+2190-2193` and placed after Roboto in the stack.

```css
@font-face{font-family:"Roboto";src:url(fonts/roboto-variable.woff2) format("woff2");font-weight:100 900;font-display:block}
@font-face{font-family:"Roboto Mono";src:url(fonts/roboto-mono-variable.woff2) format("woff2");font-weight:100 700;font-display:block}
```

### Type scale (root 16 px) — **M** `@layer theme`

| Token | Size / line-height | Letter-spacing | Used for (**H**) |
|---|---|---|---|
| `--text-h1`, `--text-h2` | 64 / 72 px | −1.28 px (−0.02em) | hero `h1` and every section `h2` |
| `--text-h3` | 40 / 48 px | +0.4 px (+0.01em) | secondary section titles |
| `--text-h4` | 32 / 40 px | −1 px (−0.031em) | blog card titles |
| `--text-h5` | 24 / 32 px | −0.32 px (−0.013em) | card titles, quotes |
| `--text-body-1` | 18 / 32 px | 0 | lede under a heading |
| `--text-body-2` | 16 / 24 px | 0 | body |
| `--text-body-3`, `--text-label` | 14 / 22 px, 14 / 24 px | 0 | card text, tabs, footer |
| `--text-button` | 16 / 24 px | 0 | buttons |
| `--text-caption` | 12 / 20 px | 0 | tags, dates, legal |

Habits:

- **Headlines are Roboto 400, never bold.** Headings carry no weight class and the reset sets
  `h1…h6{font-weight:inherit}` (**M** `@layer base`). Tight negative tracking, line-height 1.125, sentence case,
  centred on marketing pages, hand-broken with `<br>`.
- **Lede**: `text-body-1 text-gray-400`, max-width 500 px, 16 px under the heading (**H**).
- **Eyebrow**: `<p class="font-mono mb-3 text-primary">MANAGED CLICKHOUSE</p>` — Roboto Mono 400, 16 px, typed in
  capitals, accent colour, no extra tracking, 12 px above the heading (**H** home).
- **Buttons, nav, tabs, tags, dates, author lines: Roboto Mono 400**, sentence case, no tracking (**H**).
- **Big numbers**: `font-mono text-primary text-[56px] leading-[56px] tracking-[-4.71px]` (−0.084em, digits almost
  touching) with a two-line unit beside it in `text-body-3 uppercase` mono (**H** home, customer panel).
- Bold is rare: `font-semibold` (600) on footer column heads and names, `font-bold` on testimonial names.
- Docs (light) are more conventional: `h1` 36/40 px weight 400 −0.32 px; `h2` 24/36 px **600**; `h3` 20/28 px 600;
  body 18/28 px; table heads 11 px 600 uppercase (**D** `@layer theme`, `article table thead th`).

## 2. Colour

Tokens exactly as named in **M** `:root` (the docs redefine the core ones with identical values in **D** `:root`
and map them to semantic names such as `--color-text`, `--color-border`, `--color-link-token`).

| Token | Hex | Use | Light theme? |
|---|---|---|---|
| `--white` | `#ffffff` | page background in docs light (`--color-bg`); text on dark | **yes — page** |
| `--gray-50` | `#f6f7f9` | default light `--color-bg` on marketing; docs `--color-bg-01` (subtle surface, callout info) | **yes — surface** |
| `--gray-100` | `#e8e9ed` | docs `--color-border`, `--color-bg-02`, `--color-bg-active`; light card fill on marketing (`bg-gray-100`) | **yes — hairline / card** |
| `--gray-200` | `#d9d9d9` | docs `--color-border-02` (card borders); light tag fill (`bg-gray-200`) | **yes — border** |
| `--gray-300` | `#999999` | light card and tag border (`border-gray-300`); disabled text | yes (2.85:1, borders only) |
| `--gray-400` | `#8d8d8d` | secondary text on dark; docs `--color-text-02`, placeholder | yes (3.3:1, large text only) |
| `--gray-500` | `#636679` | **secondary text on light** (docs `--color-text-01`; `text-gray-500 dark:text-gray-400`) | **yes — 5.66:1** |
| `--dark` | `#25283d` | **primary text on light** (`--color-text`), logo colour on light, docs button text | **yes — 14.5:1** |
| `--gray-600` | `#3c3c3c` | dashed dividers, scrollbars (dark) | dark |
| `--gray-700` | `#353535` | borders on dark (cards, terminals, tab bar) | dark |
| `--gray-800` | `#262626` | 2 px terminal/video borders, icon tiles | dark |
| `--gray-900` | `#151515` | cards and terminals on dark; **code blocks in both themes**; docs footer | both (code) |
| `--gray-950` | `#0a0a0a` | page background (dark); text on green buttons | dark; text on green |
| `--primary` | `#27f795` | **brand accent**: buttons, eyebrows, links, stats, selection, logo hover (dark). On light: **button fill only** (`--color-bg-button`) | fill only (1.42:1) |
| `--primary-dark` | `#008060` | button hover fill (with white text); docs `--color-link-active`, button hover border; diff "added" | **yes — 4.93:1** |
| `--secondary` | `#2d27f7` | **links and text accent on light** (docs `--color-link-token`; blog `text-secondary dark:text-primary`) | **yes — 7.65:1** |
| `--secondary-light` | `#00c1ff` | code identifiers; docs inline-code tint (`--color-bg-code-token`) | fills only (2.1:1) |
| `--rawtree` | `#0019ff` | RawTree product colour inside tinybird.co (`hover:bg-rawtree` in the nav) | yes — 8.13:1 |
| `--warning` | `#fc9f5b` | warnings; code values/strings | fills only |
| `--error` | `#ff8389` | errors | fills only |

Code (**M** `:root`): text `--color-code-white #fff`, invocation / success `#27f795`, identifier `#00c1ff`,
value `#fc9f5b`, error `#ff8389`, diff added `#008060`, diff removed `maroon`. Docs code block: background
`var(--gray-900)`, header label `#a5a7b4` (**D** `.Code-module__…__codeBlock`, `__header`). Terminal dots:
`#EC6D62` `#F5C451` `#61C454` (**H** home).

Secondary palettes:

- Callouts (**M**): note `#4493f8`, important `#ab7df8`, warning `#d29922`, caution `#f85149`, tip = `--primary`.
- Blog categories (**M**), pure primaries used at 40 % as tag hover fills: news `#ff0000`, product `#00ff00`,
  built `#0000ff`, data `#ffff00`, engineering `#00dddd`, architecture `#ff8040`, AI `#8080ff`.
- Docs difficulty pills (**D**): easy `#d0f1e3`, intermediate `#fdf1cf`, advanced `#ffe5e5`.
- Diagram tokens (`…/chunks/0tlcgt95gejbt.css`): canvas `--gray-50`, nodes white with `--gray-200` border,
  connectors `--gray-300`, active `--primary`, "Tinybird-owned" `--primary-dark`, "customer-owned" `--secondary-light`.

## 3. Shape and components

| Thing | Values | Source |
|---|---|---|
| Radii | `rounded` 4 px (cards, tab bar, tags-in-bar); `--radius-card` / `--radius-lg` 8 px (icon tiles, terminals, big panels); `--radius-md` 6 px; `--radius-pill` 24 px (tags); code block 4 px | **M** theme + utilities; **F** `.Code-module__…__code` |
| **Buttons have radius 0** | no `rounded-*` class on any button; docs say `rounded-none` explicitly | **H**; **D** HTML |
| Borders | 1 px solid everywhere; 2 px only on terminal / video frames (`border-2 border-gray-800`); dashed 1 px `--gray-600` between FAQ rows (`border-t border-dashed border-gray-600`) | **H** home, `/pricing`, `/product/managed-clickhouse` |
| Shadows | **none on marketing** (flat; `shadow-*` utilities exist but no card uses them). Docs: `--shadow-card-value: 0 4px 6px #0000000d` | **H**; **D** `:root` |
| Primary button | `font-mono text-button px-6 py-4 bg-primary text-gray-950`, hover `bg-primary-dark text-white`, `transition-all duration-300`; compact: `py-3` / `py-2`, `h-10`. Docs: 16/24 px, `py-2 px-4`, 1 px `border-brand` | **H** (11 uses on home) |
| Secondary (text) button | `font-mono bg-transparent text-primary hover:underline px-0 py-0` — a green mono link beside the primary, 32 px gap | **H** |
| Outline button | `px-6 py-3 bg-transparent border border-white text-white hover:border-primary hover:text-primary` | **H** `/pricing` |
| Corner ticks | `.Button--corners`: on hover four 6 px L-shaped 1 px `--primary` brackets appear 4 px outside the corners and the fill turns green | **M** / **F** |
| Bracket tabs | mono 14 px labels written `[Label]`, separated by a `\|` in `white/20`; active = `text-primary`; boxed variant: bar `p-1 border border-gray-700 rounded`, active chip `bg-white/5 border-white/20` | **H** home |
| Tag / pill | `text-caption font-mono border rounded-pill px-[10px] py-1`; dark: `border-gray-300 text-gray-300`, transparent; **light: `border-gray-300 bg-gray-200 text-gray-950`**; active filter `bg-primary/60 border-primary` | **H** `/blog` |
| Card | `rounded border p-5 md:p-6`, dark `bg-gray-900 border-gray-700`, **light `bg-gray-100 border-gray-300`**, hover = border colour only; icon tile 40 px `bg-gray-800 rounded-card`; title `text-h5`; text `text-body-3 text-gray-500 dark:text-gray-400` | **H** home |
| Docs card (light) | `rounded border border-v-border-02 p-4`, white, hover `border-v-border-03` (`#636679`); title 17 px 600; text 12/20 px `#636679` | **D** HTML |
| Quote | left rule: `border-l` + `pl-6 … py-10`, light `border-gray-300 bg-gray-100`; opening mark at 40 % opacity hung left; attribution in mono 14 px | **H** home |
| Terminal | `bg-gray-900 border(-2) border-gray-700/800 rounded-lg`, padding 32 px, three 12 px dots, file name centred in mono `text-gray-300`, body mono 14 px, prompt `$ ❯` in `--primary`, comments `#`-prefixed `text-gray-400` | **H** home |
| Docs code block | `#151515`, radius 4 px, padding 24 px, 14/24 px; header: mono 12 px **700 uppercase, tracking .04em**, `#a5a7b4`; square 32 px `bg-gray-700` icon buttons | **D** code CSS |
| Inline code (light) | mono 16/24 px, `padding:1px 6px`, radius 2 px, text `--secondary` | **D** `article p code` |
| Tables (light) | no outer border; 1 px `--gray-100` rule under head and each row; head 11 px / 600 / uppercase; cell padding `8px 16px 8px 0` | **D** `article table…` |
| Layout rhythm | container `max-w-[1440px]`, gutters 40 px, 12 columns with 24 px gap, content on the middle 10; between sections `lg:my-38` = **152 px** (96 at `md`); eyebrow → heading 12 px; heading → lede 16 px; header block → content 40–56 px; card grid gap 24 px | **H** home |

## 4. Motifs

- **Monospace as interface voice**: every label a person could click or scan is Roboto Mono; prose is Roboto.
- **Square brackets**: `[Get Started]`, `Product [+]`, `RawTree [NEW]` (superscript, 10 px, green), footer heads
  followed by a faint `/` (**H**).
- **Terminal windows and diffs** as illustration: red rows `#800000` at 70–90 %, green rows `#008060` at 60 %,
  grey line numbers (**H** home, "clickhouse-setup-plan.md").
- **Dash matrix**: a regular grid of thin vertical green strokes (about 1.5 × 27 px on a 35 px pitch) that rotate
  and thicken towards one corner; file `…/media/pipe-matrix-static.1o7d514hw5rwx.svg` (1360 × 737, fill `#27F795`),
  also on the Open Graph image `tinybird.co/opengraph-image.png`.
- **Giant cropped wordmark** bleeding off the bottom of the footer (`…/media/cropped-wordmark.2h1vxqu87g37p.svg`).
- **Customer logos** in one row, monochrome, at 40 % opacity, the active one at 100 % with an underline.
- **Flat, hard-edged, high contrast**: no gradients, no shadows, no rounded buttons; colour comes from one accent.
- Uptime chip: five 2 × 12 px green bars beside "All systems operational" (**H** footer).

## 5. Logo

No brand or press kit is published: `/brand`, `/press`, `/brand-kit`, `/media-kit`, `/press-kit`, `/brand-assets`
all return 404 and `sitemap-0.xml` lists none, so **there are no official clear-space or usage rules**. The assets
below are the inline SVGs the site itself ships.

| File | What | Source |
|---|---|---|
| `assets/tinybird-logo.svg` | Full lockup (symbol + wordmark), `viewBox 0 0 124 32`, `fill="currentColor"` — as published. **Inline it** and set CSS `color`; through `<img>` it renders black | header of `https://www.tinybird.co/` (identical path data in the docs header) |
| `assets/tinybird-logo-ink.svg` | Same paths, `currentColor` → `#25283d`. **The version for white backgrounds**, usable as `<img>` | derived; colour = docs light `--color-text` (`--dark`) |
| `assets/tinybird-logo-white.svg` | Same paths, `#ffffff`, for a dark slide | derived; header uses `text-white` |
| `assets/tinybird-symbol.svg` | Symbol alone, `viewBox 0 0 500 500`, `currentColor` | "Sign up to Tinybird" tile in the Product menu of `https://www.tinybird.co/` |
| `assets/tinybird-symbol-ink.svg` | Symbol alone in `#25283d` | derived |
| `assets/rawtree-symbol.svg` | RawTree symbol, `viewBox 0 0 193 220`, blue gradient `#1B83FE → #5F68FA` — unmodified file | `https://rawtree.com/rawtree-logo.svg` (the site uses it as a CSS mask in `#1a1615`, with "RawTree" set in Geist 600 beside it) |

Only edit made to the Tinybird files: the `class`, `width` and `height` attributes of the `<svg>` tag were dropped
(Tailwind sizing); path data, `viewBox` and opacities are untouched.

How Tinybird uses it (observed, not a published rule):

- The symbol is three polygons: body at full opacity, wing and tail at **0.6 opacity** of the same colour. Keep it
  one colour; never recolour the parts separately.
- Colours seen: white on `#0a0a0a` (site header, hover → `#27f795`); `#25283d` on white (docs, light theme);
  all `#27f795` on `#0a0a0a` (Open Graph image); `#25283d` symbol on a `#27f795` square
  (`https://tinybird.co/tinybird-fwd-icon-square.png`, the logo in the site's JSON-LD).
- Size on the site: 109 × 28 px in a 72 px header, top-left.
- Clear space — **inferred**: keep at least the symbol's width (32/124 of the lockup width) free on every side.

## 6. How to apply to a 1920 × 1080 deck on white

Sizes below are **inferred**: the site scale multiplied by 1.25–2 for projection and aligned with the organisers'
deck (§7). Colours and shapes are the measured ones.

```css
:root{
  --paper:#ffffff;  --surface:#f6f7f9;  --line:#e8e9ed;  --line-2:#d9d9d9;
  --ink:#25283d;    --ink-2:#636679;    --ink-3:#8d8d8d;
  --green:#27f795;  --green-ink:#008060;   /* fill / text */
  --blue:#2d27f7;   --rawtree:#0019ff;
  --code:#151515;   --black:#0a0a0a;
  --sans:"Roboto","Arrows",system-ui,sans-serif;           /* Arrows supplies ← ↑ → ↓ */
  --mono:"Roboto Mono","Arrows",ui-monospace,monospace;
}
```

| Element | Recommendation |
|---|---|
| Slide | `--paper`, text `--ink`. Margins about 104 px sides, 64 px top (the 40 px gutter of a 1440 px page, scaled) |
| Cover / statement | Roboto **400**, 112–128 px, line-height 1.08, tracking −0.02em |
| Slide title | Roboto **400**, 72–80 px, line-height 1.125, tracking −0.02em, sentence case, `--ink`. No bold |
| Lede | Roboto 400, 36 px / 1.45, `--ink-2`, at most two lines, 24 px under the title |
| Eyebrow | Roboto Mono 400, 22–24 px, capitals, tracking 0, `--green-ink`, 16 px above the title. Suggestion: a bracketed index in the site's idiom, `[03] VALIDACIÓN OFFLINE` |
| Body / card text | Roboto 400, 28–30 px / 1.5; secondary `--ink-2`. Card title Roboto 400, 36 px / 1.33, tracking −0.013em |
| Labels, axes, tags, footers | Roboto Mono 400, 18–20 px, `--ink-2` |
| Key number | Roboto Mono 400, 112–144 px, line-height 1, tracking −0.084em, `--green-ink`; unit beside it in mono 20 px capitals on two lines |
| Accent | **Green `#27f795` only as a fill** with `--ink` or `--black` on top: highlight blocks, the team's bars, a marker behind a word, a 12 px bar on the left edge. **Green text and thin lines use `#008060`.** `--blue` only for links. One accent per slide |
| Card | `1px solid var(--line-2)`, radius **4 px**, padding 32 px, white or `--surface`; **no shadow**. Emphasised card: border `--ink`, or a 4 px `--green` top edge |
| Pill / tag | Roboto Mono 18 px, `1px solid #999`, radius 24 px, padding 6 px 14 px, fill `#d9d9d9`, text `--black`. "Ours": fill `--green`, border `--green-ink`. Tabs: `[Label]` in mono, active in `--green-ink` |
| Button-like callout | square (radius 0), fill `--green`, text `--black`, Roboto Mono 24 px, padding 22 px 34 px |
| Code / terminal | **stay dark on the white slide**, as the light docs do: `#151515`, radius 8 px, three 12 px dots `#EC6D62 #F5C451 #61C454`, Roboto Mono 22–24 px, text `#fff`, prompt and commands `#27f795`, identifiers `#00c1ff`, values `#fc9f5b`, comments `#8d8d8d`. This is where the bright green is at home |
| Hairlines, tables | 1 px `--line`; table head mono or Roboto 600, 16 px, capitals; no outer box |
| Logo | `assets/tinybird-logo-ink.svg`, 40–48 px high, a corner of every slide or cover and closing only. RawTree symbol beside it only where the slide is about RawTree |
| Dark slide (optional, cover or closing) | `#0a0a0a` (site) or `#25283d` (the organisers' Tinybird slide, §7), white Roboto 400, eyebrow and numbers in `#27f795`, `tinybird-logo-white.svg`, dash matrix as decoration |

Chart colours:

| Series | Colour | Notes |
|---|---|---|
| **Our team** | bars / areas `#27f795`; lines, markers and labels `#008060` | Mint bars on white are 1.42:1: give them a 2 px `#008060` edge or a direct value label in `--ink`. Lines 4 px |
| **Organisers' reference** | `#0019ff` (`--rawtree`) | Tinybird's own token for RawTree; 8.1:1 on white. `#2d27f7` is the alternative if the slide already has links |
| Other teams | `#d9d9d9` fills, `#999999` lines | one grey for all of them, no legend entry each |
| Baseline | `#636679`, dashed 2 px line, mono label | |
| Axes, grid | text `#636679` in Roboto Mono 18 px; grid `#e8e9ed` 1 px; no chart border | |
| Bad / good deltas | `#f85149` / `#008060` | the callout red (**M**); `--error #ff8389` is too pale on white |

Do not: bold headlines, round the buttons, add shadows or gradients, set green text on white, mix Roboto with Geist.

## 7. The organisers' slides (`docs/sources/slides.html`) versus tinybird.co

That deck is styled as **RawTree**, not as Tinybird; its header comment names its source as the RawTree slide
template ("azul #0119FF, tinta #25283D, kicker en mono azul, números 01/02/03 y reglas azules"). rawtree.com
(**R**) matches it: Geist + Geist Mono, `--color-brand-500 #0019ff`, page `#f7f7f4`, white cards.

| | Organisers' deck (**S** `:root`) | tinybird.co (**M**) | rawtree.com (**R**) |
|---|---|---|---|
| Sans / mono | Geist / Geist Mono (embedded) | **Roboto / Roboto Mono** | Geist / Geist Mono |
| Accent | `--accent #0019ff` | `--primary #27f795` (`--rawtree #0019ff` exists as a product colour) | `--primary #0019ff`, hover `#0012cc` |
| Ink | `--ink #25283d` | `--dark #25283d` — **same** | `--foreground #1a1615` |
| Paper | `--paper #fff`, `--paper-2 #f7f7f4` | `#0a0a0a` (dark); docs light `#fff`, `#f6f7f9` | `--background #f7f7f4`, `--surface #fff` |
| Muted text | `--muted #5e6177`; subtitles `#777169` | `--gray-500 #636679` | `--muted-foreground #737373` |
| Hairline | `--line #dfe1e8`; column rules `--rule #155eee` 2 px | `--gray-100 #e8e9ed` | `--border #e5e5e5` |
| Tint / deep | `--tint #eceeff`, `--deep #0c1dc2`, `--ok #1fa63d` | — | `--color-brand-50 #e9eefc` |
| Code | `--code #16171d`, ink `#e8e9ee`, blue `#7c9bfa`, green `#02b078`, yellow `#ee9a48`, grey `#8a9799` | `#151515`, `#27f795`, `#00c1ff`, `#fc9f5b` | keyword `#0026d9`, string `#c76100`, function `#00858c` |
| Type scale at 1920 | 128 / 80 / 40 / 32 / 24 / 20 / 16 / 14 / 12 px | 64 / 40 / 32 / 24 / 18 / 16 / 14 / 12 px at 1440 | display 48, h1 36, h2 24 px |
| Title | weight 400, −0.03em, line-height 1.08 | weight 400, −0.02em, line-height 1.125 | weight 400, −0.025em, 1.25 |
| Eyebrow ("kicker") | Geist Mono 24 px, accent blue, sentence case | Roboto Mono 16 px, green, capitals | Geist Mono 14 px, capitals, +0.05em, grey |
| Shapes | pills `99px` with 0.5 px border; cards 1 px line, radius 0.6cqw (11.5 px); terminal radius 0.8cqw (15 px) **with** shadow; 0.6cqw (11.5 px) accent bar down the left edge | square buttons, 4–8 px radii, no shadows | pill buttons (`rounded-full`), `--radius 10px`, soft shadows |
| Numbers | `01 / 02 / 03` in mono 300, 80 px, blue; stats 80–128 px, −0.045em | stats in mono 400, 56 px, −0.084em, green | — |

What the two share, and what therefore reads as "the house": regular-weight headlines with tight tracking, a mono
face for labels and numbers, one saturated accent, navy ink `#25283d`, hairlines instead of boxes, dark terminal
windows.

The deck also contains CSS for a **Tinybird-styled slide** (`.sheet--tb`, lines 1150–1159): background `var(--ink)`
`#25283d`, `--tb-green: #27f795` for kicker and title, a green bar on the left edge. Its comment credits a Figma file
"BRAND-REVAMP-2026" with a hexagon logo and a pixelated hummingbird; the markup for that slide is not in the file
and neither element appears on the live site, so **a newer Tinybird identity may exist that could not be verified**.

Choosing: Roboto + green (§6) says "Tinybird"; Geist + `#0019ff` says "RawTree" and will look like a continuation
of the organisers' deck. **The deck uses the Tinybird look** (the team asked for it), so only Roboto is in `fonts/`;
going RawTree would mean adding Geist (OFL, `github.com/google/fonts`, `ofl/geist`) and swapping
`--green-ink`/`--green` → `#0019ff`, `--surface` → `#f7f7f4`, buttons and tags → pills.

## 8. Not verified

- No official brand guidelines, clear-space rules or logo downloads were found; logo usage in §5 is observation.
- Whether Tinybird has a newer identity (the "BRAND-REVAMP-2026" Figma mentioned in **S**).
- The slide sizes in §6 are scaled from web values, not taken from a Tinybird slide template.
- Fira Mono, Geist and Seven Segment are declared in tinybird.co's CSS but no element on the pages fetched (home,
  product, blog, a blog post, pricing, about) uses them; where (or whether) they appear elsewhere was not traced.
- The marketing site was only seen in its dark theme; its light values come from the class attributes and the
  docs, not from a rendered light marketing page (none exists).
- The signed-in product UI (`cloud.tinybird.co`) was not inspected.
