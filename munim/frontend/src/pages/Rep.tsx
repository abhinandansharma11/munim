import { AnimatePresence, motion } from 'framer-motion';
import { CalendarCheck, MapPin, Phone, Sparkles, Store } from 'lucide-react';
import { useEffect, useState } from 'react';
import { get } from '../lib/api';
import { useLang } from '../lib/i18n';
import { useLive } from '../lib/live';
import { Voice } from '../lib/voice';
import { Initials, Mascot } from '../components/Art';
import { LangToggle } from '../components/LangToggle';
import { useToast } from '../components/Toast';

const PRODUCT_HI: Record<string, string> = {
  'Working-capital loan': 'बिज़नेस लोन', 'Card machine for the new outlet': 'नई दुकान के लिए कार्ड मशीन',
  'Install Soundbox at the new outlet': 'नई दुकान में साउंडबॉक्स लगाना',
};
const WHEN_HI: [RegExp, string][] = [[/tomorrow/i, 'कल'], [/today/i, 'आज'], [/\bam\b/i, 'सुबह'], [/\bpm\b/i, 'शाम']];

export default function Rep() {
  const { lang, t } = useLang();
  const toast = useToast();
  const [leads, setLeads] = useState<any[]>([]);
  const [fresh, setFresh] = useState<string | null>(null);
  const REP = 'Anil Verma';

  const load = () => get('/api/leads?rep=' + encodeURIComponent(REP)).then(setLeads).catch(() => {});
  useEffect(() => { load(); const u = () => Voice.unlock(); document.addEventListener('pointerdown', u, { once: true }); }, []);
  useLive(async (ev) => {
    if (ev.type === 'lead') {
      // The server sends every new lead to everyone; this phone only alerts if the lead is for one of Anil's shops.
      const mine = await get('/api/leads?rep=' + encodeURIComponent(REP)).catch(() => null);
      if (mine) setLeads(mine);
      if (mine?.some((l: any) => l.id === ev.lead_id)) {
        setFresh(ev.lead_id); Voice.chime(); try { navigator.vibrate?.([120, 60, 120]); } catch {}
        toast(t('newLead')); setTimeout(() => setFresh(null), 6000);
      }
      return;
    }
    if (['reset', 'poll', 'state'].includes(ev.type)) load();
  });

  const visits = leads.filter((l) => l.visit).length;
  const when = (v: string) => {
    const w = v.split(':')[0];
    if (lang !== 'hi') return w;
    const m = /(tomorrow|today)?\s*(\d{1,2})(?::(\d\d))?\s*(am|pm)/i.exec(w);
    if (!m) return WHEN_HI.reduce((s, [r, h]) => s.replace(r, h), w);
    const day = m[1] ? (m[1].toLowerCase() === 'today' ? 'आज ' : 'कल ') : '';
    const h = +m[2], part = m[4].toLowerCase() === 'am' ? 'सुबह' : h < 4 || h === 12 ? 'दोपहर' : 'शाम';
    return `${day}${part} ${h}${m[3] ? ':' + m[3] : ''} बजे`;
  };

  return (
    <div className="h-full bg-[#DDE5F0]">
      <div className="mx-auto flex h-full max-w-[440px] flex-col bg-page">
        <header className="border-b border-line bg-white px-4 pb-4 text-ink" style={{ paddingTop: 'calc(14px + env(safe-area-inset-top, 0px))' }}>
          <div className="flex items-center gap-3">
            <Initials name={REP} size={42} tone="gold" />
            <div className="flex-1"><div className="text-[18px] font-bold text-ink">{REP}</div><div className="text-[13px] text-muted">{t('repSub')}</div></div>
            <LangToggle />
          </div>
          <div className="mt-4 grid grid-cols-2 gap-2.5">
            <Stat n={leads.length} k={t('leads')} />
            <Stat n={visits} k={t('visits')} />
          </div>
        </header>
        <div className="stripe" />

        <main className="flex-1 overflow-y-auto px-3.5 py-4">
          <div className="mb-3 flex items-center gap-2 px-1 text-[15px] font-bold text-navy"><Sparkles size={17} className="text-sky-ink" />{t('newBriefs')}</div>
          {leads.length === 0 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-10 flex flex-col items-center px-6 text-center">
              <Mascot size={56} />
              <div className="mt-4 text-lg font-bold text-navy">{t('noLeads')}</div>
              <p className="mt-1 text-sm leading-relaxed text-muted">{t('noLeadsSub')}</p>
            </motion.div>
          )}
          <div className="flex flex-col gap-3">
            <AnimatePresence initial={false}>
              {leads.map((l) => (
                <motion.article layout key={l.id} initial={{ opacity: 0, y: -16, scale: .97 }} animate={{ opacity: 1, y: 0, scale: 1 }}
                  transition={{ type: 'spring', stiffness: 300, damping: 26 }}
                  className={`rounded-xl2 bg-white p-5 ${fresh === l.id ? 'ring-4 ring-gold' : ''}`}>
                  <div className="flex items-start gap-3">
                    <div className="grid h-11 w-11 flex-none place-items-center rounded-2xl bg-sky-soft text-navy"><Store size={21} /></div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <div className="truncate text-[17px] font-bold text-ink">{l.shop}</div>
                        {fresh === l.id && <span className="rounded-full bg-gold px-2 py-0.5 text-[11px] font-bold text-navy">{t('isNew')}</span>}
                      </div>
                      <div className="flex items-center gap-1 text-[12.5px] text-muted"><MapPin size={13} />{l.owner}, {l.city}</div>
                    </div>
                  </div>
                  <div className="mt-3 inline-block rounded-full bg-gold-soft px-3 py-1 text-[13px] font-bold text-gold-ink">
                    {lang === 'hi' ? PRODUCT_HI[l.product] || l.product : l.product}
                  </div>
                  <p className="mt-2.5 text-[15px] leading-relaxed text-body">{lang === 'hi' ? l.brief_hi || l.brief : l.brief}</p>
                  <div className="mt-1.5 flex items-center gap-1.5 text-[11.5px] text-faint"><Mascot size={16} />{t('briefBy')}</div>
                  <div className="mt-3.5 flex items-center gap-2">
                    {l.visit && <div className="flex flex-1 items-center gap-1.5 rounded-xl bg-good-soft px-3 py-2.5 text-[13px] font-semibold text-good">
                      <CalendarCheck size={16} />{t('visitBooked')}: {when(l.visit)}</div>}
                    <a href={`tel:${l.phone || ''}`} className={`flex items-center justify-center gap-1.5 rounded-xl bg-navy px-4 py-2.5 text-[14px] font-semibold text-white ${l.visit ? '' : 'flex-1'}`}>
                      <Phone size={16} />{t('call')}</a>
                  </div>
                </motion.article>
              ))}
            </AnimatePresence>
          </div>
        </main>
      </div>
    </div>
  );
}

function Stat({ n, k }: { n: number; k: string }) {
  return (
    <div className="rounded-2xl bg-tint px-4 py-3">
      <motion.div key={n} initial={{ scale: 1.3, color: '#00BAF2' }} animate={{ scale: 1, color: '#000000' }} className="num text-[30px] font-extrabold leading-none">{n}</motion.div>
      <div className="mt-1 text-[13px] text-muted">{k}</div>
    </div>
  );
}
