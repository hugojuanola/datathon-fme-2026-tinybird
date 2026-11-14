# Jury presentation (Sun 15 Nov, 14:00 CET)

The deck for the 30 jury points, in Spanish. One self-contained page: open [`index.html`](index.html) in a
browser (Chrome or Edge), press `F` for full screen. No server, no network, no install.

| File | What |
|---|---|
| [`index.html`](index.html) | The 16 slides, their speaker notes and the small engine that runs them |
| [`data.js`](data.js) | Leaderboard snapshot shown on the "where we stand" and "learning" slides, and since when we lead the public board (`lead`). Written by code, not by hand |
| [`update_data.py`](update_data.py) | Rewrites `data.js` from the public leaderboard and `realtime_analyisi_leaderboard/history.csv` (stdlib, read-only, no API key). For `lead` it rebuilds the board of the practice round every 5 minutes from the same API: about 290 small requests, one minute |
| [`design.md`](design.md) | RawTree's visual identity (type, colours, shapes, logo), read from the organisers' deck and rawtree.com on 14 Nov, with the source of each value. The deck's CSS follows it |
| `assets/` | RawTree's symbol and arcs and Tinybird's logo, as published by them |
| `fonts/` | Geist and Geist Mono (RawTree's typefaces), subset to Latin, under the SIL Open Font License |

## Before presenting

```bash
python3 presentation/update_data.py     # after the final ranking is published (Sun 12:00 CET)
```

The "where we stand" slide then shows the final round instead of the practice round. While the final is
running the leaderboard hides the metrics and the script leaves `data.js` as it was.

Slide 3 also says, under our place, since when we lead the public board of the practice round and for how
long we did not ("líderes desde el sábado a las 14:10, salvo 20 minutos", measured 15 Nov 00:20 CET). Run the
script once more **shortly before Sunday 10:00 CET** (not on the serving laptop) so that line covers the whole
practice round; after the final it is recomputed if the API still serves the practice windows, and kept as it
was if not.

Every other number on the slides is quoted from [`docs/findings.md`](../docs/findings.md); the speaker
notes of each slide name the section (or [`best_model.md`](../best_model.md), the record of every version
served). The deck was last brought up to date with branch `javier` at commit `ed9f8aa` (15 Nov, 00:35 CET:
findings §21–§22, the ledger of every test in `realtime_analyisi_leaderboard/experiments.md`, the store's
calendar, arms `skore_money_v31`, `v32`, `v36`, `v37` running overnight).

**Still to fill in on Sunday**, once the night is read and the final is over; the notes of these slides say
"decir aquí…" where the spoken sentence depends on it:

| Slide | What depends on Sunday |
|---|---|
| 3 | The whole slide: run `update_data.py` after 12:00 |
| 5 | Which arm served the final, and whether the third (organic) model stayed: the line under the chips says "en prueba" and quotes the offline gain of reordering the ten (+2.5 %) |
| 9 | Whether the one surviving signal (new products ×1.5 for known shoppers, `v36`) passed the night (notes) |
| 11 | What the overnight arms said (notes) |
| 12 | How the trend of the final went (notes) |
| 13 | The share of answers on time during the final, whether the cable fixed the bursts, and the two latency ticks (`queries/health.sql`) |

When the system changes again, these places need a look too: the three before → after pairs of slide 7
(`offline.train`, `offline.next_purchase`, `scripts/arms.py`), the six rows of slide 9 (each one a row of
`realtime_analyisi_leaderboard/experiments.md`), the `VERSIONS` markers of the trend chart, the feature
count and the ranking time on slide 5 (the serving ranker's, not `len(FEATURES)`), and the latency ticks on
slide 13 (`queries/health.sql`).

Slide 6 is one real request (`r_04ad0292cb677169`, 14 Nov 20:00:19 UTC): what we served and why from
`team_06.scratch`, the outcome from `team_06.feedback`, the product names from `shop.catalog` (translated).

## Built for the jury's rubric

The 30 points are four criteria ([`docs/challenge.md`](../docs/challenge.md)); the deck is ordered by them and
the kicker of each slide (top left) names the one it answers.

| Criterion (points) | What the jury asks | Slides | Where each thing they name is |
|---|---|---|---|
| Method (10) | Sound, well justified, validated offline before going live | 4–9 | measured lifts (4) · two stages (5) · one real request (6) · offline, the next-purchase judge and live arms, with the noise measured and the decision rule written before reading the data (7) · attributes (8) · six ideas that did not pass, each with the number that closed it, and the control that tells a signal from an echo of the ranker (9) |
| Learning from the stream (10) | Feedback and live events: exploration, trends, price changes, cold start | 10–12 | satiation, learned from our own feedback (10) · one row per word of the rubric (11) · a trend seen in 41 s and measured in our carousel, where the gap to the next team was made, and a fault of the third model in the next trend seen in 12 minutes and fixed in 21 (12) |
| Use of RawTree (5) | Features in SQL, embeddings, how the pipeline reads and writes | 14, 15 | an aggregation in SQL on screen, reads and writes, `scratch`, and why no embeddings, with the measurement behind it (14) · the demo runs SQL (15) |
| Communication (5) | Could a product manager understand what it does and why it works? | all | plain words on the slides, the technical terms in the speaker notes; slide 6 is the whole system in one shopper |

"Anything a team cannot explain in the presentation may be penalised": both of us should be able to take
any slide. The notes (`N`) carry the numbers and the answers to the likely questions.

## Keys

| Key | |
|---|---|
| `→` `space` `PgDn` / `←` `PgUp` | Next / back (a presentation clicker works). Some slides reveal a last line on an extra press |
| `F` | Full screen |
| `O` | Index of slides, to jump to one during the questions |
| `N` | Speaker notes of the current slide (for rehearsing: the audience would see them) |
| `C` / `R` | Show the clock: elapsed / planned up to the end of this slide; it turns red when 15 s behind. `R` restarts it |
| `L` | Switch between the short version (the default) and the long one. `index.html?larga` opens in the long one |

## Two versions, one file

Nobody has told us how long the slot is, so the deck opens in the version that fits the tightest case and
the long one is a key away:

| | Short (default) | Long (`L`, or `?larga`) |
|---|---|---|
| Length | 5 minutes with the demo inside (45 s, two commands) | 7 min 35 s (6 min 5 s of slides, 1 min 30 s of demo) |
| Slides | 13: the three marked `data-extra` are skipped | all 16 |
| Seconds per slide | `data-t5` | `data-t` |

The three extra slides (8 attributes, 10 satiation, 13 reliability) are the ones the jury's rubric leans on
least: the attributes' three numbers are on slide 7 and the real request of slide 6 shows them, satiation is
the first row of slide 11, and reliability is scored by the leaderboard. They stay in the index (`O`), marked,
for the questions. Slide numbers in the index, in `#N` and in this file are always the long version's; the
counter on screen counts the slides of the version being shown. If the slot turns out to be 5 minutes plus
a separate demo, stay in the short version and take the demo at its full length.

## Time plan

`index.html?min=N` rescales the plan of the version being shown to N minutes.

| # | Slide | Jury criterion | Short (s) | Long (s) |
|---|---|---|---|---|
| 1 | Cover | | 5 | 10 |
| 2 | The challenge | Communication | 15 | 20 |
| 3 | Where we stand | | 15 | 20 |
| 4 | Measure before modelling | Method | 25 | 30 |
| 5 | Two stages, then the store moves | Method | 25 | 25 |
| 6 | One real request, and why each of its 10 products | Method, communication | 20 | 25 |
| 7 | Three exams: offline, the next-purchase judge, live arms | Method (validated offline) | 35 | 35 |
| 8 | The finding: description attributes | Method | extra | 25 |
| 9 | What did not work, and how we know | Method | 20 | 25 |
| 10 | Satiation: what our own feedback taught first | Learning from the stream | extra | 25 |
| 11 | Feedback, exploration, trends, price changes, cold start | Learning from the stream | 35 | 35 |
| 12 | A trend, measured live; a fault in the next one, fixed in 21 minutes | Learning from the stream | 30 | 30 |
| 13 | Reliability | | extra | 20 |
| 14 | RawTree | Use of RawTree | 20 | 25 |
| 15 | Demo | Use of RawTree, communication | 45 | 90 |
| 16 | Three ideas | Communication | 10 | 15 |
| | | | **300** | **455** |

`index.html?static` shows every slide in its final state without animation; printing that page to PDF
(landscape, no margins, background graphics on) gives a 16-page backup.
