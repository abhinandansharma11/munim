import { motion } from 'framer-motion';
import { useLang } from '../lib/i18n';

// Two-option switch: हिंदी | EN. The sliding pill moves to the active language.
export function LangToggle({ dark = false }: { dark?: boolean }) {
  const { lang, setLang } = useLang();
  const opts: { k: 'hi' | 'en'; label: string }[] = [{ k: 'hi', label: 'हिंदी' }, { k: 'en', label: 'EN' }];
  return (
    <div role="group" aria-label="Language" className={`relative flex flex-none rounded-full p-1 ${dark ? 'bg-white/10' : 'bg-tint'}`}>
      {opts.map((o) => (
        <button key={o.k} onClick={() => setLang(o.k)} aria-pressed={lang === o.k}
          className={`relative z-10 flex-none whitespace-nowrap rounded-full px-2.5 py-1.5 text-[13px] font-semibold transition-colors ${lang === o.k ? 'text-navy' : dark ? 'text-white/80' : 'text-muted'}`}>
          {lang === o.k && <motion.span layoutId={dark ? 'lang-dark' : 'lang-light'} className="absolute inset-0 -z-10 rounded-full bg-white shadow"
            transition={{ type: 'spring', stiffness: 500, damping: 35 }} />}
          {o.label}
        </button>
      ))}
    </div>
  );
}
