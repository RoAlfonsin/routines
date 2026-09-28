# Fitness

Interval-timer driven exercise + meditation routines.

- `routines.json` — the source of truth. All routines live here.
- `build_timer.py` — bakes `routines.json` into a single offline HTML file.
- `timer.html` — the generated timer. Zero dependencies, no network, no install.

## Rebuild after editing routines.json

```bash
cd ~/Projects/fitness && python3 build_timer.py
```

## Routine schema

```json
{
  "id": "unique-slug",
  "name": "Shown in the picker",
  "kind": "strength | mobility | meditation",
  "source": "Darebee | local",
  "url": "original page, optional",
  "note": "one-line description shown on the menu screen",
  "prepare": 10,
  "rounds": 3,
  "rest_between_rounds": 60,
  "tone": "loud | soft | none",
  "countdown_beeps": true,
  "voice": true,
  "moves": [
    { "name": "Split Lunges", "work": 40, "rest": 20, "note": "form cue shown on screen" }
  ]
}
```

`work`/`rest` are seconds. `rounds` replays the whole `moves` list. A rest after the
very last move of the final round is dropped automatically, so sessions never end on
a pointless rest. `tone: "none"` + `countdown_beeps: false` is the right setting for
breath work.

## Using it on the phone

Download `timer.html` to the phone, open it with Chrome (`file:///sdcard/Download/timer.html`),
then Chrome's ⋮ → **Add to Home screen** so it launches like an app. It works in
airplane mode; the screen wake lock keeps the display on while a session runs.

Alternative: serve it over the LAN instead of copying the file —
`cd ~/Projects/fitness && python3 -m http.server 8000` — then open
`http://<host-lan-ip>:8000/timer.html` on the phone.
