# Jury presentation (Sun 15 Nov, 14:00 CET)

The deck for the 30 jury points, in Spanish. One self-contained page: open [`index.html`](index.html) in a
browser (Chrome or Edge) and put it in full screen with the browser's own key (`F11`). No server, no network,
no install.

| File | What |
|---|---|
| [`index.html`](index.html) | The 12 slides, their speaker notes and the small engine that runs them |
| [`data.js`](data.js) | Leaderboard snapshot shown on the "goal and result" and "learning" slides, plus our place, hourly scores and practice lead (`lead`), kept for the record. Written by code, not by hand |
| [`update_data.py`](update_data.py) | Rewrites `data.js` from the public leaderboard and `realtime_analyisi_leaderboard/history.csv` (stdlib, read-only, no API key). For `lead` it rebuilds the board of the practice round every 5 minutes from the same API: about 290 small requests, one minute |
| [`design.md`](design.md) | RawTree's visual identity (type, colours, shapes, logo), read from the organisers' deck and rawtree.com on 14 Nov, with the source of each value. The deck's CSS follows it |
| `assets/` | RawTree's symbol and arcs and Tinybird's logo, as published by them; `curva-organizadores.png`, the organisers' hour-by-hour curve, cropped from the slide they showed on 15 Nov |
| `fonts/` | Geist and Geist Mono (RawTree's typefaces), subset to Latin, under the SIL Open Font License |

## The slot (what the organisers told us on Sunday, 11:40 CET)

- **3 to 5 minutes, and no separate demo**: the presentation is the test. The plan below is 4:40, under the top
  of the range. Rehearse with the clock (`index.html?notas`) and know what to drop (the
  cut list under the time plan).
- **A big screen, in a room** (not Saturday's hall). The deck is one 1920 × 1080 sheet scaled to the window:
  put the browser in full screen (`F11`) and check that the whole slide is visible before starting.
- **The repository** goes to the organisers through their platform, or by email. The default branch of the
  GitHub repository, `main`, holds the whole work (branches `javier` and `hugo` merged) and this deck.

## The final, as the deck tells it

`data.js` holds the official result of the final (Sun 15 Nov, 10:00–12:00 CET), written by
`update_data.py` at 12:15 CET:

| | Skore Money | team_33 (1st) | team_03 (3rd) | Reference | Best sellers |
|---|---|---|---|---|---|
| Place | **2nd of 42** | 1st | 3rd | | |
| Organisers' score (of 100) | **57.7** | 58.3 | 56.2 | | |
| Expected purchases / 100 requests | **2.238** | 2.252 | 2.189 | 2.141 | 0.750 |
| Cold (new shopper or new product) | **2.622** | 2.668 | 2.554 | 2.199 | 1.177 |
| Warm (the rest, `scripts/arms.py`) | **1.876** | 1.861 | 1.848 | 2.085 | 0.348 |
| On time | **99.995 %** (21,599 of 21,600) | 99.977 % | 99.926 % | 100 % | 100 % |

Our place in the organisers' anonymised view of the final, every 5 minutes (`final` in `data.js`): 5th at
10:05, 2nd at 10:10, 3rd at 10:15, then 2nd at every checkpoint from 10:20 to the close; team_33 was first at
every one. Top five: team_33 58.3, team_06 57.7, team_03 56.2, team_17 54.3, team_37 53.7. Slide 8's chart adds
the final as one shaded point at its close (the API serves the final's two hours only as a whole).

`skore_money_v31` served all of it (`python scripts/arms.py 09:00 11:00`: one version, 09:00:00–10:59:59
UTC). By the hour (the organisers' hourly score, `hours` in `data.js`): team_33 won the first hour (52.3
against 50.6), we won the second (53.3 against 52.7). From Saturday 13:00 CET to the end we were first in
20 of the 23 hours. The gap to the winner, 0.014 purchases per 100 requests, is smaller than the 0.12 that
separates two copies of the same model over half an hour. On the organisers' scale (best sellers 0, oracle
100) the oracle of the final sells about 3.6; the reference sits at 49 % of the way, we at 52 %.

What we could not measure after the close: the trend of the final. The RawTree key stopped working when the
challenge ended (HTTP 401), so `offline/store_moves.py` no longer runs; the detector's own record is in the
server's `serve.log` on Javier's laptop. The notes of slide 9 say so.

```bash
python3 presentation/update_data.py     # re-reads the public leaderboard; in final mode it shows the final
```

Slide 2 shows the organisers' hour-by-hour curve and, below it, the goal and the final's result against the
best sellers and the reference: no place, no other team (the team's decision, 15 Nov). The place, the hourly
scores and the practice-round lead (`lead`, measured 15 Nov 09:36 CET) stay in `data.js` and in this README.

Every other number on the slides is quoted from [`docs/findings.md`](../docs/findings.md); the speaker
notes of each slide name the section (or [`best_model.md`](../best_model.md), the record of every version
served). The deck was last brought up to date with branch `javier` at commit `6930c62` (15 Nov, 09:32 CET:
findings §23–§24, `skore_money_v31` alone for the final (`ARMS` in `reco/serve.py`), the night's two questions
closed, the trends of the night and the small one of Sunday morning, the organisers' message before the final),
and with the official result of the final at 12:15 CET.

What to read before presenting, slide by slide:

| Slide | What |
|---|---|
| 2 | The organisers' published curve (`assets/curva-organizadores.png`, cropped from their slide "The learning curve"), large. Title: "Nuestra solución". Say "casi siempre" aloud, not "siempre": the top line is the best team of each hour, which was us in 19 of the 21 practice hours from Sat 13:00 CET (API `progress`), and not in the final's shaded stretch (team_33). Below: the goal and the final's 2.24 against 2.14 and 0.75, ×3.0. No place on the slide (the team's decision); the notes say what to answer if asked |
| 9 | Notes: the trend of the final is not measured here (see above); if Javier read it in `serve.log`, say it |
| 11 | Who did what, and with which agents: Hugo first prepared the repository so that the agents knew what to do, Javier built and iterated, Hugo reviewed every decision in parallel from his own branch with his agents, and both decided and made this presentation. Written from the commit history and from Hugo's account. **Both of us should read it before presenting** |
| 12 | Notes: the prepared answers, now with the final (on time on Wi-Fi, why second, what we would do with more time). The notes also list the commands to run if the jury asks to see the system working |

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
| Use of RawTree (5) | Features in SQL, embeddings, how the pipeline reads and writes | 4, 10, 11 | every table we read and write, with its cadence (4) · an aggregation in SQL on screen, reads and writes, `scratch`, and why no embeddings, with the measurement behind it (10) · how the agents reach RawTree (11) |
| Communication (5) | Could a product manager understand what it does and why it works? | all | plain words on the slides, the technical terms in the speaker notes; slide 4 is the whole system in one picture |

"Anything a team cannot explain in the presentation may be penalised": both of us should be able to take
any slide. The notes (`index.html?notas`) carry the numbers and the answers to the likely questions, the
ones about what the deck leaves out included (the attributes behind the model on slide 5, satiation on
slide 8, reliability on slide 12).

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

## Time plan: 4 minutes 40 seconds

One version, 12 slides, no demo.

| # | Slide | Jury criterion | Seconds |
|---|---|---|---|
| 1 | Cover | | 5 |
| 2 | The organisers' hour-by-hour curve, large (the top line is us in 19 of the 21 practice hours from Sat 13:00), and below it the goal and the final's 2.24 against 2.14 and 0.75 | | 20 |
| 3 | Measure before modelling, and why popularity × signals | Method | 25 |
| 4 | The architecture, end to end: what we read, the server (state, rules, 52 features, two LightGBM models, trends, hard rules), what we write, the offline loop | Method, use of RawTree | 30 |
| 5 | How the models are trained, decision by decision | Method | 35 |
| 6 | Three exams: offline, the next-purchase judge, live arms | Method (validated offline) | 30 |
| 7 | What did not work, and how we know | Method | 20 |
| 8 | Feedback, exploration, trends, price changes, cold start | Learning from the stream | 35 |
| 9 | A trend, measured live, and the night's | Learning from the stream | 25 |
| 10 | RawTree | Use of RawTree | 20 |
| 11 | Our agentic workflow: who did what, Claude Code and its limits | Communication, use of RawTree | 30 |
| 12 | Thanks, and questions (no summary: the jury does not score one) | | 5 |
| | | | **280** |

**If the time runs short**, in this order: on slide 7 tell one row instead of two (the third model); on
slide 8 skip exploration and prices; skip the three numbers under the trend on slide 9. Do not cut slides 5, 6
and 11: they are what the jury asked for by name.

`index.html?static` shows every slide in its final state without animation; printing that page to PDF
(landscape, no margins, background graphics on) gives a 12-page backup.
