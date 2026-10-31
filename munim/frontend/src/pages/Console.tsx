import { AnimatePresence, motion } from 'framer-motion';
import {
  Ban, Bell, CheckCheck, CircleCheck, Clock3, Eye, FlaskConical, Hand, KeyRound, Lightbulb, MessageCircle, Mic, QrCode, Radio,
  RotateCcw, Send, ShieldAlert, ShieldCheck, UserPlus, Smartphone, Sparkles, Store, Undo2, UserRound, Wand2, X, Zap, IndianRupee, Power, Copy,
} from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { get, hhmm, post } from '../lib/api';
import { Key, Lang, TOOL_HI, pick, useLang } from '../lib/i18n';
import { useLive } from '../lib/live';
import { Mascot } from '../components/Art';
import { LangToggle } from '../components/LangToggle';
import { useToast } from '../components/Toast';

const PHASES = ['observe', 'think', 'act', 'check'] as const;
const STATUS_TONE: Record<string, string> = {
  open: 'bg-sky-soft text-sky-ink', resolved: 'bg-good-soft text-good', waiting_merchant: 'bg-gold-soft text-gold-ink',
  waiting_human: 'bg-bad-soft text-bad', handed_over: 'bg-tint text-muted',
};
const TIER: Record<string, { k: Key; c: string; I: typeof Eye }> = {
  read: { k: 't_read', c: 'bg-tint text-muted', I: Eye }, auto: { k: 't_auto', c: 'bg-good-soft text-good', I: Zap },
  merchant: { k: 't_merchant', c: 'bg-gold-soft text-gold-ink', I: Store }, human: { k: 't_human', c: 'bg-bad-soft text-bad', I: Hand },
};
const APPROVERS = ['Priya S.', 'Rohan M.', 'Kavya T.'];

export default function Console() {
  const { lang, t } = useLang();
  const toast = useToast();
  const [cases, setCases] = useState<any[]>([]);
  const [sel, setSel] = useState<string | null>(null);
  const [detail, setDetail] = useState<any>(null);
  const [phase, setPhase] = useState<Record<string, string>>({});
  const [stats, setStats] = useState<any>({});
  const [ledger, setLedger] = useState<any[]>([]);
  const [leads, setLeads] = useState(0);
  const [by, setBy] = useState(APPROVERS[0]);
  const [demo, setDemo] = useState(false);
  const selRef = useRef(sel); selRef.current = sel;
  const pinned = useRef(false);

  const loadAll = async () => {
    const [c, s, l, ld] = await Promise.all([get('/api/cases'), get('/api/stats'), get('/api/ledger'), get('/api/leads')]).catch(() => [null, null, null, null]);
    if (!c) return;
    setCases(c); setStats(s); setLedger(l); setLeads(ld.length);
    if (!selRef.current && c[0]) setSel(c[0].id);
    if (!c.length) { setSel(null); setDetail(null); }
  };
  const loadCase = async (id = selRef.current) => { if (id) try { setDetail(await get('/api/case/' + id)); } catch {} };
  useEffect(() => { loadAll(); }, []);
  useEffect(() => { loadCase(sel); }, [sel]);

  const tmr = useRef<number>();
  useLive((ev) => {
    if (ev.type === 'phase') setPhase((p) => ({ ...p, [ev.case_id]: ev.phase }));
    if (ev.type === 'reset') { setSel(null); setDetail(null); setPhase({}); pinned.current = false; }
    // Follow the newest case unless the person picked one by hand.
    if (ev.case_id && !pinned.current && ev.case_id !== selRef.current && (ev.type === 'message' || ev.type === 'step')) setSel(ev.case_id);
    if (ev.type === 'approval') toast(t('needsOk'));
    clearTimeout(tmr.current);
    tmr.current = window.setTimeout(() => { loadAll(); loadCase(); }, 100);
  });

  const c = detail?.case;
  const curPhase = c ? phase[c.id] : undefined;
  const pendingAp = detail?.approvals?.find((a: any) => a.status === 'pending');
  const said = detail?.messages?.find((m: any) => m.role === 'merchant' || m.role === 'system');

  return (
    <div className="flex h-full flex-col bg-page">
      <header className="border-b border-line bg-white text-ink">
        <div className="flex items-center gap-3 px-5 py-2.5">
          <Mascot size={34} />
          <div className="flex items-baseline gap-2.5 whitespace-nowrap"><span className="text-[22px] font-extrabold text-ink">Munim</span>
            <span className="border-l border-line pl-2.5 text-[15px] text-muted">{t('desk')}</span></div>
          <div className="flex-1" />
          <span className="flex items-center gap-1.5 whitespace-nowrap text-[14px] font-semibold text-good"><span className="relative flex h-2.5 w-2.5">
            <span className="absolute inset-0 animate-ping rounded-full bg-[#2BD37B] opacity-60" /><span className="relative h-2.5 w-2.5 rounded-full bg-[#2BD37B]" /></span>Live</span>
          <label className="flex items-center gap-2 whitespace-nowrap text-[14px] text-muted">{t('approver')}
            <select value={by} onChange={(e) => setBy(e.target.value)} className="rounded-full border border-line bg-white px-3 py-1.5 text-[14px] font-semibold text-ink outline-none">
              {APPROVERS.map((a) => <option key={a} className="text-ink">{a}</option>)}</select></label>
          <LangToggle />
          <motion.button whileTap={{ scale: .95 }} onClick={() => setDemo(true)} className="flex items-center gap-1.5 rounded-full bg-navy px-4 py-2 text-[14px] font-semibold text-white">
            <Wand2 size={16} />{t('demo')}</motion.button>
        </div>
      </header>

      <div className="grid min-h-0 flex-1 grid-cols-[280px_1fr_330px] gap-4 p-4">
        {/* cases */}
        <aside className="flex min-h-0 flex-col rounded-xl2 bg-white">
          <div className="px-4 pb-2 pt-4 text-[17px] font-bold text-ink">{t('liveCases')}</div>
          <div className="flex-1 overflow-y-auto px-2.5 pb-3">
            {cases.length === 0 && <p className="px-2 py-6 text-sm text-muted">{t('noCases')}</p>}
            <AnimatePresence initial={false}>
              {cases.map((x) => (
                <motion.button layout key={x.id} initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }}
                  onClick={() => { pinned.current = true; setSel(x.id); }}
                  className={`relative mb-1.5 w-full rounded-2xl px-3 py-2.5 text-left ${sel === x.id ? 'text-white' : 'hover:bg-tint'}`}>
                  {sel === x.id && <motion.span layoutId="caseSel" className="absolute inset-0 rounded-2xl bg-navy" transition={{ type: 'spring', stiffness: 400, damping: 34 }} />}
                  <div className="relative">
                    <div className="flex items-center gap-2">
                      <span className="truncate text-[14px] font-semibold">{x.shop}</span>
                      {phase[x.id] && !['done', 'idle'].includes(phase[x.id]) && <span className="dots ml-auto text-sky"><i /><i /><i /></span>}
                    </div>
                    <div className={`truncate text-[12.5px] ${sel === x.id ? 'text-[#CFE0F7]' : 'text-muted'}`}>{x.title}</div>
                    <div className="mt-1.5 flex items-center gap-1.5">
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${STATUS_TONE[x.status] || 'bg-tint text-muted'}`}>{t(('s_' + x.status) as Key) || x.status}</span>
                      <ChannelIcon ch={x.channel} light={sel === x.id} />
                      <span className={`ml-auto text-[11px] ${sel === x.id ? 'text-[#CFE0F7]' : 'text-faint'}`}>{hhmm(x.updated)}</span>
                    </div>
                  </div>
                </motion.button>
              ))}
            </AnimatePresence>
          </div>
        </aside>

        {/* the case */}
        <section className="flex min-h-0 flex-col rounded-xl2 bg-white">
          {!c ? (
            <div className="flex flex-1 flex-col items-center justify-center px-10 text-center">
              <Mascot size={64} />
              <div className="mt-5 text-xl font-bold text-navy">{t('waiting')}</div>
              <p className="mt-1.5 max-w-md text-[15px] text-muted">{t('waitingSub')}</p>
            </div>
          ) : (
            <>
              <div className="flex items-start gap-4 px-6 pb-4 pt-5">
                <div className="grid h-12 w-12 flex-none place-items-center rounded-2xl bg-sky-soft text-navy"><Store size={24} /></div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2.5">
                    <h2 className="truncate text-[24px] font-extrabold text-ink">{c.shop}</h2>
                    <span className={`rounded-full px-2.5 py-0.5 text-[12px] font-semibold ${STATUS_TONE[c.status]}`}>{t(('s_' + c.status) as Key)}</span>
                  </div>
                  <div className="text-[14px] text-muted">{c.owner}, {c.city}</div>
                  {said && <div className="mt-2 inline-flex max-w-full items-center gap-2 rounded-2xl bg-tint px-3 py-1.5 text-[14px] text-ink">
                    {said.role === 'system' ? <Bell size={15} className="flex-none text-sky-ink" /> : said.voice ? <Mic size={15} className="flex-none text-sky-ink" /> : <MessageCircle size={15} className="flex-none text-sky-ink" />}
                    <span className="truncate">“{said.role === 'system' ? pick(said, lang) : said.text}”</span></div>}
                </div>
                <Loop phase={curPhase} status={c.status} />
              </div>
              <div className="flex-1 overflow-y-auto px-6 pb-6">
                <AnimatePresence>{pendingAp && <Approval key={pendingAp.id} ap={pendingAp} by={by} onDone={() => { loadCase(); loadAll(); }} />}</AnimatePresence>
                <ol className="relative ml-4 border-l-2 border-tint pl-6">
                  <AnimatePresence initial={false}>
                    {detail.steps.filter((s: any) => s.kind !== 'system').map((s: any) => <Step key={s.id} s={s} lang={lang} />)}
                  </AnimatePresence>
                </ol>
              </div>
            </>
          )}
        </section>

        {/* today */}
        <aside className="flex min-h-0 flex-col gap-4">
          <div className="grid grid-cols-2 gap-3">
            <Kpi I={CheckCheck} v={stats.resolved ?? 0} k={t('kSolved')} tone="good" />
            <Kpi I={Clock3} v={stats.avg_resolve_seconds != null ? `${Math.max(1, Math.round(stats.avg_resolve_seconds))}s` : '—'} k={t('kTime')} tone="sky" />
            <Kpi I={ShieldCheck} v={stats.blocked ?? 0} k={t('kBlocked')} tone="bad" />
            <Kpi I={Sparkles} v={leads} k={t('kLeads')} tone="gold" />
          </div>
          <SalesStrip s={stats.sales} />
          <CostPanel e={stats.economics} />
          <div className="flex min-h-0 flex-1 flex-col rounded-xl2 bg-white">
            <div className="px-4 pb-2 pt-4 text-[17px] font-bold text-ink">{t('activity')}</div>
            <div className="flex-1 overflow-y-auto px-3 pb-3">
              {ledger.length === 0 && <p className="px-1 py-4 text-sm text-muted">{t('nothingYet')}</p>}
              <AnimatePresence initial={false}>
                {ledger.map((s) => (
                  <motion.div layout key={s.id} initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-2.5 rounded-xl px-2 py-2 hover:bg-tint">
                    <div className={`grid h-8 w-8 flex-none place-items-center rounded-full ${s.status === 'blocked' ? 'bg-bad-soft text-bad' : s.actor === 'Munim' ? 'bg-sky-soft text-navy' : 'bg-gold-soft text-gold-ink'}`}>
                      {s.status === 'blocked' ? <Ban size={15} /> : s.actor === 'Munim' ? <Mascot size={22} /> : <UserRound size={15} />}</div>
                    <div className="min-w-0 flex-1">
                      <div className={`truncate text-[13px] font-medium ${s.status === 'undone' ? 'text-faint line-through' : 'text-ink'}`}>{label(s, lang)}</div>
                      <div className="text-[11px] text-faint">{s.actor === 'Munim' ? 'Munim' : s.actor}, {hhmm(s.ts)}</div>
                    </div>
                    {s.undoable && <motion.button whileTap={{ scale: .9 }} onClick={async () => { await post('/api/undo', { step_id: s.id, by }); toast(t('undoneToast')); }}
                      className="flex items-center gap-1 rounded-lg bg-tint px-2 py-1 text-[12px] font-semibold text-navy"><Undo2 size={13} />{t('undo')}</motion.button>}
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </div>
        </aside>
      </div>

      <AnimatePresence>{demo && <DemoDrawer onClose={() => setDemo(false)} />}</AnimatePresence>
    </div>
  );
}

function label(s: any, lang: Lang) {
  if (lang === 'hi' && s.tool && TOOL_HI[s.tool]) return TOOL_HI[s.tool];
  return s.title;
}

function ChannelIcon({ ch, light }: { ch: string; light: boolean }) {
  const I = ch === 'soundbox' ? Radio : ch === 'network' ? ShieldAlert : ch === 'onboarding' ? UserPlus : ch === 'monitor' || ch === 'proactive' ? Bell : Smartphone;
  return <I size={13} className={light ? 'text-[#CFE0F7]' : 'text-faint'} />;
}

function Loop({ phase, status }: { phase?: string; status: string }) {
  const { t } = useLang();
  const active = phase && PHASES.includes(phase as any) ? phase : null;
  const done = !active && status === 'resolved';
  return (
    <div className="flex flex-none items-center gap-1 rounded-full bg-tint p-1">
      {PHASES.map((p) => (
        <div key={p} className={`relative rounded-full px-3 py-1.5 text-[12.5px] font-semibold ${active === p ? 'text-white' : done ? 'text-good' : 'text-muted'}`}>
          {active === p && <motion.span layoutId="phase" className="absolute inset-0 rounded-full bg-navy" transition={{ type: 'spring', stiffness: 420, damping: 32 }} />}
          <span className="relative">{t(p as Key)}</span>
        </div>
      ))}
      {done && <CircleCheck size={20} className="mx-1 text-good" />}
    </div>
  );
}

function Step({ s, lang }: { s: any; lang: Lang }) {
  const { t } = useLang();
  const anim = { initial: { opacity: 0, x: -10 }, animate: { opacity: 1, x: 0 }, transition: { type: 'spring' as const, stiffness: 300, damping: 28 } };
  const dot = (cls: string, icon: React.ReactNode) => <span className={`absolute -left-[39px] grid h-7 w-7 place-items-center rounded-full ring-4 ring-white ${cls}`}>{icon}</span>;

  if (s.kind === 'think') return (
    <motion.li {...anim} className="relative mb-4">{dot('bg-tint text-muted', <Lightbulb size={14} />)}
      <div className="text-[12px] font-semibold text-faint">{t('thinks')}</div>
      <div className="text-[14px] italic text-muted">{s.title}</div></motion.li>
  );
  if (s.kind === 'reply') {
    const r = s.result || {};
    return (
      <motion.li {...anim} className="relative mb-4">{dot('bg-sky text-navy', <MessageCircle size={14} />)}
        <div className="text-[12px] font-semibold text-sky-ink">{t('told')}</div>
        <div className="mt-1 rounded-2xl rounded-tl-md bg-sky-softer px-3.5 py-2.5 text-[14.5px] leading-relaxed text-ink">{(lang === 'hi' ? r.hi : r.en) || s.title}</div>
      </motion.li>
    );
  }
  if (s.kind === 'event') return (
    <motion.li {...anim} className="relative mb-4">{dot('bg-gold text-navy', <Bell size={14} />)}
      <div className="text-[12px] font-semibold text-gold-ink">{s.actor === 'Merchant' ? t('app') : t('foundBy')}</div>
      <div className="text-[14px] text-ink">{s.title}</div></motion.li>
  );
  if (s.kind === 'human') return (
    <motion.li {...anim} className="relative mb-4">{dot('bg-gold-soft text-gold-ink', <UserRound size={14} />)}
      <div className="text-[14px] font-semibold text-ink">{s.title}</div><div className="text-[11.5px] text-faint">{hhmm(s.ts)}</div></motion.li>
  );
  // act
  const tier = TIER[s.tier] || TIER.read;
  const blocked = s.status === 'blocked', pending = s.status === 'pending', undone = s.status === 'undone', err = s.status === 'error';
  return (
    <motion.li {...anim} className="relative mb-4">
      {dot(blocked ? 'bg-bad-solid text-white' : s.tier === 'read' ? 'bg-tint text-navy' : 'bg-navy text-white', blocked ? <Ban size={14} /> : <tier.I size={14} />)}
      <div className="flex flex-wrap items-center gap-2">
        <span className={`text-[14.5px] font-semibold ${undone ? 'text-faint line-through' : 'text-ink'}`}>{label(s, lang)}</span>
        {!blocked && <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${tier.c}`}>{t(tier.k)}</span>}
        {undone && <span className="rounded-full bg-tint px-2 py-0.5 text-[11px] font-semibold text-muted">{t('undone')}</span>}
        <span className="text-[11.5px] text-faint">{hhmm(s.ts)}</span>
      </div>
      {blocked && <div className="mt-1.5 flex items-start gap-2 rounded-xl bg-bad-soft px-3 py-2 text-[13px] text-bad">
        <ShieldCheck size={16} className="mt-0.5 flex-none" /><div><b>{t('stopped')}.</b> {s.result?.blocked || s.result?.gateway?.reason}</div></div>}
      {pending && <div className="mt-1 text-[12.5px] font-semibold text-bad">{t('pending')}</div>}
      {err && <div className="mt-1 text-[12.5px] text-bad">{s.result?.error}</div>}
    </motion.li>
  );
}

function Approval({ ap, by, onDone }: { ap: any; by: string; onDone: () => void }) {
  const { t } = useLang();
  const [busy, setBusy] = useState(false);
  const go = async (approved: boolean) => { setBusy(true); await post('/api/approve', { approval_id: ap.id, approved, by }); onDone(); };
  return (
    <motion.div initial={{ opacity: 0, y: -10, scale: .98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, height: 0, marginBottom: 0 }}
      className="mb-5 overflow-hidden rounded-[22px] bg-gold-soft p-5">
      <div className="flex items-center gap-2 text-[14px] font-semibold text-gold-ink"><Hand size={16} />{t('needsOk')}</div>
      <div className="mt-1 flex items-center gap-2 text-xl font-bold text-navy"><IndianRupee size={20} />{ap.title}</div>
      <div className="text-[13px] text-gold-ink">{t('neverAlone')}</div>
      <ul className="mt-3 space-y-1.5">
        {ap.evidence.map((e: string, i: number) => (
          <motion.li key={i} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: .1 + i * .08 }} className="flex items-start gap-2 text-[13.5px] text-ink">
            <CircleCheck size={16} className="mt-0.5 flex-none text-good" />{e}</motion.li>
        ))}
      </ul>
      <div className="mt-4 flex gap-2.5">
        <motion.button whileTap={{ scale: .96 }} disabled={busy} onClick={() => go(true)} className="flex items-center gap-2 rounded-xl bg-navy px-5 py-2.5 font-semibold text-white disabled:opacity-60">
          <CircleCheck size={18} />{t('approve')}</motion.button>
        <motion.button whileTap={{ scale: .96 }} disabled={busy} onClick={() => go(false)} className="rounded-xl bg-white px-5 py-2.5 font-semibold text-navy disabled:opacity-60">{t('handle')}</motion.button>
      </div>
    </motion.div>
  );
}

function SalesStrip({ s }: { s?: any }) {
  const { t } = useLang();
  if (!s) return null;
  const cell = (v: number, k: string) => (
    <div><motion.div key={v} initial={{ scale: 1.25 }} animate={{ scale: 1 }} className="num text-[22px] font-extrabold leading-none text-ink">{v}</motion.div>
      <div className="mt-1 text-[12.5px] text-muted">{k}</div></div>
  );
  return (
    <div className="rounded-xl2 bg-white px-4 py-3.5">
      <div className="flex items-center gap-2 text-[14px] font-semibold text-ink"><UserPlus size={16} className="text-good" />{t('sales')}</div>
      <div className="mt-2.5 grid grid-cols-3 gap-2">{cell(s.signed_up, t('sNew'))}{cell(s.leads, t('sLeads'))}{cell(s.visits, t('sVisits'))}</div>
      {s.avg_minutes != null && <div className="mt-2 text-[12.5px] text-good">{t('sAvg', { m: String(s.avg_minutes) })}</div>}
    </div>
  );
}

function CostPanel({ e }: { e?: any }) {
  const { t } = useLang();
  if (!e) return null;
  const munim = e.munim_cost_per_case || 0, person = e.human_cost_per_case || 100;
  const pct = Math.max(1.5, Math.min(100, (munim / person) * 100));
  const rs = (n: number) => '₹' + (n < 10 ? n.toFixed(2) : Math.round(n).toLocaleString('en-IN'));
  return (
    <div className="rounded-xl2 bg-navy p-4 text-white">
      <div className="text-[13px] font-semibold text-[#CFE0F7]">{t('cTitle')}</div>
      <div className="mt-2 space-y-2">
        <div>
          <div className="flex justify-between text-[12.5px]"><span>{t('cMunim')}</span><b className="text-gold">{rs(munim)}</b></div>
          <div className="mt-1 h-2 rounded-full bg-white/10"><motion.div className="h-2 rounded-full bg-gold" initial={{ width: 0 }} animate={{ width: pct + '%' }} /></div>
        </div>
        <div>
          <div className="flex justify-between text-[12.5px] text-[#CFE0F7]"><span>{t('cPerson')}</span><b>{rs(person)}</b></div>
          <div className="mt-1 h-2 rounded-full bg-white/30" />
        </div>
      </div>
      <div className="mt-3 flex items-end justify-between border-t border-white/10 pt-3">
        <div><div className="text-[12px] text-[#CFE0F7]">{t('cSaved')}</div>
          <motion.div key={e.saved_inr} initial={{ scale: 1.15 }} animate={{ scale: 1 }} className="text-2xl font-extrabold">{rs(Math.max(0, e.saved_inr))}</motion.div></div>
        <div className="text-right text-[11.5px] leading-snug text-[#CFE0F7]">
          <div><b className="text-white">{e.fast_path_share}%</b> {t('cFast')}</div>
          <div><b className="text-white">{e.calls_prevented}</b> {t('cPrevented')}</div>
        </div>
      </div>
    </div>
  );
}

function Kpi({ I, v, k, tone }: { I: typeof Eye; v: React.ReactNode; k: string; tone: 'good' | 'sky' | 'bad' | 'gold' }) {
  const c = { good: 'bg-good-soft text-good', sky: 'bg-sky-soft text-sky-ink', bad: 'bg-bad-soft text-bad', gold: 'bg-gold-soft text-gold-ink' }[tone];
  return (
    <div className="rounded-xl2 bg-white p-3.5">
      <div className={`grid h-8 w-8 place-items-center rounded-full ${c}`}><I size={16} /></div>
      <motion.div key={String(v)} initial={{ y: 6, opacity: 0 }} animate={{ y: 0, opacity: 1 }} className="num mt-2 text-[28px] font-extrabold leading-none text-ink">{v}</motion.div>
      <div className="text-[12px] leading-tight text-muted">{k}</div>
    </div>
  );
}

function DemoDrawer({ onClose }: { onClose: () => void }) {
  const { t, lang } = useLang();
  const toast = useToast();
  const [msg, setMsg] = useState('');
  const [key, setKey] = useState('');
  const [cur, setCur] = useState<any>(null);
  const [test, setTest] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [sure, setSure] = useState(false);
  useEffect(() => { get('/api/settings').then(setCur).catch(() => {}); }, []);

  const ev = async (kind: string) => { await post('/api/event', { kind }); toast('✓'); };
  const save = async () => {
    setSaving(true); setTest(null);
    try { const r = await post('/api/settings', { sarvam_key: key.trim() }); setTest(r); setCur(await get('/api/settings')); setKey(''); }
    catch (e: any) { toast(e.message); }
    setSaving(false);
  };
  const reset = async () => {
    if (!sure) { setSure(true); setTimeout(() => setSure(false), 3000); return; }
    await post('/api/reset'); toast(t('dResetDone')); setSure(false); onClose();
  };
  const events: [string, Key, typeof Eye][] = [['customer_pays', 'dPay', IndianRupee], ['device_offline', 'dOff', Power], ['double_debit', 'dTwice', Copy], ['shop_closed', 'dClose', Store], ['fake_claims', 'dFraud', ShieldAlert]];

  return (
    <motion.div className="fixed inset-0 z-40 flex justify-end bg-navy-ink/40" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose}>
      <motion.aside role="dialog" aria-label={t('demo')} onClick={(e) => e.stopPropagation()}
        initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }} transition={{ type: 'spring', stiffness: 320, damping: 34 }}
        className="flex h-full w-[400px] max-w-full flex-col overflow-y-auto bg-page">
        <div className="flex items-center gap-2 border-b border-line bg-white px-5 py-4 text-ink">
          <FlaskConical size={19} className="text-navy" /><div className="flex-1 text-[19px] font-bold">{t('demo')}</div>
          <button onClick={onClose} aria-label="Close" className="grid h-9 w-9 place-items-center rounded-full bg-tint text-navy"><X size={18} /></button>
        </div>

        <div className="space-y-4 p-4">
          <Panel title={t('dSim')}>
            <div className="grid grid-cols-2 gap-2">
              {events.map(([k, l, I]) => (
                <motion.button key={k} whileTap={{ scale: .95 }} onClick={() => ev(k)} className="flex items-center gap-2 rounded-2xl bg-tint px-3 py-3 text-left text-[13px] font-semibold text-navy hover:bg-sky-soft">
                  <I size={17} className="flex-none text-sky-ink" />{t(l)}</motion.button>
              ))}
            </div>
          </Panel>

          <Panel title={t('dType')}>
            <div className="flex gap-2">
              <input value={msg} onChange={(e) => setMsg(e.target.value)} placeholder={lang === 'hi' ? 'साउंडबॉक्स नहीं बोल रहा' : 'My Soundbox is not speaking'}
                onKeyDown={(e) => { if (e.key === 'Enter' && msg.trim()) { post('/api/message', { text: msg, channel: 'app' }); setMsg(''); } }}
                className="min-w-0 flex-1 rounded-xl bg-tint px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-sky" />
              <button onClick={() => { if (msg.trim()) { post('/api/message', { text: msg, channel: 'app' }); setMsg(''); } }} className="grid h-10 w-10 place-items-center rounded-xl bg-navy text-white"><Send size={17} /></button>
            </div>
          </Panel>

          <Panel title={t('dMode')}>
            <div className="grid grid-cols-2 gap-2">
              {([['saver', 'dSaver', 'dSaverSub'], ['llm', 'dAlways', 'dAlwaysSub']] as const).map(([k, a, b]) => (
                <motion.button key={k} whileTap={{ scale: .96 }} onClick={async () => { await post('/api/settings', { brain: k }); setCur({ ...cur, brain_mode: k }); }}
                  className={`rounded-2xl px-3 py-2.5 text-left ${(cur?.brain_mode || 'saver') === k ? 'bg-navy text-white' : 'bg-tint text-navy'}`}>
                  <div className="text-[13.5px] font-bold">{t(a)}</div><div className="text-[11.5px] leading-snug opacity-75">{t(b)}</div>
                </motion.button>
              ))}
            </div>
          </Panel>

          <Panel title={t('dKey')} icon={<KeyRound size={16} />}>
            <p className="mb-2 text-[13px] text-muted">{cur?.has_key ? t('dKeySet', { k: cur.hint }) : t('dNoKey')}</p>
            <div className="flex gap-2">
              <input type="password" value={key} onChange={(e) => setKey(e.target.value)} placeholder={t('dKeyPh')} autoComplete="off"
                className="min-w-0 flex-1 rounded-xl bg-tint px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-sky" />
            </div>
            <motion.button whileTap={{ scale: .97 }} disabled={saving || (!key.trim() && !cur?.has_key)} onClick={save}
              className="mt-2 w-full rounded-xl bg-navy py-2.5 text-sm font-semibold text-white disabled:opacity-50">{saving ? <span className="dots"><i /><i /><i /></span> : t('dSave')}</motion.button>
            <AnimatePresence>{test && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="mt-3 space-y-1.5">
                {([['dVoice', test.voice], ['dBrain', test.brain]] as const).map(([k, r]) => (
                  <div key={k} className={`flex items-start gap-2 rounded-xl px-3 py-2 text-[13px] ${r.ok ? 'bg-good-soft text-good' : 'bg-bad-soft text-bad'}`}>
                    {r.ok ? <CircleCheck size={16} className="mt-0.5 flex-none" /> : <X size={16} className="mt-0.5 flex-none" />}
                    <div><b>{t(k)}:</b> {r.detail}</div></div>
                ))}
              </motion.div>
            )}</AnimatePresence>
          </Panel>

          <Link to="/" className="flex items-center gap-2 rounded-2xl bg-white px-4 py-3.5 font-semibold text-navy"><QrCode size={19} />{t('dPhones')}</Link>
          <motion.button whileTap={{ scale: .97 }} onClick={reset}
            className={`flex w-full items-center justify-center gap-2 rounded-2xl px-4 py-3 font-semibold ${sure ? 'bg-bad-solid text-white' : 'bg-white text-bad'}`}>
            <RotateCcw size={17} />{sure ? t('dResetSure') : t('dReset')}</motion.button>
        </div>
      </motion.aside>
    </motion.div>
  );
}

function Panel({ title, icon, children }: { title: string; icon?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl bg-white p-4">
      <div className="mb-3 flex items-center gap-2 text-[14px] font-bold text-navy">{icon}{title}</div>
      {children}
    </section>
  );
}
