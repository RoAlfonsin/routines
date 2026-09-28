#!/usr/bin/env python3
"""Build a self-contained interval timer HTML from routines.json.

Usage:
    python3 build_timer.py            # writes timer.html next to routines.json
    python3 build_timer.py out.html

The output is one file with routine data embedded, no network needed.
Open it from the phone's local storage (Chrome) and add to home screen.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE / "routines.json"
OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "timer.html"

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0f1115">
<title>Interval Timer</title>
<style>
  :root{
    --bg:#0f1115; --panel:#171a21; --line:#262b36; --txt:#eef1f6; --dim:#95a0b3;
    --work:#22c55e; --rest:#f59e0b; --prep:#3b82f6; --round:#a855f7;
  }
  *{box-sizing:border-box; -webkit-tap-highlight-color:transparent}
  html,body{margin:0;height:100%}
  body{background:var(--bg);color:var(--txt);font:16px/1.4 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;overflow:hidden}
  #app{display:flex;flex-direction:column;height:100dvh;padding:env(safe-area-inset-top) 14px env(safe-area-inset-bottom)}
  header{display:flex;align-items:center;gap:10px;padding:12px 2px}
  header h1{font-size:15px;margin:0;font-weight:600;letter-spacing:.02em;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .pill{font-size:12px;color:var(--dim);border:1px solid var(--line);border-radius:999px;padding:4px 10px}
  select,button{font:inherit;color:inherit;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:10px 12px}
  select{width:100%}
  .hint{font-size:12px;color:var(--dim);margin:8px 2px 0;min-height:2.6em}
  .list{flex:1;overflow:auto;margin-top:8px}
  .row{display:flex;justify-content:space-between;gap:10px;padding:11px 12px;border:1px solid var(--line);border-radius:12px;background:var(--panel);margin-bottom:8px;align-items:baseline}
  .row b{font-weight:600}
  .row span{color:var(--dim);font-size:13px;text-align:right}
  .primary{background:var(--work);border-color:transparent;color:#04220f;font-weight:700;width:100%;padding:16px;border-radius:14px}
  /* ---- run view ---- */
  #run{display:none;flex-direction:column;height:100%}
  #phasebar{height:6px;border-radius:99px;background:var(--line);overflow:hidden;margin:10px 0 0}
  #phasefill{height:100%;width:0;background:var(--work);transition:width .18s linear}
  #runMain{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px;text-align:center}
  #phaseName{font-size:13px;letter-spacing:.18em;text-transform:uppercase;color:var(--dim)}
  #clock{font-size:clamp(64px,26vw,150px);font-weight:800;line-height:.95;font-variant-numeric:tabular-nums}
  #moveName{font-size:clamp(22px,7vw,34px);font-weight:700}
  #note{color:var(--dim);font-size:13px;max-width:34em;min-height:2.4em}
  #meta{color:var(--dim);font-size:13px}
  #next{font-size:13px;color:var(--dim);min-height:1.4em}
  #totals{display:flex;gap:14px;justify-content:center;color:var(--dim);font-size:12px;padding-bottom:6px}
  .controls{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;padding:10px 0}
  .controls button{padding:14px 6px;font-size:14px}
  #startBtn{grid-column:span 4;background:var(--work);border-color:transparent;color:#04220f;font-weight:700;font-size:17px}
  .done #clock{color:var(--work)}
</style>
</head>
<body>
<div id="app">

  <div id="menu">
    <header>
      <h1>Interval Timer</h1>
      <span class="pill" id="libCount"></span>
    </header>
    <select id="picker"></select>
    <div class="hint" id="descr"></div>
    <div class="list" id="list"></div>
    <button class="primary" id="begin">Start</button>
  </div>

  <div id="run">
    <div id="phasebar"><div id="phasefill"></div></div>
    <div id="runMain">
      <div id="phaseName">ready</div>
      <div id="clock">0:00</div>
      <div id="moveName">&nbsp;</div>
      <div id="note"></div>
      <div id="meta"></div>
      <div id="next"></div>
    </div>
    <div id="totals"></div>
    <div class="controls">
      <button id="startPause">Pause</button>
      <button id="back">Back</button>
      <button id="skip">Skip</button>
      <button id="addTime">+10s</button>
      <button id="quit">Stop &amp; pick another</button>
    </div>
  </div>

</div>
<script>
const LIB = __ROUTINES_JSON__;

/* ---------- audio ---------- */
let AC = null;
function ac(){ if(!AC){ try{ AC = new (window.AudioContext||window.webkitAudioContext)(); }catch(e){} } if(AC && AC.state==="suspended") AC.resume(); return AC; }
function beep(freq, ms, gain){
  const c = ac(); if(!c || cur.tone === "none") return;
  const g = c.createGain(); const o = c.createOscillator();
  o.type = "sine"; o.frequency.value = freq;
  const vol = (cur.tone === "soft" ? 0.08 : 0.22) * (gain || 1);
  g.gain.setValueAtTime(0.0001, c.currentTime);
  g.gain.exponentialRampToValueAtTime(vol, c.currentTime + 0.01);
  g.gain.exponentialRampToValueAtTime(0.0001, c.currentTime + ms/1000);
  o.connect(g).connect(c.destination); o.start(); o.stop(c.currentTime + ms/1000 + 0.02);
}
function say(text){
  if(!cur.voice || !("speechSynthesis" in window) || !text) return;
  try{
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 1.05; u.volume = 0.9;
    speechSynthesis.speak(u);
  }catch(e){}
}

/* ---------- state ---------- */
const empty = { steps:[], i:0, left:0, running:false, prepared:false, tone:"loud", voice:true };
let cur = { id:null, name:"", rounds:0, rest_between_rounds:0, tone:"loud", voice:true, countdown_beeps:true, moves:[] };
let st = Object.assign({}, empty);
let lastTick = 0, hb = null, wakeLock = null;

const $ = id => document.getElementById(id);
const fmt = s => { s = Math.max(0, Math.ceil(s)); const m = Math.floor(s/60); const r = s%60; return m + ":" + String(r).padStart(2,"0"); };
const human = s => { s = Math.round(s); const m = Math.floor(s/60); return m ? m+"m "+(s%60 ? (s%60)+"s" : "") : s+"s"; };

function buildTimeline(r){
  const out = [];
  if(r.prepare) out.push({ kind:"prepare", label:"Get ready", dur:r.prepare, move:(r.moves[0]||{}).name });
  const n = r.moves.length;
  for(let round=1; round<=r.rounds; round++){
    r.moves.forEach((m, idx) => {
      out.push({ kind:"work", label:m.name, note:m.note||"", dur:m.work, round, roundCount:r.rounds, moveIndex:idx+1, moveCount:n,
                 next: (idx+1 < n) ? m2rest(r.moves[idx+1]) : (round < r.rounds && r.rest_between_rounds ? "Round " + (round+1) : null) });
      if(m.rest > 0 && !(round === r.rounds && idx === n-1))
        out.push({ kind:"rest", label:"Rest", note:"", dur:m.rest, round, roundCount:r.rounds, moveIndex:idx+1, moveCount:n,
                   next: (idx+1 < n) ? r.moves[idx+1].name : (round < r.rounds && r.rest_between_rounds ? "Round " + (round+1) : null) });
    });
    if(r.rest_between_rounds && round < r.rounds)
      out.push({ kind:"roundrest", label:"Round " + round + " done", note:"Shake it out.", dur:r.rest_between_rounds, round, roundCount:r.rounds,
                 moveIndex:n, moveCount:n, next: r.moves[0].name });
  }
  out.push({ kind:"done", label:"Finished", note:"Nice work.", dur:0, round:r.rounds, roundCount:r.rounds, moveIndex:n, moveCount:n });
  return out;
}
function m2rest(m){ return m.name; } // name of the move you rest *into*

function totalSeconds(r){
  let t = r.prepare || 0;
  const n = r.moves.length;
  for(let round=1; round<=r.rounds; round++){
    r.moves.forEach((m, idx) => {
      t += m.work;
      if(m.rest > 0 && !(round === r.rounds && idx === n-1)) t += m.rest;
    });
    if(r.rest_between_rounds && round < r.rounds) t += r.rest_between_rounds;
  }
  return t;
}

/* ---------- menu ---------- */
function menu(){
  const p = $("picker"); p.innerHTML = "";
  LIB.routines.forEach(r => { const o = document.createElement("option"); o.value = r.id; o.textContent = r.name; p.appendChild(o); });
  if(cur.id) p.value = cur.id;
  $("libCount").textContent = LIB.routines.length + " routines";
  p.onchange = () => load(p.value);
  load(p.value);
}
function load(id){
  cur = LIB.routines.find(r => r.id === id) || LIB.routines[0];
  const t = totalSeconds(cur);
  $("descr").textContent = (cur.note || "") + "  Total " + human(t) + " · " + cur.rounds + (cur.rounds > 1 ? " rounds" : " round") + " · " + cur.moves.length + " moves.";
  const box = $("list"); box.innerHTML = "";
  cur.moves.forEach((m, i) => {
    const d = document.createElement("div"); d.className = "row";
    d.innerHTML = "<b>" + (i+1) + ". " + m.name + "</b><span>" + fmt(m.work) + (m.rest ? " / " + m.rest + "s rest" : "") + "</span>";
    box.appendChild(d);
  });
}

/* ---------- run ---------- */
function startRun(){
  ac(); // unlock audio on the user gesture
  st = Object.assign({}, empty, { steps: buildTimeline(cur), i: 0, left: cur.prepare || cur.moves[0].work, running: true, tone: cur.tone, voice: cur.voice });
  if(!cur.prepare) st.left = cur.moves[0] ? cur.moves[0].work : 0;
  $("menu").style.display = "none"; $("run").style.display = "flex";
  requestWakeLock();
  lastTick = performance.now();
  enterStep(true);
  render();
  if(hb) clearInterval(hb);
  hb = setInterval(tick, 100);   // wall-clock driven: keeps working when the tab is not composited
}
function requestWakeLock(){
  try{ if("wakeLock" in navigator) navigator.wakeLock.request("screen").then(l => wakeLock = l).catch(()=>{}); }catch(e){}
}
function current(){ return st.steps[st.i] || st.steps[st.steps.length-1]; }

function enterStep(first){
  const s = current();
  document.body.classList.toggle("done", s.kind === "done");
  const col = { prepare:"var(--prep)", work:"var(--work)", rest:"var(--rest)", roundrest:"var(--round)", done:"var(--work)" }[s.kind];
  $("phasefill").style.background = col;
  $("clock").style.color = s.kind === "done" ? "var(--work)" : "var(--txt)";
  $("phaseName").textContent = s.kind === "prepare" ? "get ready" : (s.kind === "rest" ? "rest" : (s.kind === "roundrest" ? "round break" : (s.kind === "done" ? "session complete" : "work")));
  $("moveName").textContent = s.kind === "done" ? "Finished" : s.label;
  $("note").textContent = s.note || "";
  $("meta").textContent = s.kind === "done" ? "" : (s.roundCount > 1 ? "Round " + s.round + " / " + s.roundCount + "  ·  Move " + s.moveIndex + " / " + s.moveCount : "");
  $("next").textContent = s.next ? "Next: " + s.next : "";
  if(s.kind !== "done"){
    if(first && s.kind === "prepare") say("Get ready");
    else if(s.kind === "work") say(s.label);
    if(s.kind !== "prepare") beep(s.kind === "work" ? 880 : 500, 220);
  }
}
function advance(){
  if(st.i >= st.steps.length - 1){ st.running = false; return; }
  st.i++; const s = current();
  const prev = st.steps[st.i-1];
  // hold rest between the last move and a round break? no: just enter
  st.left = s.dur;
  enterStep(false);
  if(s.kind === "done"){ say("Done"); beep(1046, 600); releaseWakeLock(); }
}
function releaseWakeLock(){ try{ if(wakeLock){ wakeLock.release(); wakeLock = null; } }catch(e){} }

function tick(){
  const now = performance.now();
  const dt = Math.min(5, (now - lastTick) / 1000); lastTick = now;
  const s = current();
  if(st.running && s.kind !== "done"){
    st.left -= dt;
    if(st.left <= 0){ advance(); return; }
    if(cur.countdown_beeps && st.left <= 3.2 && Math.ceil(st.left) !== st.lastBeep){
      st.lastBeep = Math.ceil(st.left);
      if(s.kind === "work" || s.kind === "rest" || s.kind === "roundrest") beep(660, 90, 0.6);
    }
  }
  render();
}
function render(){
  const s = current();
  $("clock").textContent = s.kind === "done" ? fmt(0) : fmt(st.left);
  const frac = s.dur ? (1 - Math.max(0, st.left) / s.dur) : 1;
  $("phasefill").style.width = (frac * 100).toFixed(1) + "%";
  $("startPause").textContent = (s.kind === "done") ? "Restart" : (st.running ? "Pause" : "Resume");
  let elapsed = 0;
  for(let k = 0; k < st.i; k++) elapsed += st.steps[k].dur;
  elapsed += Math.max(0, s.dur - st.left);
  $("totals").textContent = "Elapsed " + fmt(elapsed) + "  ·  Remaining " + fmt(Math.max(0, totalSeconds(cur) - elapsed));
}

function togglePause(){
  const s = current();
  if(s.kind === "done"){ startRun(); return; }
  st.running = !st.running; lastTick = performance.now();
  if(st.running) requestWakeLock(); else say("");
}

/* ---------- controls ---------- */
$("begin").onclick = startRun;
$("startPause").onclick = togglePause;
$("skip").onclick = () => { const s = current(); if(s.kind === "done"){ startRun(); return; } st.left = 0.001; };
$("back").onclick = () => { if(st.i > 0){ st.i--; st.left = current().dur; lastTick = performance.now(); enterStep(true); } };
$("addTime").onclick = () => { st.left += 10; };
$("quit").onclick = () => { st.running = false; releaseWakeLock(); try{speechSynthesis.cancel();}catch(e){}
  $("run").style.display = "none"; $("menu").style.display = "block"; st = Object.assign({}, empty);
  if(hb){ clearInterval(hb); hb = null; } };

// returning to the tab must not fast-forward the clock
document.addEventListener("visibilitychange", () => { lastTick = performance.now(); });

menu();
</script>
</body>
</html>
"""


def main():
    data = json.loads(SRC.read_text(encoding="utf-8"))
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    html = TEMPLATE.replace("__ROUTINES_JSON__", payload)
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT} ({len(html)} bytes, {len(data['routines'])} routines)")


if __name__ == "__main__":
    main()
