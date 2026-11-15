# Jury presentation (Sun 15 Nov, 14:00 CET)

The deck for the 30 jury points, in Spanish. One self-contained page: open [`index.html`](index.html) in a
browser (Chrome or Edge) and put it in full screen with the browser's own key (`F11`). No server, no network,
no install.

| File | What |
|---|---|
| [`index.html`](index.html) | The cover and five slides, their speaker notes and the small engine that runs them |
| [`data.js`](data.js) | The final's figures shown on slide 2, plus our place, hourly scores, the practice trend and lead (`lead`), kept for the record. Written by code, not by hand |
| [`update_data.py`](update_data.py) | Rewrites `data.js` from the public leaderboard and `realtime_analyisi_leaderboard/history.csv` (stdlib, read-only, no API key). For `lead` it rebuilds the board of the practice round every 5 minutes from the same API: about 290 small requests, one minute |
| [`design.md`](design.md) | RawTree's visual identity (type, colours, shapes, logo), read from the organisers' deck and rawtree.com on 14 Nov, with the source of each value. The deck's CSS follows it |
| `assets/` | RawTree's symbol and arcs and Tinybird's logo, as published by them; `curva-organizadores.png`, the organisers' hour-by-hour curve, cropped from the slide they showed on 15 Nov |
| `fonts/` | Geist and Geist Mono (RawTree's typefaces), subset to Latin, under the SIL Open Font License |

## The slot (what the organisers told us on Sunday, 11:40 CET)

- **3 to 5 minutes, and no separate demo**: the presentation is the test. The plan below is 3:50, inside the range
  with room for a question. Rehearse with the clock (`index.html?notas`) and know what to drop (the
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
every one. Top five: team_33 58.3, team_06 57.7, team_03 56.2, team_17 54.3, team_37 53.7.

`skore_money_v31` served all of it (`python scripts/arms.py 09:00 11:00`: one version, 09:00:00–10:59:59
UTC). By the hour (the organisers' hourly score, `hours` in `data.js`): team_33 won the first hour (52.3
against 50.6), we won the second (53.3 against 52.7). From Saturday 13:00 CET to the end we were first in
20 of the 23 hours. The gap to the winner, 0.014 purchases per 100 requests, is smaller than the 0.12 that
separates two copies of the same model over half an hour. On the organisers' scale (best sellers 0, oracle
100) the oracle of the final sells about 3.6; the reference sits at 49 % of the way, we at 52 %.

What we could not measure after the close: the trend of the final. The RawTree key stopped working when the
challenge ended (HTTP 401), so `offline/store_moves.py` no longer runs; the detector's own record is in the
server's `serve.log` on Javier's laptop.

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
| 3 | The exploratory analysis in plain words: what makes a click (favourite category ×19, seen recently ×7.1, first position ×6.6, already bought ×0.5) and what makes a purchase (regular customer ×12, in the cart ×10, seen recently ×10, same category ×5); the notes name each feature in `reco/features.py`. Click numbers from `avanced_data_analysis/` (figure 10), purchase rates from findings §1, §4, §5 |
| 4 | The agentic workflow as two roles in a loop: the iterating agent (proposes, trains on the replayed store, validates on the held-out week, serves a new `model_version`) and the analysing agent (reads the board and the feedback per version with SQL, against the measured noise and a rule written beforehand, keeps `experiments.md`). Hugo and Javier decide. Who did what is in the notes. **Both of us should read them before presenting** |
| 5 | The final architecture, drawn like the Transformer figure (Vaswani et al., 2017): the live state on the left (shopper, product, store and its trend detector), one request on the right (retrieval 5,200 → 1,000, 52 features, two LightGBM multiplied, × trend, hard rules), the feedback loop dashed. On the right: P(clic) × P(compra \| clic) = P(compra), and why not one model for the purchase (only a clicked product can be bought; 3× more clicks than purchases to learn from; live, one direct model v9d sold 2.12 against 2.37, findings §15), then the offline training |
| 6 | Animated like the cover: the pixel grid (one blue pixel per shopper answered, three a second) and an illustrative till that starts at €12,324 the first time the slide is shown and rings up each shopper by uneven amounts (mostly €1–4, sometimes €5–9, now and then €10–20); it is not a measured figure (the final's expected sales were 21,600 × €1.08 = €23,319). Notes: the prepared answers (on time on Wi-Fi, why second, what we would do with more time), and the commands to run if the jury asks to see the system working |

When the system changes again, these places need a look too: the bars of slide 3, and the numbers in the
boxes of slide 5 (feature count, number of trees — the serving ranker's: `models/v9/*.txt`, not
`len(FEATURES)` —, ranking and answer times from `realtime_analyisi_leaderboard/latency_history.csv`, cadences
from `reco/serve.py` and `reco/state.py`).

## Built for what the jury asked

On Sunday morning the organisers told every team what they want from the demos:

> For the demos, we'd like to know the HOW and the WHY rather than the WHAT. Why you did something, how you
> trained the models, what coding agents you used, what every team member did... And remember to send us a
> GitHub repo with the code and a README so we can take a look!

On Sunday at noon the slot turned out to be 3 to 5 minutes, so the deck was cut to the cover and five
slides (the longer version, 12 slides, is in the history of this file at commit `0a6f199`). The deck does not
explain the challenge (the jury wrote it):

| What they asked | Slide |
|---|---|
| Why you did something | 3 (what the data says makes a click and a purchase, and the recipe that follows from it) · 5 (each stage of the model) |
| How you trained the models | 5 (offline, the replayed store with the same code, validated on a week the model did not see) · 4 (how each change was tested before it served) |
| What coding agents you used | 4 (Claude Code, as two agents in a loop, and what they may not do) |
| What every team member did | 4 (notes) |

| Criterion (points) | Slides |
|---|---|
| Method (10): sound, justified, validated offline | 3, 4, 5 |
| Learning from the stream (10): feedback, trends, cold start | 5 (the live state, the trend detector, the feedback loop) · 2 (the curve) |
| Use of RawTree (5) | 3 (the analysis in SQL inside RawTree) · 4 (versions and feedback through RawTree) · 5 (what is read and written) |
| Communication (5) | all |

"Anything a team cannot explain in the presentation may be penalised": both of us should be able to take
any slide. The notes (`index.html?notas`) carry the numbers and the answers to the likely questions.

## Keys

Only the arrows: `→` (or `↓`) goes forward, `←` (or `↑`) goes back. Slide 3 reveals its last line on an
extra press. No other key and no click does anything, so nothing can be triggered by mistake while
presenting. (A clicker that sends Page Down instead of the arrows will not move the deck: try it beforehand.)

| URL | |
|---|---|
| `index.html?notas` | For rehearsing: the speaker notes of each slide under it, with the clock (elapsed / planned up to the end of this slide; it turns red when 15 s behind). The clock starts when the cover is left |
| `index.html#5` | Opens on slide 5 |
| `index.html?min=5` | Rescales the time plan to 5 minutes |
| `index.html?static` | Every slide in its final state, no animation (screenshots, PDF) |

## Time plan: 3 minutes 50 seconds

| # | Slide | Seconds |
|---|---|---|
| 1 | Cover | 5 |
| 2 | Nuestra solución: the goal, the organisers' curve, the final's 2.24 | 40 |
| 3 | The exploratory analysis: what makes a click and a purchase | 55 |
| 4 | Our agentic workflow: the iterating agent and the analysing agent | 65 |
| 5 | The final architecture, in one figure | 60 |
| 6 | Thanks, and questions | 5 |
| | | **230** |

**If the time runs short**: on slide 3 tell one column per side's top two bars; on slide 5 skip the offline
note on the right.

`index.html?static` shows every slide in its final state without animation; printing that page to PDF
(landscape, no margins, background graphics on) gives a 6-page backup.
