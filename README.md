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
circuit, cool-down, closing meditation — with its duration, its cue, and its pattern /
position / level. The sun class and the closing meditation rows also link straight to their
YouTube video. There are no pictograms and no per-move demo searches: the cue text is the
instruction.

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

## Editing the routines from the phone

**✎ Edit routines** on the menu opens an editor that writes back to this repo. No server, no
database: `routines.json` and `pool.json` stay the only source of truth, and the page talks
straight to the GitHub Contents API.

What you can do per day: change any move's **work and rest seconds**, **add or remove moves**
(a picker over the whole pool, plus inventing a new move with its own cue), **reorder** them
(↑ ↓), **change the number of rounds** and the rest between rounds, **add a section** (an extra
circuit named what you like, with its own rounds and moves), and **take a section out** of a day
— including the warm-up, the sun class, the cool-down and the closing meditation.

Notes on the model:

- **Warm-up, the sun class, the cool-down and the closing meditation are shared by every day.**
  Editing them changes all seven days; the editor tags them *every day*. Only `main` and the
  extra sections belong to a single day (*this day*).
- A day can carry `skip: ["sun", "cooldown"]` (any of `warmup`, `sun`, `cooldown`, `settle`)
  and `extra: [{label, rounds, rest_between_rounds, moves: [...]}]`, inserted after the main
  circuit. A 15s transition only happens when the block it bridges is present.
- A section with no moves is dropped on save — it does nothing.
- Timing stays nominal: the editor prints each day's total and warns when a day drifts more
  than 7 minutes from an hour. Nothing is forced onto an exact 60:00.

Saving needs a write token, and it is the only credential anywhere in this setup:

1. github.com/settings/personal-access-tokens/new — a **fine-grained** token.
2. Repository access: **only RoAlfonsin/routines**.
3. Repository permissions → **Contents: Read and write**. Nothing else.
4. Expiration: 90 days (set a calendar reminder; an expired token just means the editor
   refuses to save, reading the site is unaffected).
5. Paste it into the box at the bottom of the editor, on the device you edit from. It is kept
   in that browser's localStorage, never in the repo and never sent anywhere but
   `api.github.com`. **Forget token** removes it.

The tradeoff this design accepts: a token in browser storage is only as safe as the page, so
scope it to one repo and let it expire. If it leaks, the worst case is a wrong routine you can
undo with a commit.

### How the page gets its data

At boot the page fetches the committed `routines.json` and `pool.json` from
`raw.githubusercontent.com` (cache-busted), so a save is live on the next load without waiting
for the Pages rebuild. If the network is down — or the committed data is broken, e.g. a move
`ref` that does not exist — it falls back to the copy baked into the HTML and says so under the
menu. Airplane mode still runs the last built copy.

## Changing things by hand

- **Swap a meditation or the sun class:** change the `video` ID in `routines.json`
  (`settle` and `sun` are shared all week). Durations are measured at runtime.
- **Swap the music:** change `music.video`.
- **Change a main routine:** edit that day's `main.moves` (a `ref` into `pool.json` plus
  `work`/`rest` seconds) and `rounds`.
- **Add a move:** append to `pool.json` with a unique `id`, then reference it by `ref`.
- **Rounds on the shared blocks:** `warmup` and `cooldown` take an optional
  `rounds` / `rest_between_rounds` too, same as a main circuit. Both default to 1 round, which
  is how they run today.

## Attribution

Routine structures and exercise names come from [DAREBEE](https://darebee.com), a free
donation-funded project. Cue text here is our own. Scraped source pages are kept in
`.scratch/`, which is gitignored and never published.
