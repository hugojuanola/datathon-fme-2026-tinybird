# Jury presentation (Sun 15 Nov, 14:00 CET)

The deck for the 30 jury points, in Spanish. One self-contained page: open [`index.html`](index.html) in a
browser (Chrome or Edge), press `F` for full screen. No server, no network, no install.

| File | What |
|---|---|
| [`index.html`](index.html) | The 13 slides, their speaker notes and the small engine that runs them |
| [`data.js`](data.js) | Leaderboard snapshot shown on the "where we stand" and "learning" slides. Written by code, not by hand |
| [`update_data.py`](update_data.py) | Rewrites `data.js` from the public leaderboard and `realtime_analyisi_leaderboard/history.csv` (stdlib, read-only, no API key) |
| `fonts/` | Adwaita Sans (Inter) and iA Writer Mono, subset to Latin; both under the SIL Open Font License |

## Before presenting

```bash
python3 presentation/update_data.py     # after the final ranking is published (Sun 12:00 CET)
```

The "where we stand" slide then shows the final round instead of the practice round. While the final is
running the leaderboard hides the metrics and the script leaves `data.js` as it was.

Every other number on the slides is quoted from [`docs/findings.md`](../docs/findings.md); the speaker
notes of each slide name the section. If a newer ranker than v8 goes live, three places need a look: the
columns of slide 7, the `VERSIONS` markers of the trend chart (top of the script in `index.html`) and the
feature count on slide 6.

## Keys

| Key | |
|---|---|
| `→` `space` `PgDn` / `←` `PgUp` | Next / back (a presentation clicker works). Some slides reveal a last line on an extra press |
| `F` | Full screen |
| `O` | Index of slides, to jump to one during the questions |
| `N` | Speaker notes of the current slide (for rehearsing: the audience would see them) |
| `C` / `R` | Show the clock: elapsed / planned up to the end of this slide; it turns red when 15 s behind. `R` restarts it |
| `T` | Light / dark. Use light if the projector washes out the dark theme |

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
| 6 | Two stages | Method | 35 |
| 7 | Validated offline, confirmed live | Method | 40 |
| 8 | The finding: description attributes | Method, cold start | 40 |
| 9 | Learning from the stream | Learning from the stream | 40 |
| 10 | Reliability | | 30 |
| 11 | RawTree | Use of RawTree | 25 |
| 12 | Demo | | 90 |
| 13 | Three ideas | Communication | 15 |

`index.html?static` shows every slide in its final state without animation; printing that page to PDF
(landscape, no margins, background graphics on) gives a 13-page backup.
