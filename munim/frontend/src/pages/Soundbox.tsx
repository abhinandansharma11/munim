import { AnimatePresence, motion } from 'framer-motion';
import { Mic, Send, ShieldAlert, Volume2, WifiOff } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { get, inr, post, sendVoice, shopFromUrl } from '../lib/api';
import { useLang } from '../lib/i18n';
import { useLive } from '../lib/live';
import { PhoneListen, Recorder, Voice, serverHasVoice } from '../lib/voice';
import { LangToggle } from '../components/LangToggle';
import { useToast } from '../components/Toast';

type Screen = 'ready' | 'received' | 'listening' | 'thinking' | 'speaking';

export default function Soundbox() {
  const { lang, t } = useLang();
  const toast = useToast();
  const [mid, setMid] = useState(shopFromUrl() || 'M1001');
  const [shop, setShop] = useState('');
  const [alert, setAlert] = useState(false);
  const alertT = useRef<number>();
  const [pending, setPending] = useState<{ hi: string; en: string; id?: string } | null>(null);
  const buzzT = useRef<number>();
  const asking = useRef(false);
  const [online, setOnline] = useState(true);
  const [screen, setScreen] = useState<Screen>('ready');
  const [amount, setAmount] = useState(0);
  const [caption, setCaption] = useState('');
  const [unlocked, setUnlocked] = useState(false);
  const [rec, setRec] = useState(false);
  const langRef = useRef(lang); langRef.current = lang;

  const heardKey = (id: string) => 'munim-heard-' + id;
  const load = async (id = mid) => {
    try {
      const s = await get('/api/merchant/' + id); setOnline(s.device?.status === 'online'); setShop(s.merchant.shop);
      // A fraud alert raised while this Soundbox was off or not yet open: show it now, until it has been heard.
      const a = s.area_alert;
      let heard = false; try { heard = !!(a && localStorage.getItem(heardKey(a.id))); } catch {}
      if (a && !heard) { setAlert(true); setPending((p) => p || { hi: a.hi, en: a.en, id: a.id }); }
    } catch {}
  };
  useEffect(() => {
    if (shopFromUrl()) { load(); return; }
    get('/api/info').then((i) => { setMid(i.merchant_id); load(i.merchant_id); }).catch(() => load());
  }, []);
  useEffect(() => { setCaption(t('sbIntro')); }, [lang]);
  useEffect(() => { const i = window.setInterval(() => load(), 5000); return () => clearInterval(i); }, [mid]);

  const say = (hi: string, en: string) => {
    const l = langRef.current, line = l === 'hi' ? hi : en;
    setCaption(line);
    Voice.say(line, l, { onStart: () => setScreen('speaking'), onEnd: () => setScreen('ready') });
  };

  useLive((ev) => {
    if (ev.merchant_id && ev.merchant_id !== mid) return;
    if (ev.type === 'device' || ev.type === 'state' || ev.type === 'reset' || ev.type === 'poll') load();
    if (ev.type === 'payment') {
      if (ev.announced) { setAmount(ev.amount); setScreen('received'); Voice.chime(); }
      else setCaption(t('sbMissed', { amt: inr(ev.amount) }));
    }
    if (ev.type === 'announce' && ev.alert) {
      // Fraud alert for the whole area: red screen, it beeps and vibrates until the shopkeeper taps to listen.
      setAlert(true); clearTimeout(alertT.current); alertT.current = window.setTimeout(() => setAlert(false), 120000);
      setPending({ hi: ev.speak || ev.text, en: ev.en || ev.text, id: ev.alert_id });
      return;
    }
    if (ev.type === 'announce') {
      const amt = /₹([\d,]+)/.exec(ev.text || '')?.[1];
      say(ev.speak || ev.text, ev.en || (amt ? `Received ${amt} rupees.` : ev.text));
    }
    if (ev.type === 'phase' && ev.merchant_id === mid && asking.current && screen !== 'speaking') setScreen('thinking');
    if (ev.type === 'phase' && ev.merchant_id === mid && ['done', 'idle'].includes(ev.phase)) asking.current = false;
    if (ev.type === 'message' && ev.channel === 'soundbox' && (ev.speak || ev.en)) say(ev.speak || ev.text, ev.en || ev.text);
  });

  // Buzz: two beeps and a vibration every 4 seconds while an alert waits to be heard (stops after ~1 minute).
  useEffect(() => {
    if (!pending) return;
    let n = 0;
    const buzz = () => { Voice.chime(); setTimeout(() => Voice.chime(), 350); Voice.vibrate([300, 150, 300, 150, 300]); if (++n >= 15) clearInterval(buzzT.current); };
    buzz(); buzzT.current = window.setInterval(buzz, 4000);
    return () => clearInterval(buzzT.current);
  }, [pending]);
  const hear = () => {
    if (!pending) return;
    Voice.unlock(); clearInterval(buzzT.current);
    if (pending.id) { try { localStorage.setItem(heardKey(pending.id), '1'); } catch {} }
    say(pending.hi, pending.en); setPending(null);
  };

  const ask = async (q: string) => {
    asking.current = true;
    setCaption(t('sbAsked', { q })); setScreen('thinking');
    try { await post('/api/message', { merchant_id: mid, text: q, channel: 'soundbox' }); } catch (e: any) { toast(e.message); setScreen('ready'); }
  };
  const talk = async () => {
    Voice.unlock();
    if (PhoneListen.active) { PhoneListen.stop(); return; }
    if (!Recorder.active && !(await serverHasVoice()) && PhoneListen.supported()) {
      setRec(true); setScreen('listening');
      PhoneListen.start(lang, (txt) => { setRec(false); if (txt) ask(txt); else { setScreen('ready'); toast(t('micNothing')); } }, () => setRec(false));
      return;
    }
    if (Recorder.active) {
      setRec(false); setScreen('thinking');
      const b = await Recorder.stop();
      asking.current = true;
      if (b) { try { const tx = await sendVoice(b, 'voice.wav', mid, 'soundbox'); if (tx) setCaption(t('sbAsked', { q: tx })); } catch (e: any) { toast(e.message, 4500); setScreen('ready'); } }
      return;
    }
    if (!Recorder.supported()) { toast(t('micHttps')); return; }
    try { await Recorder.start(20, () => talk()); setRec(true); setScreen('listening'); } catch { toast(t('micBlocked')); }
  };

  const presets = lang === 'hi' ? ['आज कितना आया?', 'दुकान बंद, आज का हिसाब सुनाओ'] : ['How much came today?', 'Closing the shop, tell me today\'s total'];
  const label = !online ? t('sbNoNet') : alert && screen !== 'listening' ? t('sbAlert') : { ready: t('sbReady'), received: t('sbReceived'), listening: t('sbListening'), thinking: t('sbThinking'), speaking: t('sbSpeaking') }[screen];

  return (
    <div className="relative flex h-full flex-col items-center overflow-hidden bg-sky-soft px-5"
      style={{ paddingTop: 'calc(16px + env(safe-area-inset-top, 0px))', paddingBottom: 'calc(20px + env(safe-area-inset-bottom, 0px))' }}>
      <div className="flex w-full max-w-sm items-center justify-between">
        <div className="min-w-0 text-sm font-bold text-navy"><div>Paytm Soundbox</div>{shop && <div className="truncate text-[12px] font-semibold text-muted">{shop}</div>}</div>
        <LangToggle />
      </div>

      <div className="relative mt-6 flex flex-1 flex-col items-center justify-center">
        {/* sound rings */}
        <AnimatePresence>{online && (screen === 'speaking' || screen === 'received') && [0, 1, 2].map((i) => (
          <motion.span key={i} className={`absolute h-[260px] w-[260px] rounded-full ${alert ? 'bg-bad-solid' : 'bg-sky'}`}
            initial={{ scale: .8, opacity: .35 }} animate={{ scale: 1.5, opacity: 0 }} exit={{ opacity: 0 }}
            transition={{ duration: 1.8, repeat: Infinity, delay: i * .6 }} />
        ))}</AnimatePresence>

        <motion.div onClick={hear} animate={pending ? { rotate: [0, -3, 3, -3, 3, 0] } : screen === 'received' ? { rotate: [0, -2, 2, -1, 0] } : { rotate: 0 }}
          transition={pending ? { duration: .6, repeat: Infinity, repeatDelay: 1 } : { duration: .5 }}
          className={`relative flex h-[330px] w-[230px] flex-col items-center rounded-[46px] pt-6 shadow-lift ${online ? 'bg-navy' : 'bg-[#2A3550]'}`}>
          <div className="text-[13px] font-bold tracking-widest text-sky">paytm</div>
          {/* screen */}
          <motion.div animate={alert ? { backgroundColor: ['#FDE4E5', '#F9B8BB', '#FDE4E5'] } : {}} transition={{ duration: 1.2, repeat: alert ? Infinity : 0 }}
            className={`mt-3 flex h-[92px] w-[170px] flex-col items-center justify-center rounded-2xl ${alert ? 'bg-bad-soft' : online ? 'bg-[#E9F8FE]' : 'bg-[#C8CEDA]'}`}>
            <AnimatePresence mode="wait">
              <motion.div key={label + amount} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} className="text-center">
                {!online ? <WifiOff size={26} className="mx-auto text-bad" /> : alert && screen !== 'listening' ? <ShieldAlert size={30} className="mx-auto text-bad" /> : screen === 'received' ? <div className="text-[28px] font-extrabold text-navy">{inr(amount)}</div> : null}
                <div className={`text-[13px] font-bold tracking-wider ${online && !alert ? 'text-navy' : 'text-bad'}`}>{label}</div>
              </motion.div>
            </AnimatePresence>
          </motion.div>
          {/* speaker grill */}
          <div className="mt-6 grid grid-cols-7 gap-[9px]">
            {Array.from({ length: 35 }).map((_, i) => (
              <motion.span key={i} className={`h-[9px] w-[9px] rounded-full ${online ? 'bg-[#0B3C8F]' : 'bg-[#3A4660]'}`}
                animate={screen === 'speaking' ? { scale: [1, 1.5, 1], backgroundColor: ['#0B3C8F', '#00BAF2', '#0B3C8F'] } : { scale: 1 }}
                transition={{ duration: .6, repeat: screen === 'speaking' ? Infinity : 0, delay: (i % 7) * .05 + Math.floor(i / 7) * .04 }} />
            ))}
          </div>
          <div className={`absolute bottom-5 h-3.5 w-3.5 rounded-full ${online ? 'bg-[#2BD37B]' : 'bg-bad-solid'}`} />
        </motion.div>

        <AnimatePresence mode="wait">
          {pending ? (
            <motion.button key="hear" onClick={hear} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0, scale: [1, 1.05, 1] }}
              transition={{ scale: { duration: 1, repeat: Infinity } }} exit={{ opacity: 0 }}
              className="mt-7 flex items-center gap-2.5 rounded-2xl bg-bad-solid px-5 py-4 text-[17px] font-bold text-white shadow-lift">
              <Volume2 size={24} />{t('sbNewAlert')}
            </motion.button>
          ) : (
          <motion.p key={caption} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className={`mt-7 min-h-[52px] max-w-xs text-center text-[16px] font-medium leading-snug ${alert ? 'rounded-2xl bg-bad-soft px-4 py-3 text-bad' : 'text-navy'}`}>{caption}</motion.p>
          )}
        </AnimatePresence>
      </div>

      <div className="w-full max-w-sm">
        <div className="mb-3 flex flex-wrap justify-center gap-2">
          {presets.map((p) => (
            <motion.button key={p} whileTap={{ scale: .95 }} onClick={() => ask(p)} className="rounded-full border border-navy/25 bg-white px-4 py-2 text-[14px] font-semibold text-navy">{p}</motion.button>
          ))}
        </div>
        <motion.button whileTap={{ scale: .96 }} onClick={talk}
          className={`flex w-full items-center justify-center gap-2.5 rounded-full py-4 text-lg font-bold ${rec ? 'bg-bad-solid text-white' : 'bg-navy text-white'}`}>
          {rec ? <Send size={22} /> : <Mic size={22} />}{rec ? t('sbSend') : t('sbAsk')}
        </motion.button>
      </div>

      <AnimatePresence>{!unlocked && (
        <motion.button initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          onClick={() => { Voice.unlock(); Voice.keepAwake(); setUnlocked(true); }}
          className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-4 bg-navy/90 px-8 text-center text-white">
          <motion.div animate={{ scale: [1, 1.08, 1] }} transition={{ duration: 1.6, repeat: Infinity }} className="grid h-24 w-24 place-items-center rounded-full bg-gold text-navy">
            <Volume2 size={44} /></motion.div>
          <div className="text-xl font-bold">{t('sbUnlock')}</div>
        </motion.button>
      )}</AnimatePresence>
    </div>
  );
}
