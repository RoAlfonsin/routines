# The Hour — daily exercise + meditation routines

One hour a day, seven days a week. Same order every day:

| block | nominal | what |
|---|---|---|
| Warm-Up | 8:04 | 11 moves, seated → standing, up the body: neck, shoulders, spine, arms, wrists, hips, legs |
| Sun Salutations | ~11 min | **follow-along class** (YouTube) — watch and copy the rhythm |
| *Transition* | 0:15 | breathe, shake it out |
| Main routine | 22–24 min | the only block that changes day to day |
| *Transition* | 0:15 | catch your breath |
| Cool-Down | 5:00 | 8 stretches |
| Settle | ~10 min | seated guided meditation (YouTube) — **the same one every day** |

There is no opening meditation — the hour starts straight into the warm-up.

Two blocks are YouTube videos and take their **real** length at runtime, so the hour runs
**57:00–59:00**. Timing is deliberately nominal, with about ±1½ minutes of slack per
block; no block is forced onto an exact total.

**Music** (lofi girl) plays under the three timed blocks and stops automatically while a
video block is on, then picks up again.

## Seeing the moves

The menu lists **every move in the selected routine, in order** — warm-up, sun class, main
circuit, cool-down, closing meditation — with its duration, its cue, and a **▶ see it done**
link that opens a demonstration search for that move.

Each move also carries a small **pictogram**: a stick figure in the move's body position
with a green arrow in a clear lane beside the figure, aligned to the joint that actually
travels and joined to it by a faint connector. It shows *position and direction*, not fine
form — the cue text and the demo link carry the detail.

## The week

- **Mon** Strong Start — full-body strength (Darebee)
- **Tue** Bubble Butt — glutes and legs (Darebee)
- **Wed** Total Core — core (Darebee)
- **Thu** Arms & Back — upper body (Darebee)
- **Fri** Outlast + Last Life — low-impact cardio (Darebee)
- **Sat** Low Impact — mobility, full body (Darebee)
- **Sun** Gentle Recovery Flow — recovery

## Sound

Transitions use synthesised singing-bowl tones rather than beeps: a low bowl (288 Hz) to
mark rest and block changes, a mid bowl (432 Hz) for the cool-down and the 3-second
warning, and a high bowl (528 Hz) to start each exercise. Sessions open and close with a
gong and a three-strike chime.

## Files

- `pool.json` — the move pool: 55 home bodyweight moves tagged by pattern, body position,
  impact and level. 45 come from real Darebee cards; the rest are standard stretches.
- `routines.json` — the seven days, the shared sun class, the music bed, block lengths.
- `build_site.py` — joins them, prints the block-length table, writes `docs/index.html`.
- `.github/workflows/deploy.yml` — builds and deploys to GitHub Pages on every push.

## Rebuild and deploy

```bash
cd ~/Projects/fitness && python3 build_site.py     # local preview
git add -A && git commit -m "..." && git push      # CI builds and publishes
```

Pages is served by a **GitHub Actions workflow**, not a branch folder, because the review
webhook is injected at build time from the `HOUR_WEBHOOK` repository secret. It is never
committed. Building locally without that variable simply makes the review button copy to
the clipboard instead of posting.

## Reviews

After a session you rate the whole hour **and each block** 1–5, add a note, and hit **Send
review** — it posts straight into the Discord thread Hermes watches, formatted so the week
can be retuned from it:

```
📋 **Monday review — 2026-09-28**
Overall ★★★☆☆ (3/5)
Arrive: 2 · WarmUp: 4 · Sun: 1 · Main: 5 · CoolDown: 3 · Settle: 4
_liked the circuit, sun class too fast_
```

Reviews are also kept in the browser's localStorage (device-local); **Reviews** on the menu
shows the recent ones.

## Changing things

- **Swap a meditation or the sun class:** change the `video` ID in `routines.json`
  (`settle` and `sun` are shared all week). Durations are measured at runtime.
- **Adjust a pictogram:** each pool move has `fig: [pose, motion, anchor]`. Poses live in
  `POSES` in `build_site.py`, each with a `lane` (the clear column its arrows are drawn in)
  and an `at` map of joint coordinates.
- **Swap the music:** change `music.video`.
- **Change a main routine:** edit that day's `main.moves` (a `ref` into `pool.json` plus
  `work`/`rest` seconds) and `rounds`.
- **Add a move:** append to `pool.json` with a unique `id`, then reference it by `ref`.

## Attribution

Routine structures and exercise names come from [DAREBEE](https://darebee.com), a free
donation-funded project. Cue text here is our own. Scraped source pages are kept in
`.scratch/`, which is gitignored and never published.
