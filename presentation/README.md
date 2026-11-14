# Jury presentation (Sun 15 Nov, 14:00 CET)

The deck for the 30 jury points, in Spanish. One self-contained page: open [`index.html`](index.html) in a
browser (Chrome or Edge), press `F` for full screen. No server, no network, no install.

| File | What |
|---|---|
| [`index.html`](index.html) | The 13 slides, their speaker notes and the small engine that runs them |
| [`data.js`](data.js) | Leaderboard snapshot shown on the "where we stand" and "learning" slides. Written by code, not by hand |
| [`update_data.py`](update_data.py) | Rewrites `data.js` from the public leaderboard and `realtime_analyisi_leaderboard/history.csv` (stdlib, read-only, no API key) |
| [`design.md`](design.md) | RawTree's visual identity (type, colours, shapes, logo), read from the organisers' deck and rawtree.com on 14 Nov, with the source of each value. The deck's CSS follows it |
| `assets/` | RawTree's symbol and arcs and Tinybird's logo, as published by them |
| `fonts/` | Geist and Geist Mono (RawTree's typefaces), subset to Latin, under the SIL Open Font License |

## Before presenting

```bash
python3 presentation/update_data.py     # after the final ranking is published (Sun 12:00 CET)
```

The "where we stand" slide then shows the final round instead of the practice round. While the final is
running the leaderboard hides the metrics and the script leaves `data.js` as it was.

Every other number on the slides is quoted from [`docs/findings.md`](../docs/findings.md); the speaker
notes of each slide name the section (or [`best_model.md`](../best_model.md), the record of every version
served). The deck was last brought up to date with branch `javier` at commit `2f3e282` (14 Nov, 20:10 CET:
findings §15–§18, the overnight experiment `skore_money_v21`–`v28` still running).

**Still to fill in on Sunday**, once the night is read and the final is over; the notes of these slides say
"decir aquí…" where the spoken sentence depends on it:

| Slide | What depends on Sunday |
|---|---|
| 3 | The whole slide: run `update_data.py` after 12:00 |
| 6 | Which of the eight arms served the final (one ranker or one per kind of request; trend lift on or off) |
| 9 | What the overnight experiment said, in the last row of the list and in the notes |
| 10 | The share of answers on time during the final, and whether the cable fixed the bursts |

When the system changes again, these places need a look too: the columns and the live bars of slide 7
(held-out table of `offline.train`, `scripts/arms.py`), the `VERSIONS` markers and caption of the trend chart,
the feature count on slide 6, and the latency ticks on slide 10 (`queries/health.sql`).

## Keys

| Key | |
|---|---|
| `→` `space` `PgDn` / `←` `PgUp` | Next / back (a presentation clicker works). Some slides reveal a last line on an extra press |
| `F` | Full screen |
| `O` | Index of slides, to jump to one during the questions |
| `N` | Speaker notes of the current slide (for rehearsing: the audience would see them) |
| `C` / `R` | Show the clock: elapsed / planned up to the end of this slide; it turns red when 15 s behind. `R` restarts it |

## Time plan

The brief only says "a short presentation with a demo". The plan is 5 min 50 s of slides plus 1 min 30 s
of demo (`data-t` on each slide, in seconds). `index.html?min=5` rescales the whole plan to 5 minutes.

| # | Slide | Jury criterion | Seconds |
|---|---|---|---|
| 1 | Cover | | 10 |
| 2 | The challenge | Communication | 30 |
| 3 | Where we stand | | 25 |
| 4 | Measure before modelling | Method | 35 |
| 5 | The trap: satiation | Method, learning from the stream | 25 |
| 6 | Two stages, then the store moves | Method | 35 |
| 7 | Validated offline, confirmed live, noise measured | Method | 40 |
| 8 | The finding: description attributes | Method, cold start | 40 |
| 9 | Learning from the stream | Learning from the stream | 40 |
| 10 | Reliability | | 30 |
| 11 | RawTree | Use of RawTree | 25 |
| 12 | Demo | | 90 |
| 13 | Three ideas | Communication | 15 |

`index.html?static` shows every slide in its final state without animation; printing that page to PDF
(landscape, no margins, background graphics on) gives a 13-page backup.
