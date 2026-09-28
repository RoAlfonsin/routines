# The Hour — daily exercise + meditation routines

One hour a day, seven days a week. Every session runs in the same order and always
totals exactly **60:00**:

| block | length | what |
|---|---|---|
| Arrive | ~5 min | seated guided meditation pulled from YouTube |
| Warm-Up | 8:00 | seated → standing, bottom-up: neck, shoulders, spine, hips, legs |
| Sun Salutations | 7:00 | 10 rounds of the full 13-pose Surya Namaskar |
| Main routine | ~23 min | the only block that changes day to day |
| Cool-Down | ~5 min | stretching; absorbs the slack so the hour is exact |
| Settle | ~10 min | seated guided meditation from YouTube |

The meditations are embedded with YouTube's official player and driven by the timer —
the real video length is read at runtime, so if you swap a video everything rebalances
and the hour still lands on 60:00.

## The week

- **Mon** Strong Start — full-body strength (Darebee)
- **Tue** Bubble Butt — glutes and legs (Darebee)
- **Wed** Total Core — core (Darebee)
- **Thu** Arms & Back — upper body (Darebee)
- **Fri** Outlast + Last Life — low-impact cardio (Darebee)
- **Sat** Low Impact — mobility, full body (Darebee)
- **Sun** Gentle Recovery Flow — recovery

## Files

- `pool.json` — the move pool. 55 home bodyweight moves tagged by pattern, body
  position, impact and level. 45 come from real Darebee cards, 10 are standard
  stretches. This is where you add exercises.
- `routines.json` — the seven days: block budgets, circuits, round counts, and which
  meditation video each day uses.
- `build_site.py` — joins the two, **verifies every day totals 60:00**, and writes
  `docs/index.html`.
- `docs/index.html` — the built site. Self-contained, no build step at runtime.

## Rebuild

```bash
cd ~/Projects/fitness && python3 build_site.py
```

The build refuses to emit a day that doesn't add up to 60:00, and prints the per-block
breakdown for all seven days.

## Changing things

- **Swap a meditation:** edit the `arrive`/`settle` block for a day in `routines.json`
  and paste the YouTube video ID. Duration is measured at runtime, nothing else to
  adjust.
- **Change the main routine:** edit that day's `main.moves` (each entry is a `ref` into
  `pool.json` plus `work`/`rest` seconds) and `rounds`. Rebuild; the build tells you if
  it no longer fits.
- **Add a move:** append it to `pool.json` with an `id`, then reference it by `ref`.

## Ratings

Rate any session 1–5 with a note. Ratings are stored in the browser's localStorage, so
they live on the machine you trained on. **Copy all ratings** puts the JSON on your
clipboard — paste it into the chat and the week gets retuned from the feedback. That
paste is also the backup if you move machines.

## Deploy

Served by GitHub Pages from the `/docs` folder on `main`. Push and Pages republishes.

## Attribution

Routine structures and exercise names are drawn from [DAREBEE](https://darebee.com),
a free donation-funded project — go read their cards, they are better than this
summary. Cues and coaching text here are our own. The scraped source pages are kept
locally in `.scratch/` and deliberately not published.
