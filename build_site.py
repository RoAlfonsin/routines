#!/usr/bin/env python3
"""Build the one-hour daily routine site.

Reads pool.json + routines.json, verifies every day totals exactly 60:00,
and emits a single self-contained dist/index.html.

    python3 build_site.py
"""
import json
import pathlib
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
DIST = HERE / "docs"

POOL = json.loads((HERE / "pool.json").read_text(encoding="utf-8"))
R = json.loads((HERE / "routines.json").read_text(encoding="utf-8"))
HOUR = R["hour_seconds"]

SUN = R["sun_salutation"]
SUN_ROUND = sum(p["sec"] for p in SUN["poses"])
WARM = R["warmup"]
COOL = R["cooldown"]


# ---------------------------------------------------------------- verification
def round_cost(m):
    return sum(x["work"] + x["rest"] for x in m["moves"]) + m["rest_between_rounds"]


def audit():
    """Every day must total exactly HOUR. Fails the build otherwise."""
    problems = []
    rows = []
    warm = sum(m["work"] + m["rest"] for m in WARM["moves"])
    sun_rounds = SUN["budget"] // SUN_ROUND
    sun_cost = sun_rounds * SUN_ROUND
    sun_tail = SUN["budget"] - sun_cost
    cool_raw = sum(m["work"] + m["rest"] for m in COOL["moves"])
    for d in R["days"]:
        arrive = d["arrive"]["nominal"] + 5
        settle = d["settle"]["nominal"] + 5
        m = d["main"]
        per = sum(x["work"] + x["rest"] for x in m["moves"])
        # the rest after the very last move is dropped by the timeline
        main = m["rounds"] * per + (m["rounds"] - 1) * m["rest_between_rounds"] - m["moves"][-1]["rest"]
        slack = HOUR - (arrive + warm + sun_cost + sun_tail + main + COOL["budget"] + settle)
        if slack < -45:
            problems.append(f"{d['id']}: cool-down would need {slack}s (main circuit too long for the hour)")
        cool = COOL["budget"] + slack
        rows.append((d["id"], arrive, warm, sun_cost + sun_tail, main, cool, settle,
                     arrive + warm + sun_cost + sun_tail + main + cool + settle,
                     cool_raw, round(cool / cool_raw, 2)))
    return problems, rows


def build():
    problems, rows = audit()
    if problems:
        print("BUILD FAILED — the hour does not add up:")
        for p in problems:
            print("  -", p)
        return 1

    print(f"{'day':<4} {'arrive':>6} {'warm':>5} {'sun':>4} {'main':>5} {'cool':>5} {'settle':>6} {'TOTAL':>6}  stretch")
    for r in rows:
        print(f"{r[0]:<4} {r[1]:>6} {r[2]:>5} {r[3]:>4} {r[4]:>5} {r[5]:>5} {r[6]:>6} {r[7]:>6}  {r[9]}x")

    data = {"pool": {m["id"]: m for m in POOL["moves"]}, "routines": R}
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    DIST.mkdir(exist_ok=True)
    html = TEMPLATE.replace("__DATA__", payload)
    (DIST / "index.html").write_text(html, encoding="utf-8")
    for extra in ("README.md",):
        pass
    print(f"\nwrote {DIST/'index.html'} ({len(html)//1024} KB) · {len(R['days'])} days · {len(data['pool'])} moves in the pool")
    return 0


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#0f1115">
<title>The Hour · daily routines</title>
<style>
  :root{--bg:#0f1115;--panel:#171a21;--line:#262b36;--txt:#eef1f6;--dim:#95a0b3;
        --work:#22c55e;--rest:#f59e0b;--prep:#3b82f6;--sun:#14b8a6;--med:#8b5cf6;--cool:#0ea5e9}
  *{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
  html,body{margin:0;height:100%}
  body{background:var(--bg);color:var(--txt);font:16px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
  #app{max-width:880px;margin:0 auto;padding:20px 18px 40px}
  h1{font-size:22px;margin:0 0 2px;font-weight:700}
  h2{font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:var(--dim);margin:26px 0 8px;font-weight:600}
  .sub{color:var(--dim);font-size:13px;margin-bottom:14px}
  .days{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px}
  .day{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:12px 13px;cursor:pointer;text-align:left}
  .day:hover{border-color:#3d4657}
  .day.on{border-color:var(--work);background:#16241c}
  .day b{display:block;font-size:15px}
  .day span{display:block;color:var(--dim);font-size:12px;margin-top:3px;min-height:2.2em}
  .blocks{margin-top:6px}
  .blk{display:flex;justify-content:space-between;gap:12px;padding:10px 13px;background:var(--panel);
       border:1px solid var(--line);border-radius:12px;margin-bottom:7px;align-items:baseline}
  .blk b{font-weight:600;font-size:14px}
  .blk em{font-style:normal;color:var(--dim);font-size:12px;display:block;margin-top:2px}
  .blk u{text-decoration:none;color:var(--txt);font-variant-numeric:tabular-nums;font-size:13px;white-space:nowrap}
  .dot{display:inline-block;width:9px;height:9px;border-radius:99px;margin-right:8px;vertical-align:baseline}
  button{font:inherit;color:inherit;background:var(--panel);border:1px solid var(--line);border-radius:11px;padding:10px 14px;cursor:pointer}
  button:hover{border-color:#3d4657}
  .primary{background:var(--work);border-color:transparent;color:#04220f;font-weight:700}
  .row{display:flex;gap:9px;flex-wrap:wrap;align-items:center;margin-top:17px}
  /* run */
  #run{display:none}
  #bar{display:flex;height:9px;border-radius:99px;overflow:hidden;background:var(--line);margin:16px 0 12px}
  #bar i{height:100%;transition:width .2s linear}
  .topline{display:flex;justify-content:space-between;align-items:baseline;gap:12px}
  #blockName{font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--dim)}
  #hourClock{font-variant-numeric:tabular-nums;color:var(--dim);font-size:13px}
  #clock{font-size:clamp(58px,15vw,108px);font-weight:800;line-height:1;font-variant-numeric:tabular-nums;margin:10px 0 4px}
  #moveName{font-size:clamp(19px,4.4vw,28px);font-weight:700}
  #cue{color:var(--dim);font-size:14px;margin-top:5px;min-height:2.6em}
  #meta{color:var(--dim);font-size:13px;margin-top:8px}
  #next{color:var(--dim);font-size:13px;min-height:1.4em;margin-top:2px}
  #videos{margin:14px 0}
  .vwrap{display:none}
  .vwrap.on{display:block}
  iframe{width:100%;aspect-ratio:16/9;border:0;border-radius:12px;background:#000}
  .vlink{color:var(--dim);font-size:12px;margin-top:6px}
  .vlink a{color:#7dd3fc}
  #controls{display:grid;grid-template-columns:repeat(4,1fr);gap:9px;margin-top:20px}
  #controls button{padding:13px 6px;font-size:14px}
  #pauseBtn{grid-column:span 4;font-size:16px;padding:15px}
  /* rate */
  #rate{display:none;background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:20px;margin-top:20px}
  .stars{display:flex;gap:8px;margin:10px 0 16px}
  .star{font-size:32px;cursor:pointer;color:#3d4657;line-height:1;background:none;border:0;padding:0}
  .star.on{color:#fbbf24}
  textarea{width:100%;background:#0f1115;color:var(--txt);border:1px solid var(--line);border-radius:11px;padding:10px;font:inherit;min-height:64px}
  .hist{font-size:13px;color:var(--dim)}
  .hist b{color:var(--txt)}
  .hint{color:var(--dim);font-size:12px;margin-top:8px}
  label.tog{display:flex;gap:8px;align-items:center;font-size:13px;color:var(--dim);cursor:pointer}
</style>
</head>
<body>
<div id="app">
  <div id="menu">
    <h1>The Hour</h1>
    <div class="sub">One hour a day · warm-up seated to standing · sun salutations · main routine · cool-down · seated meditation</div>
    <div class="days" id="days"></div>
    <h2>Today's hour</h2>
    <div class="blocks" id="blocks"></div>
    <div class="row">
      <button class="primary" id="startBtn" style="flex:1;padding:15px;font-size:16px">Start the hour</button>
      <label class="tog"><input type="checkbox" id="voiceTog"> spoken move names</label>
    </div>
    <div class="hint" id="vstatus"></div>
    <div id="histBox"></div>
  </div>

  <div id="run">
    <div class="topline">
      <div id="blockName">—</div>
      <div id="hourClock">0:00 / 60:00</div>
    </div>
    <div id="bar"></div>
    <div id="clock">0:00</div>
    <div id="moveName">&nbsp;</div>
    <div id="cue"></div>
    <div id="meta"></div>
    <div id="next"></div>
    <div id="videos">
      <div class="vwrap" id="wrapArrive"><div id="vpArrive"></div><div class="vlink" id="linkArrive"></div></div>
      <div class="vwrap" id="wrapSettle"><div id="vpSettle"></div><div class="vlink" id="linkSettle"></div></div>
    </div>
    <div id="controls">
      <button id="pauseBtn">Pause</button>
      <button id="backBtn">Back</button>
      <button id="skipBtn">Skip</button>
      <button id="addBtn">+10s</button>
      <button id="stopBtn">Stop</button>
    </div>
  </div>

  <div id="rate">
    <h1 id="rateTitle">How was it?</h1>
    <div class="sub" id="rateSub"></div>
    <div class="stars" id="stars"></div>
    <textarea id="note" placeholder="What worked, what didn't — anything you want changed next week?"></textarea>
    <div class="row">
      <button class="primary" id="saveRate">Save rating</button>
      <button id="copyRates">Copy all ratings</button>
      <button id="backMenu">Back to the week</button>
    </div>
    <div class="hint" id="rateHint"></div>
  </div>
</div>

<script>
const DATA = __DATA__;
const POOL = DATA.pool, R = DATA.routines, HOUR = R.hour_seconds;
const SUN = R.sun_salutation, WARM = R.warmup, COOL = R.cooldown;
const SUN_ROUND = SUN.poses.reduce((a,p)=>a+p.sec,0);
const $ = id => document.getElementById(id);
const fmt = s => { s=Math.max(0,Math.ceil(s)); return Math.floor(s/60)+":"+String(s%60).padStart(2,"0"); };
const BLOCKCOL = {meditation:"var(--med)", warmup:"var(--prep)", sun:"var(--sun)", main:"var(--work)", cooldown:"var(--cool)"};

/* ---------------- audio ---------------- */
let AC=null;
const ac = () => { if(!AC){ try{AC=new (window.AudioContext||window.webkitAudioContext)();}catch(e){} } if(AC&&AC.state==="suspended")AC.resume(); return AC; };
function beep(freq,ms,vol){
  const c=ac(); if(!c) return;
  const g=c.createGain(), o=c.createOscillator();
  o.type="sine"; o.frequency.value=freq;
  g.gain.setValueAtTime(0.0001,c.currentTime);
  g.gain.exponentialRampToValueAtTime(vol||0.18,c.currentTime+0.01);
  g.gain.exponentialRampToValueAtTime(0.0001,c.currentTime+ms/1000);
  o.connect(g).connect(c.destination); o.start(); o.stop(c.currentTime+ms/1000+0.03);
}
function double(){ beep(1046,140,0.16); setTimeout(()=>beep(1318,180,0.16),160); }
let voiceEnabled=false;
function say(t){ if(!voiceEnabled||!("speechSynthesis" in window)||!t) return;
  try{ speechSynthesis.cancel(); const u=new SpeechSynthesisUtterance(t); u.rate=1.05; speechSynthesis.speak(u);}catch(e){} }

/* ---------------- youtube ---------------- */
let ytReady=false, pArrive=null, pSettle=null, durArrive=null, durSettle=null;
window.onYouTubeIframeAPIReady = function(){
  ytReady = true;
  const day = currentDay();
  pArrive = mk("vpArrive", day.arrive.video, d => durArrive=d);
  pSettle = mk("vpSettle", day.settle.video, d => durSettle=d);
};
function mk(elId, vid, cb){
  try{
    return new YT.Player(elId,{
      videoId: vid, host:"https://www.youtube-nocookie.com",
      playerVars:{rel:0,modestbranding:1,playsinline:1},
      events:{
        onReady:e=>{ const d=e.target.getDuration(); if(d) cb(d); },
        onStateChange:e=>{ if(e.data===YT.PlayerState.CUED||e.data===YT.PlayerState.PLAYING){ const d=e.target.getDuration(); if(d) cb(d);} }
      }
    });
  }catch(e){ return null; }
}
function loadYT(){
  if(window.YT && window.YT.Player) { window.onYouTubeIframeAPIReady(); return; }
  const s=document.createElement("script"); s.src="https://www.youtube.com/iframe_api";
  s.onerror=()=>{ $("vstatus").textContent = "YouTube unavailable — meditations fall back to their nominal length and a link."; };
  document.head.appendChild(s);
}

/* ---------------- timeline ---------------- */
function roundCost(m){ return m.moves.reduce((a,x)=>a+x.work+x.rest,0)+m.rest_between_rounds; }

function buildTimeline(day){
  const steps=[];
  const arr = (durArrive || day.arrive.nominal) + 5;
  const stl = (durSettle || day.settle.nominal) + 5;
  steps.push({block:"Arrive", kind:"meditation", label:day.arrive.title, sub:day.arrive.channel,
              cue:"Sit down, settle in. Let the recording guide you.", dur:arr, video:"arrive", round:1, rounds:1});

  WARM.moves.forEach((x,i)=>{
    const mv=POOL[x.ref];
    steps.push({block:"Warm-Up", kind:"work", label:mv.name, cue:mv.cue, dur:x.work,
                round:1, rounds:1, idx:i+1, count:WARM.moves.length, next:(WARM.moves[i+1]?POOL[WARM.moves[i+1].ref].name:"Sun Salutations")});
    if(x.rest>0) steps.push({block:"Warm-Up", kind:"rest", label:"Change over", cue:"Move on when you are ready.",
                dur:x.rest, round:1, rounds:1, idx:i+1, count:WARM.moves.length,
                next:(WARM.moves[i+1]?POOL[WARM.moves[i+1].ref].name:"Sun Salutations")});
  });

  const sr = Math.floor(SUN.budget/SUN_ROUND), sunSlack = SUN.budget - sr*SUN_ROUND;
  for(let r=1;r<=sr;r++){
    SUN.poses.forEach((p,i)=>{
      steps.push({block:"Sun Salutations", kind:"sun", label:p.name, sub:p.sanskrit, cue:p.cue, dur:p.sec,
                  round:r, rounds:sr, idx:i+1, count:SUN.poses.length,
                  next:(SUN.poses[i+1]?SUN.poses[i+1].name:"Mountain Pose (next round)")});
    });
  }
  if(sunSlack>0) steps.push({block:"Sun Salutations", kind:"sun", label:"Mountain Pose", sub:"", dur:sunSlack,
                          cue:"Stand and breathe. The main routine is next.", round:sr, rounds:sr, idx:SUN.poses.length, count:SUN.poses.length, next:"Main routine"});

  const m = day.main;

  for(let r=1;r<=m.rounds;r++){
    m.moves.forEach((x,i)=>{
      const mv=POOL[x.ref], last = (r===m.rounds && i===m.moves.length-1);
      steps.push({block:m.label, kind:"work", label:mv.name, cue:mv.cue, dur:x.work,
                  round:r, rounds:m.rounds, idx:i+1, count:m.moves.length,
                  next:(m.moves[i+1]?POOL[m.moves[i+1].ref].name:(r<m.rounds?"Round "+(r+1):"Cool-down"))});
      if(x.rest>0 && !last) steps.push({block:m.label, kind:"rest", label:"Rest", cue:"Breathe. Shake it out.",
                  dur:x.rest, round:r, rounds:m.rounds, idx:i+1, count:m.moves.length,
                  next:(m.moves[i+1]?POOL[m.moves[i+1].ref].name:"Round "+(r+1))});
    });
    if(m.rest_between_rounds>0 && r<m.rounds)
      steps.push({block:m.label, kind:"rest", label:"Round "+r+" done", cue:"Shake it out, breathe, then go again.",
                  dur:m.rest_between_rounds, round:r, rounds:m.rounds, idx:m.moves.length, count:m.moves.length,
                  next:"Round "+(r+1)+" · "+POOL[m.moves[0].ref].name});
  }

  // The cool-down takes whatever is left after everything else, so the hour is exactly
  // 60:00 no matter how long the two YouTube videos actually run.
  const usedSoFar = steps.reduce((a,x)=>a+x.dur,0);
  const coolRaw = COOL.moves.reduce((a,x)=>a+x.work+x.rest,0);
  const coolDur = Math.max(45, HOUR - usedSoFar - stl);
  const scale = coolRaw ? (coolDur/coolRaw) : 1;
  let used=0;
  COOL.moves.forEach((x,i)=>{
    const mv=POOL[x.ref];
    let d = (i===COOL.moves.length-1) ? (coolDur-used) : Math.floor((x.work+x.rest)*scale);
    used += d;
    steps.push({block:"Cool-Down", kind:"stretch", label:mv.name, cue:mv.cue, dur:d,
                round:1, rounds:1, idx:i+1, count:COOL.moves.length,
                next:(COOL.moves[i+1]?POOL[COOL.moves[i+1].ref].name:"Settle")});
  });

  steps.push({block:"Settle", kind:"meditation", label:day.settle.title, sub:day.settle.channel,
              cue:"Sit down again. Close your eyes and follow the voice.", dur:stl, video:"settle", round:1, rounds:1});
  return steps;
}
function sum(moves){ return moves.reduce((a,x)=>a+x.work+x.rest,0); }

/* ---------------- menu ---------------- */
let selId = null;
function currentDay(){ return R.days.find(d=>d.id===selId) || R.days[0]; }

function breakdown(day){
  const groups=[];
  buildTimeline(day).forEach(s=>{
    const g=groups[groups.length-1];
    if(g && g.name===s.block) g.dur+=s.dur; else groups.push({name:s.block,dur:s.dur});
  });
  return groups;
}
function colorFor(day,name){
  if(name==="Arrive"||name==="Settle") return "var(--med)";
  if(name==="Warm-Up") return "var(--prep)";
  if(name==="Sun Salutations") return "var(--sun)";
  if(name==="Cool-Down") return "var(--cool)";
  return "var(--work)";
}
function blockDesc(day,name){
  if(name==="Arrive") return day.arrive.channel+" · "+fmt(day.arrive.nominal);
  if(name==="Settle") return day.settle.channel+" · "+fmt(day.settle.nominal);
  if(name==="Warm-Up") return WARM.moves.length+" moves · seated to standing";
  if(name==="Sun Salutations") return Math.floor(SUN.budget/SUN_ROUND)+" rounds · "+SUN.poses.length+" poses";
  if(name==="Cool-Down") return COOL.moves.length+" stretches · absorbs the slack";
  return day.main.rounds+" rounds · "+day.main.moves.length+" moves · "+day.main.source;
}

function renderMenu(){
  const box=$("days"); box.innerHTML="";
  R.days.forEach(d=>{
    const b=document.createElement("button");
    b.className="day"+(d.id===selId?" on":"");
    b.innerHTML="<b>"+d.day+"</b><span>"+d.focus+"<br>"+d.main.label+"</span>";
    b.onclick=()=>{ selId=d.id; renderMenu(); renderBlocks(); };
    box.appendChild(b);
  });
  renderBlocks();
}
function renderBlocks(){
  const day=currentDay(), groups=breakdown(day), box=$("blocks");
  box.innerHTML="";
  let total=0;
  groups.forEach(g=>{
    total+=g.dur;
    const div=document.createElement("div"); div.className="blk";
    div.innerHTML="<div><b><span class='dot' style='background:"+colorFor(day,g.name)+"'></span>"+g.name+"</b><em>"
                  +blockDesc(day,g.name)+"</em></div><u>"+fmt(g.dur)+"</u>";
    box.appendChild(div);
  });
  const tot=document.createElement("div"); tot.className="blk";
  const drift = total===HOUR ? "one hour exactly" : ("off by "+(HOUR-total)+"s");
  tot.innerHTML="<div><b>Total</b><em>"+drift+"</em></div><u>"+fmt(total)+"</u>";
  box.appendChild(tot);
  $("startBtn").textContent="Start "+day.day+" · "+day.main.label;
  if(durArrive){ $("vstatus").textContent="Meditation lengths read from YouTube ("+fmt(durArrive)+" and "+fmt(durSettle)+") — the cool-down absorbed the difference."; }
}

/* ---------------- runner ---------------- */
let st={steps:[],i:0,left:0,running:false,last:0,started:0,lastBeep:null};
let hb=null;

function start(){
  ac();
  st={steps:buildTimeline(currentDay()),i:0,left:0,running:true,last:performance.now(),started:Date.now(),lastBeep:null};
  st.left=st.steps[0].dur;
  $("menu").style.display="none"; $("rate").style.display="none"; $("run").style.display="block";
  paintBar(); enter(true);
  if(hb) clearInterval(hb); hb=setInterval(tick,100);
  try{ if("wakeLock" in navigator) navigator.wakeLock.request("screen").catch(()=>{}); }catch(e){}
}
function enter(first){
  const s=st.steps[st.i];
  $("blockName").textContent=s.block+(s.rounds>1?(" · round "+s.round+"/"+s.rounds):"");
  $("moveName").textContent=s.label;
  $("cue").textContent=s.cue||"";
  $("meta").textContent = s.count>1 ? ("move "+s.idx+" of "+s.count) : "";
  $("next").textContent = s.next ? ("next: "+s.next) : "";
  // videos
  $("wrapArrive").classList.toggle("on", s.video==="arrive");
  $("wrapSettle").classList.toggle("on", s.video==="settle");
  if(s.video==="arrive" && pArrive){ try{pArrive.unMute(); pArrive.setVolume(85); pArrive.playVideo();}catch(e){} }
  if(s.video==="settle" && pSettle){ try{pSettle.unMute(); pSettle.setVolume(85); pSettle.playVideo();}catch(e){} }
  if(s.video!=="arrive" && pArrive){ try{pArrive.pauseVideo();}catch(e){} }
  if(s.video!=="settle" && pSettle){ try{pSettle.pauseVideo();}catch(e){} }
  if(first || s.kind!=="rest"){
    if(s.kind==="meditation") double();
    else if(s.kind==="work") beep(880,170,0.18);
    else if(s.kind==="sun") beep(660,120,0.12);
    else if(s.kind==="stretch") beep(587,180,0.14);
  } else beep(494,150,0.14);
  say(s.kind==="rest" ? "" : s.label);
  paintBar();
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
    if(st.left<=3.2 && Math.ceil(st.left)!==st.lastBeep && (s.kind==="work"||s.kind==="rest")){
      st.lastBeep=Math.ceil(st.left); beep(740,80,0.12);
    }
  }
  render();
}
function render(){
  const s=st.steps[st.i];
  $("clock").textContent=fmt(st.left);
  const done=st.steps.slice(0,st.i).reduce((a,x)=>a+x.dur,0)+ (s.dur-Math.max(0,st.left));
  $("hourClock").textContent=fmt(done)+" / "+fmt(HOUR);
  $("pauseBtn").textContent=st.running?"Pause":"Resume";
  paintCursor(done);
}
function paintBar(){
  const bar=$("bar"); bar.innerHTML="";
  const groups=[];
  st.steps.forEach(s=>{
    const g=groups[groups.length-1];
    if(g && g.name===s.block) g.dur+=s.dur; else groups.push({name:s.block,dur:s.dur,kind:s.kind});
  });
  groups.forEach(g=>{
    const el=document.createElement("i");
    el.style.width=(g.dur/HOUR*100)+"%";
    el.style.background=BLOCKCOL[g.kind]||"var(--line)";
    el.style.opacity="0.35";
    el.title=g.name;
    bar.appendChild(el);
  });
}
function paintCursor(done){
  const segs=[...document.querySelectorAll("#bar i")];
  const groups=[]; st.steps.forEach(s=>{ const g=groups[groups.length-1]; if(g&&g.name===s.block)g.dur+=s.dur; else groups.push({name:s.block,dur:s.dur}); });
  let acc=0;
  groups.forEach((g,k)=>{
    const full = (done>=acc+g.dur) ? 1 : (done<=acc ? 0 : (done-acc)/g.dur);
    if(segs[k]) segs[k].style.opacity=(0.35+0.65*full).toFixed(2);
    acc+=g.dur;
  });
}
function finish(){
  st.running=false; if(hb){clearInterval(hb);hb=null;}
  double(); setTimeout(double,400);
  try{pArrive&&pArrive.pauseVideo();}catch(e){}
  try{pSettle&&pSettle.pauseVideo();}catch(e){}
  $("run").style.display="none"; showRate();
}

/* ---------------- rating ---------------- */
const RKEY="fitness.ratings.v1";
const loadRates=()=>{ try{return JSON.parse(localStorage.getItem(RKEY))||[];}catch(e){return [];} };
const saveRates=a=>{ try{localStorage.setItem(RKEY,JSON.stringify(a));}catch(e){} };
const today=()=>new Date().toISOString().slice(0,10);
let pending={stars:0};

function showRate(){
  const day=currentDay();
  $("rate").style.display="block";
  $("rateTitle").textContent="How was "+day.day+"?";
  $("rateSub").textContent=day.focus+" · "+day.main.label;
  const box=$("stars"); box.innerHTML="";
  for(let i=1;i<=5;i++){
    const b=document.createElement("button"); b.className="star"+(pending.stars>=i?" on":""); b.textContent="★";
    b.onclick=()=>{ pending.stars=i; showRate(); };
    box.appendChild(b);
  }
  $("note").value=pending.note||"";
  const hist=loadRates().slice(-14).reverse();
  $("rateHint").innerHTML = hist.length ? ("<div class='hist' style='margin-top:14px'>"+hist.map(h=>
      "<div><b>"+h.date+"</b> "+h.day+" · "+"★".repeat(h.stars)+"☆".repeat(5-h.stars)+(h.note?(" — "+h.note):"")+"</div>").join("")+"</div>") : "";
}
$("saveRate").onclick=()=>{
  if(!pending.stars){ $("rateHint").textContent="Pick a star rating first."; return; }
  const a=loadRates();
  a.push({date:today(),day:currentDay().day,id:selId,stars:pending.stars,note:$("note").value.trim()});
  saveRates(a);
  $("rateHint").textContent="Saved on this device. Use “Copy all ratings” and paste them to Hermes to retune the week.";
  pending={stars:0};
};
$("copyRates").onclick=async()=>{
  const txt=JSON.stringify(loadRates());
  try{ await navigator.clipboard.writeText(txt); $("rateHint").textContent="Ratings copied — paste them into the chat."; }
  catch(e){ $("rateHint").textContent=txt; }
};
$("backMenu").onclick=()=>{ $("rate").style.display="none"; $("menu").style.display="block"; renderBlocks(); };

/* ---------------- controls ---------------- */
$("startBtn").onclick=start;
$("pauseBtn").onclick=()=>{ st.running=!st.running; st.last=performance.now(); };
$("skipBtn").onclick=()=>{ st.left=0.001; };
$("backBtn").onclick=()=>{ if(st.i>0){ st.i--; st.left=st.steps[st.i].dur; st.last=performance.now(); enter(true); } };
$("addBtn").onclick=()=>{ st.left+=10; };
$("stopBtn").onclick=()=>{ st.running=false; if(hb){clearInterval(hb);hb=null;}
  try{pArrive&&pArrive.pauseVideo();}catch(e){} try{pSettle&&pSettle.pauseVideo();}catch(e){}
  $("run").style.display="none"; $("menu").style.display="block"; };
$("voiceTog").onchange=e=>{ voiceEnabled=e.target.checked; if(voiceEnabled) say("Voice on"); };

selId = R.days[new Date().getDay()===0?6:new Date().getDay()-1].id;
renderMenu();
loadYT();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    sys.exit(build())
