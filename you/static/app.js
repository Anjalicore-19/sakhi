const $ = (id) => document.getElementById(id);
const CODES = { hi: "hi-IN", ta: "ta-IN" };
const ICON = { idle: "", speaking: "🔊", listening: "👂", thinking: "⏳", done: "" };

let lang = new URLSearchParams(location.search).get("lang") || (navigator.language || "hi").slice(0, 2);
if (!CODES[lang]) lang = "hi";
document.documentElement.lang = lang;
let busy = false;
const DEBUG = new URLSearchParams(location.search).has("debug");

function setState(s) { document.body.dataset.state = s; $("status").textContent = ICON[s]; }

function speak(lines) {
  return new Promise((resolve) => {
    setState("speaking");
    const synth = window.speechSynthesis;
    synth.cancel();
    const queue = [...lines];
    const next = () => {
      if (!queue.length) return resolve();
      const text = queue.shift();
      if (DEBUG) $("caption").textContent = text;
      const u = new SpeechSynthesisUtterance(text);
      u.lang = CODES[lang]; u.rate = 0.85;
      let finished = false, timer;
      const done = () => {
        if (finished) return;
        finished = true; clearTimeout(timer); next();
      };
      timer = setTimeout(done, 3000 + text.length * 150); // never wait forever
      u.onend = done; u.onerror = done;
      synth.speak(u);
    };
    next();
  });
}

// Record until she stops talking (no button to press = zero digital knowledge needed)
async function listen() {
  setState("listening");
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const rec = new MediaRecorder(stream);
  const chunks = [];
  rec.ondataavailable = (e) => chunks.push(e.data);
  const ctx = new AudioContext();
  const analyser = ctx.createAnalyser();
  ctx.createMediaStreamSource(stream).connect(analyser);
  const buf = new Uint8Array(analyser.fftSize);
  rec.start();
  await new Promise((done) => {
    const t0 = Date.now();
    let heardVoice = false, lastVoice = Date.now();
    const tick = setInterval(() => {
      analyser.getByteTimeDomainData(buf);
      const rms = Math.sqrt(buf.reduce((s, v) => s + (v - 128) ** 2, 0) / buf.length);
      if (rms > 6) { heardVoice = true; lastVoice = Date.now(); }
      if ((heardVoice && Date.now() - lastVoice > 1300) || Date.now() - t0 > 10000) {
        clearInterval(tick); done();
      }
    }, 100);
  });
  await new Promise((r) => { rec.onstop = r; rec.stop(); });
  stream.getTracks().forEach((t) => t.stop());
  ctx.close();
  return toWav(new Blob(chunks));
}

// Browser recording -> 16 kHz mono WAV (a format Gemini accepts)
async function toWav(blob) {
  const ctx = new AudioContext();
  const audio = await ctx.decodeAudioData(await blob.arrayBuffer());
  ctx.close();
  const src = audio.getChannelData(0);
  const ratio = audio.sampleRate / 16000;
  const out = new Int16Array(Math.floor(src.length / ratio));
  for (let i = 0; i < out.length; i++) {
    out[i] = Math.max(-1, Math.min(1, src[Math.floor(i * ratio)])) * 0x7fff;
  }
  const head = new ArrayBuffer(44), v = new DataView(head);
  const w = (o, s) => [...s].forEach((c, i) => v.setUint8(o + i, c.charCodeAt(0)));
  w(0, "RIFF"); v.setUint32(4, 36 + out.length * 2, true); w(8, "WAVE"); w(12, "fmt ");
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, 16000, true); v.setUint32(28, 32000, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true);
  w(36, "data"); v.setUint32(40, out.length * 2, true);
  return new Blob([head, out.buffer], { type: "audio/wav" });
}

async function converse() {
  if (busy) return;
  busy = true;
  try {
    let res = await (await fetch(`/api/start?lang=${lang}`)).json();
    while (true) {
      await speak(res.speech);
      if (res.card) { showCard(res); return; }
      const wav = await listen();
      setState("thinking");
      const form = new FormData();
      form.append("lang", lang);
      form.append("asked", res.asked);
      form.append("facts", JSON.stringify(res.facts));
      form.append("audio", wav, "a.wav");
      res = await (await fetch("/api/turn", { method: "POST", body: form })).json();
      if (DEBUG) $("caption").textContent = "facts: " + JSON.stringify(res.facts);
    }
  } catch (e) {
    console.error(e);
    setState("idle");
    $("status").textContent = "⚠ " + e.message;
  } finally {
    busy = false;
  }
}

// The "Pocket Pass": pictures + her language, to show an Anganwadi didi / ASHA
function showCard(res) {
  const c = res.card, el = $("card");
  setState("done");
  el.hidden = false;
  el.innerHTML = "";
  if (c.amount) el.innerHTML += `<div class="amount">₹${c.amount.toLocaleString("en-IN")}</div>`;
  c.docs.forEach((d) => {
    const t = document.createElement("div");
    t.className = "tile";
    const todo = d.id === "passbook" && c.need_account ? "➕" : "";
    t.innerHTML = `<b>${d.emoji}${todo}</b><span>${d.label}</span>`;
    t.onclick = () => speak([d.label]).then(() => setState("done"));
    el.appendChild(t);
  });
  const actions = document.createElement("div");
  actions.className = "actions";
  actions.innerHTML = `<button id="replay">🔊</button><button id="share">📤</button><button id="call">📞</button>`;
  el.appendChild(actions);
  $("replay").onclick = () => speak(res.speech).then(() => setState("done"));
  $("call").onclick = () => (location.href = `tel:${c.helpline}`);
  $("share").onclick = () => {
    const text = (c.amount ? `₹${c.amount}\n` : "") + c.docs.map((d) => `${d.emoji} ${d.label}`).join("\n");
    navigator.share ? navigator.share({ text }) : window.open(`https://wa.me/?text=${encodeURIComponent(text)}`);
  };
}

// Shared-phone safety: one tap wipes everything and leaves to a neutral page
$("hide").onclick = () => {
  speechSynthesis.cancel();
  document.body.innerHTML = "";
  location.replace("https://www.google.com/search?q=weather");
};

$("mic").onclick = converse;