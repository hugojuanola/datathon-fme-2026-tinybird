# Sources (verbatim material)

Everything here was captured on **Sat 14 Nov 2026** (the announcement before the final on Sun 15 Nov) and is kept unedited as the ground truth behind the
summaries in [`../challenge.md`](../challenge.md), [`../data.md`](../data.md), [`../rawtree.md`](../rawtree.md)
and [`../event.md`](../event.md). If a summary and a source disagree, the source wins — and fix the summary.

| File | What | Origin |
|---|---|---|
| [`challenge-readme.md`](challenge-readme.md) | **Official challenge brief** (most complete and authoritative) | README of <https://github.com/rawtreedb/datathon-fme-2026> at commit `381ca07` |
| [`challenge-page.txt`](challenge-page.txt) | Text of the challenge web page, including its FAQ | <https://datathon.rawtree.dev> |
| [`slides.html`](slides.html) | Challenge presentation from the opening ceremony (open in a browser) | Handed out by Tinybird |
| [`slides.txt`](slides.txt) | Text extracted from the slides (animated numbers are lost; see the README for the point values) | Derived from `slides.html` |
| [`schedule.pdf`](schedule.pdf) / [`schedule.txt`](schedule.txt) | Event schedule | Datathon organisers |
| [`final-announcement.md`](final-announcement.md) | **Organisers' message before the final** (Sun 15 Nov, about 09:10 CET): the final continues Saturday's state | Posted by the organisers to the teams, pasted by Javier |
| [`rawtree-llms.txt`](rawtree-llms.txt) | Index of all RawTree documentation for agents | <https://rawtree.com/llms.txt> |

Related, elsewhere in the repo:

- [`../../starter/`](../../starter/) — the official starter kit, copied unmodified from the same commit
  (`recommender.py`, `queries.sql`, `offline_eval.ipynb`, `requirements.txt`).
- [`../rawtree/`](../rawtree/) — 30 official RawTree doc pages (`https://rawtree.com/docs/<path>.md`,
  with `/` replaced by `_` in the file name). Any other page listed in `rawtree-llms.txt` can be fetched the same way.
- [`../../.claude/skills/rawtree/`](../../.claude/skills/rawtree/SKILL.md) — the official RawTree agent skill
  (v0.5.1, Apache-2.0) from <https://github.com/rawtreedb/agent-skills>.
