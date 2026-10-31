// Sound out (Sarvam voice, or the phone's own voice as a fallback) and sound in (16 kHz WAV for Sarvam).
let queue: Promise<void> = Promise.resolve();
let ctx: AudioContext | null = null;

export const Voice = {
  enabled: true,
  unlock() {
    try { ctx = ctx || new (window.AudioContext || (window as any).webkitAudioContext)(); ctx.resume(); } catch {}
    try { window.speechSynthesis?.speak(new SpeechSynthesisUtterance('')); } catch {}
  },
  say(text: string, lang: 'hi' | 'en', hooks: { onStart?: () => void; onEnd?: () => void } = {}) {
    if (!this.enabled || !text) return queue;
    // A clip that never reports "ended" (some phones) must not block every later reply: give up after 25 s.
    queue = queue.then(() => Promise.race([speak(text, lang, hooks), new Promise<void>((r) => setTimeout(() => { hooks.onEnd?.(); r(); }, 25000))]))
      .catch(() => {});
    return queue;
  },
  vibrate(pattern: number[]) { try { navigator.vibrate?.(pattern); } catch {} },
  async keepAwake() { try { await (navigator as any).wakeLock?.request('screen'); } catch {} },
  chime() {
    try {
      ctx = ctx || new (window.AudioContext || (window as any).webkitAudioContext)();
      const c = ctx;
      [0, 0.13].forEach((t, i) => {
        const o = c.createOscillator(), g = c.createGain();
        o.frequency.value = i ? 1046 : 784; o.connect(g); g.connect(c.destination);
        g.gain.setValueAtTime(0.0001, c.currentTime + t);
        g.gain.exponentialRampToValueAtTime(0.25, c.currentTime + t + 0.02);
        g.gain.exponentialRampToValueAtTime(0.0001, c.currentTime + t + 0.35);
        o.start(c.currentTime + t); o.stop(c.currentTime + t + 0.4);
      });
    } catch {}
  },
};

async function speak(text: string, lang: 'hi' | 'en', { onStart, onEnd }: { onStart?: () => void; onEnd?: () => void }) {
  onStart?.();
  try {
    const r = await fetch('/api/tts', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text, lang }) });
    if (!r.ok) throw new Error('no voice key');
    const url = URL.createObjectURL(await r.blob());
    await new Promise<void>((res) => { const a = new Audio(url); a.onended = () => res(); a.onerror = () => res(); a.play().catch(() => res()); });
  } catch {
    await browserSay(text, lang);
  }
  onEnd?.();
}

function browserSay(text: string, lang: 'hi' | 'en') {
  return new Promise<void>((res) => {
    const synth = window.speechSynthesis;
    if (!synth) return res();
    const u = new SpeechSynthesisUtterance(text);
    const code = lang === 'hi' ? 'hi-IN' : 'en-IN';
    const v = synth.getVoices().find((x) => x.lang === code) || synth.getVoices().find((x) => x.lang.startsWith(lang));
    if (v) u.voice = v;
    u.lang = code;
    u.onend = () => res(); u.onerror = () => res();
    synth.speak(u);
    setTimeout(res, 16000);
  });
}

export const Recorder = {
  stream: null as MediaStream | null, ac: null as AudioContext | null, node: null as ScriptProcessorNode | null,
  chunks: [] as Float32Array[], rate: 48000, active: false, startedAt: 0, timer: 0,
  supported() { return !!(navigator.mediaDevices && typeof navigator.mediaDevices.getUserMedia === "function" && window.isSecureContext); },
  async start(maxSeconds: number, onAutoStop: () => void) {
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
    this.ac = new (window.AudioContext || (window as any).webkitAudioContext)();
    this.rate = this.ac.sampleRate;
    const src = this.ac.createMediaStreamSource(this.stream);
    this.node = this.ac.createScriptProcessor(4096, 1, 1);
    this.chunks = [];
    this.node.onaudioprocess = (e) => this.chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
    src.connect(this.node); this.node.connect(this.ac.destination);
    this.active = true; this.startedAt = Date.now();
    this.timer = window.setTimeout(onAutoStop, maxSeconds * 1000);
  },
  async stop(): Promise<Blob | null> {
    clearTimeout(this.timer);
    if (!this.active) return null;
    this.active = false;
    this.node?.disconnect(); this.stream?.getTracks().forEach((t) => t.stop());
    await this.ac?.close();
    const len = this.chunks.reduce((n, c) => n + c.length, 0), all = new Float32Array(len);
    let off = 0; this.chunks.forEach((c) => { all.set(c, off); off += c.length; });
    return wav(downsample(all, this.rate, 16000), 16000);
  },
};

function downsample(buf: Float32Array, from: number, to: number) {
  if (from === to) return buf;
  const ratio = from / to, out = new Float32Array(Math.floor(buf.length / ratio));
  for (let i = 0; i < out.length; i++) {
    const a = Math.floor(i * ratio), b = Math.min(buf.length, Math.floor((i + 1) * ratio));
    let s = 0; for (let j = a; j < b; j++) s += buf[j];
    out[i] = s / Math.max(1, b - a);
  }
  return out;
}

function wav(samples: Float32Array, rate: number) {
  const b = new ArrayBuffer(44 + samples.length * 2), v = new DataView(b);
  const w = (o: number, s: string) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
  w(0, 'RIFF'); v.setUint32(4, 36 + samples.length * 2, true); w(8, 'WAVE'); w(12, 'fmt ');
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true); v.setUint32(24, rate, true);
  v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true); w(36, 'data'); v.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i++) { const s = Math.max(-1, Math.min(1, samples[i])); v.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true); }
  return new Blob([b], { type: 'audio/wav' });
}

// Without a Sarvam key, the phone's own speech recognition (free, Chrome on Android supports Hindi) turns speech into text.
let sarvamOn: boolean | null = null;
export async function serverHasVoice() {
  if (sarvamOn === null) {
    try { sarvamOn = !!(await (await fetch('/api/info')).json()).sarvam; } catch { sarvamOn = false; }
  }
  return sarvamOn;
}

export const PhoneListen = {
  rec: null as any,
  active: false,
  supported() { return !!((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition); },
  start(lang: 'hi' | 'en', onText: (t: string) => void, onEnd: () => void) {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    const r = new SR();
    r.lang = lang === 'hi' ? 'hi-IN' : 'en-IN';
    r.interimResults = false; r.maxAlternatives = 1;
    let got = false;
    r.onresult = (e: any) => { const t = e.results?.[0]?.[0]?.transcript; if (t) { got = true; onText(t); } };
    r.onend = () => { this.active = false; onEnd(); if (!got) onText(''); };
    r.onerror = () => { this.active = false; };
    this.rec = r; this.active = true; r.start();
  },
  stop() { try { this.rec?.stop(); } catch {} },
};
