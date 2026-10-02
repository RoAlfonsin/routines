#!/usr/bin/env python3
"""Build The Hour — Rodri's one-hour daily routines.

Reads pool.json + routines.json, sanity-checks the block lengths, and emits a
single self-contained docs/index.html.

    HOUR_WEBHOOK="https://discord.com/api/webhooks/..." python3 build_site.py

The webhook is injected at build time only; it is never committed to the repo.
Without it the review button copies the review to the clipboard instead.
"""
import json
import os
import shutil
import subprocess
import tempfile
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
OUTDIR = HERE / "docs"

POOL = json.loads((HERE / "pool.json").read_text(encoding="utf-8"))
R = json.loads((HERE / "routines.json").read_text(encoding="utf-8"))

HOUR = R["hour_seconds"]
TAIL = R["video_tail"]
SUN = R["sun"]
SETTLE = R["settle"]
TR = R["transitions"]
MUSIC = R["music"]
TR_SECONDS = TR["after_sun"] + TR["before_cooldown"]
REVIEW_THREAD = "1553973467496316948"


def circuit_cost(m, drop_final_rest=False):
    """Rounds + breaks. `drop_final_rest` mirrors the timeline, which emits no rest step
    after the very last move of the very last round (a circuit) — warm-up and cool-down
    keep every rest they declare."""
    moves = m.get("moves") or []
    if not moves:
        return 0
    rounds = m.get("rounds", 1)
    cost = sum(x["work"] + x["rest"] for x in moves) * rounds
    cost += m.get("rest_between_rounds", 0) * (rounds - 1)
    return cost - (moves[-1]["rest"] if drop_final_rest else 0)


def transitions_for(day):
    """The 15s transitions only happen when the blocks they bridge are present."""
    skip = set(day.get("skip") or [])
    t = 0
    if "sun" not in skip:
        t += TR["after_sun"]
    if "cooldown" not in skip:
        t += TR["before_cooldown"]
    return t


def day_blocks(day):
    """Ordered [(label, seconds)] for one day, honouring skip[] and extra[]."""
    skip = set(day.get("skip") or [])
    out = []
    if "warmup" not in skip:
        out.append(("Warm-Up", circuit_cost(R["warmup"])))
    if "sun" not in skip:
        out.append(("Sun Salutations", SUN["nominal"] + TAIL))
    out.append((day["main"]["label"], circuit_cost(day["main"], drop_final_rest=True)))
    for i, ex in enumerate(day.get("extra") or []):
        out.append((ex.get("label") or f"Extra {i + 1}", circuit_cost(ex, drop_final_rest=True)))
    if "cooldown" not in skip:
        out.append(("Cool-Down", circuit_cost(R["cooldown"])))
    if "settle" not in skip:
        out.append(("Settle", SETTLE["nominal"] + TAIL))
    return out


def audit():
    """Report only. Rodri tunes the length himself and does not want it policed; the
    'vs 60:00' column is there so a drift is visible, not to warn about it."""
    print(f"{'day':<4} {'total':>7} {'vs 60:00':>9}  blocks")
    for d in R["days"]:
        bl = day_blocks(d)
        tot = sum(v for _, v in bl) + transitions_for(d)
        cells = " ".join(f"{lbl} {v // 60}:{v % 60:02d}" for lbl, v in bl)
        print(f"{d['id']:<4} {tot // 60}:{tot % 60:02d}".rjust(12) + f" {tot - HOUR:+5d}s".rjust(9)
              + f"  {cells}")
    return []


def build():
    warnings = audit()
    if warnings:
        print("\nWARNINGS:")
        for w in warnings:
            print("  -", w)

    webhook = os.environ.get("HOUR_WEBHOOK", "").strip()
    print(f"\nreview webhook: {'configured' if webhook else 'NOT set — reviews will copy to clipboard instead'}")

    data = {
        "pool": {m["id"]: m for m in POOL["moves"]},
        "poolFile": POOL,
        "routines": R,
        "webhook": webhook,
        "thread": REVIEW_THREAD,
        "repo": "RoAlfonsin/routines",
        "branch": "main",
    }
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    OUTDIR.mkdir(exist_ok=True)
    html = TEMPLATE.replace("__DATA__", payload)
    path = OUTDIR / "index.html"
    path.write_text(html, encoding="utf-8")
    print(f"wrote {path} ({len(html)//1024} KB) · {len(R['days'])} days · {len(data['pool'])} moves")

    # A broken script tag ships a blank page silently. If node is around, parse the inline
    # JS and refuse to call the build good when it doesn't.
    if shutil.which("node"):
        js = html[html.index("<script>") + 8: html.rindex("</script>")]
        tmp = pathlib.Path(tempfile.gettempdir()) / "hour_check.js"
        tmp.write_text(js, encoding="utf-8")
        r = subprocess.run(["node", "--check", str(tmp)], capture_output=True, text=True)
        if r.returncode != 0:
            print("\nJS SYNTAX ERROR — the page would not run:")
            print(r.stderr.strip()[:1500])
            return 1
        print("inline JS parses cleanly (node --check)")
    return 0


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#0f1115">
<title>The Hour</title>
<style>
  :root{
    --bg:#0e1014; --panel:#171b22; --line:#28303c; --txt:#f1f4f9; --dim:#98a4b8;
    --work:#22c55e; --rest:#f59e0b; --med:#8b5cf6; --yoga:#14b8a6; --cool:#0ea5e9; --warm:#3b82f6;
  }
  *{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
  html,body{margin:0;height:100%;overflow:hidden}
  body{background:var(--bg);color:var(--txt);
       font:clamp(15px,1.6vh,21px)/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
  #app{height:100dvh;display:flex;flex-direction:column;padding:clamp(10px,2vh,26px) clamp(12px,2.5vw,40px)}
  button{font:inherit;color:inherit;background:var(--panel);border:1px solid var(--line);
         border-radius:14px;padding:clamp(9px,1.4vh,16px) clamp(12px,2vw,22px);cursor:pointer}
  button:hover{border-color:#46536a}
  .primary{background:var(--work);border-color:transparent;color:#04220f;font-weight:800}
  a{color:#7dd3fc}

  /* ---------- menu ---------- */
  #menu{display:flex;flex-direction:column;height:100%;overflow:auto}
  h1{font-size:clamp(26px,4.4vh,46px);margin:0 0 2px;font-weight:800;letter-spacing:-.01em}
  .sub{color:var(--dim);font-size:clamp(12px,1.5vh,16px);margin-bottom:clamp(8px,1.6vh,18px)}
  .days{display:grid;grid-template-columns:repeat(auto-fit,minmax(clamp(120px,12vw,190px),1fr));gap:clamp(6px,1vh,12px)}
  .day{background:var(--panel);border:1px solid var(--line);border-radius:16px;
       padding:clamp(8px,1.4vh,16px);cursor:pointer;text-align:left}
  .day.on{border-color:var(--work);background:#14251b;box-shadow:0 0 0 1px var(--work) inset}
  .day b{display:block;font-size:clamp(15px,2vh,22px);font-weight:700}
  .day span{display:block;color:var(--dim);font-size:clamp(11px,1.3vh,14px);margin-top:2px}
  .cols{display:grid;grid-template-columns:1fr 1fr;gap:clamp(8px,1.6vw,26px);margin-top:clamp(8px,1.8vh,22px)}
  .blk{display:flex;justify-content:space-between;gap:12px;align-items:baseline;
       border-bottom:1px solid var(--line);padding:clamp(5px,.9vh,11px) 0}
  .blk:last-child{border-bottom:0}
  .blk b{font-weight:600}
  .blk em{font-style:normal;color:var(--dim);font-size:.82em;display:block}
  .blk u{text-decoration:none;font-variant-numeric:tabular-nums;white-space:nowrap;font-weight:600}
  .dot{display:inline-block;width:.6em;height:.6em;border-radius:99px;margin-right:.5em}
  .foot{display:flex;gap:14px;align-items:center;flex-wrap:wrap;margin-top:auto;padding-top:clamp(10px,2vh,22px)}
  #startBtn{flex:1;min-width:240px;font-size:clamp(17px,2.4vh,26px);padding:clamp(14px,2.2vh,24px)}
  .tog{display:flex;gap:8px;align-items:center;color:var(--dim);font-size:.86em;cursor:pointer}
  .hint{color:var(--dim);font-size:.8em}
  #vstatus{color:var(--dim);font-size:.8em;margin-top:8px;min-height:1.2em}

  /* ---------- run ---------- */
  #run{display:none;flex-direction:column;height:100%}
  #bar{display:flex;height:clamp(7px,1vh,13px);border-radius:99px;overflow:hidden;background:var(--line)}
  #bar i{height:100%}
  .topline{display:flex;justify-content:space-between;align-items:baseline;gap:16px;margin-top:clamp(6px,1.2vh,14px)}
  #blockName{font-size:clamp(15px,2.3vh,28px);letter-spacing:.16em;text-transform:uppercase;color:var(--dim);font-weight:600}
  #hourClock{font-variant-numeric:tabular-nums;color:#c3cddd;font-size:clamp(15px,2.2vh,26px);font-weight:600}
  #stage{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;min-height:0;gap:clamp(2px,.6vh,10px)}
  #clock{font-size:clamp(64px,20vh,300px);font-weight:800;line-height:.92;font-variant-numeric:tabular-nums;letter-spacing:-.03em}
  #moveName{font-size:clamp(26px,6.2vh,80px);font-weight:800;line-height:1.08;letter-spacing:-.01em}
  #sub{color:#b9c4d4;font-size:clamp(15px,2.3vh,28px)}
  #cue{color:#cdd6e4;font-size:clamp(16px,2.8vh,36px);max-width:38ch;margin-top:clamp(3px,1vh,14px);min-height:1.3em}
  #meta,#next{color:#b9c4d4;font-size:clamp(14px,2.1vh,24px)}
  #meta{margin-top:clamp(4px,1vh,12px)}
  #vidwrap{margin:clamp(4px,1vh,14px) 0;display:none}
  #vidwrap.on{display:block}
  iframe{width:100%;aspect-ratio:16/9;border:0;border-radius:14px;background:#000;max-height:52vh}
  .vbar{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-top:8px;font-size:.82em;color:var(--dim)}
  #musicbar{display:none;align-items:center;gap:clamp(8px,1.4vw,18px);flex-wrap:wrap;
            background:var(--panel);border:1px solid var(--line);border-radius:14px;
            padding:clamp(7px,1.1vh,14px) clamp(10px,1.6vw,20px);font-size:.86em}
  #musicbar.on{display:flex}
  #musicbar .nm{color:var(--dim)}
  #musicbar b{font-weight:600}
  #musicbar .nm{white-space:nowrap;flex:0 0 auto}
  #musicbar button{flex:0 0 auto}
  input[type=range]{flex:1 1 auto;min-width:180px;width:auto;accent-color:var(--work)}
  #controls{display:grid;grid-template-columns:repeat(4,1fr);gap:clamp(6px,1vh,14px);margin-top:clamp(8px,1.4vh,18px)}
  #controls button{font-size:clamp(14px,1.9vh,22px);padding:clamp(12px,2vh,24px) 4px}
  #pauseBtn{grid-column:span 4;font-weight:800;background:#20304a;border-color:#39507a}
  /* music player must exist but stay out of the way */
  #musicHost{position:fixed;bottom:0;right:0;width:1px;height:1px;overflow:hidden;opacity:.01;pointer-events:none}

  /* ---------- review ---------- */
  #rate{display:none;flex-direction:column;height:100%;overflow:auto}
  #rate.on{display:flex}
  .rateRow{display:grid;grid-template-columns:minmax(120px,1fr) auto;gap:12px;align-items:center;
           border-bottom:1px solid var(--line);padding:clamp(4px,.8vh,9px) 0}
  .rateRow span:first-child{font-size:.95em}
  .stars{display:flex;gap:4px}
  .star{background:none;border:0;padding:0 2px;font-size:clamp(20px,3vh,34px);line-height:1;
        cursor:pointer;color:#3a4455}
  .star.on{color:#fbbf24}
  textarea{width:100%;background:#0e1014;color:var(--txt);border:1px solid var(--line);border-radius:12px;
           padding:12px;font:inherit;min-height:clamp(60px,12vh,140px);margin-top:8px}
  .hist{font-size:.82em;color:var(--dim);margin-top:10px}
  .hist b{color:var(--txt)}
  /* ---------- editor ---------- */
  #edit{display:none;flex-direction:column;height:100%;overflow:auto}
  #edit.on{display:flex}
  .ecard{background:var(--panel);border:1px solid var(--line);border-radius:14px;
         padding:clamp(8px,1.4vh,14px) clamp(9px,1.5vw,16px);margin-bottom:clamp(6px,1.2vh,12px)}
  .ehead{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
  .ehead b{font-size:clamp(14px,1.9vh,20px)}
  .ehead em{font-style:normal;color:var(--dim);font-size:.8em;margin-left:auto;font-variant-numeric:tabular-nums}
  .etag{font-size:.68em;color:var(--dim);border:1px solid var(--line);border-radius:99px;padding:1px 7px}
  .erow{display:grid;grid-template-columns:1fr auto auto auto;gap:6px;align-items:center;
        border-top:1px solid #1a2231;padding:clamp(4px,.8vh,9px) 0}
  .erow .nm{font-size:clamp(12px,1.6vh,17px);font-weight:600}
  .erow .nm i{font-style:normal;color:var(--dim);font-weight:400;font-size:.8em;display:block}
  .erow .nm small{color:var(--dim);font-weight:400;font-size:.82em}
  input.num{width:clamp(50px,7vw,72px);background:#0e1014;color:var(--txt);border:1px solid var(--line);
            border-radius:9px;padding:6px 3px;text-align:center;font:inherit;font-size:clamp(12px,1.6vh,16px)}
  .erow button,.ebtn{background:#0e1014;border:1px solid var(--line);color:var(--txt);border-radius:9px;
      padding:6px 9px;font:inherit;font-size:clamp(12px,1.6vh,16px);cursor:pointer}
  .ebtn.wide{width:100%;margin-top:8px}
  .ebtn.warn{color:#fca5a5;border-color:#5b2a2a}
  .estep{display:flex;align-items:center;gap:6px}
  .estep span{min-width:1.5em;text-align:center;font-variant-numeric:tabular-nums}
  #sheet{position:fixed;inset:0;background:rgba(4,6,10,.72);display:none;z-index:20;
         align-items:flex-end;justify-content:center}
  #sheet.on{display:flex}
  #sheet .sheetInner{background:var(--panel);border:1px solid var(--line);border-radius:16px 16px 0 0;
      width:min(680px,100%);max-height:86vh;display:flex;flex-direction:column;padding:14px}
  .sheetHead{display:flex;justify-content:space-between;align-items:center;gap:10px}
  #sheetSearch{margin:10px 0;background:#0e1014;color:var(--txt);border:1px solid var(--line);
      border-radius:10px;padding:10px;font:inherit}
  #sheetList{overflow:auto;flex:1;min-height:0}
  .pick{border-bottom:1px solid #1a2231;padding:9px 2px;display:flex;gap:10px;align-items:baseline;cursor:pointer}
  .pick b{font-size:clamp(13px,1.7vh,18px)}
  .pick span{color:var(--dim);font-size:.78em;margin-left:auto;white-space:nowrap}
  .sheetNew{border-top:1px solid var(--line);margin-top:10px;padding-top:10px;display:grid;gap:8px}
  .sheetNew input{background:#0e1014;color:var(--txt);border:1px solid var(--line);border-radius:10px;padding:9px;font:inherit}
</style>
</head>
<body>
<script src="https://www.youtube.com/iframe_api" async></script>
<div id="app">

  <!-- ============ MENU ============ -->
  <div id="menu">
    <h1>The Hour</h1>
    <div class="sub" id="tagline"></div>
    <div class="days" id="days"></div>
    <div class="cols">
      <div><div class="sub" style="margin:0 0 4px">Today's hour</div><div id="blocks"></div></div>
      <div><div class="sub" style="margin:0 0 4px">Move pool</div><div id="poolInfo"></div></div>
    </div>
    <div class="foot">
      <button class="primary" id="startBtn">Start</button>
      <label class="tog"><input type="checkbox" id="voiceTog"> spoken move names</label>
      <label class="tog"><input type="checkbox" id="musicTog" checked> music between videos</label>
      <button id="histBtn">Reviews</button>
      <button id="editBtn">✎ Edit routines</button>
    </div>
    <div id="vstatus"></div>
    <div id="liveStatus" class="hist"></div>
  </div>

  <!-- ============ RUN ============ -->
  <div id="run">
    <div id="bar"></div>
    <div class="topline"><div id="blockName">&nbsp;</div><div id="hourClock">&nbsp;</div></div>
    <div id="stage">
      <div id="clock">0:00</div>
      <div id="moveName">&nbsp;</div>
      <div id="sub"></div>
      <div id="cue"></div>
      <div id="meta"></div>
      <div id="next"></div>
      <div id="vidwrap"><div id="vpMain"></div><div class="vbar" id="vbar"></div></div>
    </div>
    <div id="musicbar">
      <b>♪</b><span class="nm" id="musicName"></span>
      <button id="musicToggle">Pause music</button>
      <input type="range" id="musicVol" min="0" max="100" value="35">
    </div>
    <div id="controls">
      <button id="pauseBtn">Pause</button>
      <button id="backBtn">Back</button>
      <button id="skipBtn">Skip</button>
      <button id="addBtn">+10s</button>
      <button id="stopBtn">Stop</button>
    </div>
  </div>

  <!-- ============ REVIEW ============ -->
  <div id="rate">
    <h1 id="rateTitle">How was it?</h1>
    <div class="sub" id="rateSub"></div>
    <div id="rateRows"></div>
    <textarea id="note" placeholder="Anything you want changed — a move to drop, a video that dragged, a block that felt wrong."></textarea>
    <div class="foot">
      <button class="primary" id="sendBtn">Send review</button>
      <button id="backMenu">Back to the week</button>
    </div>
    <div class="hint" id="rateHint"></div>
    <div class="hist" id="hist"></div>
  </div>

  <!-- ============ EDIT ============ -->
  <div id="edit">
    <h1>Edit the routines</h1>
    <div class="sub" id="editSub"></div>
    <div class="days" id="editDays"></div>
    <div id="editBody"></div>
    <div class="foot">
      <button class="primary" id="editSave">Save to GitHub</button>
      <button id="editAddSection">＋ add a section</button>
      <button id="editDiscard">Discard changes</button>
      <button id="editBack">Back to the week</button>
    </div>
    <div class="hint" id="editHint"></div>
    <div class="hist" id="tokenBox"></div>
  </div>

  <div id="sheet"><div class="sheetInner">
    <div class="sheetHead"><b id="sheetTitle">Add a move</b><button class="ebtn" id="sheetClose">✕ close</button></div>
    <input id="sheetSearch" placeholder="search the move pool…" autocomplete="off">
    <div id="sheetList"></div>
    <div class="sheetNew">
      <div class="sub" style="margin:0">Not in the pool? Make it up.</div>
      <input id="newName" placeholder="move name" autocomplete="off">
      <input id="newCue" placeholder="cue — one line, the way you would say it" autocomplete="off">
      <button class="ebtn" id="newAdd">Create it and add it to this section</button>
    </div>
  </div></div>

  <div id="musicHost"><div id="vpMusic"></div></div>
</div>

<script>
const DATA = __DATA__;
const REPO = DATA.repo || "RoAlfonsin/routines", BRANCH = DATA.branch || "main";
const WEBHOOK = DATA.webhook, THREAD = DATA.thread;
/* The routines and the move pool are live data. At boot they are replaced by whatever is
   committed on GitHub, so an edit lands on the phone without waiting for the Pages rebuild;
   the baked-in copy stays as the offline fallback. The editor works on a copy of all this. */
let POOL = DATA.pool, POOLFILE = DATA.poolFile, R = DATA.routines;
let HOUR = 3600, TAIL = 0, SUN = {}, SETTLE = {}, TR = {}, MUSIC = {}, WARM = {}, COOL = {},
    TR_SECONDS = 0;
const indexPool = file => { const m = {}; (file.moves || []).forEach(x => { m[x.id] = x; }); return m; };
function applyData(routines, poolFile){
  R = routines; POOLFILE = poolFile; POOL = indexPool(poolFile);
  HOUR = R.hour_seconds || 3600; TAIL = R.video_tail || 0;
  SUN = R.sun || {}; SETTLE = R.settle || {}; TR = R.transitions || {}; MUSIC = R.music || {};
  WARM = R.warmup || {moves: []}; COOL = R.cooldown || {moves: []};
  TR_SECONDS = (TR.after_sun || 0) + (TR.before_cooldown || 0);
}
applyData(R, POOLFILE);
const $ = id => document.getElementById(id);
const fmt = s => { s=Math.max(0,Math.ceil(s)); return Math.floor(s/60)+":"+String(s%60).padStart(2,"0"); };
const sumMoves = ms => ms.reduce((a,x)=>a+x.work+x.rest,0);
const COL = {meditation:"var(--med)", yoga:"var(--yoga)", warm:"var(--warm)", work:"var(--work)",
             rest:"var(--rest)", stretch:"var(--cool)"};

/* ================= sound: bells and bowls, not beeps ================= */
let AC=null;
const ac = () => { if(!AC){ try{AC=new (window.AudioContext||window.webkitAudioContext)();}catch(e){} }
                   if(AC&&AC.state==="suspended")AC.resume(); return AC; };
/* inharmonic partials + long decay = singing bowl / temple bell */
function bell(freq, vol, dur){
  const c=ac(); if(!c) return;
  const t0=c.currentTime;
  const partials=[[1,1],[2.00,.55],[2.76,.34],[5.40,.20],[8.93,.10],[13.34,.05]];
  partials.forEach(([mult,amp])=>{
    const o=c.createOscillator(), g=c.createGain();
    o.type="sine"; o.frequency.value=freq*mult;
    const decay = dur/(1+ (mult-1)*0.42);
    g.gain.setValueAtTime(0.0001,t0);
    g.gain.exponentialRampToValueAtTime(Math.max(0.0002,vol*amp), t0+0.014);
    g.gain.exponentialRampToValueAtTime(0.0001, t0+decay);
    o.connect(g).connect(c.destination);
    o.start(t0); o.stop(t0+decay+0.05);
  });
}
const BOWL_LOW = 288, BOWL_MID = 432, BOWL_HIGH = 528;
function strike(f, v, d){ bell(f, v===undefined?0.16:v, d===undefined?4:d); }
function gong(){ strike(BOWL_LOW,0.20,6); setTimeout(()=>strike(BOWL_LOW*1.5,0.10,5),90); }
function chime3(){ strike(BOWL_HIGH,0.18,5); setTimeout(()=>strike(BOWL_MID,0.16,5),600);
                   setTimeout(()=>strike(BOWL_LOW,0.18,7),1250); }

let voiceEnabled=false;
function say(t){ if(!voiceEnabled||!("speechSynthesis" in window)||!t) return;
  try{ speechSynthesis.cancel(); const u=new SpeechSynthesisUtterance(t); u.rate=1.04; speechSynthesis.speak(u);}catch(e){} }

/* ================= youtube: 2 content blocks + a music bed ================= */
let ytReady=false, pMain=null, pMusic=null;
let durs={sun:null,settle:null}, dursFor=null;
let musicWanted=true, musicVol=35;

function mkPlayer(hostId, vid, opts){
  try{
    return new YT.Player(hostId,{
      videoId: vid, host:"https://www.youtube-nocookie.com",
      playerVars:{rel:0,modestbranding:1,playsinline:1},
      events:{ onReady:e=>{ if(opts&&opts.music){ try{e.target.setVolume(musicVol);}catch(x){} } } }
    });
  }catch(e){ return null; }
}
window.onYouTubeIframeAPIReady = function(){
  ytReady = true;
  if(pMain) return;
  pMain  = mkPlayer("vpMain",  SUN.video, {main:true});
  pMusic = mkPlayer("vpMusic", MUSIC.video, {music:true});
  prefetch(currentDay());
};
/* Read the real length of both videos once, through the single visible player. */
function prefetch(day){
  if(!pMain || dursFor===day.id) return;
  dursFor = day.id; durs = {sun:null,settle:null};
  try{ pMain.mute(); }catch(e){}
  const list=[["sun",SUN.video],["settle",SETTLE.video]];
  let k=0;
  const next=()=>{
    if(k>=list.length){
      try{ pMain.cueVideoById(SUN.video); pMain.unMute(); }catch(e){}
      renderMenu(); return;
    }
    const key=list[k][0], vid=list[k][1]; k++;
    try{ pMain.loadVideoById(vid); }catch(e){}
    let tries=0;
    const poll=setInterval(()=>{
      let d=0; try{ d=pMain.getDuration(); }catch(e){}
      if(d>1){ durs[key]=d; clearInterval(poll); renderMenu(); next(); }
      else if(++tries>30){ clearInterval(poll); next(); }
    }, 250);
  };
  next();
}

/* ================= timeline ================= */
/* A day is an ordered list of blocks. Warm-up, the sun class, the cool-down and the closing
   meditation are shared by every day; the main circuit belongs to the day, and a day can
   carry extra circuits of its own. Any block except the day's main circuit can be skipped. */

const skipped = (day,key) => (day.skip||[]).indexOf(key) >= 0;

function circuitCost(cfg, dropFinalRest){
  const ms = (cfg && cfg.moves) || [];
  if(!ms.length) return 0;
  const rounds = cfg.rounds || 1;
  let cost = ms.reduce((a,x)=>a+(x.work||0)+(x.rest||0),0)*rounds;
  cost += (cfg.rest_between_rounds||0)*(rounds-1);
  return cost - (dropFinalRest ? (ms[ms.length-1].rest||0) : 0);
}
function blockList(day, Rx){
  Rx = Rx || R;
  const W = Rx.warmup||{moves:[]}, C = Rx.cooldown||{moves:[]}, S = Rx.sun||{}, ST = Rx.settle||{};
  const out=[];
  if(!skipped(day,"warmup")) out.push({key:"warmup", block:"Warm-Up", kind:"warm", shared:true,
        dur:circuitCost(W,false), moves:(W.moves||[]).length, rounds:W.rounds||1});
  if(!skipped(day,"sun")) out.push({key:"sun", block:"Sun Salutations", kind:"yoga", shared:true,
        video:true, dur:((durs.sun||S.nominal||0)+TAIL), moves:0, rounds:1});
  out.push({key:"main", block:day.main.label, kind:"work", shared:false,
        dur:circuitCost(day.main,true), moves:(day.main.moves||[]).length, rounds:day.main.rounds||1});
  (day.extra||[]).forEach((ex,i)=>out.push({key:"extra:"+i, block:(ex.label||("Extra "+(i+1))),
        kind:"work", shared:false, extra:i, dur:circuitCost(ex,true),
        moves:(ex.moves||[]).length, rounds:ex.rounds||1}));
  if(!skipped(day,"cooldown")) out.push({key:"cooldown", block:"Cool-Down", kind:"stretch", shared:true,
        dur:circuitCost(C,false), moves:(C.moves||[]).length, rounds:C.rounds||1});
  if(!skipped(day,"settle")) out.push({key:"settle", block:"Settle", kind:"meditation", shared:true,
        video:true, dur:((durs.settle||ST.nominal||0)+TAIL), moves:0, rounds:1});
  return out;
}
function cfgFor(day,key,Rx){
  Rx = Rx || R;
  if(key==="warmup") return Rx.warmup;
  if(key==="cooldown") return Rx.cooldown;
  if(key==="main") return day.main;
  if(key.indexOf("extra:")===0) return (day.extra||[])[+key.slice(6)];
  return null;
}
function transFor(day){
  return (skipped(day,"sun") ? 0 : (TR.after_sun||0))
       + (skipped(day,"cooldown") ? 0 : (TR.before_cooldown||0));
}
function plan(day,Rx){
  const blocks=blockList(day,Rx), trans=transFor(day);
  return {blocks, trans, total: blocks.reduce((a,b)=>a+b.dur,0)+trans};
}
function nextName(day, key, fallback){
  const bl=blockList(day), i=bl.findIndex(b=>b.key===key);
  if(i<0 || i+1>=bl.length) return fallback;
  const n=bl[i+1];
  if(n.key==="sun") return "the sun salutation class";
  if(n.key==="settle") return "the closing meditation";
  return n.block;
}
/* Rest steps come after every move except the very last of the last round of a circuit;
   warm-up and cool-down keep every rest they declare. Stretches fold the rest into the hold. */
function circuitSteps(cfg, block, kind, o){
  const steps=[], ms=(cfg && cfg.moves) || [], rounds=(cfg && cfg.rounds) || 1;
  for(let r=1;r<=rounds;r++){
    ms.forEach((x,i)=>{
      const mv = POOL[x.ref] || {name:x.ref, cue:""};
      const nxt = ms[i+1] ? (POOL[ms[i+1].ref]||{}).name : (r<rounds ? "Round "+(r+1) : o.next);
      const last = (r===rounds && i===ms.length-1);
      const base = {block, round:r, rounds, idx:i+1, count:ms.length, next:nxt, music:o.music};
      steps.push(Object.assign({}, base, {kind, label:mv.name, cue:mv.cue||"",
        dur: o.mergeRest ? (x.work||0)+(x.rest||0) : (x.work||0)}));
      if(!o.mergeRest && (x.rest||0)>0 && !(o.dropFinalRest && last))
        steps.push(Object.assign({}, base, {kind:"rest", dur:x.rest,
          label:o.restLabel||"Rest", cue:o.restCue||""}));
    });
    if((cfg.rest_between_rounds||0)>0 && r<rounds)
      steps.push({block, kind:"rest", label:"Round "+r+" done", cue:"Shake it out, then go again.",
                  dur:cfg.rest_between_rounds, round:r, rounds, idx:ms.length, count:ms.length,
                  next:"Round "+(r+1)+(ms[0] ? " · "+((POOL[ms[0].ref]||{}).name||"") : ""),
                  music:o.music});
  }
  return steps;
}
function blockSteps(day, b){
  if(b.key==="warmup")
    return circuitSteps(WARM, "Warm-Up", "work", {music:true, restLabel:"Change over",
             next:nextName(day,"warmup","the sun salutation class")});
  if(b.key==="cooldown")
    return circuitSteps(COOL, "Cool-Down", "stretch", {music:true, mergeRest:true,
             next:nextName(day,"cooldown","the closing meditation")});
  if(b.key==="main")
    return circuitSteps(day.main, day.main.label, "work",
             {music:true, restLabel:"Rest", restCue:"Breathe.", dropFinalRest:true,
              next:nextName(day,"main","the closing meditation")});
  if(b.key.indexOf("extra:")===0)
    return circuitSteps(cfgFor(day,b.key), b.block, "work",
             {music:true, restLabel:"Rest", restCue:"Breathe.", dropFinalRest:true,
              next:nextName(day,b.key,"the closing meditation")});
  if(b.key==="sun")
    return [{block:"Sun Salutations", kind:"yoga", label:SUN.title, sub:SUN.channel,
             cue:"Follow along. Match your breath to hers — no timer, just rhythm.",
             dur:b.dur, video:"sun", round:1, rounds:1}];
  if(b.key==="settle")
    return [{block:"Settle", kind:"meditation", label:SETTLE.title, sub:SETTLE.channel,
             cue:"Same closing meditation every day. Sit down, close your eyes, follow the voice.",
             dur:b.dur, video:"settle", round:1, rounds:1}];
  return [];
}
function buildTimeline(day){
  const parts=blockList(day).map(b=>({b, steps:blockSteps(day,b)})), out=[];
  parts.forEach((p,i)=>{
    out.push(...p.steps);
    const nx=parts[i+1];
    if(!nx) return;
    if(p.b.key==="sun" && (TR.after_sun||0)>0)
      out.push({block:"Transition", kind:"rest", label:"Transition",
                cue:"Shake out the sun salutations. "+(TR.after_sun||0)+" seconds, then the main routine.",
                dur:TR.after_sun, round:1, rounds:1, music:true});
    if(nx.b.key==="cooldown" && (TR.before_cooldown||0)>0)
      out.push({block:"Transition", kind:"rest", label:"Transition",
                cue:"Catch your breath. "+(TR.before_cooldown||0)+" seconds, then the cool-down.",
                dur:TR.before_cooldown, round:1, rounds:1, music:true});
  });
  return out;
}

/* ================= menu ================= */
let selId = R.days[0].id;
const currentDay = () => R.days.find(d=>d.id===selId) || R.days[0];

function colorFor(name,day){
  if(name==="Arrive"||name==="Settle") return COL.meditation;
  if(name==="Transition") return "var(--dim)";
  if(name==="Sun Salutations") return COL.yoga;
  if(name==="Warm-Up") return COL.warm;
  if(name==="Cool-Down") return COL.stretch;
  return COL.work;
}
const roundsTxt = n => n + (n===1 ? " round · " : " rounds · ");
function descFor(b,day){
  if(b.key==="settle") return (SETTLE.channel||"")+" · same every day";
  if(b.key==="sun") return (SUN.channel||"")+" · follow-along class";
  if(b.key==="warmup") return b.moves+" moves · seated to standing";
  if(b.key==="cooldown") return b.moves+" stretches";
  if(b.key.indexOf("extra:")===0) return (b.rounds>1?roundsTxt(b.rounds):"")+b.moves+" moves";
  return roundsTxt(day.main.rounds)+day.main.moves.length+" moves · "+day.main.source;
}
function renderMenu(){
  const box=$("days"); box.innerHTML="";
  R.days.forEach(d=>{
    const b=document.createElement("button");
    b.className="day"+(d.id===selId?" on":"");
    b.innerHTML="<b>"+d.day+"</b><span>"+d.focus+"</span><span>"+d.main.label+"</span>";
    b.onclick=()=>{ selId=d.id; renderMenu(); if(dursFor!==d.id) prefetch(currentDay()); };
    box.appendChild(b);
  });
  const day=currentDay();
  const p=plan(day);
  const box2=$("blocks"); box2.innerHTML="";
  p.blocks.forEach(b=>{
    const div=document.createElement("div"); div.className="blk";
    div.innerHTML="<div><b><span class='dot' style='background:"+colorFor(b.block,day)+"'></span>"+b.block+"</b><em>"+descFor(b,day)+"</em></div><u>"+fmt(b.dur)+"</u>";
    box2.appendChild(div);
  });
  const tot=document.createElement("div"); tot.className="blk";
  tot.innerHTML="<div><b>Total</b><em>nominal, ±1½ min per block</em></div><u>"+fmt(p.total)+"</u>";
  box2.appendChild(tot);
  $("poolInfo").innerHTML = "<div class='blk'><div><b>"+Object.keys(POOL).length+" moves</b><em>tagged by pattern, position, impact, level</em></div></div>"
    + "<div class='blk'><div><b>Music</b><em>"+MUSIC.title+" · "+MUSIC.channel+"</em></div></div>"
    + "<div class='blk'><div><b>Sun class</b><em>"+SUN.title+"</em></div></div>";
  $("tagline").textContent = "One hour a day · warm-up seated to standing · sun salutation class · main routine · cool-down · closing meditation";
  $("startBtn").textContent="Start "+day.day+" · "+day.main.label;
  $("musicName").textContent = MUSIC.title+" · "+MUSIC.channel;
  $("vstatus").textContent = (durs.sun
      ? "Video lengths read from YouTube: "+fmt(durs.sun)+", "+fmt(durs.settle||0)+"."
      : (ytReady ? "Reading video lengths…" : "YouTube unavailable — nominal lengths used."));
}

/* ================= run ================= */
let st={steps:[],i:0,left:0,running:false,last:0,lastTick5:null};
let hb=null, curVideo=null;

function start(){
  ac(); strike(BOWL_MID,0.14,3);
  st={steps:buildTimeline(currentDay()),i:0,left:0,running:true,last:performance.now(),lastTick5:null};
  st.left=st.steps[0].dur;
  $("menu").style.display="none"; $("rate").classList.remove("on"); $("run").style.display="flex";
  paintBar(); enter(true);
  if(hb) clearInterval(hb); hb=setInterval(tick,100);
  try{ if("wakeLock" in navigator) navigator.wakeLock.request("screen").catch(()=>{}); }catch(e){}
}
function enter(first){
  const s=st.steps[st.i], day=currentDay();
  $("blockName").textContent = s.block + (s.rounds>1 ? " · round "+s.round+"/"+s.rounds : "");
  $("moveName").textContent = s.label;
  $("sub").textContent = s.sub || "";
  $("cue").textContent = s.cue || "";
  $("meta").textContent = s.count>1 ? ("move "+s.idx+" of "+s.count) : "";
  $("next").textContent = s.next ? ("next · "+s.next) : "";
  document.body.style.setProperty("--accent", colorFor(s.block,day));

  // video vs music
  const wantsVideo = s.video || null;
  $("vidwrap").classList.toggle("on", !!wantsVideo);
  if(wantsVideo!==curVideo){
    if(wantsVideo){
      const id = wantsVideo==="sun" ? SUN.video : SETTLE.video;
      try{ pMain.loadVideoById(id); pMain.unMute(); pMain.setVolume(90); }catch(e){}
      startVideo(wantsVideo, day, s);
    } else {
      try{ pMain.pauseVideo(); }catch(e){}
    }
    curVideo = wantsVideo;
  } else if(!wantsVideo){ try{ pMain.pauseVideo(); }catch(e){} }

  // music runs under every non-video block
  const wantMusic = !wantsVideo && musicWanted;
  $("musicbar").classList.toggle("on", !!wantMusic);
  if(pMusic){
    if(wantMusic){ try{ pMusic.unMute(); pMusic.setVolume(musicVol); pMusic.playVideo(); }catch(e){} }
    else { try{ pMusic.pauseVideo(); }catch(e){} }
  }

  if(first || s.kind!=="rest"){
    if(s.video) gong();
    else if(s.block==="Cool-Down") strike(BOWL_MID,0.14,4);
    else if(s.kind==="work") strike(BOWL_HIGH,0.15,3);
    else strike(BOWL_LOW,0.13,4);
  } else strike(BOWL_LOW,0.11,3);
  say(s.kind==="rest" ? "" : s.label);
  paintBar();
}
function startVideo(which, day, s){
  const meta = which==="sun" ? SUN : SETTLE;
  const id = which==="sun" ? SUN.video : SETTLE.video;
  if(!pMain){ $("vbar").innerHTML="<span>YouTube unavailable</span>"; return; }
  $("vbar").innerHTML = "<a href='https://www.youtube.com/watch?v="+id+"' target='_blank' rel='noopener'>open on YouTube</a>"
                      + " <button id='tapPlay' style='display:none'>▶ tap to play</button>"
                      + " <span>"+meta.channel+"</span>";
  const token = st.i;
  setTimeout(()=>{
    if(st.i!==token || !pMain) return;
    let s2=-1; try{ s2=pMain.getPlayerState(); }catch(e){}
    const btn=$("tapPlay");
    if(btn && s2!==1 && s2!==3){ btn.style.display="inline-block";
      btn.onclick=()=>{ try{pMain.unMute(); pMain.setVolume(90); pMain.playVideo();}catch(e){} btn.style.display="none"; }; }
  }, 2500);
}
function advance(){
  if(st.i>=st.steps.length-1){ finish(); return; }
  st.i++; st.left=st.steps[st.i].dur; enter(false);
}
function tick(){
  const now=performance.now(), dt=Math.min(5,(now-st.last)/1000); st.last=now;
  const s=st.steps[st.i];
  if(st.running){
    st.left-=dt;
    if(st.left<=0){ advance(); return; }
    if(st.left<=3.4 && Math.ceil(st.left)!==st.lastTick5 && s.kind==="work"){
      st.lastTick5=Math.ceil(st.left); strike(BOWL_MID,0.05,1.2);
    }
  }
  render();
}
function render(){
  const s=st.steps[st.i];
  $("clock").textContent = fmt(st.left);
  const done = st.steps.slice(0,st.i).reduce((a,x)=>a+x.dur,0) + (s.dur-Math.max(0,st.left));
  $("hourClock").textContent = fmt(done)+" / ≈"+fmt(st.steps.reduce((a,x)=>a+x.dur,0));
  $("pauseBtn").textContent = st.running ? "Pause" : "Resume";
  paintCursor(done);
}
function paintBar(){
  const bar=$("bar"); bar.innerHTML="";
  const groups=[]; st.steps.forEach(s=>{ const g=groups[groups.length-1];
    if(g && g.name===s.block) g.dur+=s.dur; else groups.push({name:s.block,dur:s.dur,kind:s.kind}); });
  groups.forEach(g=>{ const el=document.createElement("i");
    el.style.width=(g.dur/HOUR*100)+"%"; el.style.background=COL[g.kind]||"var(--line)";
    el.style.opacity="0.3"; el.title=g.name; bar.appendChild(el); });
}
function paintCursor(done){
  const segs=[...document.querySelectorAll("#bar i")];
  const groups=[]; st.steps.forEach(s=>{ const g=groups[groups.length-1];
    if(g && g.name===s.block) g.dur+=s.dur; else groups.push({name:s.block,dur:s.dur}); });
  let acc=0;
  groups.forEach((g,k)=>{ const full = done>=acc+g.dur ? 1 : (done<=acc ? 0 : (done-acc)/g.dur);
    if(segs[k]) segs[k].style.opacity=(0.3+0.7*full).toFixed(2); acc+=g.dur; });
}
function finish(){
  st.running=false; if(hb){clearInterval(hb);hb=null;}
  chime3();
  if(curVideo && pMain){ try{pMain.pauseVideo();}catch(e){} }
  if(pMusic){ try{pMusic.pauseVideo();}catch(e){} }
  $("run").style.display="none"; showReview();
}

/* ================= review ================= */
const RKEY="fitness.reviews.v2";
const load=()=>{ try{return JSON.parse(localStorage.getItem(RKEY))||[];}catch(e){return [];} };
const save=a=>{ try{localStorage.setItem(RKEY,JSON.stringify(a));}catch(e){} };
const today=()=>new Date().toISOString().slice(0,10);
let draft={overall:0,blocks:{},note:""};

function blockKeys(day){ return blockList(day).map(b=>b.block); }
function shortOf(label){
  if(SHORT[label]) return SHORT[label];
  const w=(label||"block").split(/[\s·&]+/)[0];
  return w.length>9 ? w.slice(0,9) : w;
}
function starsFor(key,n,onPick){
  const wrap=document.createElement("div"); wrap.className="stars";
  for(let i=1;i<=5;i++){
    const b=document.createElement("button");
    b.className="star"+(n>=i?" on":""); b.textContent="★"; b.title=i+" / 5";
    b.onclick=()=>onPick(i);
    wrap.appendChild(b);
  }
  return wrap;
}
function showReview(){
  const day=currentDay();
  $("rate").classList.add("on");
  $("rateTitle").textContent="How was "+day.day+"?";
  $("rateSub").textContent=day.focus+" · "+day.main.label+" · "+today();
  const rows=$("rateRows"); rows.innerHTML="";
  const mk=(label,get,set)=>{
    const r=document.createElement("div"); r.className="rateRow";
    const s=document.createElement("span"); s.textContent=label;
    r.appendChild(s); r.appendChild(starsFor(label,get(),set)); rows.appendChild(r);
  };
  mk("Overall",()=>draft.overall,v=>{draft.overall=v;showReview();});
  blockKeys(day).forEach(k=>mk(k,()=>draft.blocks[k]||0,v=>{draft.blocks[k]=v;showReview();}));
  $("note").value=draft.note||"";
  $("hist").innerHTML = reviewHistoryHTML();
}
function reviewHistoryHTML(){
  const h=load().slice(-12).reverse();
  if(!h.length) return "";
  return "<div style='margin-top:6px'><b>Recent reviews</b></div>" + h.map(r=>
    "<div><b>"+r.date+"</b> "+r.day+" · "+"★".repeat(r.overall)+"☆".repeat(5-r.overall)
    + " · "+Object.entries(r.blocks||{}).map(([k,v])=>k.slice(0,4)+" "+v).join(" ")+"</div>").join("");
}
const SHORT={ "Arrive":"Arrive", "Warm-Up":"WarmUp", "Sun Salutations":"Sun",
              "Cool-Down":"CoolDown", "Settle":"Settle" };
function reviewText(day){
  const lines=["📋 **"+day.day+" review — "+today()+"**",
               "Overall **"+"★".repeat(draft.overall)+"☆".repeat(5-draft.overall)+"** ("+draft.overall+"/5)"];
  const parts=blockKeys(day).map(k=>((SHORT[k]||shortOf(k))+" : "+(draft.blocks[k]||"-"))).join(" · ");
  lines.push(parts);
  if(draft.note.trim()) lines.push("_" + draft.note.trim() + "_");
  return lines.join("\n");
}
$("sendBtn").onclick=async ()=>{
  const day=currentDay();
  draft.note=$("note").value;
  if(!draft.overall){ $("rateHint").textContent="Pick an overall rating first."; return; }
  const rec={date:today(),day:day.day,id:day.id,overall:draft.overall,blocks:draft.blocks,note:draft.note.trim()};
  const a=load(); a.push(rec); save(a);
  const url = WEBHOOK ? (WEBHOOK + "?thread_id=" + THREAD + "&wait=true") : null;
  if(url){
    $("rateHint").textContent="Sending…";
    try{
      const res=await fetch(url,{method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({username:"The Hour", content:reviewText(day)})});
      $("rateHint").textContent = res.ok
        ? "Sent. Hermes has the review."
        : ("Could not send (HTTP "+res.status+"). Saved on this device — copy it instead.");
    }catch(e){ $("rateHint").textContent="Could not send (offline?). Saved on this device."; }
  } else {
    try{ await navigator.clipboard.writeText(reviewText(day));
         $("rateHint").textContent="No webhook configured — review copied to the clipboard."; }
    catch(e){ $("rateHint").textContent=reviewText(day).replace(/\*/g,""); }
  }
  draft={overall:0,blocks:{},note:""};
  $("hist").innerHTML=reviewHistoryHTML();
};
$("backMenu").onclick=()=>{ $("rate").classList.remove("on"); $("menu").style.display="flex"; renderMenu(); };
$("histBtn").onclick=()=>{ $("menu").style.display="none"; $("rate").classList.add("on");
  $("rateTitle").textContent="Your reviews"; $("rateSub").textContent="Stored on this device.";
  $("rateRows").innerHTML=""; $("hist").innerHTML=reviewHistoryHTML()||"<div>No reviews yet.</div>"; };

/* ================= editor ================= */
/* Edits happen on a working copy in memory. Save commits routines.json — and pool.json when a
   move was invented — straight to GitHub with a token that lives only in this browser. No
   server, no database: the repo stays the one source of truth, and CI rebuilds the offline copy. */
const TOKKEY="fitness.gh.token";
const getTok=()=>{ try{ return localStorage.getItem(TOKKEY)||""; }catch(e){ return ""; } };
const setTok=t=>{ try{ t ? localStorage.setItem(TOKKEY,t) : localStorage.removeItem(TOKKEY); }catch(e){} };
const clone=o=>JSON.parse(JSON.stringify(o));
const RAWURL=n=>"https://raw.githubusercontent.com/"+REPO+"/"+BRANCH+"/"+n;
const APIURL=p=>"https://api.github.com/repos/"+REPO+"/contents/"+p;
const SKIPKEYS=["warmup","sun","cooldown","settle"];
const SKIPNAME={warmup:"the warm-up", sun:"the sun salutation class",
                cooldown:"the cool-down", settle:"the closing meditation"};
let ED=null;

function validateData(routines,poolFile){
  const bad=[];
  if(!routines || !Array.isArray(routines.days) || !routines.days.length) bad.push("routines.json has no days");
  if(!poolFile || !Array.isArray(poolFile.moves) || !poolFile.moves.length) bad.push("the move pool is empty");
  if(bad.length) return bad.join("; ");
  const ids={};
  poolFile.moves.forEach(m=>{ if(m && m.id) ids[m.id]=1; else bad.push("a move has no id"); });
  [["the warm-up",routines.warmup],["the cool-down",routines.cooldown]].forEach(pair=>{
    const name=pair[0], c=pair[1];
    if(!c || !Array.isArray(c.moves)){ bad.push(name+" is missing"); return; }
    c.moves.forEach(x=>{ if(!ids[x.ref]) bad.push(name+" uses unknown move "+x.ref); });
  });
  routines.days.forEach(d=>{
    if(!d.main || !d.main.label || !Array.isArray(d.main.moves)){ bad.push((d.id||"?")+" has no main circuit"); return; }
    if(!(d.main.rounds>=1)) d.main.rounds=1;
    d.main.moves.forEach(x=>{ if(!ids[x.ref]) bad.push(d.id+" uses unknown move "+x.ref); });
    (d.extra||[]).forEach((ex,i)=>{
      if(!Array.isArray(ex.moves)){ bad.push(d.id+" section "+(i+1)+" has no moves list"); return; }
      ex.moves.forEach(x=>{ if(!ids[x.ref]) bad.push(d.id+" section "+(i+1)+" uses unknown move "+x.ref); });
    });
    (d.skip||[]).forEach(k=>{ if(SKIPKEYS.indexOf(k)<0) bad.push(d.id+" skips something unknown: "+k); });
  });
  return bad.length ? bad.slice(0,4).join("; ") : null;
}
async function fetchJSON(url){
  const r=await fetch(url+(url.indexOf("?")<0?"?":"&")+"t="+Date.now(),{cache:"no-store"});
  if(!r.ok) throw new Error("HTTP "+r.status);
  return r.json();
}
async function loadLive(){
  const both=await Promise.all([fetchJSON(RAWURL("routines.json")), fetchJSON(RAWURL("pool.json"))]);
  const problem=validateData(both[0],both[1]);
  if(problem) throw new Error(problem);
  return {routines:both[0], poolFile:both[1]};
}
function b64(s){ const b=new TextEncoder().encode(s); let bin="";
  for(let i=0;i<b.length;i++) bin+=String.fromCharCode(b[i]); return btoa(bin); }
async function ghGet(path){
  const r=await fetch(APIURL(path)+"?ref="+BRANCH,{cache:"no-store",
    headers:{Authorization:"Bearer "+getTok(), Accept:"application/vnd.github+json"}});
  if(!r.ok){
    const why = r.status===401 ? " — the token is wrong or expired"
              : r.status===404 ? " — the token cannot see this repo, or lacks Contents access"
              : r.status===403 ? " — the token cannot read this repo's contents"
              : "";
    throw new Error("reading "+path+" failed (HTTP "+r.status+why+")");
  }
  return r.json();
}
/* A read-only token reads a public repo fine and only fails on the write, which is confusing.
   The repo endpoint reports the token's own permissions, so the editor can say which it is. */
async function ghRepoPerms(){
  const r=await fetch("https://api.github.com/repos/"+REPO,{cache:"no-store",
    headers:{Authorization:"Bearer "+getTok(), Accept:"application/vnd.github+json"}});
  if(!r.ok) throw new Error("HTTP "+r.status+(r.status===401 ? " — the token is wrong or expired" : ""));
  const j=await r.json();
  return !!(j.permissions && j.permissions.push);
}
const READONLY_HINT = "this token can read "+REPO+" but not write to it. Open the token on GitHub and set "
  + "Repository permissions → Contents to Read and write (choosing Public repositories as the repository access, "
  + "or using a classic token without the repo scope, gives exactly this).";
async function checkToken(){
  const hint=$("editHint");
  if(!getTok()){ hint.textContent="No token saved on this device yet — paste one in the box below."; return; }
  hint.textContent="Checking the token…";
  try{
    hint.textContent = await ghRepoPerms()
      ? "Token is good: it can write to "+REPO+"."
      : "Not usable for saving — "+READONLY_HINT;
  }catch(e){ hint.textContent="Could not check the token — "+e.message; }
}
async function ghPut(path,obj,message){
  const cur=await ghGet(path);                       /* fresh sha: never write against a stale one */
  const r=await fetch(APIURL(path),{method:"PUT",
    headers:{Authorization:"Bearer "+getTok(), Accept:"application/vnd.github+json","Content-Type":"application/json"},
    body:JSON.stringify({message, branch:BRANCH, sha:cur.sha, content:b64(JSON.stringify(obj,null,2)+"\n")})});
  if(!r.ok){
    const t=await r.text();
    const why = r.status===403 ? " — "+READONLY_HINT
              : r.status===409 ? " — the file changed since it was read: reload the page and edit again"
              : r.status===404 ? " — the token cannot see this repo, or the branch is missing"
              : "";
    throw new Error("writing "+path+" failed (HTTP "+r.status+why+") "+t.slice(0,120));
  }
  return r.json();
}

const clampNum=(v,lo,hi)=>{ let n=Math.round(+v); if(isNaN(n)) n=lo; return Math.max(lo,Math.min(hi,n)); };
const edDay=()=>ED.routines.days.filter(d=>d.id===ED.dayId)[0] || ED.routines.days[0];
const edPool=()=>indexPool(ED.poolFile);
const edName=ref=>{ const m=edPool()[ref]; return m ? m.name : ref; };
const edCfg=key=>cfgFor(edDay(),key,ED.routines);
const markDirty=()=>{ ED.dirty=true; };

function openEditor(){
  ED={routines:clone(R), poolFile:clone(POOLFILE), dayId:selId, dirty:false, poolDirty:false, sheet:null};
  $("menu").style.display="none"; $("run").style.display="none";
  $("rate").classList.remove("on"); $("edit").classList.add("on");
  renderEditor();
}
function closeEditor(){
  ED=null; $("edit").classList.remove("on"); $("sheet").classList.remove("on");
  $("menu").style.display="flex"; renderMenu();
}
const edRight=b=>fmt(b.dur)+(b.key==="sun"||b.key==="settle" ? "" : " · "+b.moves+" moves");
function edSubLine(){
  const day=edDay();
  return day.day+" · "+day.focus+" · "+fmt(plan(day,ED.routines).total)
    +" nominal — the sun class and the closing meditation take their real length at run time.";
}
function renderEditor(){
  if(!ED) return;
  const day=edDay(), bl=blockList(day,ED.routines);
  $("editSub").textContent=edSubLine();
  const chips=$("editDays"); chips.innerHTML="";
  ED.routines.days.forEach(d=>{
    const b=document.createElement("button");
    b.className="day"+(d.id===ED.dayId?" on":"");
    b.innerHTML="<b>"+d.day.slice(0,3)+"</b><span>"+d.main.label+"</span><span>"+fmt(plan(d,ED.routines).total)+"</span>";
    b.onclick=()=>{ ED.dayId=d.id; renderEditor(); };
    chips.appendChild(b);
  });
  const body=$("editBody"); body.innerHTML="";
  bl.forEach(b=>body.appendChild(edCard(b)));
  const gone=SKIPKEYS.filter(k=>skipped(day,k));
  if(gone.length){
    const box=document.createElement("div"); box.className="ecard";
    box.innerHTML="<div class='ehead'><b>Not in this day</b><em>removed</em></div>";
    gone.forEach(k=>{
      const btn=document.createElement("button"); btn.className="ebtn wide";
      btn.textContent="＋ put "+SKIPNAME[k]+" back";
      btn.onclick=()=>{ day.skip=day.skip.filter(x=>x!==k); if(!day.skip.length) delete day.skip;
                        markDirty(); renderEditor(); };
      box.appendChild(btn);
    });
    body.appendChild(box);
  }
  refreshEd();
  $("tokenBox").innerHTML=tokenBoxHTML();
  const ts=$("tokSave");
  if(ts) ts.onclick=()=>{ const v=$("tokIn").value.trim();
    if(!v){ $("tokIn").placeholder="paste the token first"; return; }
    setTok(v); $("tokIn").value=""; renderEditor(); };
  const tf=$("tokForget");
  if(tf) tf.onclick=()=>{ setTok(""); renderEditor(); };
  const tc=$("tokCheck");
  if(tc) tc.onclick=checkToken;
  $("editHint").textContent = ED.dirty ? "Changes live only on this device until you save." : "";
}
function refreshEd(){
  if(!ED) return;
  const day=edDay();
  blockList(day,ED.routines).forEach(b=>{ const el=$("edh:"+b.key); if(el) el.textContent=edRight(b); });
  const bl=blockList(day,ED.routines);
  const t=$("edTotal");
  if(t) t.innerHTML="<div class='ehead'><b>Total</b><em>"+fmt(plan(day,ED.routines).total)+"</em></div>";
  $("editSub").textContent=edSubLine();
  const chips=$("editDays").children;
  ED.routines.days.forEach((d,i)=>{ const c=chips[i];
    if(c && c.children[2]) c.children[2].textContent=fmt(plan(d,ED.routines).total); });
}
function edCard(b){
  const day=edDay(), card=document.createElement("div"); card.className="ecard";
  const head=document.createElement("div"); head.className="ehead";
  head.innerHTML="<b>"+b.block+"</b>"
    +"<span class='etag'>"+(b.shared?"every day":"this day")+"</span>"
    +"<em id='edh:"+b.key+"'>"+edRight(b)+"</em>";
  card.appendChild(head);
  const isCircuit = b.key==="warmup" || b.key==="cooldown" || b.key==="main" || b.key.indexOf("extra:")===0;
  if(isCircuit){
    const cfg=edCfg(b.key);
    const row=document.createElement("div"); row.className="ehead"; row.style.marginTop="8px";
    const step=document.createElement("div"); step.className="estep";
    const minus=document.createElement("button"); minus.className="ebtn"; minus.textContent="−";
    const val=document.createElement("span"); val.textContent=(cfg.rounds||1)+"×";
    const plus=document.createElement("button"); plus.className="ebtn"; plus.textContent="+";
    minus.onclick=()=>{ const n=(cfg.rounds||1)-1; if(n<=1) delete cfg.rounds; else cfg.rounds=n;
                        markDirty(); renderEditor(); };
    plus.onclick=()=>{ cfg.rounds=Math.min(20,(cfg.rounds||1)+1); markDirty(); renderEditor(); };
    step.appendChild(minus); step.appendChild(val); step.appendChild(plus);
    row.appendChild(step);
    if((cfg.rounds||1)>1){
      const lbl=document.createElement("span"); lbl.className="etag"; lbl.textContent="rest between rounds";
      const inp=document.createElement("input"); inp.type="number"; inp.inputMode="numeric"; inp.className="num";
      inp.value=(cfg.rest_between_rounds||0); inp.title="seconds between rounds";
      inp.onchange=()=>{ cfg.rest_between_rounds=clampNum(inp.value,0,600); markDirty(); refreshEd(); };
      row.appendChild(lbl); row.appendChild(inp);
    }
    card.appendChild(row);
    const hdr=document.createElement("div"); hdr.className="erow"; hdr.style.borderTop="0";
    hdr.innerHTML="<div class='nm'><small>move</small></div><div class='nm'><small>work″</small></div>"
      +"<div class='nm'><small>rest″</small></div><div></div>";
    card.appendChild(hdr);
    (cfg.moves||[]).forEach((x,i)=>{
      const r=document.createElement("div"); r.className="erow";
      const nm=document.createElement("div"); nm.className="nm";
      nm.innerHTML=edName(x.ref)+"<i>"+(edPool()[x.ref]||{}).cue+"</i>";
      const w=document.createElement("input"); w.type="number"; w.inputMode="numeric"; w.className="num";
      w.value=(x.work||0); w.onchange=()=>{ x.work=clampNum(w.value,0,600); markDirty(); refreshEd(); };
      const rst=document.createElement("input"); rst.type="number"; rst.inputMode="numeric"; rst.className="num";
      rst.value=(x.rest||0); rst.onchange=()=>{ x.rest=clampNum(rst.value,0,600); markDirty(); refreshEd(); };
      const ctl=document.createElement("div"); ctl.className="estep";
      [["↑",-1],["↓",1]].forEach(pair=>{
        const b2=document.createElement("button"); b2.className="ebtn"; b2.textContent=pair[0];
        b2.onclick=()=>edShift(b.key,i,pair[1]); ctl.appendChild(b2);
      });
      const del=document.createElement("button"); del.className="ebtn warn"; del.textContent="✕";
      del.onclick=()=>{ cfg.moves.splice(i,1); markDirty(); renderEditor(); };
      ctl.appendChild(del);
      r.appendChild(nm); r.appendChild(w); r.appendChild(rst); r.appendChild(ctl);
      card.appendChild(r);
    });
    const add=document.createElement("button"); add.className="ebtn wide";
    add.textContent="＋ add a move to "+b.block;
    add.onclick=()=>openSheet(b.key);
    card.appendChild(add);
  } else {
    const p=document.createElement("div"); p.className="cue"; p.style.marginTop="6px";
    p.textContent = b.key==="sun" ? (SUN.channel||"") : (SETTLE.channel||"");
    card.appendChild(p);
  }
  const foot=document.createElement("button"); foot.className="ebtn wide"+(b.key.indexOf("extra:")===0?" warn":"");
  if(b.key.indexOf("extra:")===0){
    foot.textContent="✕ remove this section from "+day.day;
    foot.onclick=()=>{ day.extra.splice(b.extra,1); if(!day.extra.length) delete day.extra;
                       markDirty(); renderEditor(); };
  } else {
    foot.textContent="✕ take "+b.block+" out of "+day.day;
    foot.onclick=()=>{ day.skip=(day.skip||[]).concat([b.key]); markDirty(); renderEditor(); };
  }
  card.appendChild(foot);
  return card;
}
function edShift(key,i,dir){
  const ms=edCfg(key).moves, j=i+dir;
  if(j<0 || j>=ms.length) return;
  const t=ms[i]; ms[i]=ms[j]; ms[j]=t; markDirty(); renderEditor();
}
function edAddMove(key,ref){
  const cfg=edCfg(key);
  if(!cfg) return;
  cfg.moves.push({ref, work:40, rest:(key==="cooldown"?0:15)});
  markDirty(); renderEditor();
}
function edNewMove(name,cue){
  const base=(name||"move").toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-+|-+$/g,"") || "move";
  let id=base, n=2, have=edPool();
  while(have[id]){ id=base+"-"+(n++); }
  ED.poolFile.moves.push({id, name:name, pattern:"mobility", position:"standing", impact:"low",
                          level:1, unit:"reps", default:10, cue:cue||"", from:"Rodri"});
  ED.poolDirty=true;
  return id;
}
function edAddSection(){
  const day=edDay();
  const label=window.prompt("Name for the new section (for example: Abs finisher)","");
  if(label===null) return;
  const clean=(label||"").trim() || ("Extra "+(((day.extra||[]).length)+1));
  day.extra=(day.extra||[]).concat([{label:clean, rounds:1, rest_between_rounds:0, moves:[]}]);
  markDirty(); renderEditor();
}

/* ---------- move picker ---------- */
function openSheet(addTo){
  ED.sheet={addTo};
  const b=blockList(edDay(),ED.routines).filter(x=>x.key===addTo)[0];
  $("sheetTitle").textContent="Add a move to "+(b?b.block:addTo);
  $("sheetSearch").value="";
  renderSheet("");
  $("sheet").classList.add("on");
  try{ $("sheetSearch").focus(); }catch(e){}
}
function renderSheet(q){
  const list=$("sheetList"), pool=edPool();
  const cfg=edCfg(ED.sheet.addTo), used=((cfg&&cfg.moves)||[]).map(x=>x.ref);
  const ql=(q||"").toLowerCase();
  list.innerHTML="";
  const moves=Object.keys(pool).map(k=>pool[k]).filter(m=>{
    const hay=(m.name+" "+(m.pattern||"")+" "+(m.position||"")+" "+(m.impact||"")).toLowerCase();
    return !ql || hay.indexOf(ql)>=0;
  }).sort((a,b)=>(used.indexOf(a.id)>=0)-(used.indexOf(b.id)>=0) || a.name.localeCompare(b.name));
  moves.forEach(m=>{
    const d=document.createElement("div"); d.className="pick";
    d.innerHTML="<b>"+m.name+(used.indexOf(m.id)>=0?" ·":"")+"</b><span>"+(m.pattern||"")+" · "
      +(m.position||"")+" · level "+(m.level||1)+"</span>";
    d.onclick=()=>{ edAddMove(ED.sheet.addTo,m.id); $("sheet").classList.remove("on"); };
    list.appendChild(d);
  });
  if(!list.children.length) list.innerHTML="<div class='pick'><b>Nothing in the pool matches that.</b></div>";
}

/* ---------- token ---------- */
function tokenBoxHTML(){
  const has=!!getTok();
  return "<div><b>GitHub access</b> — "+(has
      ? "a token is saved in this browser."
      : "no token on this device yet, so nothing can be saved.")+"</div>"
    +"<div style='margin-top:5px'>Saving writes the JSON straight to <b>"+REPO+"</b>, which needs a token that can WRITE to "
    +"that one repo. Make a <b>fine-grained</b> token at github.com/settings/personal-access-tokens/new:</div>"
    +"<div style='margin-top:4px'>1 · Repository access → <b>Only select repositories</b> → add <b>"+REPO+"</b> "
    +"(<i>Public repositories</i> is read-only and will not work)<br>"
    +"2 · Permissions → Repository permissions → <b>Contents: Read and write</b><br>"
    +"3 · Expiration → 90 days</div>"
    +"<div style='margin-top:5px'>A <b>classic</b> token needs the <b>repo</b> scope; without it, reading this public "
    +"repo still works and only saving fails with HTTP 403. The token is kept in this browser's storage only: never in "
    +"the repo, never sent anywhere but api.github.com.</div>"
    +"<div style='margin-top:8px;display:flex;gap:8px;flex-wrap:wrap;align-items:center'>"
    +"<input id='tokIn' type='password' autocomplete='off' placeholder='github_pat_…' "
    +"style='flex:1;min-width:170px;background:#0e1014;color:var(--txt);border:1px solid var(--line);border-radius:10px;padding:9px;font:inherit'>"
    +"<button class='ebtn' id='tokSave'>Save token</button>"
    +(has ? "<button class='ebtn' id='tokCheck'>Check token</button>" : "")
    +(has ? "<button class='ebtn warn' id='tokForget'>Forget token</button>" : "")
    +"</div>";
}

/* ---------- save ---------- */
/* routines.json carries an `updated` stamp: the page only replaces its built-in copy with
   GitHub's when GitHub's is strictly newer, so a CDN lag can never roll the data backwards. */
const SAVEDKEY="fitness.saved.v1";
const SAVED_TTL=10*60*1000;
function cacheSaved(routines,poolFile){
  try{ localStorage.setItem(SAVEDKEY, JSON.stringify({at:Date.now(), routines, poolFile})); }catch(e){}
}
function readSaved(){
  try{
    const j=JSON.parse(localStorage.getItem(SAVEDKEY));
    if(!j || !j.routines || !j.poolFile){ clearSaved(); return null; }
    if(Date.now()-j.at > SAVED_TTL){ clearSaved(); return null; }
    return j;
  }catch(e){ clearSaved(); return null; }
}
function clearSaved(){ try{ localStorage.removeItem(SAVEDKEY); }catch(e){} }
const stampOf=r=>Date.parse((r && r.updated) || "")||0;

async function waitForLive(wantR, wantP){
  for(let i=0;i<20;i++){
    try{
      const live=await loadLive();
      if(JSON.stringify(live.routines)===JSON.stringify(wantR) && JSON.stringify(live.poolFile)===JSON.stringify(wantP))
        return true;
    }catch(e){}
    await new Promise(r=>setTimeout(r,3000));
  }
  return false;
}
async function saveEdits(){
  const hint=$("editHint");
  if(!ED) return;
  if(!getTok()){ hint.textContent="Add a GitHub token first — see the box at the bottom."; return; }
  const problem=validateData(ED.routines,ED.poolFile);
  if(problem){ hint.textContent="Not saved — "+problem+"."; return; }
  /* Length is Rodri's call: no nag about a day being off the hour. */
  ED.routines.updated=new Date().toISOString();      /* the freshness stamp the page compares */
  /* A section with no moves in it contributes nothing and only confuses the menu: drop it. */
  let dropped=0;
  ED.routines.days.forEach(d=>{
    if(!d.extra) return;
    const keep=d.extra.filter(ex=>(ex.moves||[]).length);
    dropped += d.extra.length - keep.length;
    if(keep.length) d.extra=keep; else delete d.extra;
  });
  if(dropped) renderEditor();
  hint.textContent="Saving…";
  try{
    await ghPut("routines.json", ED.routines, "The Hour: routine edits from the phone editor");
    if(ED.poolDirty) await ghPut("pool.json", ED.poolFile, "The Hour: new moves from the phone editor");
    const wantR=clone(ED.routines), wantP=clone(ED.poolFile);
    ED.poolDirty=false;
    cacheSaved(wantR, wantP);                   /* this device shows its own save straight away */
    applyData(clone(wantR), clone(wantP));      /* the app runs the new version right away */
    ED.dirty=false;
    hint.textContent="Committed. Waiting for GitHub to serve the new file…";
    renderEditor();
    const ok=await waitForLive(wantR, wantP);
    const gone = dropped ? " (Dropped "+dropped+" empty section"+(dropped>1?"s":"")+" — a section with no moves does nothing.)" : "";
    hint.textContent = (ok
      ? "Live and saved to GitHub."
      : "Saved. GitHub is still serving the old copy, but this device keeps showing your edit — a reload elsewhere may lag a minute.") + gone;
    renderMenu();
  }catch(e){
    hint.textContent="Could not save — "+e.message;
  }
}

/* ================= controls ================= */
$("startBtn").onclick=start;
$("pauseBtn").onclick=()=>{ st.running=!st.running; st.last=performance.now(); };
$("skipBtn").onclick=()=>{ st.left=0.001; };
$("backBtn").onclick=()=>{ if(st.i>0){ st.i--; st.left=st.steps[st.i].dur; st.last=performance.now(); curVideo=null; enter(true); } };
$("addBtn").onclick=()=>{ st.left+=10; };
$("stopBtn").onclick=()=>{ st.running=false; if(hb){clearInterval(hb);hb=null;}
  if(curVideo&&pMain){try{pMain.pauseVideo();}catch(e){}} if(pMusic){try{pMusic.pauseVideo();}catch(e){}}
  curVideo=null; $("run").style.display="none"; $("menu").style.display="flex"; renderMenu(); };
$("voiceTog").onchange=e=>{ voiceEnabled=e.target.checked; };
$("musicTog").onchange=e=>{ musicWanted=e.target.checked;
  if(!musicWanted && pMusic){ try{pMusic.pauseVideo();}catch(x){} $("musicbar").classList.remove("on"); } };
$("musicVol").oninput=e=>{ musicVol=+e.target.value; if(pMusic){ try{pMusic.setVolume(musicVol);}catch(x){} } };
$("musicToggle").onclick=()=>{ if(!pMusic) return;
  let playing=false; try{ playing = pMusic.getPlayerState()===1; }catch(e){}
  if(playing){ try{pMusic.pauseVideo();}catch(e){} $("musicToggle").textContent="Play music"; }
  else { try{pMusic.unMute(); pMusic.setVolume(musicVol); pMusic.playVideo();}catch(e){} $("musicToggle").textContent="Pause music"; } };

/* ================= editor wiring ================= */
$("editBtn").onclick=openEditor;
$("editBack").onclick=()=>{ if(ED && ED.dirty && !window.confirm("Leave without saving the changes on this device?")) return; closeEditor(); };
$("editDiscard").onclick=()=>{
  if(!ED) return;
  if(!window.confirm("Throw away the changes on this device?")) return;
  ED.routines=clone(R); ED.poolFile=clone(POOLFILE); ED.poolDirty=false; ED.dirty=false; renderEditor();
};
$("editSave").onclick=saveEdits;
$("editAddSection").onclick=edAddSection;
$("sheetClose").onclick=()=>$("sheet").classList.remove("on");
$("sheetSearch").oninput=e=>renderSheet(e.target.value);
$("newAdd").onclick=()=>{
  const nm=$("newName").value.trim(), cue=$("newCue").value.trim();
  if(!nm){ $("sheetSearch").placeholder="name the move above first"; return; }
  const id=edNewMove(nm,cue);
  edAddMove(ED.sheet.addTo,id);
  $("newName").value=""; $("newCue").value="";
  $("sheet").classList.remove("on");
};

/* ================= boot ================= */
/* Three copies of the routines can exist: the one baked into this page by the last successful
   build, the one GitHub serves right now, and the one this device saved minutes ago. They are
   compared by the `updated` stamp the editor writes — GitHub's copy is adopted only when it is
   strictly newer than the built one, so a slow CDN can never show an older routine. */
async function boot(){
  const bakedStamp=stampOf(DATA.routines);
  let routines=DATA.routines, poolFile=DATA.poolFile, stamp=bakedStamp, note=null, problem=null;
  try{
    const live=await loadLive();
    const liveStamp=stampOf(live.routines);
    if(liveStamp>bakedStamp){
      routines=live.routines; poolFile=live.poolFile; stamp=liveStamp;
      note="Live from GitHub · "+(poolFile.moves||[]).length+" moves.";
    } else if(liveStamp<bakedStamp){
      note="GitHub is serving an older copy than this build — running the built one.";
    } else if(liveStamp>0){
      note="Live from GitHub · "+(live.poolFile.moves||[]).length+" moves.";
    } else {
      note="Working from the copy stored in this page.";
    }
  }catch(e){ problem=e.message; }

  const saved=readSaved();
  if(saved && saved.at>stamp){
    routines=saved.routines; poolFile=saved.poolFile; stamp=saved.at;
    note="Showing the edit saved from this device — GitHub may still be catching up.";
  } else if(saved) clearSaved();

  applyData(routines, poolFile);
  if(!note)
    note = navigator.onLine===false ? "Offline — using the copy stored in this page."
         : (problem ? "GitHub is not serving usable data ("+problem+") — using the copy stored in this page."
                    : "Working from the copy stored in this page.");
  const TODAY=new Date().getDay();                      // 0 Sun .. 6 Sat
  selId=(R.days[(TODAY+6)%7] || R.days[0]).id;           // Monday-first week
  $("liveStatus").textContent=note;
  renderMenu();
}
boot();
if(!ytReady){ setTimeout(()=>{ if(window.YT && window.YT.Player) window.onYouTubeIframeAPIReady(); },1200); }
setInterval(()=>{ if(!pMain && window.YT && window.YT.Player) window.onYouTubeIframeAPIReady(); }, 1500);
</script>
</body>
</html>
"""


if __name__ == "__main__":
    sys.exit(build())
