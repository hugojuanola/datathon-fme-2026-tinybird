# Jury presentation (Sun 15 Nov, 14:00 CET)

The deck for the 30 jury points, in Spanish. One self-contained page: open [`index.html`](index.html) in a
browser (Chrome or Edge) and put it in full screen with the browser's own key (`F11`). No server, no network,
no install.

| File | What |
|---|---|
| [`index.html`](index.html) | The 13 slides, their speaker notes and the small engine that runs them |
| [`data.js`](data.js) | Leaderboard snapshot shown on the "where we stand" and "learning" slides, and since when we lead the public board (`lead`). Written by code, not by hand |
| [`update_data.py`](update_data.py) | Rewrites `data.js` from the public leaderboard and `realtime_analyisi_leaderboard/history.csv` (stdlib, read-only, no API key). For `lead` it rebuilds the board of the practice round every 5 minutes from the same API: about 290 small requests, one minute |
| [`design.md`](design.md) | RawTree's visual identity (type, colours, shapes, logo), read from the organisers' deck and rawtree.com on 14 Nov, with the source of each value. The deck's CSS follows it |
| `assets/` | RawTree's symbol and arcs and Tinybird's logo, as published by them |
| `fonts/` | Geist and Geist Mono (RawTree's typefaces), subset to Latin, under the SIL Open Font License |

## The slot (what the organisers told us on Sunday, 11:40 CET)

- **3 to 5 minutes.** The plan below is 5:00 with the demo inside, the very top of the range: there is no
  margin, so rehearse with the clock (`index.html?notas`) and know what to drop (the cut list under the time
  plan).
- **A big screen, in a room** (not Saturday's hall). The deck is one 1920 × 1080 sheet scaled to the window:
  put the browser in full screen (`F11`) and check that the whole slide is visible before starting.
- **The repository** goes to the organisers through their platform, or by email. The default branch of the
  GitHub repository is `main`, which holds only the first two commits: before sending the link, the work
  (branches `javier` and `hugo`) has to be on the default branch, or the link has to name the branch.

## Before presenting

```bash
python3 presentation/update_data.py     # after the final ranking is published (Sun 12:00 CET)
```

The "where we stand" slide then shows the final round instead of the practice round. While the final is
running the leaderboard hides the metrics and the script leaves `data.js` as it was.

Slide 2 also says, under our place, since when we lead the public board of the practice round and for how
long we did not ("líderes desde el sábado a las 14:10, salvo 1 h 25 min", measured 15 Nov 09:36 CET, twenty-four
minutes before the practice round ended). After the final it is recomputed if the API still serves the
practice windows, and kept as it was if not.

Every other number on the slides is quoted from [`docs/findings.md`](../docs/findings.md); the speaker
notes of each slide name the section (or [`best_model.md`](../best_model.md), the record of every version
served). The deck was last brought up to date with branch `javier` at commit `6930c62` (15 Nov, 09:32 CET:
findings §23–§24, `skore_money_v31` alone for the final (`ARMS` in `reco/serve.py`), the night's two questions
closed, the trends of the night and the small one of Sunday morning, the organisers' message before the final).

**Still to fill in on Sunday**, once the final is over; the notes of these slides say "decir aquí…" where
the spoken sentence depends on it:

| Slide | What depends on the final |
|---|---|
| 2 | The whole slide: run `update_data.py` after 12:00. If we are first in the final, the title says so by itself |
| 7 | The last line says the final was served by Saturday afternoon's model plus the trend lift (`skore_money_v31`). It was the only arm at 09:32 CET; check that nothing was changed after that |
| 9 | How the trend of the final went (notes) |
| 11 | Who did what, and with which agents: Hugo first prepared the repository so that the agents knew what to do, Javier built and iterated, Hugo reviewed every decision in parallel from his own branch with his agents, and both decided and made this presentation. Written from the commit history and from Hugo's account. **Both of us should read it before presenting** |
| 12 | The demo runs commands 01 and 02; 03 and 04 are for the questions. Whether the store still sends requests at 14:00. If it does not, run the same commands on the window of the final (`python scripts/arms.py 09:00 11:00`, UTC) and change the title, which says "it is answering right now" |
| 13 | The share of answers on time during the final, on Wi-Fi (notes: the prepared answer on reliability) |

When the system changes again, these places need a look too: the bars of slide 3 and the two rates next to
each (findings §1, §4, §5), the diagram of slide 4 (feature count, number of trees — the serving ranker's:
`models/v9/*.txt`, not `len(FEATURES)` —, ranking and answer times from
`realtime_analyisi_leaderboard/latency_history.csv`, cadences from `reco/serve.py` and `reco/state.py`), the
six rows of slide 5 (`offline/build_dataset.py`, `offline/train.py`), the three before → after pairs of
slide 6 (`offline.train`, `offline.next_purchase`, `scripts/arms.py`), the six rows of slide 7 (each one a row
of `realtime_analyisi_leaderboard/experiments.md`), the `VERSIONS` markers of the trend chart on slide 8, and
the three numbers under the trend on slide 9 (findings §23; the watch notes of
`realtime_analyisi_leaderboard/notes/` for the dose in each trend).

## Built for what the jury asked

On Sunday morning the organisers told every team what they want from the demos:

> For the demos, we'd like to know the HOW and the WHY rather than the WHAT. Why you did something, how you
> trained the models, what coding agents you used, what every team member did... And remember to send us a
> GitHub repo with the code and a README so we can take a look!

So the deck does not explain the challenge (the jury wrote it) and gives the result ten seconds. Every other
slide is a decision and its reason:

| What they asked | Slide |
|---|---|
| Why you did something | 3 (why popularity × measured signals: the first version, signals alone, sold what the best sellers sell) · 4 (why each stage) · 7 (six ideas dropped, each with the number that closed it, and why the final ran on Saturday afternoon's model) |
| How you trained the models | 5 (the training table, the same code offline and live, the features, the two models, the slot, the held-out future) · 6 (how a trained model is examined before it serves) |
| What coding agents you used | 11 (Claude Code, and how: `AGENTS.md` as the contract, one role per session, everything written down, what an agent may not do) |
| What every team member did | 11 |

And the 30 points are four criteria ([`docs/challenge.md`](../docs/challenge.md)); the kicker of each slide
(top left) names the one it answers.

| Criterion (points) | What the jury asks | Slides | Where each thing they name is |
|---|---|---|---|
| Method (10) | Sound, well justified, validated offline before going live | 3–7 | measured lifts, with the two rates behind each (3) · the architecture end to end, from the tables we read to the ones we write (4) · how the two LightGBM models are trained (5) · offline, the next-purchase judge and live arms, with the noise measured and the decision rule written before reading the data (6) · six ideas that did not pass; the last one won offline and lost live (7) |
| Learning from the stream (10) | Feedback and live events: exploration, trends, price changes, cold start | 8–9 | one row per word of the rubric (8) · a trend seen in 41 s and measured in our carousel, where the gap to the next team is made, the dose of the lift checked in four more trends, and the detector replayed on the ten trends the store has had (9) |
| Use of RawTree (5) | Features in SQL, embeddings, how the pipeline reads and writes | 4, 10, 11, 12 | every table we read and write, with its cadence (4) · an aggregation in SQL on screen, reads and writes, `scratch`, and why no embeddings, with the measurement behind it (10) · how the agents reach RawTree (11) · the demo runs SQL (12) |
| Communication (5) | Could a product manager understand what it does and why it works? | all | plain words on the slides, the technical terms in the speaker notes; slide 4 is the whole system in one picture |

"Anything a team cannot explain in the presentation may be penalised": both of us should be able to take
any slide. The notes (`index.html?notas`) carry the numbers and the answers to the likely questions, the
ones about what the deck leaves out included (the attributes behind the model on slide 5, satiation on
slide 8, reliability on slide 13).

## Keys

Only the arrows: `→` (or `↓`) goes forward, `←` (or `↑`) goes back. Some slides reveal a last line on an
extra press. No other key and no click does anything, so nothing can be triggered by mistake while
presenting. (A clicker that sends Page Down instead of the arrows will not move the deck: try it beforehand.)

| URL | |
|---|---|
| `index.html?notas` | For rehearsing: the speaker notes of each slide under it, with the clock (elapsed / planned up to the end of this slide; it turns red when 15 s behind). The clock starts when the cover is left |
| `index.html#7` | Opens on slide 7 |
| `index.html?min=6` | Rescales the time plan to 6 minutes |
| `index.html?static` | Every slide in its final state, no animation (screenshots, PDF) |

## Time plan: 5 minutes, demo included

One version, 13 slides.

| # | Slide | Jury criterion | Seconds |
|---|---|---|---|
| 1 | Cover | | 5 |
| 2 | Where we stand | | 10 |
| 3 | Measure before modelling, and why popularity × signals | Method | 25 |
| 4 | The architecture, end to end: what we read, the server (state, rules, 52 features, two LightGBM models, trends, hard rules), what we write, the offline loop | Method, use of RawTree | 30 |
| 5 | How the models are trained, decision by decision | Method | 30 |
| 6 | Three exams: offline, the next-purchase judge, live arms | Method (validated offline) | 30 |
| 7 | What did not work, and how we know | Method | 20 |
| 8 | Feedback, exploration, trends, price changes, cold start | Learning from the stream | 30 |
| 9 | A trend, measured live, and the night's | Learning from the stream | 25 |
| 10 | RawTree | Use of RawTree | 20 |
| 11 | How we worked: who did what, Claude Code and its limits | Communication, use of RawTree | 25 |
| 12 | Demo: two commands (`health.sql`, `arms.py`) | Use of RawTree, communication | 45 |
| 13 | Thanks, and questions (no summary: the jury does not score one) | | 5 |
| | | | **300** |

**If the time runs short**, in this order: on slide 7 tell one row instead of two (the third model); on
slide 8 skip exploration and prices; skip the three numbers under the trend on slide 9; run one command in
the demo instead of two. Do not cut slides 5, 6 and 11: they are what the jury asked for by name.

`index.html?static` shows every slide in its final state without animation; printing that page to PDF
(landscape, no margins, background graphics on) gives a 13-page backup.
