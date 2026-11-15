# RawTree visual identity — reference for the jury deck

The deck follows **RawTree's slide template**: the one the organisers' own challenge deck is built on. The
cover and the closing slide carry both logos, Tinybird and RawTree, parted by a thin rule: RawTree is
Tinybird's product and Tinybird presents the challenge.

Measured on **14 Nov 2026**. Nothing here is from memory; anything not read directly from a file is marked
**inferred**. Sources, cited below by letter:

| Ref | What | Where |
|---|---|---|
| **S** | The organisers' challenge slides. Their header comment names the source: the RawTree slide template ("RawTree basic - Nov. 10th 2026.pdf": blue, navy ink, mono kicker in blue, numbers 01/02/03 and blue rules) | `docs/sources/slides.html` in this repo, `<style>` lines 34–2550; fonts and art embedded as data URIs on lines 2551–2552 |
| **R** | rawtree.com stylesheet and page | `https://rawtree.com/` (bundle `…/_next/static/chunks/161_1dx67vk.u.css`; hashed names change on every deploy) |
| **T** | tinybird.co header and docs (for Tinybird's logo and its colour on white) | `https://www.tinybird.co/`, `https://www.tinybird.co/docs` |

An earlier version of the deck was styled as tinybird.co (Roboto, mint green `#27f795`, square buttons). The
full reading of that site is in the git history of this file (commit `0590d9d`); §6 keeps the comparison.

## 1. Typography

| Role | Family | Source | Licence |
|---|---|---|---|
| Titles, body, the "RawTree" wordmark | **Geist** (Vercel), variable `wght` 100–900 | **S** `--sans`; **R** | SIL OFL 1.1 |
| Kickers, labels, big numbers, code | **Geist Mono**, variable `wght` 100–900 | **S** `--mono`; **R** | SIL OFL 1.1 |

Files: `fonts/geist-variable.woff2` (34 KB) and `fonts/geist-mono-variable.woff2` (35 KB), from the upstream
release in `github.com/google/fonts` (`ofl/geist`, `ofl/geistmono`), subset with `pyftsubset` to Basic Latin +
Latin-1 plus `€ – — … − ≈ ≤ ≥ ← ↑ → ↓` and typographic quotes. The licence texts travel with them (`fonts/OFL-*.txt`).

Type scale of the template at 1920 px (**S** `:root`, "only these sizes"): 128 / 80 / 40 / 32 / 24 / 20 / 16 / 14 / 12.

| Element | Template value (**S**) | In our deck |
|---|---|---|
| Slide title | Geist 400, 75 px (`3.889cqw`), line-height 1.12, tracking 0, colour `#25283d` (`.sheet--tpl .title`) | the same size and colour, but **weight 500, tracking −0.035em**: the team found regular weight too plain at this size. Cover title and "Gracias." in 600 |
| Emphasis | upright, regular, brand blue (`.sub em`); the template never bolds or highlights a title | `h1 em` in `--accent` |
| Subtitle | 40 px, line-height 1.35, tracking −0.01em, warm grey `#777169` (`.sub`) | `.lead` |
| Kicker (top left) | Geist Mono 24 px, line-height 1.3, **sentence case**, `--accent` (`.kicker`) | `.kick` |
| Ticket (top right) | Geist Mono 24 px, `--muted` (`header.furniture .ticket`) | `.ticket`: "Skore Money · team_06" |
| Column number `01 02 03` | Geist Mono **300**, 80 px, `--accent` (`.no`) | demo list |
| Big figure | Geist Mono **300**, 128 px, `--accent`, slashed zero (`.cols--stat .stat`) | `.big` (112–240 px) |
| Secondary figure | Geist 400, 80 px, tracking −0.045em, `--accent` (`.stat`) | `.trio b` at 64 px |
| Name + text | 32 px / 500 / 1.25, then 24 px / 1.35 in `--muted` (`.sheet--tpl .name`, `.text`) | cards, lists, columns |
| Counter | Geist Mono 16 px, tracking 0.04em, tabular, current slide in bold (`.ticket`, `.count`) | `#count` at 18 px |

## 2. Colour

Tokens exactly as named in **S** `:root` (lines 35–67).

| Token | Hex | Use |
|---|---|---|
| `--paper` | `#ffffff` | the sheet |
| `--ink` | `#25283d` | titles, names, logo. The same navy as Tinybird's `--dark` |
| `--muted` | `#5e6177` | body text, tickets, labels |
| (sub) | `#777169` | subtitles and ledes, "warm grey … from RawTree's Google Slides template" |
| `--accent` | `#0019ff` | **RawTree's brand blue** (`--color-brand-500` in **R**): kicker, numbers, emphasis, the edge, "our" marks |
| `--rule` | `#155eee` | the vertical rules between columns |
| `--tint` | `#eceeff` | fill of team tags and inline code |
| `--line` | `#dfe1e8` | hairlines, card borders |
| `--deep` | `#0c1dc2` | the arcs on a full-blue sheet (we have none) |
| `--ok` | `#1fa63d` | "live" tags (fill `#e8faeb`) |
| `--code` | `#16171d` | terminal; text `#e8e9ee`, comments `#8a9799`, keywords `#7c9bfa`, strings `#02b078`, numbers `#ee9a48` |

Contrast on white (computed): `--accent` 8.1:1, `--muted` 6.1:1, `#777169` 4.8:1.

Charts are ours; the template has none. Rule: **one accent, everything else grey**, the way the template's
scoring slide does it.

| Series | Colour | |
|---|---|---|
| Our team | `#0019ff` | bars, line, end dot |
| Organisers' reference | `#70748a` (4.6:1) | a darker grey, always named in a direct label |
| Baseline, other teams | bars `#d5d8e2`, lines `#a7abba` | |
| Grid, axis text | `#dfe1e8`, `#5e6177` in Geist Mono 20 px | no chart border |

Every bar and line end carries its value as text, so no series depends on colour alone.

## 3. Shape and components

| Thing | Template value (**S**) | In our deck |
|---|---|---|
| Sheet margins | 104 px sides (`5.4cqw`), 65 px top, 54 px bottom | the same |
| **Blue edge** | an 11.5 px (`0.6cqw`) `--accent` bar down the left edge of every white sheet (`.sheet::after`) | `#stage::after` |
| **Arcs** | the logo's arcs, enormous, in ink at **3.5 % opacity** behind the content (`.sheet::before`) | `#stage::before`, `assets/rawtree-arcs.png` |
| Furniture | header: kicker left, ticket right; footer: logo left, counter right | `.furn`, `#logo`, `#count` |
| Columns | `border-left: 3px solid var(--rule)` between columns, none before the first; text 34 px from the rule (`.cols > li`) | three stats, the `trio` |
| Tag | pill: radius 99 px, 0.5 px border in the text colour, Geist Mono 14 px; neutral `#eef0f5` / `--muted`, team `--tint` / `--accent`, live `#e8faeb` / `--ok` (`.tag`) | `.chip` (team variant, 1 px border at our size) |
| Card | white, 1 px `--line`, radius 11.5 px, no shadow | `.card`, `.stage`, `.node` (radius 12 px) |
| Terminal | `--code`, radius 15 px (`0.8cqw`), shadow `0 27px 61px -19px rgb(16 18 40 / 40%)`, three 15 px dots in `#3b3c46`, file name centred in mono grey, body Geist Mono 24 px / 1.65 (`.term`) | `.term`, `.cmd` |
| Inline code | `--tint` fill, `--accent` text, radius 0.2em, 0.86em (`.content code`) | `.mono`, `.desc mark` |
| Full-blue sheet | `--accent` background, white text, arcs in `--deep`: cover, statements, quotes | **not used**: the team asked for a white deck |
| rawtree.com (**R**) | pill buttons (`rounded-full`), `--radius 10px`, page `#f7f7f4`, soft shadows | not used: the slide template is the closer model |

## 4. Motifs

- **The arcs of the logo** as a watermark, and the **blue edge**: what makes a sheet read as RawTree at a glance.
- **Mono blue numbers**: `01 / 02 / 03` over columns separated by blue rules; big figures in Geist Mono Light.
- **The pixel tree**: the template's cover is a pixelated tree on blue (cells of 8.5 px). Our cover borrows the
  idea, not the image: a grid of pixels where three light up in blue every second, one per shopper answered
  (the real rate of the stream).
- **Dark terminal windows** on white sheets for anything that is code.

## 5. Logos

| File | What | Source |
|---|---|---|
| `assets/rawtree-symbol.svg` | RawTree symbol, `viewBox 0 0 193 220`, blue gradient `#1B83FE → #5F68FA`. Unmodified | `https://rawtree.com/rawtree-logo.svg`; byte-identical to the `--logo` data URI in **S** |
| `assets/rawtree-symbol-ink.svg` | The same paths with the gradient fill replaced by `#25283d`: the template shows the symbol in ink, through a CSS mask (`.logo::before`), and a mask cannot load from a `file://` page | derived |
| `assets/rawtree-arcs.png` | The arcs watermark, 1280 × 720, alpha mask tinted `#25283d` | the `--arcs` data URI in **S** (line 2552) |
| `assets/tinybird-logo-ink.svg` | Tinybird's full lockup, `viewBox 0 0 124 32`, in `#25283d` (its colour on white in Tinybird's docs). Path data untouched; only the Tailwind `class`, `width`, `height` were dropped and `currentColor` fixed to the ink | inline SVG in the header of **T** |

The RawTree lockup has no wordmark file: the template and rawtree.com both set **"RawTree" in Geist 600,
tracking −0.025em**, beside the symbol (symbol 40 px wide for 32 px text, gap 11.5 px: **S** `.logo`).

The double lockup, `tinybird | RawTree`, is ours: both marks in the same ink at the same optical
height, a thin vertical rule in `--muted` between them (not a `×`: the two are one company, not a
collaboration), used on the cover and on the closing slide. Every other slide
carries the RawTree logo bottom-left, as the template does.

Neither company publishes brand guidelines (`/brand`, `/press` and similar return 404 on tinybird.co), so
there are **no official clear-space or co-branding rules**; the lockup follows the common convention.

## 6. RawTree versus Tinybird

| | RawTree template (**S**) — used | rawtree.com (**R**) | tinybird.co |
|---|---|---|---|
| Sans / mono | Geist / Geist Mono | Geist / Geist Mono | Roboto / Roboto Mono |
| Accent | `#0019ff` | `#0019ff`, hover `#0012cc` | `#27f795` (dark site); `--rawtree #0019ff` exists as a product colour |
| Ink | `#25283d` | `#1a1615` | `#25283d` |
| Paper | `#ffffff`, `#f7f7f4` | `#f7f7f4`, white cards | `#0a0a0a`; docs light `#ffffff` |
| Title | weight 400, line-height 1.12 | weight 400, −0.025em | weight 400, −0.02em |
| Kicker | mono 24 px, blue, sentence case | mono 14 px, capitals, grey | mono 16 px, green, capitals |
| Shapes | pills, 11.5 px cards, 15 px terminal with shadow, blue edge | pill buttons, 10 px radius, soft shadows | square buttons, 4–8 px radii, no shadows |
| Numbers | mono 300, blue | — | mono 400, green, −0.084em |

What the two brands share: regular-weight titles, a mono face for labels and numbers, one saturated accent,
navy ink, hairlines instead of boxes, dark terminal windows.

## 7. Not verified

- The original "RawTree basic" slide template (a PDF / Google Slides file) was not seen: everything comes from
  the organisers' HTML rendering of it.
- No official brand guidelines or logo downloads were found for either company.
- The organisers' CSS mentions a Figma file "BRAND-REVAMP-2026" (a hexagon logo, a pixelated hummingbird) for
  Tinybird; neither appears on the live site, so a newer Tinybird identity may exist.
- Sizes marked "in our deck" that differ from the template (figures at 112–240 px, counter at 18 px) are our
  choices for a projector, not template values. So are the heavier, tighter titles (500 / 600 instead of 400).
