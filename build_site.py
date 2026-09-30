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


def main_cost(m):
    """Rounds + breaks, minus the rest the timeline drops after the very last move."""
    per = sum(x["work"] + x["rest"] for x in m["moves"])
    return per * m["rounds"] + m["rest_between_rounds"] * (m["rounds"] - 1) - m["moves"][-1]["rest"]


def blocks(day):
    return {
        "Warm-Up": sum(m["work"] + m["rest"] for m in R["warmup"]["moves"]),
        "Sun Salutations": SUN["nominal"] + TAIL,
        day["main"]["label"]: main_cost(day["main"]),
        "Cool-Down": sum(m["work"] + m["rest"] for m in R["cooldown"]["moves"]),
        "Settle": SETTLE["nominal"] + TAIL,
    }


def audit():
    """Report only. Timing is nominal by design; warn if a day drifts far."""
    warnings = []
    print(f"{'day':<4} {'warm':>6} {'sun':>6} {'main':>6} {'cool':>6} {'settle':>7} "
          f"{'trans':>6} {'TOTAL':>7} {'vs 60:00':>9}")
    for d in R["days"]:
        b = blocks(d)
        tot = sum(b.values()) + TR_SECONDS
        if abs(tot - HOUR) > 420:
            warnings.append(f"{d['id']}: total {tot}s is more than 7 minutes off an hour")
        print(f"{d['id']:<4} " + " ".join(f"{v//60}:{v%60:02d}".rjust(6) for v in list(b.values())[:-1])
              + f" {b['Settle']//60}:{b['Settle']%60:02d}".rjust(8)
              + f" {TR_SECONDS}s".rjust(6)
              + f" {tot//60}:{tot%60:02d}".rjust(7) + f" {tot-HOUR:+5d}s".rjust(9))
    return warnings


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
        "routines": R,
        "webhook": webhook,
        "thread": REVIEW_THREAD,
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
  /* ---------- routine moves ---------- */
  #routine{margin-top:clamp(10px,2vh,26px)}
  .rsec{margin-bottom:clamp(10px,1.6vh,20px)}
  .rhead{display:flex;justify-content:space-between;align-items:baseline;gap:10px;
         border-bottom:1px solid var(--line);padding-bottom:6px;margin-bottom:4px}
  .rhead b{font-size:clamp(13px,1.8vh,19px);font-weight:700}
  .rhead em{font-style:normal;color:var(--dim);font-size:.84em;white-space:nowrap}
  .rmv{display:grid;grid-template-columns:clamp(46px,6vh,72px) 1fr;gap:clamp(8px,1.2vw,16px);
       padding:clamp(5px,.9vh,11px) 0;border-bottom:1px solid #1a2231;align-items:start}
  .rmv:last-child{border-bottom:0}
  .rmv svg{width:100%;height:auto;display:block}
  .rmv .nm{font-weight:700;font-size:clamp(14px,1.9vh,21px)}
  .rmv .nm u{text-decoration:none;color:var(--dim);font-weight:600;font-size:.8em;
             margin-left:.6em;font-variant-numeric:tabular-nums;white-space:nowrap}
  .rmv .cue{color:#b9c4d4;font-size:clamp(12px,1.55vh,17px);margin-top:2px}
  .rmv .links{margin-top:5px;display:flex;gap:14px;flex-wrap:wrap;align-items:baseline}
  .rmv .links a{font-size:clamp(11px,1.45vh,15px);text-decoration:none;white-space:nowrap}
  .rmv a.demo{color:var(--work)}
  .rnote{color:var(--dim);font-size:clamp(11px,1.5vh,16px);text-align:center;
         padding:clamp(4px,.7vh,9px) 0}
  .rtitle{font-size:clamp(16px,2.3vh,26px);font-weight:800;margin:0 0 2px}
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
  #runfig{display:none;margin:clamp(2px,.8vh,12px) auto 0;width:clamp(92px,15vh,190px);opacity:.95}
  #runfig svg{width:100%;height:auto;display:block}
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
    <div class="rtitle" style="margin-top:clamp(10px,2vh,24px)">The moves <span class="sub" style="margin:0">— every move in the selected routine, in order</span></div>
    <div id="routine"></div>
    <div class="cols">
      <div><div class="sub" style="margin:0 0 4px">Today's hour</div><div id="blocks"></div></div>
      <div><div class="sub" style="margin:0 0 4px">Move pool</div><div id="poolInfo"></div></div>
    </div>
    <div class="foot">
      <button class="primary" id="startBtn">Start</button>
      <label class="tog"><input type="checkbox" id="voiceTog"> spoken move names</label>
      <label class="tog"><input type="checkbox" id="musicTog" checked> music between videos</label>
      <button id="histBtn">Reviews</button>
    </div>
    <div id="vstatus"></div>
  </div>

  <!-- ============ RUN ============ -->
  <div id="run">
    <div id="bar"></div>
    <div class="topline"><div id="blockName">&nbsp;</div><div id="hourClock">&nbsp;</div></div>
    <div id="stage">
      <div id="clock">0:00</div>
      <div id="runfig"></div>
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

  <div id="musicHost"><div id="vpMusic"></div></div>
</div>

<script>
const DATA = __DATA__;
const POOL = DATA.pool, R = DATA.routines, HOUR = R.hour_seconds, TAIL = R.video_tail;
const SUN = R.sun, SETTLE = R.settle, TR = R.transitions, MUSIC = R.music, WARM = R.warmup, COOL = R.cooldown;
const TR_SECONDS = (TR.after_sun||0) + (TR.before_cooldown||0);
const WEBHOOK = DATA.webhook, THREAD = DATA.thread;
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
function mainCost(m){
  const per = sumMoves(m.moves);
  return per*m.rounds + m.rest_between_rounds*(m.rounds-1) - m.moves[m.moves.length-1].rest;
}
function plan(day){
  const sun    = (durs.sun    || SUN.nominal) + TAIL;
  const settle = (durs.settle || SETTLE.nominal) + TAIL;
  const warm = sumMoves(WARM.moves), cool = sumMoves(COOL.moves), main = mainCost(day.main);
  return {warm, sun, main, cool, settle, tr:TR_SECONDS,
          total: warm+sun+main+cool+settle+TR_SECONDS};
}
function buildTimeline(day){
  const p = plan(day), steps=[];
  const V = (name,label,sub,cue,dur,which) => steps.push({block:name,kind:"meditation",label,sub,cue,dur,video:which,round:1,rounds:1});

  WARM.moves.forEach((x,i)=>{
    const mv=POOL[x.ref], nx = WARM.moves[i+1] ? POOL[WARM.moves[i+1].ref].name : "the sun salutation class";
    steps.push({block:"Warm-Up", kind:"work", label:mv.name, cue:mv.cue, dur:x.work, fig:mv.fig,
                round:1, rounds:1, idx:i+1, count:WARM.moves.length, next:nx, music:true});
    if(x.rest>0) steps.push({block:"Warm-Up", kind:"rest", label:"Change over", cue:"",
                dur:x.rest, round:1, rounds:1, idx:i+1, count:WARM.moves.length, next:nx, music:true});
  });

  steps.push({block:"Sun Salutations", kind:"yoga", label:SUN.title, sub:SUN.channel,
              cue:"Follow along. Match your breath to hers — no timer, just rhythm.",
              dur:p.sun, video:"sun", round:1, rounds:1});

  if(TR.after_sun>0)
    steps.push({block:"Transition", kind:"rest", label:"Transition",
                cue:"Shake out the sun salutations. "+TR.after_sun+" seconds, then the main routine.",
                dur:TR.after_sun, round:1, rounds:1, music:true});

  const m = day.main;
  for(let r=1;r<=m.rounds;r++){
    m.moves.forEach((x,i)=>{
      const mv=POOL[x.ref], last=(r===m.rounds && i===m.moves.length-1);
      const nx = m.moves[i+1] ? POOL[m.moves[i+1].ref].name : (r<m.rounds ? "Round "+(r+1) : "Cool-down");
      steps.push({block:m.label, kind:"work", label:mv.name, cue:mv.cue, dur:x.work, fig:mv.fig,
                  round:r, rounds:m.rounds, idx:i+1, count:m.moves.length, next:nx, music:true});
      if(x.rest>0 && !last) steps.push({block:m.label, kind:"rest", label:"Rest", cue:"Breathe.",
                  dur:x.rest, round:r, rounds:m.rounds, idx:i+1, count:m.moves.length,
                  next: nx, music:true});
    });
    if(m.rest_between_rounds>0 && r<m.rounds)
      steps.push({block:m.label, kind:"rest", label:"Round "+r+" done", cue:"Shake it out, then go again.",
                  dur:m.rest_between_rounds, round:r, rounds:m.rounds, idx:m.moves.length, count:m.moves.length,
                  next:"Round "+(r+1)+" · "+POOL[m.moves[0].ref].name, music:true});
  }

  if(TR.before_cooldown>0)
    steps.push({block:"Transition", kind:"rest", label:"Transition",
                cue:"Catch your breath. "+TR.before_cooldown+" seconds, then the cool-down.",
                dur:TR.before_cooldown, round:1, rounds:1, music:true});

  COOL.moves.forEach((x,i)=>{
    const mv=POOL[x.ref];
    steps.push({block:"Cool-Down", kind:"stretch", label:mv.name, cue:mv.cue, dur:x.work+x.rest, fig:mv.fig,
                round:1, rounds:1, idx:i+1, count:COOL.moves.length,
                next: COOL.moves[i+1] ? POOL[COOL.moves[i+1].ref].name : "the closing meditation", music:true});
  });

  V("Settle", SETTLE.title, SETTLE.channel, "Same closing meditation every day. Sit down, close your eyes, follow the voice.", p.settle, "settle");
  return steps;
}

/* ================= move pictograms ================= */
/* Own schematic artwork. Each pool move carries [pose, motion, anchor] — a stick figure in
   the move's body position, with the arrow drawn at the joint that actually travels (head,
   arms, torso, hips, legs, feet). It shows POSITION and DIRECTION, not fine form: the cue
   text and the demo link on each row carry the detail. */
const POSES = {
  standing: { art:"<circle cx='24' cy='9' r='3.7'/><path d='M24 13.5V27M24 16.5L17.5 24M24 16.5L30.5 24M24 27L19.5 39.5M24 27L28.5 39.5'/>",
              at:{head:[24,9],shoulders:[24,15],torso:[24,21],arms:[30.5,23],hips:[24,27],legs:[26,33],feet:[26,39]}, lane:41 },
  seated:   { art:"<circle cx='17' cy='11' r='3.6'/><path d='M17 15V25M17 25H30M30 25V36.5M30 36.5H34M17 18L24 23'/><path d='M12 27.5H33' stroke-dasharray='2 3.2' opacity='.5'/>",
              at:{head:[17,11],shoulders:[17,16],torso:[17,21],arms:[24,23],hips:[17,25],legs:[26,25],feet:[32,36]}, lane:47 },
  allfours: { art:"<circle cx='12' cy='15.5' r='3.4'/><path d='M15.5 17.5H31M17 18V31M28 18V31M30.5 18L37.5 24M37.5 24V32'/>",
              at:{head:[12,15.5],shoulders:[17,18],torso:[24,18],arms:[17,25],hips:[30.5,18.5],legs:[34,22],feet:[37.5,31]}, lane:49 },
  plank:    { art:"<circle cx='11' cy='15' r='3.4'/><path d='M13.5 17L39 24M16 18V31M22 19.5V32M39 24L43.5 30'/>",
              at:{head:[11,15],shoulders:[16.5,18],torso:[25,20],arms:[16,25],hips:[31.5,21],legs:[36,23],feet:[41.5,27]}, lane:51 },
  v:        { art:"<circle cx='12' cy='30' r='3.4'/><path d='M15 28L24 20L30.5 17.5M15 28L13 36.5M24 20L34 27M34 27L40.5 36.5M30.5 17.5L36 25'/>",
              at:{head:[12,30],shoulders:[16.5,26],torso:[24,20],arms:[14,32],hips:[30.5,17.5],legs:[35,26],feet:[40.5,36]}, lane:49 },
  floor:    { art:"<circle cx='16' cy='28' r='3.4'/><path d='M20.5 27L25 25L34 31.5M20.5 27L11 29M34 31.5L38.5 36'/>",
              at:{head:[16,28],shoulders:[21,26],torso:[27,28],arms:[15,28.5],hips:[34,31.5],legs:[36.5,34],feet:[38.5,36]}, lane:47 },
  supine:   { art:"<circle cx='10' cy='30' r='3.4'/><path d='M13.5 31H29M29 31L38.5 25M29 31L38.5 35.5M15.5 31L17.5 24M29 31L32 24.5'/>",
              at:{head:[10,30],shoulders:[15.5,31],torso:[21,31],arms:[16.5,24.5],hips:[29,31],legs:[35,29],feet:[42,31]}, lane:49 },
  prone:    { art:"<circle cx='11' cy='29' r='3.4'/><path d='M14.5 31H31M31 31H42M13 30L6 26M13 32L6 35'/>",
              at:{head:[11,29],shoulders:[15.5,31],torso:[22,31],arms:[9,30],hips:[31,31],legs:[36,31],feet:[42,31]}, lane:49 },
};
const ARROW = "#7ee0a8";
function headAt(x,y,dx,dy){ const n=Math.hypot(dx,dy)||1; dx/=n; dy/=n; const p=6.5,o=3.1;
  return "<path d='M"+x.toFixed(1)+" "+y.toFixed(1)+"L"+(x-dx*p+dy*o).toFixed(1)+" "+(y-dy*p-dx*o).toFixed(1)
       + "M"+x.toFixed(1)+" "+y.toFixed(1)+"L"+(x-dx*p-dy*o).toFixed(1)+" "+(y-dy*p+dx*o).toFixed(1)+"'/>"; }
function arrowSVG(motion, a, lane){
  /* Arrows live in a clear lane to the right of the figure, at the height of the joint
     that moves, joined to it by a faint connector — so nothing is drawn over the body. */
  const x = lane, yc = Math.max(10, Math.min(38, a[1]));
  const go = { up:[0,-1], down:[0,1], out:[1,0], in:[-1,0], fwd:[0.76,-0.65], back:[-0.76,0.65] }[motion];
  let body = "<path d='M"+a[0]+" "+a[1]+"L"+x+" "+yc+"' opacity='.45'/>";
  if(go){
    let x1,y1,x2,y2;
    if(Math.abs(go[1]) > Math.abs(go[0])){ x1=x; y1=yc - go[1]*7;  x2=x; y2=yc + go[1]*6; }
    else if(go[0] > 0){                     x1=x-1; y1=yc;          x2=x+10; y2=yc; }
    else {                                  x1=x+10; y1=yc;         x2=x-1;  y2=yc; }
    if(go[1] && go[0]){ x1=x-4; y1=yc+6; x2=x+7; y2=yc-6; if(go[1]>0){ const t=[x1,y1]; x1=x2; y1=y2; x2=t[0]; y2=t[1]; } }
    body += "<path d='M"+x1.toFixed(1)+" "+y1.toFixed(1)+"L"+x2.toFixed(1)+" "+y2.toFixed(1)+"'/>"
          + headAt(x2,y2,x2-x1,y2-y1);
  } else if(motion==="circle" || motion==="twist"){
    body += "<path d='M"+(x+5.5)+" "+yc+"a5.5 5.5 0 1 1-5 2.8'/>" + headAt(x+0.3,yc+2.8,-1,0.3);
  } else {  /* hold */
    body += "<circle cx='"+x+"' cy='"+yc+"' r='5.5'/><circle cx='"+x+"' cy='"+yc+"' r='1.4' fill='"+ARROW+"'/>";
  }
  return "<g stroke='"+ARROW+"' stroke-width='2.2' fill='none' stroke-linecap='round' stroke-linejoin='round'>"+body+"</g>";
}
function figSVG(fig, px){
  const pose = (fig && POSES[fig[0]]) ? POSES[fig[0]] : POSES.standing;
  const at = pose.at[(fig && fig[2]) || "torso"] || pose.at.torso;
  return "<svg viewBox='0 0 64 48' width='"+(px||64)+"' role='img' aria-label='"+(fig?fig.join(" "):"")+"'>"
       + "<g stroke='#cfe0ff' stroke-width='2.4' fill='none' stroke-linecap='round' stroke-linejoin='round'>"
       + pose.art + "</g>" + arrowSVG((fig && fig[1]) || "hold", at, pose.lane || 45) + "</svg>";
}
function demoURL(name){
  return "https://www.youtube.com/results?search_query="+encodeURIComponent(name+" exercise proper form");
}
function moveRow(mv, x){
  const d = x ? (x.work + (x.rest||0)) : 0;
  return "<div class='rmv'>" + figSVG(mv.fig)
    + "<div class='body'><div class='nm'>" + mv.name + (d ? "<u>" + fmt(d) + "</u>" : "") + "</div>"
    + "<div class='cue'>" + mv.cue + "</div>"
    + "<div class='links'><a class='demo' href='" + demoURL(mv.name) + "' target='_blank' rel='noopener'>▶ see it done</a>"
    + "<span class='rsum'>" + mv.pattern + " · " + mv.position + " · level " + mv.level + "</span></div>"
    + "</div></div>";
}
function rsection(title, right, rows){
  return "<div class='rsec'><div class='rhead'><b>" + title + "</b><em>" + right + "</em></div>"
       + rows.join("") + "</div>";
}
function routinePanel(day){
  const p = plan(day), m = day.main, out = [];
  out.push(rsection("Warm-Up", fmt(p.warm) + " · " + R.warmup.moves.length + " moves",
                    R.warmup.moves.map(x => moveRow(POOL[x.ref], x))));
  out.push(rsection("Sun Salutations", fmt(p.sun),
    ["<div class='rmv'>" + figSVG(["floor","up"])
     + "<div class='body'><div class='nm'>" + SUN.title + "<u>" + fmt(p.sun) + "</u></div>"
     + "<div class='cue'>" + SUN.channel + " — follow along and copy the rhythm; no timer during this block.</div>"
     + "<div class='links'><a class='demo' href='https://www.youtube.com/watch?v=" + SUN.video
     + "' target='_blank' rel='noopener'>▶ open the class</a></div></div></div>"]));
  out.push("<div class='rnote'>↓ transition · " + TR.after_sun + "s</div>");
  out.push(rsection(m.label, m.rounds + " rounds · " + m.moves.length + " moves · " + fmt(p.main),
                    m.moves.map(x => moveRow(POOL[x.ref], x))));
  out.push("<div class='rnote'>↓ transition · " + TR.before_cooldown + "s</div>");
  out.push(rsection("Cool-Down", fmt(p.cool) + " · " + COOL.moves.length + " stretches",
                    COOL.moves.map(x => moveRow(POOL[x.ref], x))));
  out.push(rsection("Closing meditation", fmt(p.settle),
    ["<div class='rmv'>" + figSVG(["seated","hold"])
     + "<div class='body'><div class='nm'>" + SETTLE.title + "<u>" + fmt(p.settle) + "</u></div>"
     + "<div class='cue'>" + SETTLE.channel + " — the same closing meditation every day.</div>"
     + "<div class='links'><a class='demo' href='https://www.youtube.com/watch?v=" + SETTLE.video
     + "' target='_blank' rel='noopener'>▶ open on YouTube</a></div></div></div>"]));
  return out.join("");
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
function descFor(name,day){
  if(name==="Settle") return SETTLE.channel+" · same every day";
  if(name==="Sun Salutations") return SUN.channel+" · follow-along class";
  if(name==="Warm-Up") return WARM.moves.length+" moves · seated to standing";
  if(name==="Cool-Down") return COOL.moves.length+" stretches";
  return day.main.rounds+" rounds · "+day.main.moves.length+" moves · "+day.main.source;
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
  const keys=["Warm-Up","Sun Salutations",day.main.label,"Cool-Down","Settle"];
  const p=plan(day);
  const vals=[p.warm,p.sun,p.main,p.cool,p.settle];
  const box2=$("blocks"); box2.innerHTML="";
  keys.forEach((k,i)=>{
    const div=document.createElement("div"); div.className="blk";
    div.innerHTML="<div><b><span class='dot' style='background:"+colorFor(k,day)+"'></span>"+k+"</b><em>"+descFor(k,day)+"</em></div><u>"+fmt(vals[i])+"</u>";
    box2.appendChild(div);
  });
  const tot=document.createElement("div"); tot.className="blk";
  tot.innerHTML="<div><b>Total</b><em>nominal, ±1½ min per block</em></div><u>"+fmt(p.total)+"</u>";
  box2.appendChild(tot);
  $("poolInfo").innerHTML = "<div class='blk'><div><b>"+Object.keys(POOL).length+" moves</b><em>tagged by pattern, position, impact, level</em></div></div>"
    + "<div class='blk'><div><b>Music</b><em>"+MUSIC.title+" · "+MUSIC.channel+"</em></div></div>"
    + "<div class='blk'><div><b>Sun class</b><em>"+SUN.title+"</em></div></div>";
  $("tagline").textContent = "One hour a day · warm-up seated to standing · sun salutation class · main routine · cool-down · closing meditation";
  $("routine").innerHTML = "<div class='sub'>"+day.day+" · "+day.focus+" — "+day.main.label
                         + " · "+fmt(p.total)+" total</div>" + routinePanel(day);
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
  const fw = $("runfig");
  if(s.fig){ fw.innerHTML = figSVG(s.fig, 190); fw.style.display = "block"; }
  else { fw.innerHTML = ""; fw.style.display = "none"; }
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

function blockKeys(day){ return ["Warm-Up","Sun Salutations",day.main.label,"Cool-Down","Settle"]; }
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
  const parts=blockKeys(day).map(k=>((SHORT[k]||"Main")+": "+(draft.blocks[k]||"-"))).join(" · ");
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

const TODAY = new Date().getDay();          // 0 Sun .. 6 Sat
selId = R.days[(TODAY+6)%7].id;             // Monday-first week
renderMenu();
if(!ytReady){ setTimeout(()=>{ if(window.YT && window.YT.Player) window.onYouTubeIframeAPIReady(); },1200); }
setInterval(()=>{ if(!pMain && window.YT && window.YT.Player) window.onYouTubeIframeAPIReady(); }, 1500);
</script>
</body>
</html>
"""


if __name__ == "__main__":
    sys.exit(build())
