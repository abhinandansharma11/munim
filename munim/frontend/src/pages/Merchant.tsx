import { AnimatePresence, animate, motion } from 'framer-motion';
import { CircleCheck, CircleHelp, IdCard, Landmark, Mic, Radio, RefreshCw, ScrollText, Send, ShieldAlert, ShieldCheck, Store, Volume2, VolumeX, Bell, Wallet, TrendingUp, ReceiptText, Hourglass, HandCoins, ChevronRight, Home, MessageCircle, QrCode } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { get, hhmm, inr, post, sendVoice, shopFromUrl } from '../lib/api';
import { Key, Lang, pick, useLang } from '../lib/i18n';
import { useLive } from '../lib/live';
import { PhoneListen, Recorder, Voice, serverHasVoice } from '../lib/voice';
import { Initials, Mascot } from '../components/Art';
import { QRCodeSVG } from 'qrcode.react';
import { LangToggle } from '../components/LangToggle';
import { useToast } from '../components/Toast';

type Msg = { id: number; role: string; text: string; speak?: string; en?: string; kind: string; data?: any; ts: string; voice: number; channel: string };

// Ready-made questions a shopkeeper can tap. They go to Munim as normal messages; nothing here is a canned answer.
const SUGGEST: Record<Lang, [typeof Volume2, string, string][]> = {
  hi: [[Hourglass, 'ग्राहक का पैसा अटका', 'ग्राहक का ₹650 कट गया पर मेरे पास नहीं आया'], [HandCoins, 'पैसा कम क्यों?', 'बैंक में पैसा कम क्यों आया?'],
    [Wallet, 'बैंक बैलेंस', 'मेरे बैंक में कितना पैसा है?'], [ScrollText, 'आज का हिसाब', 'आज कितना पैसा आया?'],
    [TrendingUp, 'इस हफ्ते की बिक्री', 'इस हफ्ते कितनी बिक्री हुई?'], [ReceiptText, 'आखिरी पेमेंट', 'आखिरी 5 पेमेंट दिखाओ'],
    [VolumeX, 'साउंडबॉक्स बंद', 'साउंडबॉक्स नहीं बोल रहा'], [Landmark, 'पैसा नहीं आया', 'कल का पैसा नहीं आया'],
    [RefreshCw, 'दो बार कटा', 'ग्राहक का ₹4,800 दो बार कट गया'], [ShieldAlert, '₹2,000 आया?', 'रोहित ने ₹2,000 भेजा, आया क्या?'],
    [Store, 'नई दुकान', 'दूसरी दुकान खोल रहा हूँ, वहाँ भी साउंडबॉक्स चाहिए']],
  en: [[Hourglass, 'Payment stuck', "A customer's ₹650 was debited but I didn't get it"], [HandCoins, 'Why less money?', 'Why did less money come to my bank?'],
    [Wallet, 'Bank balance', 'How much money is in my bank?'], [ScrollText, "Today's sales", "Tell me today's sales"],
    [TrendingUp, 'This week', 'How much did I sell this week?'], [ReceiptText, 'Last payments', 'Show my last 5 payments'],
    [VolumeX, 'Soundbox silent', 'My Soundbox is not speaking'], [Landmark, 'Money not in bank', 'My payout from yesterday has not come'],
    [RefreshCw, 'Charged twice', 'A customer was charged ₹4,800 twice'], [ShieldAlert, 'Did ₹2,000 come?', 'Did ₹2,000 from Rohit come?'],
    [Store, 'New shop', 'I am opening a second shop, I need a Soundbox there']],
};
// Tapping a status box asks about it; Munim answers from the data and only acts if something is wrong.
const ASK: Record<Lang, { soundbox: string; payout: string; kyc: string }> = {
  hi: { soundbox: 'मेरा साउंडबॉक्स ठीक है?', payout: 'बैंक में पैसा कब और कितना आया?', kyc: 'मेरा केवाईसी कैसा है?' },
  en: { soundbox: 'Is my Soundbox working?', payout: 'When and how much money came to my bank?', kyc: 'What is my KYC status?' },
};
const PHASE_KEY: Record<string, Key> = { observe: 'w_observe', think: 'w_think', act: 'w_act', check: 'w_check' };

export default function Merchant() {
  const { lang, t } = useLang();
  const toast = useToast();
  const [mid, setMid] = useState(shopFromUrl() || 'M1001');
  const [s, setS] = useState<any>(null);
  const [onboard, setOnboard] = useState(() => { if (new URLSearchParams(location.search).get('preview')) return false; try { return !localStorage.getItem('munim-onboarded'); } catch { return true; } });
  const [working, setWorking] = useState<Key | null>(null);
  const [rec, setRec] = useState(false);
  const [recSecs, setRecSecs] = useState(0);
  const [text, setText] = useState('');
  const [sheet, setSheet] = useState(false);
  const [voiceOn, setVoiceOn] = useState(true);
  const [tab, setTab] = useState<'home' | 'munim' | 'qr'>(() => (new URLSearchParams(location.search).get('tab') as any) || 'home');
  const [unread, setUnread] = useState(false);
  const tabRef = useRef(tab); tabRef.current = tab;
  const scroller = useRef<HTMLDivElement>(null);
  const filePick = useRef<HTMLInputElement>(null);
  const langRef = useRef(lang); langRef.current = lang;
  const spokeLast = useRef(false);

  const load = async (id = mid) => { try { setS(await get('/api/merchant/' + id)); } catch (e: any) { toast(e.message); } };
  useEffect(() => {
    if (shopFromUrl()) { load(); return; }
    get('/api/info').then((i) => { setMid(i.merchant_id); load(i.merchant_id); }).catch(() => load());
  }, []);
  useEffect(() => { const u = () => Voice.unlock(); document.addEventListener('pointerdown', u, { once: true }); return () => document.removeEventListener('pointerdown', u); }, []);
  useEffect(() => { requestAnimationFrame(() => scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: 'smooth' })); }, [s?.messages?.length, working]);

  const refreshT = useRef<number>();
  const refresh = () => { clearTimeout(refreshT.current); refreshT.current = window.setTimeout(() => load(), 120); };
  useLive((ev) => {
    if (ev.merchant_id && ev.merchant_id !== mid) return;
    if (ev.type === 'phase') { if (ev.merchant_id === mid) setWorking(PHASE_KEY[ev.phase] ?? null); return; }
    if (ev.type === 'case' && ev.status !== 'open') setWorking(null);
    // Speak only when it helps: the shopkeeper spoke to us, or Munim is raising an alert on its own.
    // Typed questions get text (and a Listen button), which keeps voice costs down.
    if (ev.type === 'message' && tabRef.current !== 'munim') setUnread(true);
    if (ev.type === 'message' && ev.channel === 'alert') Voice.vibrate([300, 150, 300]);
    if (ev.type === 'message' && (ev.speak || ev.en) && ev.channel !== 'soundbox' && (spokeLast.current || ev.channel === 'proactive' || ev.channel === 'alert')) {
      const l = langRef.current; Voice.say(l === 'hi' ? ev.speak : ev.en, l);
    }
    if (ev.type === 'payment') toast(t(ev.announced ? 'payToast' : 'payMissed', { amt: inr(ev.amount) }), 3600);
    if (ev.type === 'reset') setWorking(null);
    refresh();
  });

  const send = async (msg?: string) => {
    const m = (msg ?? text).trim(); if (!m) return;
    // A tapped button is how many shopkeepers "talk", so its answer is spoken. Only typed questions get text alone.
    setText(''); setWorking('w_read'); spokeLast.current = msg !== undefined;
    try { await post('/api/message', { merchant_id: mid, text: m, channel: 'app' }); } catch (e: any) { setWorking(null); toast(e.message); }
  };
  const upload = async (blob: Blob, name: string) => {
    setWorking('w_listen'); spokeLast.current = true;
    try { await sendVoice(blob, name, mid, 'app'); } catch (e: any) { setWorking(null); toast(e.message, 4500); }
  };
  const tick = useRef<number>();
  const mic = async () => {
    Voice.unlock();
    if (PhoneListen.active) { PhoneListen.stop(); return; }
    if (!Recorder.active && !(await serverHasVoice()) && PhoneListen.supported()) {
      // No Sarvam key: let the phone itself turn speech into text, then send it like a voice message.
      setRec(true); setRecSecs(0);
      PhoneListen.start(lang, (txt) => { setRec(false); if (txt) { spokeLast.current = true; send(txt).then(() => { spokeLast.current = true; }); } else toast(t('micNothing')); },
        () => setRec(false));
      return;
    }
    if (Recorder.active) {
      clearInterval(tick.current); setRec(false);
      const b = await Recorder.stop(); if (b) upload(b, 'voice.wav'); return;
    }
    if (!Recorder.supported()) { toast(t('micHttps')); filePick.current?.click(); return; }
    try {
      await Recorder.start(25, () => mic());
      setRec(true); setRecSecs(0);
      tick.current = window.setInterval(() => setRecSecs(Math.floor((Date.now() - Recorder.startedAt) / 1000)), 250);
    } catch { toast(t('micBlocked')); }
  };
  const toggleVoice = () => { Voice.enabled = !Voice.enabled; setVoiceOn(Voice.enabled); toast(t(Voice.enabled ? 'voiceOn' : 'voiceOff')); };

  if (!s) return <div className="grid h-full place-items-center bg-page"><Mascot size={64} /></div>;
  const m = s.merchant, online = s.device?.status === 'online', coming = s.device?.status === 'not_installed';
  const held = s.settlements.find((x: any) => x.status === 'on_hold');
  const kycOk = m.kyc_status === 'verified';
  const sug = SUGGEST[lang];

  const go = (q: string) => { setTab('munim'); send(q); };
  const upi = (m.shop.toLowerCase().replace(/[^a-z0-9]/g, '').slice(0, 14) || 'shop') + m.id.slice(-2) + '@paytm';
  const rows = [
    { icon: <Radio size={19} />, k: t('soundbox'), v: online ? t('working') : coming ? t('sbComing') : t('notWorking'),
      tone: online ? 'good' : coming ? 'warn' : 'bad', q: ASK[lang].soundbox },
    { icon: <Landmark size={19} />, k: t('payout'), v: held ? t('stuck', { amt: inr(held.amount) }) : t('allIn'),
      tone: held ? 'warn' : 'good', q: ASK[lang].payout },
    { icon: <IdCard size={19} />, k: t('kyc'), v: kycOk ? t('kycDone') : t('kycNeeded'), tone: kycOk ? 'good' : 'warn', q: ASK[lang].kyc },
  ] as const;

  return (
    <div className="h-full bg-[#DDE5F0]">
      <div className="relative mx-auto flex h-full max-w-[440px] flex-col overflow-hidden bg-page">
        <header className="flex items-center gap-3 border-b border-line bg-white px-4 pb-3 text-ink" style={{ paddingTop: 'calc(12px + env(safe-area-inset-top, 0px))' }}>
          <Initials name={m.shop} size={40} />
          <div className="min-w-0 flex-1">
            <div className="truncate text-[17px] font-bold leading-tight text-ink">{m.shop}</div>
            <div className="truncate text-[13px] text-muted">Paytm for Business</div>
          </div>
          <LangToggle />
          {tab === 'munim' ? (
            <button onClick={toggleVoice} aria-label={voiceOn ? t('voiceOff') : t('voiceOn')} className="grid h-9 w-9 flex-none place-items-center rounded-full text-navy hover:bg-tint">
              {voiceOn ? <Volume2 size={21} /> : <VolumeX size={21} className="text-faint" />}
            </button>
          ) : (
            <button onClick={() => setOnboard(true)} aria-label={t('help')} className="grid h-9 w-9 flex-none place-items-center rounded-full text-navy hover:bg-tint"><CircleHelp size={21} /></button>
          )}
        </header>

        {tab === 'home' && (
          <main className="flex-1 overflow-y-auto px-4 pb-4 pt-4">
            <section className="rounded-xl2 bg-white px-5 pb-4 pt-5">
              <div className="text-[15px] font-semibold text-body">{t('todayEarn')}</div>
              <div className="num mt-1.5 text-[42px] font-extrabold leading-none tracking-tight text-ink"><CountUp value={s.today.collected_value} /></div>
              <div className="mt-2 flex items-center justify-between text-[14px] text-muted">
                <span>{t('payments', { n: s.today.payments })}</span>
                {s.recent_payments[0] && <span>{t('lastPay', { amt: inr(s.recent_payments[0].amount), t: hhmm(s.recent_payments[0].ts) })}</span>}
              </div>
              <button onClick={() => go(ASK[lang].payout)} className="mt-4 flex w-full items-center justify-between border-t border-line pt-3.5 text-left">
                <span className="text-[14.5px] text-body">{t('nextSettle')}</span>
                <span className="flex items-center gap-1 text-[14.5px] font-semibold text-ink">{s.today.settles_tomorrow_morning}, {t('settleWhen')}<ChevronRight size={17} className="text-faint" /></span>
              </button>
            </section>

            <button onClick={() => setTab('munim')} className="mt-3 flex w-full items-center gap-3.5 rounded-xl2 bg-navy px-5 py-4 text-left text-white">
              <Mascot size={44} />
              <span className="min-w-0 flex-1">
                <span className="block text-[17px] font-bold">{t('askMunim')}</span>
                <span className="block text-[13.5px] text-white/75">{t('askMunimSub')}</span>
              </span>
              <span className="grid h-11 w-11 flex-none place-items-center rounded-full bg-white text-navy"><Mic size={21} /></span>
            </button>

            <h2 className="mb-2 ml-1 mt-6 text-[17px] font-bold">{t('yourBiz')}</h2>
            <section className="overflow-hidden rounded-xl2 bg-white">
              {rows.map((r, i) => (
                <button key={r.k} onClick={() => go(r.q)} className={`flex w-full items-center gap-3.5 px-4 py-3.5 text-left active:bg-tint ${i ? 'border-t border-line' : ''}`}>
                  <span className="grid h-10 w-10 flex-none place-items-center rounded-xl bg-sky-soft text-navy">{r.icon}</span>
                  <span className="min-w-0 flex-1 text-[15.5px] font-semibold text-ink">{r.k}</span>
                  <span className={`rounded-full px-2.5 py-0.5 text-[13px] font-semibold ${{ good: 'bg-good-soft text-good', bad: 'bg-bad-soft text-bad', warn: 'bg-gold-soft text-gold-ink' }[r.tone]}`}>{r.v}</span>
                  <ChevronRight size={18} className="flex-none text-faint" />
                </button>
              ))}
            </section>

            <h2 className="mb-2 ml-1 mt-6 text-[17px] font-bold">{t('recentPay')}</h2>
            <section className="overflow-hidden rounded-xl2 bg-white">
              {s.recent_payments.length === 0 && <div className="px-4 py-5 text-[14.5px] text-muted">{t('noPayments')}</div>}
              {s.recent_payments.map((p: any, i: number) => (
                <div key={p.id} className={`flex items-center gap-3.5 px-4 py-3 ${i ? 'border-t border-line' : ''}`}>
                  <Initials name={p.payer} size={38} tone="tint" />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[15px] font-semibold text-ink">{p.payer}</span>
                    <span className="block text-[13px] text-muted">{p.status === 'success' ? hhmm(p.ts) : t('pendingPay')}</span>
                  </span>
                  <span className={`num text-[16px] font-bold ${p.status === 'success' ? 'text-good' : 'text-faint line-through'}`}>+ {inr(p.amount)}</span>
                </div>
              ))}
            </section>
          </main>
        )}

        {tab === 'qr' && (
          <main className="flex flex-1 flex-col items-center overflow-y-auto px-6 pb-6 pt-8">
            <section className="w-full max-w-[320px] overflow-hidden rounded-[28px] bg-white text-center">
              <div className="px-6 pb-5 pt-6">
                <div className="text-[22px] font-extrabold text-ink">{m.shop}</div>
                <div className="mt-0.5 text-[14px] text-muted">{t('scanPay')}</div>
                <div className="mx-auto mt-5 w-fit"><QRCodeSVG value={`upi://pay?pa=${upi}&pn=${encodeURIComponent(m.shop)}&cu=INR`} size={210} fgColor="#000000" level="M" /></div>
                <div className="mt-3 text-[13.5px] text-muted">{upi}</div>
              </div>
              <div className="bg-navy py-3 text-[14px] font-semibold text-white">{t('acceptsAll')}</div>
            </section>
          </main>
        )}

        {tab === 'munim' && (
        <main ref={scroller} className="flex-1 overflow-y-auto px-3.5 pb-2 pt-4">
          <div className="flex flex-col gap-2.5 pb-1.5">
            {s.messages.length === 0 && <Bot><Bubble>{t('hello', { name: m.owner.split(' ')[0] })}</Bubble></Bot>}
            <AnimatePresence initial={false}>
              {s.messages.map((x: Msg) => <Message key={x.id} m={x} lang={lang} held={held || s.settlements[0]} kycOk={kycOk} onVerify={() => setSheet(true)} />)}
            </AnimatePresence>
            <AnimatePresence>
              {working && (
                <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="flex items-end gap-2">
                  <Mascot size={30} />
                  <div className="flex items-center gap-2.5 rounded-[18px] rounded-bl-md bg-white px-3.5 py-2.5 text-[15px] text-navy">
                    <span className="dots"><i /><i /><i /></span>{t(working)}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </main>
        )}

        {tab === 'munim' && (
        <footer className="border-t border-line bg-white px-3 pt-3">
          <div className="no-scrollbar -mx-3 flex gap-2 overflow-x-auto px-3 pb-2.5">
            {sug.map(([Icon, label, msg]) => (
              <motion.button whileTap={{ scale: .95 }} key={label} onClick={() => send(msg)}
                className="flex flex-none items-center gap-1.5 rounded-full border border-navy/25 bg-white px-3.5 py-2 text-[14px] font-semibold text-navy"><Icon size={15} />{label}</motion.button>
            ))}
          </div>
          <div className="flex items-center gap-2 pb-2.5">
            <input value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && send()} placeholder={t('typeHere')}
              aria-label={t('typeHere')} className="min-w-0 flex-1 rounded-full bg-tint px-4 py-3 text-[15px] outline-none focus:ring-2 focus:ring-sky" />
            {text.trim() && (
              <motion.button initial={{ scale: 0 }} animate={{ scale: 1 }} onClick={() => send()} aria-label="Send"
                className="grid h-11 w-11 flex-none place-items-center rounded-full bg-sky text-navy"><Send size={19} /></motion.button>
            )}
            <div className="relative flex-none">
              {rec && [0, 1].map((i) => (
                <motion.span key={i} className="absolute inset-0 rounded-full bg-bad-solid" initial={{ scale: 1, opacity: .45 }}
                  animate={{ scale: 1.9, opacity: 0 }} transition={{ duration: 1.4, repeat: Infinity, delay: i * .7 }} />
              ))}
              <motion.button whileTap={{ scale: .92 }} onClick={mic} aria-label={rec ? t('listeningSend') : t('tapSpeak')}
                className={`relative grid h-[54px] w-[54px] place-items-center rounded-full text-white ${rec ? 'bg-bad-solid' : 'bg-navy'}`}>
                {rec ? <Send size={21} /> : <Mic size={24} />}
              </motion.button>
            </div>
          </div>
          {rec && <div className="-mt-1 pb-2 text-center text-[12.5px] font-semibold text-bad">{`${t('listeningSend')} 0:${String(recSecs).padStart(2, '0')}`}</div>}
          <input ref={filePick} type="file" accept="audio/*" capture className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) upload(f, f.name); e.target.value = ''; }} />
        </footer>
        )}

        <nav className="grid grid-cols-3 border-t border-line bg-white" style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}>
          {([['home', Home, t('tabHome')], ['munim', MessageCircle, t('tabMunim')], ['qr', QrCode, t('tabQR')]] as const).map(([k, I, label]) => (
            <button key={k} onClick={() => { setTab(k); if (k === 'munim') setUnread(false); }} aria-current={tab === k ? 'page' : undefined}
              className={`relative flex flex-col items-center gap-0.5 py-2 text-[12.5px] font-semibold ${tab === k ? 'text-navy' : 'text-faint'}`}>
              {k === 'munim' && unread && tab !== 'munim' && <span className="absolute right-[calc(50%-18px)] top-1.5 h-2.5 w-2.5 rounded-full bg-bad-solid ring-2 ring-white" />}
              <I size={22} strokeWidth={tab === k ? 2.4 : 1.8} />{label}
            </button>
          ))}
        </nav>

        <AnimatePresence>{sheet && <KycSheet onClose={() => setSheet(false)} onDone={async () => {
          await post('/api/kyc/complete', { merchant_id: mid }); setSheet(false); toast(t('kycDoneToast')); setWorking('w_release');
        }} />}</AnimatePresence>
        <AnimatePresence>{onboard && <Onboarding onDone={() => { try { localStorage.setItem('munim-onboarded', '1'); } catch {} Voice.unlock(); setOnboard(false); }} />}</AnimatePresence>
      </div>
    </div>
  );
}

function CountUp({ value }: { value: number }) {
  const [v, setV] = useState(value);
  const prev = useRef(value);
  useEffect(() => {
    const c = animate(prev.current, value, { duration: 1, ease: 'easeOut', onUpdate: (x) => setV(Math.round(x)) });
    prev.current = value; return () => c.stop();
  }, [value]);
  return <>{inr(v)}</>;
}

function Tile({ tone, icon, k, v, onClick }: { tone: 'good' | 'bad' | 'warn'; icon: React.ReactNode; k: string; v: string; onClick: () => void }) {
  const c = { good: 'bg-good-soft text-good', bad: 'bg-bad-soft text-bad', warn: 'bg-gold-soft text-gold-ink' }[tone];  // status colour = meaning
  return (
    <motion.button layout whileTap={{ scale: .95 }} onClick={onClick} className={`min-w-0 rounded-2xl px-2.5 py-2.5 text-left ${c}`}>
      <div className="flex items-center gap-1 text-[12.5px] font-semibold">{icon}<span className="truncate">{k}</span></div>
      <motion.div key={v} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} className="mt-1 text-[15px] font-bold leading-tight">{v}</motion.div>
    </motion.button>
  );
}

const pop = { initial: { opacity: 0, y: 12, scale: .97 }, animate: { opacity: 1, y: 0, scale: 1 }, transition: { type: 'spring' as const, stiffness: 380, damping: 30 } };
function Bot({ children }: { children: React.ReactNode }) {
  return <motion.div {...pop} className="flex items-end gap-2"><Mascot size={30} />{children}</motion.div>;
}
function Bubble({ children }: { children: React.ReactNode }) {
  return <div className="max-w-[80%] rounded-[18px] rounded-bl-md bg-white px-4 py-3 text-[16px] leading-relaxed text-ink">{children}</div>;
}

function Message({ m, lang, held, kycOk, onVerify }: { m: Msg; lang: Lang; held: any; kycOk: boolean; onVerify: () => void }) {
  const { t } = useLang();
  const via = m.channel === 'soundbox' ? <div className="mb-1 flex items-center gap-1 text-[11px] font-semibold opacity-75"><Radio size={12} />{t('viaSoundbox')}</div> : null;
  if (m.kind === 'alert') return (
    <motion.div {...pop} className="rounded-[20px] bg-bad-soft p-4 text-bad">
      <div className="flex items-center gap-2 text-[15px] font-bold"><ShieldAlert size={19} />{t('alertTitle')}</div>
      <p className="mt-1.5 text-[14px] leading-relaxed text-ink">{pick(m, lang)}</p>
      <div className="mt-2 text-[11.5px] font-semibold opacity-80">{t('alertBy')}, {hhmm(m.ts)}</div>
    </motion.div>
  );
  if (m.role === 'system') return (
    <motion.div {...pop} className="flex max-w-[92%] items-center gap-2 self-center rounded-full bg-tint px-3.5 py-1.5 text-[12.5px] font-semibold text-navy">
      <Bell size={15} className="text-sky-ink" />{t('noticed', { x: pick(m, lang) })}</motion.div>
  );
  if (m.role === 'merchant') return (
    <motion.div {...pop} className="flex justify-end">
      <div className="max-w-[80%] rounded-[18px] rounded-br-md bg-navy px-4 py-3 text-[16px] leading-relaxed text-white">
        {m.voice ? <div className="mb-1 flex items-center gap-1 text-[11px] font-semibold opacity-75"><Mic size={12} />{t('voiceNote')}</div> : via}
        {m.text}<div className="mt-1 text-right text-[11px] opacity-60">{hhmm(m.ts)}</div>
      </div>
    </motion.div>
  );
  if (m.kind === 'kyc') return (
    <motion.div {...pop} className="ml-[38px] rounded-[20px] bg-gold-soft p-4 text-navy-ink">
      <div className="flex items-center gap-2 text-[15px] font-bold"><IdCard size={18} />{t('kycTitle')}</div>
      <p className="mb-3 mt-1.5 text-[13.5px] leading-snug">{t('kycText', { amt: held ? inr(held.amount) : '' })}</p>
      {kycOk ? <span className="inline-flex items-center gap-1.5 rounded-full bg-good-soft px-3 py-1 text-[13px] font-semibold text-good"><CircleCheck size={15} />{t('verified')}</span>
        : <motion.button whileTap={{ scale: .96 }} onClick={onVerify} className="inline-flex items-center gap-2 rounded-xl bg-navy px-4 py-2.5 text-[15px] font-semibold text-white"><ShieldCheck size={18} />{t('verifyNow')}</motion.button>}
    </motion.div>
  );
  if (m.kind === 'credit') {
    const d = typeof m.data === 'string' ? JSON.parse(m.data) : m.data || {};
    return (
      <motion.div {...pop} className="ml-[38px] flex items-center gap-3 rounded-[20px] bg-good-soft p-4 text-good">
        <motion.div initial={{ scale: 0, rotate: -90 }} animate={{ scale: 1, rotate: 0 }} transition={{ type: 'spring', delay: .15 }}><CircleCheck size={30} /></motion.div>
        <div><div className="text-[17px] font-bold">{t('credited', { amt: d.amount })}</div><div className="text-[13px] text-ink">{t('inBank', { bank: d.credited_to })}, {hhmm(m.ts)}</div></div>
      </motion.div>
    );
  }
  const say = pick(m, lang);
  return (
    <Bot><Bubble>{via}{say}
      <div><button onClick={() => Voice.say(say, lang)} className="mt-1.5 inline-flex items-center gap-1 text-xs font-semibold text-sky-ink"><Volume2 size={15} />{t('listen')}</button></div>
    </Bubble></Bot>
  );
}

function KycSheet({ onClose, onDone }: { onClose: () => void; onDone: () => Promise<void> }) {
  const { t } = useLang();
  const digits = '428196'.split('');
  const [n, setN] = useState(0), [busy, setBusy] = useState(false);
  useEffect(() => { if (n < 6) { const x = setTimeout(() => setN(n + 1), n ? 160 : 400); return () => clearTimeout(x); } }, [n]);
  return (
    <motion.div className="absolute inset-0 z-20 flex items-end bg-navy-ink/45" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose}>
      <motion.div role="dialog" aria-label={t('otpTitle')} className="w-full rounded-t-[26px] bg-white px-5 pt-6" style={{ paddingBottom: 'calc(22px + env(safe-area-inset-bottom, 0px))' }}
        initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }} transition={{ type: 'spring', stiffness: 320, damping: 32 }} onClick={(e) => e.stopPropagation()}>
        <h3 className="text-xl font-bold text-navy">{t('otpTitle')}</h3>
        <p className="mb-4 mt-1 text-sm text-muted">{t('otpSent')}</p>
        <div className="mb-5 flex gap-2">{digits.map((d, i) => (
          <div key={i} className="grid h-[52px] flex-1 place-items-center rounded-xl bg-tint text-2xl font-bold text-navy">
            <AnimatePresence>{i < n && <motion.span initial={{ y: 10, opacity: 0 }} animate={{ y: 0, opacity: 1 }}>{d}</motion.span>}</AnimatePresence>
          </div>))}
        </div>
        <motion.button whileTap={{ scale: .97 }} disabled={n < 6 || busy} onClick={async () => { setBusy(true); await onDone(); }}
          className="w-full rounded-xl bg-navy py-3.5 text-base font-semibold text-white disabled:opacity-50">{busy ? <span className="dots"><i /><i /><i /></span> : t('verify')}</motion.button>
        <div className="mt-2.5 text-center text-xs text-faint">{t('demoNote')}</div>
      </motion.div>
    </motion.div>
  );
}

function Onboarding({ onDone }: { onDone: () => void }) {
  const { t, setLang, lang } = useLang();
  const [step, setStep] = useState(0);
  const icon = (I: typeof Mic, bg: string) => <div className={`grid h-24 w-24 place-items-center rounded-[28px] ${bg}`}><I size={46} /></div>;
  const slides: { title: Key; body: Key; art: React.ReactNode }[] = [
    { title: 'ob1t', body: 'ob1b', art: <Mascot size={96} /> },
    { title: 'ob2t', body: 'ob2b', art: icon(Mic, 'bg-sky-soft text-navy') },
    { title: 'ob3t', body: 'ob3b', art: icon(ShieldCheck, 'bg-good-soft text-good') },
  ];
  return (
    <motion.div className="absolute inset-0 z-30 flex flex-col bg-white text-ink" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      style={{ paddingTop: 'calc(20px + env(safe-area-inset-top, 0px))', paddingBottom: 'calc(24px + env(safe-area-inset-bottom, 0px))' }}>
      <div className="flex h-8 justify-end px-5">{step > 0 && <button onClick={onDone} className="text-[15px] font-semibold text-muted">{t('skip')}</button>}</div>
      <div className="flex flex-1 flex-col justify-center px-7">
        <AnimatePresence mode="wait">
          {step === 0 ? (
            <motion.div key="lang" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex w-full flex-col">
              <Mascot size={64} />
              <h1 className="mt-6 text-[30px] font-extrabold leading-tight">नमस्ते!<br />Namaste!</h1>
              <p className="mb-7 mt-2 text-[17px] leading-snug text-muted">अपनी भाषा चुनिए<br />Choose your language</p>
              <div className="grid w-full gap-3">
                {([['hi', 'हिंदी', 'Hindi'], ['en', 'English', 'अंग्रेज़ी']] as const).map(([k, a, b]) => (
                  <motion.button key={k} whileTap={{ scale: .98 }} onClick={() => { setLang(k); Voice.unlock(); setStep(1); }}
                    className={`flex items-center justify-between rounded-2xl border px-5 py-4 text-left ${lang === k ? 'border-navy bg-sky-softer' : 'border-line bg-white'}`}>
                    <span className="text-[20px] font-bold text-ink">{a}</span><span className="text-[14px] text-muted">{b}</span></motion.button>
                ))}
              </div>
            </motion.div>
          ) : (
            <motion.div key={step} initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -24 }} className="flex flex-col">
              <div className="mb-8">{slides[step - 1].art}</div>
              <h1 className="text-[30px] font-extrabold leading-tight">{t(slides[step - 1].title)}</h1>
              <p className="mt-3 text-[17px] leading-relaxed text-body">{t(slides[step - 1].body)}</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
      {step > 0 && (
        <div className="px-6">
          <div className="mb-5 flex gap-1.5">{[1, 2, 3].map((i) => <motion.span key={i} animate={{ width: i === step ? 24 : 8 }} className={`h-2 rounded-full ${i === step ? 'bg-navy' : 'bg-line'}`} />)}</div>
          <motion.button whileTap={{ scale: .98 }} onClick={() => (step < 3 ? setStep(step + 1) : onDone())} className="w-full rounded-full bg-navy py-4 text-[17px] font-bold text-white">
            {step < 3 ? t('next') : t('start')}
          </motion.button>
        </div>
      )}
    </motion.div>
  );
}
