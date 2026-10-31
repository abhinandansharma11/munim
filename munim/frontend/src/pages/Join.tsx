import { AnimatePresence, motion } from 'framer-motion';
import { CalendarCheck, CircleCheck, Hand, Loader2, Mic, Send, ShieldCheck, Sparkles, Store, UserPlus } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { post } from '../lib/api';
import { Lang, useLang } from '../lib/i18n';
import { useLive } from '../lib/live';
import { PhoneListen, Recorder, Voice, serverHasVoice } from '../lib/voice';
import { Mascot } from '../components/Art';
import { LangToggle } from '../components/LangToggle';
import { useToast } from '../components/Toast';

type Q = { key: string; kind: string; hi: string; en: string; step: number; total: number;
  options?: { value: string; hi: string; en: string }[]; summary?: { hi: string; en: string; v: string; ok?: boolean }[] };
type Line = { who: 'munim' | 'me'; text: string; id: number };

const T = {
  title: { hi: 'पेटीएम पर दुकान जोड़ें', en: 'Join Paytm' },
  sub: { hi: 'कोई फ़ॉर्म नहीं। बस मुनीम से बात कीजिए।', en: 'No forms. Just talk to Munim.' },
  intro: { hi: 'मुनीम 2 मिनट में आपकी दुकान पेटीएम पर जोड़ देगा: QR आज से, साउंडबॉक्स कल।', en: 'Munim adds your shop to Paytm in 2 minutes: QR from today, Soundbox tomorrow.' },
  go: { hi: 'बोलकर शुरू करें', en: 'Start by talking' },
  tap: { hi: 'दबाकर बोलिए', en: 'Tap & speak' }, listening: { hi: 'सुन रहा हूँ… भेजने के लिए दबाएँ', en: 'Listening… tap to send' },
  type: { hi: 'या यहाँ लिखिए…', en: 'Or type here…' },
  otpTitleTel: { hi: 'मोबाइल OTP', en: 'Mobile OTP' }, otpTitleKyc: { hi: 'आधार OTP से केवाईसी', en: 'KYC with Aadhaar OTP' },
  otpBtn: { hi: 'आधार OTP से पूरा करें', en: 'Complete with Aadhaar OTP' }, verify: { hi: 'पूरा करें', en: 'Verify' },
  demo: { hi: 'डेमो: OTP नकली है', en: 'Demo: OTP is simulated' },
  start: { hi: 'सब सही है, शुरू करें', en: 'All correct, start' },
  working: { hi: 'मुनीम आपकी दुकान तैयार कर रहा है', en: 'Munim is setting up your shop' },
  w1: { hi: 'बैंक खाते में ₹1 भेजकर नाम मिलाया', en: 'Sent ₹1 to the bank to match the name' },
  w2: { hi: 'मोबाइल, आधार और डुप्लिकेट की जाँच', en: 'Checked mobile, Aadhaar and duplicates' },
  w3: { hi: 'QR चालू किया', en: 'Turned on your QR' },
  w4: { hi: 'मशीन ऑर्डर की, फील्ड साथी बुक किया', en: 'Ordered the device, booked the field rep' },
  done: { hi: 'बधाई हो! आपकी दुकान पेटीएम पर है', en: 'Congratulations! Your shop is on Paytm' },
  qrNow: { hi: 'आपका QR अभी से चालू है', en: 'Your QR works from now' },
  visit: { hi: 'कल सुबह 11 बजे Anil Verma {d} लगाने आएँगे', en: 'Anil Verma will install your {d} tomorrow at 11 am' },
  open: { hi: 'अपनी दुकान का ऐप खोलें', en: 'Open my shop app' },
  wait: { hi: 'एक चीज़ दोबारा देखनी है। पेटीएम के एक साथी अभी जाँच रहे हैं…', en: 'One detail needs a second look. A Paytm teammate is checking now…' },
  rejected: { hi: 'बैंक खाते का नाम आपसे नहीं मिला। हमारी टीम आपको कॉल करके मदद करेगी।', en: "The bank account name didn't match yours. Our team will call to help." },
  heard: { hi: 'सुनाई नहीं दिया, फिर से बोलिए।', en: "Didn't catch that, please say it again." },
};
type K = keyof typeof T;

export default function Join() {
  const { lang } = useLang();
  const toast = useToast();
  const t = (k: K, v: Record<string, string> = {}) => Object.entries(v).reduce((s, [a, b]) => s.replace(`{${a}}`, b), T[k][lang]);
  const [sid, setSid] = useState('');
  const [q, setQ] = useState<Q | null>(null);
  const [lines, setLines] = useState<Line[]>([]);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [rec, setRec] = useState(false);
  const [otp, setOtp] = useState<null | 'tel' | 'kyc'>(null);
  const [phase, setPhase] = useState<'chat' | 'working' | 'waiting' | 'done' | 'rejected'>('chat');
  const [result, setResult] = useState<any>(null);
  const [tick, setTick] = useState(0);
  const pendingTel = useRef('');
  const scroller = useRef<HTMLDivElement>(null);
  const id = useRef(0);
  const langRef = useRef<Lang>(lang); langRef.current = lang;

  const add = (who: Line['who'], text: string) => setLines((l) => [...l, { who, text, id: ++id.current }]);
  const ask = (nq: Q) => { setQ(nq); add('munim', nq[langRef.current]); Voice.say(nq[langRef.current], langRef.current); };
  useEffect(() => { requestAnimationFrame(() => scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: 'smooth' })); }, [lines.length, phase]);

  const begin = async () => {
    Voice.unlock(); Voice.keepAwake();
    const r = await post('/api/onboard/start');
    setSid(r.sid); ask(r.next);
  };

  const submit = async (value: string, shown?: string) => {
    if (!value.trim() || !q || busy) return;
    if (q.kind === 'tel' && !otp && value.replace(/\D/g, '').length >= 10) { pendingTel.current = value; add('me', shown || value); setOtp('tel'); return; }
    if (q.kind !== 'tel') add('me', shown || value);
    setText(''); setBusy(true);
    try {
      const r = await post('/api/onboard/answer', { sid, text: value });
      if (r.error) { add('munim', r.error[langRef.current]); Voice.say(r.error[langRef.current], langRef.current); setQ(r.next); }
      else ask(r.next);
    } catch (e: any) { toast(e.message); }
    setBusy(false);
  };

  const finish = async () => {
    add('me', t('start')); setPhase('working'); setTick(0);
    const timer = window.setInterval(() => setTick((x) => Math.min(4, x + 1)), 1100);
    try {
      const r = await post('/api/onboard/finish', { sid });
      clearInterval(timer); setTick(4); setResult(r);
      setTimeout(() => setPhase(r.status === 'active' ? 'done' : 'waiting'), 500);
    } catch (e: any) { clearInterval(timer); toast(e.message); setPhase('chat'); }
  };

  // A teammate's decision arrives live while the shopkeeper waits.
  useLive((ev) => {
    if (ev.type === 'onboarded' && result && ev.merchant_id === result.merchant_id) {
      if (ev.status === 'active') { setResult({ ...result, ...ev }); setPhase('done'); }
      else setPhase('rejected');
    }
  });
  useEffect(() => {
    if (phase === 'done' && result) {
      try { localStorage.setItem('munim-onboarded', '1'); } catch {}  // they already chose a language here
      const d = lang === 'hi' ? (result.device?.[1] || 'साउंडबॉक्स') : (result.device?.[0] || 'Soundbox');
      Voice.say(t('done') + '. ' + t('qrNow') + '. ' + (result.visit ? t('visit', { d }) : ''), lang);
      Voice.chime();
    }
    if (phase === 'waiting') Voice.say(t('wait'), lang);
    if (phase === 'rejected') Voice.say(t('rejected'), lang);
  }, [phase]);

  const mic = async () => {
    Voice.unlock();
    if (PhoneListen.active) { PhoneListen.stop(); return; }
    if (Recorder.active) {
      setRec(false);
      const b = await Recorder.stop(); if (!b) return;
      const fd = new FormData(); fd.append('file', b, 'voice.wav');
      setBusy(true);
      try {
        const r = await fetch('/api/stt', { method: 'POST', body: fd }); const j = await r.json();
        setBusy(false);
        if (j.transcript) submit(j.transcript); else toast(t('heard'));
      } catch { setBusy(false); toast(t('heard')); }
      return;
    }
    if (!(await serverHasVoice()) && PhoneListen.supported()) {
      setRec(true);
      PhoneListen.start(lang, (txt) => { setRec(false); if (txt) submit(txt); else toast(t('heard')); }, () => setRec(false));
      return;
    }
    if (!Recorder.supported()) { toast(t('heard')); return; }
    try { await Recorder.start(15, () => mic()); setRec(true); } catch { toast(t('heard')); }
  };

  const numeric = q?.kind === 'tel' || q?.kind === 'digits4';

  return (
    <div className="h-full bg-[#DDE5F0]">
      <div className="relative mx-auto flex h-full max-w-[440px] flex-col overflow-hidden bg-page">
        <header className="border-b border-line bg-white px-4 pb-3 text-ink" style={{ paddingTop: 'calc(14px + env(safe-area-inset-top, 0px))' }}>
          <div className="flex items-center gap-3">
            <div className="grid h-11 w-11 place-items-center rounded-full bg-sky-soft"><UserPlus size={22} className="text-navy" /></div>
            <div className="min-w-0 flex-1"><div className="text-[18px] font-bold leading-tight text-ink">{t('title')}</div><div className="text-[13px] text-muted">{t('sub')}</div></div>
            <LangToggle />
          </div>
          {q && phase === 'chat' && (
            <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-tint">
              <motion.div className="h-full rounded-full bg-sky" animate={{ width: `${((q.step - 1) / q.total) * 100}%` }} transition={{ type: 'spring', stiffness: 120, damping: 20 }} />
            </div>
          )}
        </header>
        <div className="stripe" />

        {!sid ? (
          <div className="flex flex-1 flex-col items-center justify-center px-7 text-center">
            <motion.div initial={{ scale: .8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className=""><Mascot size={72} /></motion.div>
            <h1 className="mt-6 text-[30px] font-extrabold leading-tight">{t('title')}</h1>
            <p className="mt-2 max-w-xs text-[15.5px] leading-relaxed text-muted">{t('intro')}</p>
            <div className="mt-5 flex gap-2 text-[12.5px] font-semibold">
              {[[Store, 'QR'], [ShieldCheck, 'KYC'], [CalendarCheck, 'Soundbox']].map(([I, l]: any) => (
                <span key={l} className="flex items-center gap-1 rounded-full border border-navy/20 px-3 py-1.5 text-navy"><I size={14} />{l}</span>))}
            </div>
            <motion.button whileTap={{ scale: .96 }} onClick={begin} className="mt-8 flex items-center gap-2.5 rounded-full bg-navy px-8 py-4 text-lg font-bold text-white">
              <Mic size={22} />{t('go')}</motion.button>
          </div>
        ) : (
          <>
            <main ref={scroller} className="flex-1 overflow-y-auto px-3.5 py-4">
              <div className="flex flex-col gap-2.5">
                <AnimatePresence initial={false}>
                  {lines.map((l) => (
                    <motion.div key={l.id} initial={{ opacity: 0, y: 10, scale: .97 }} animate={{ opacity: 1, y: 0, scale: 1 }}
                      className={l.who === 'me' ? 'flex justify-end' : 'flex items-end gap-2'}>
                      {l.who === 'munim' && <Mascot size={30} />}
                      <div className={`max-w-[80%] px-4 py-3 text-[16px] leading-relaxed ${l.who === 'me' ? 'rounded-[18px] rounded-br-md bg-navy text-white' : 'rounded-[18px] rounded-bl-md bg-white text-ink'}`}>{l.text}</div>
                    </motion.div>
                  ))}
                </AnimatePresence>

                {phase === 'chat' && q?.kind === 'confirm' && q.summary && (
                  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="ml-[38px] rounded-[20px] bg-white p-4">
                    {q.summary.map((r) => (
                      <div key={r.en} className="flex items-center justify-between border-b border-line py-2 text-[14px] last:border-0">
                        <span className="text-muted">{r[lang]}</span>
                        <span className="flex items-center gap-1.5 font-semibold text-navy">{r.v}{r.ok && <CircleCheck size={15} className="text-good" />}</span>
                      </div>
                    ))}
                  </motion.div>
                )}

                {phase !== 'chat' && phase !== 'done' && phase !== 'rejected' && (
                  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="ml-[38px] rounded-[20px] bg-white p-4">
                    <div className="mb-2 flex items-center gap-2 text-[15px] font-bold text-navy"><Sparkles size={17} className="text-sky-ink" />{t('working')}</div>
                    {(['w1', 'w2', 'w3', 'w4'] as K[]).map((k, i) => (
                      <motion.div key={k} initial={{ opacity: .35 }} animate={{ opacity: tick > i ? 1 : .35 }} className="flex items-center gap-2 py-1 text-[14px]">
                        {tick > i ? <CircleCheck size={17} className="text-good" /> : <Loader2 size={17} className="animate-spin text-faint" />}{t(k)}
                      </motion.div>
                    ))}
                    {phase === 'waiting' && (
                      <div className="mt-3 flex items-start gap-2 rounded-xl bg-gold-soft px-3 py-2.5 text-[13.5px] text-gold-ink"><Hand size={17} className="mt-0.5 flex-none" />{t('wait')}</div>
                    )}
                  </motion.div>
                )}

                {phase === 'rejected' && (
                  <div className="ml-[38px] rounded-[20px] bg-bad-soft p-4 text-[14.5px] text-bad">{t('rejected')}</div>
                )}

                {phase === 'done' && result && (
                  <motion.div initial={{ opacity: 0, scale: .9 }} animate={{ opacity: 1, scale: 1 }} transition={{ type: 'spring', stiffness: 200, damping: 18 }}
                    className="relative overflow-hidden rounded-[24px] bg-navy p-5 text-center text-white shadow-lift">
                    {Array.from({ length: 14 }).map((_, i) => (
                      <motion.span key={i} className="absolute h-2 w-2 rounded-sm" style={{ left: `${(i * 7) % 100}%`, top: -10, background: ['#FFC400', '#00BAF2', '#2BD37B'][i % 3] }}
                        animate={{ y: [0, 380], rotate: [0, 360], opacity: [1, 0] }} transition={{ duration: 2.4, delay: i * .08, ease: 'easeIn' }} />
                    ))}
                    <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: 'spring', delay: .2 }} className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-good"><CircleCheck size={32} /></motion.div>
                    <div className="mt-3 text-xl font-bold">{t('done')}</div>
                    <div className="mx-auto mt-4 w-fit rounded-2xl bg-white p-3">
                      <QRCodeSVG value={`upi://pay?pa=${result.upi_id}&cu=INR`} size={150} fgColor="#002970" />
                      <div className="mt-1 text-[12px] font-semibold text-navy">{result.upi_id}</div>
                    </div>
                    <div className="mt-3 text-[14px] text-[#CFE0F7]">{t('qrNow')}</div>
                    {result.visit && <div className="mt-2 flex items-center justify-center gap-1.5 rounded-xl bg-white/10 px-3 py-2 text-[13.5px]"><CalendarCheck size={16} />{t('visit', { d: lang === 'hi' ? result.device?.[1] || 'साउंडबॉक्स' : result.device?.[0] || 'Soundbox' })}</div>}
                    <Link to={`/merchant?m=${result.merchant_id}`} className="mt-4 block rounded-xl bg-gold py-3 font-bold text-navy">{t('open')}</Link>
                  </motion.div>
                )}
              </div>
            </main>

            {phase === 'chat' && q && (
              <footer className="border-t border-line bg-white px-3 pt-3" style={{ paddingBottom: 'calc(10px + env(safe-area-inset-bottom, 0px))' }}>
                {q.kind === 'confirm' ? (
                  <motion.button whileTap={{ scale: .97 }} onClick={finish} className="mb-1 w-full rounded-full bg-navy py-4 text-lg font-bold text-white">{t('start')}</motion.button>
                ) : q.kind === 'otp' ? (
                  <motion.button whileTap={{ scale: .97 }} onClick={() => setOtp('kyc')} className="mb-1 flex w-full items-center justify-center gap-2 rounded-full bg-navy py-4 text-[17px] font-bold text-white">
                    <ShieldCheck size={20} />{t('otpBtn')}</motion.button>
                ) : (
                  <>
                    {q.options && (
                      <div className="mb-2.5 flex flex-wrap gap-2">
                        {q.options.map((o, i) => (
                          <motion.button key={o.value} whileTap={{ scale: .95 }} disabled={busy} onClick={() => submit(o.value, o[lang])}
                            className={`rounded-full px-4 py-2 text-[15px] font-semibold ${i === 0 && q.key === 'device' ? 'bg-navy text-white' : 'border border-navy/25 bg-white text-navy'}`}>{o[lang]}</motion.button>
                        ))}
                      </div>
                    )}
                    <div className="flex items-center gap-2">
                      <input value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && submit(text)}
                        inputMode={numeric ? 'numeric' : 'text'} placeholder={t('type')} aria-label={t('type')}
                        className="min-w-0 flex-1 rounded-full bg-tint px-4 py-3 text-[15px] outline-none focus:ring-2 focus:ring-sky" />
                      {text.trim() && <motion.button initial={{ scale: 0 }} animate={{ scale: 1 }} onClick={() => submit(text)} aria-label="Send"
                        className="grid h-11 w-11 flex-none place-items-center rounded-full bg-sky text-navy"><Send size={19} /></motion.button>}
                      <div className="relative flex-none">
                        {rec && [0, 1].map((i) => <motion.span key={i} className="absolute inset-0 rounded-full bg-bad-solid" initial={{ scale: 1, opacity: .45 }}
                          animate={{ scale: 1.9, opacity: 0 }} transition={{ duration: 1.4, repeat: Infinity, delay: i * .7 }} />)}
                        <motion.button whileTap={{ scale: .92 }} onClick={mic} disabled={busy} aria-label={t('tap')}
                          className={`relative grid h-[58px] w-[58px] place-items-center rounded-full text-white shadow-lift ${rec ? 'bg-bad-solid' : 'bg-navy'}`}>
                          {busy ? <Loader2 size={24} className="animate-spin" /> : rec ? <Send size={22} /> : <Mic size={26} />}
                        </motion.button>
                      </div>
                    </div>
                    <div className="mt-1.5 text-center text-[12px] font-semibold text-muted">{rec ? t('listening') : t('tap')}</div>
                  </>
                )}
              </footer>
            )}
          </>
        )}

        <AnimatePresence>{otp && (
          <OtpSheet title={otp === 'tel' ? t('otpTitleTel') : t('otpTitleKyc')} verify={t('verify')} note={t('demo')}
            onDone={() => { const kind = otp; setOtp(null); if (kind === 'tel') submitTel(); else submit('verified', '✓ Aadhaar OTP'); }} />
        )}</AnimatePresence>
      </div>
    </div>
  );

  async function submitTel() {
    const v = pendingTel.current; setBusy(true);
    try {
      const r = await post('/api/onboard/answer', { sid, text: v });
      if (r.error) { add('munim', r.error[langRef.current]); setQ(r.next); } else ask(r.next);
    } catch (e: any) { toast(e.message); }
    setBusy(false);
  }
}

function OtpSheet({ title, verify, note, onDone }: { title: string; verify: string; note: string; onDone: () => void }) {
  const digits = '561904'.split('');
  const [n, setN] = useState(0);
  useEffect(() => { if (n < 6) { const x = setTimeout(() => setN(n + 1), n ? 150 : 450); return () => clearTimeout(x); } }, [n]);
  return (
    <motion.div className="absolute inset-0 z-20 flex items-end bg-navy-ink/45" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <motion.div role="dialog" aria-label={title} className="w-full rounded-t-[26px] bg-white px-5 pt-6" style={{ paddingBottom: 'calc(22px + env(safe-area-inset-bottom, 0px))' }}
        initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }} transition={{ type: 'spring', stiffness: 320, damping: 32 }}>
        <h3 className="mb-4 text-xl font-bold text-navy">{title}</h3>
        <div className="mb-5 flex gap-2">{digits.map((d, i) => (
          <div key={i} className="grid h-[52px] flex-1 place-items-center rounded-xl bg-tint text-2xl font-bold text-navy">
            <AnimatePresence>{i < n && <motion.span initial={{ y: 10, opacity: 0 }} animate={{ y: 0, opacity: 1 }}>{d}</motion.span>}</AnimatePresence>
          </div>))}
        </div>
        <motion.button whileTap={{ scale: .97 }} disabled={n < 6} onClick={onDone} className="w-full rounded-xl bg-navy py-3.5 text-base font-semibold text-white disabled:opacity-50">{verify}</motion.button>
        <div className="mt-2.5 text-center text-xs text-faint">{note}</div>
      </motion.div>
    </motion.div>
  );
}
