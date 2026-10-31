import { motion } from 'framer-motion';
import { ArrowUpRight, LayoutDashboard, Radio, Smartphone, UserRound, Wifi, ScanLine, ShieldCheck, ShieldAlert, UserPlus } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { get } from '../lib/api';
import { Key, useLang } from '../lib/i18n';
import { Mascot } from '../components/Art';
import { LangToggle } from '../components/LangToggle';

const AREA_SHOPS = [
  { id: 'M1001', n: 1, shop: 'Sharma Kirana', kind: { en: 'Kirana', hi: 'किराना' } },
  { id: 'M1002', n: 2, shop: 'Gupta Medicals', kind: { en: 'Pharmacy', hi: 'मेडिकल' } },
  { id: 'M1003', n: 3, shop: 'Khan Electronics', kind: { en: 'Electronics', hi: 'इलेक्ट्रॉनिक्स' } },
];

const PHONES: { path: string; title: Key; sub: Key; Icon: typeof Radio }[] = [
  { path: '/merchant', title: 'qMerchant', sub: 'qMerchantSub', Icon: Smartphone },
  { path: '/soundbox', title: 'qSoundbox', sub: 'qSoundboxSub', Icon: Radio },
  { path: '/rep', title: 'qRep', sub: 'qRepSub', Icon: UserRound },
  { path: '/join', title: 'qJoin', sub: 'qJoinSub', Icon: UserPlus },
];

export default function Start() {
  const { t, lang } = useLang();
  const [base, setBase] = useState('');
  useEffect(() => { get('/api/info').then((i) => setBase(i.urls.https)).catch(() => setBase(location.origin)); }, []);

  return (
    <div className="min-h-full bg-page">
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-5 py-3">
          <div className="rounded-full bg-sky-soft p-1"><Mascot size={36} /></div>
          <div className="text-[22px] font-extrabold text-ink">{t('sTitle')}</div>
          <div className="flex-1" />
          <LangToggle />
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-5 pb-16 pt-10">
        <section className="grid items-center gap-8 md:grid-cols-[1.1fr_1fr]">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
            <h1 className="text-[44px] font-extrabold leading-[1.22] md:text-[60px]">{t('sHero1')}<br /><span className="text-sky">{t('sHero2')}</span></h1>
            <p className="mt-5 max-w-xl text-[19px] leading-relaxed text-body">{t('sLead')}</p>
            <Link to="/console" className="mt-7 inline-flex items-center gap-2.5 rounded-full bg-navy px-6 py-3.5 text-[17px] font-semibold text-white">
              <LayoutDashboard size={19} />{t('qConsole')}<ArrowUpRight size={18} />
            </Link>
            <div className="mt-2.5 text-[14px] text-muted">{t('qConsoleSub')}</div>
          </motion.div>
          <div className="justify-self-center">
            {/* The real shopkeeper app, live, inside a phone frame */}
            <div className="relative h-[620px] w-[300px] overflow-hidden rounded-[46px] border-[10px] border-black bg-white shadow-lift">
              <iframe src="/merchant?preview=1" title={t('qMerchant')} className="pointer-events-auto origin-top-left border-0"
                style={{ width: 390, height: 840, transform: 'scale(0.718)' }} />
            </div>
          </div>
        </section>

        <section className="mt-12 rounded-[28px] bg-white p-6 md:p-10">
          <h2 className="text-[32px] font-extrabold leading-tight">{t('sHow')}</h2>
          <ol className="mt-5 grid gap-4 md:grid-cols-3">
            {([['sStep1', Wifi], ['sStep2', ScanLine], ['sStep3', ShieldCheck]] as const).map(([k, Icon], i) => (
              <motion.li key={k} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: .15 + i * .08 }}
                className="flex gap-3 rounded-2xl bg-page p-4">
                <div className="grid h-10 w-10 flex-none place-items-center rounded-full bg-gold text-lg font-bold text-navy">{i + 1}</div>
                <div className="text-[16px] leading-snug text-body"><Icon size={18} className="mb-1 text-navy" />{t(k)}</div>
              </motion.li>
            ))}
          </ol>

          <div className="mt-7 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {PHONES.map(({ path, title, sub, Icon }, i) => (
              <motion.div key={path} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: .3 + i * .08 }}
                whileHover={{ y: -4 }} className="flex flex-col items-center rounded-3xl bg-sky-soft p-6 text-center">
                <div className="flex items-center gap-2 text-[20px] font-bold text-ink"><Icon size={20} className="text-navy" />{t(title)}</div>
                <div className="text-sm text-muted">{t(sub)}</div>
                <div className="mt-4 rounded-2xl bg-white p-3">
                  {base ? <QRCodeSVG value={base + path} size={168} fgColor="#002970" level="M" /> : <div className="h-[168px] w-[168px]" />}
                </div>
                <div className="mt-3 break-all text-[13px] text-muted">{base.replace('https://', '')}{path}</div>
                <Link to={path} className="mt-3 rounded-full border border-navy/25 px-4 py-1.5 text-[14px] font-semibold text-navy">{t('openHere')}</Link>
              </motion.div>
            ))}
          </div>
        </section>
        <section className="mt-8 rounded-[28px] bg-white p-6 md:p-10">
          <h2 className="flex items-center gap-2.5 text-[32px] font-extrabold leading-tight"><ShieldAlert size={24} className="text-bad" />{t('fTitle')}</h2>
          <p className="mt-2 max-w-3xl text-[17px] leading-relaxed text-body">{t('fSub')}</p>
          <div className="mt-6 grid gap-5 md:grid-cols-3">
            {AREA_SHOPS.map((x) => (
              <div key={x.id} className={`rounded-3xl p-5 ${x.n === 3 ? 'bg-bad-soft' : 'bg-sky-soft'}`}>
                <div className="flex items-center gap-3">
                  <div className={`grid h-9 w-9 place-items-center rounded-full text-lg font-bold ${x.n === 3 ? 'bg-bad-solid text-white' : 'bg-gold text-navy'}`}>{x.n}</div>
                  <div><div className="text-[19px] font-bold text-ink">{x.shop}</div><div className="text-[14px] text-muted">{x.kind[lang]}, Vijay Nagar</div></div>
                </div>
                <div className="mt-4 grid grid-cols-2 gap-3">
                  {([['merchant', 'fApp'], ['soundbox', 'fBox']] as const).map(([pg, k]) => (
                    <div key={pg} className="flex flex-col items-center">
                      <div className="rounded-xl bg-white p-2">
                        {base ? <QRCodeSVG value={`${base}/${pg}?m=${x.id}`} size={104} fgColor="#002970" level="M" /> : <div className="h-[104px] w-[104px]" />}
                      </div>
                      <Link to={`/${pg}?m=${x.id}`} className="mt-2 text-[14px] font-semibold text-sky-ink underline-offset-2 hover:underline">{t(k)}</Link>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
