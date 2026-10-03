# The Hour — daily exercise + meditation routines

One hour a day, seven days a week. Same order every day:

| block | nominal | what |
|---|---|---|
| Warm-Up | 8:04 | 11 moves, seated → standing, up the body: neck, shoulders, spine, arms, wrists, hips, legs |
| *Pause* | 0:30 | stand easy and breathe |
| Sun Salutations | 9:20 | written sequence — 8 rounds of 10 poses, 1:10 a round, no stops |
| *Transition* | 0:15 | breathe, shake it out |
| Main routine | 22–24 min | the only block that changes day to day |
| *Transition* | 0:15 | catch your breath |
| Cool-Down | 5:00 | 8 stretches |
| Settle | ~10 min | seated guided meditation (YouTube) — **the same one every day** |

There is no opening meditation — the hour starts straight into the warm-up.

The closing meditation is a YouTube video and takes its **real** length at runtime, so the hour
runs about **55:00–58:00**. Timing is deliberately nominal, with about ±1½ minutes of slack per
block; no block is forced onto an exact total, and the length is Rodri's call — nothing warns
about a day being off the hour.

**Music** (lofi girl) plays under the timed blocks and stops automatically while a video block
is on, then picks up again.

### Sun salutations

Ten poses, **work-only** — the rest between them was folded into each hold, so the flow runs
without stops. Holds follow the class's own proportions (the long ones are the lower-down, cobra,
downward dog, the mountain and the arms-up at the end of the round) and are scaled so a round is
**exactly 1:10**:

Mountain 9s → Forward Fold 5s → Halfway Lift 6s → Plank 5s → Lower Down 9s → Cobra 8s →
Downward Dog 8s → Step Forward and Flat Back 6s → Forward Fold 5s → Stand Tall 9s

Eight rounds → **9:20**. No opening setup and no closing stillness: the warm-up and the Settle
block already bracket the day. Rodri replaced the follow-along class with this sequence on
2026-10-02; the timings came from the class's caption track (raw class holds run ~1:27 a round —
scaled here to keep 1:10).

## Seeing the moves

The menu is deliberately short: the day cards (focus, main routine, total), **Today's hour**
(one row per block with its length), the pool/music/salutations summary, and the buttons. It no
longer lists the moves — Rodri asked for the list to go once the editor existed. Moves are
visible in **✎ Edit routines**, and the run screen shows each one as it comes up.

There are no pictograms and no per-move demo searches: the cue text is the instruction.

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

- `pool.json` — the move pool: 63 moves tagged by pattern, body position, impact and level.
  45 come from real Darebee cards; the rest are standard stretches plus the ten sun-salutation poses.
- `routines.json` — the seven days, the shared blocks, the music bed, block lengths, transitions.
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
_liked the circuit, salutations too fast_
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
— including the warm-up, the sun salutations, the cool-down and the closing meditation.

Notes on the model:

- **Warm-up, the sun salutations, the cool-down and the closing meditation are shared by every day.**
  Editing them changes all seven days; the editor tags them *every day*. Only `main` and the
  extra sections belong to a single day (*this day*).
- A day can carry `skip: ["sun", "cooldown"]` (any of `warmup`, `sun`, `cooldown`, `settle`)
  and `extra: [{label, rounds, rest_between_rounds, moves: [...]}]`, inserted after the main
  circuit. The pauses between blocks live in `transitions` (30s after the warm-up, 15s after the
  salutations, 15s before the cool-down) and only happen when the blocks they bridge are present.
- A section with no moves is dropped on save — it does nothing.
- Timing stays nominal: the editor prints each day's total. Length is Rodri's to decide, so nothing
  warns about a day being off the hour.

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

`routines.json` carries an **`updated` stamp**, written by the editor on every save. Three copies
can exist — the one baked into the HTML by the last build, the one GitHub serves, and the one this
device saved moments ago — and the page picks the newest by that stamp:

- GitHub's copy is adopted only when its stamp is **strictly newer** than the built copy's. A slow
  CDN serving the previous file therefore can never roll the routines backwards; the page says
  "GitHub is serving an older copy than this build — running the built one" when it sees that.
- A save from **this device** is kept for 10 minutes and preferred while GitHub catches up, so the
  person who just saved always sees their own edit.
- If GitHub is unreachable, or its data is broken (a `ref` that does not exist, an empty pool), the
  page falls back to the built copy and says why under the menu. Airplane mode runs the last build.

Editing from this device is live on reload; other devices get it as soon as the CDN and the Pages
build catch up, usually under a minute.

## Changing things by hand

- **Swap the meditation:** change `settle.video` in `routines.json`. Durations are measured at
  runtime.
- **Bring the sun salutation class back, or point it at another video:** put `video`, `title` and
  `channel` back into `sun` and drop its `moves` — the builder runs the sun block as either a
  written circuit or a follow-along video, whichever the data says. The old class (Charlie Follows,
  `I9_wJmIAckA`) and three alternates are in the git history.
- **Change the salutations:** `sun.moves` (the ten poses, in order) and `sun.rounds` — or just use
  the editor.
- **Change a pause:** `transitions.after_warmup`, `after_sun`, `before_cooldown`, in seconds.
- **Swap the music:** change `music.video`.
- **Change a main routine:** edit that day's `main.moves` (a `ref` into `pool.json` plus
  `work`/`rest` seconds) and `rounds`.
- **Add a move:** append to `pool.json` with a unique `id`, then reference it by `ref`.
- **Rounds on the shared blocks:** `warmup` and `cooldown` take an optional
  `rounds` / `rest_between_rounds` too, same as a main circuit. Both default to 1 round, which
  is how they run today.

## Attribution

Routine structures and exercise names come from [DAREBEE](https://darebee.com), a free
donation-funded project. Cue text here is our own. The sun-salutation sequence was written from
the timing of a follow-along class, but the move list and cues here are ours — the class's caption
track was used as a measurement only and is not published (it lives outside the repo). Scraped
source pages are kept in `.scratch/`, which is gitignored and never published.
