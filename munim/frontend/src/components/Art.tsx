// Flat illustrations in the deck's style.
// Munim's mark: the Devanagari letter म in a Paytm-navy circle. Used wherever Munim speaks or acts.
export function Mascot({ size = 64 }: { size?: number; wave?: boolean }) {
  return (
    <span role="img" aria-label="Munim" className="relative inline-grid flex-none place-items-center rounded-full bg-navy font-bold text-white"
      style={{ width: size, height: size, fontSize: size * 0.56, lineHeight: 1 }}>
      <span style={{ transform: 'translateY(-4%)' }}>म</span>
      <span className="absolute rounded-full bg-sky" style={{ width: size * 0.2, height: size * 0.2, right: size * 0.04, top: size * 0.06, boxShadow: `0 0 0 ${Math.max(1.5, size * 0.035)}px white` }} />
    </span>
  );
}

// Initials avatar, as real apps show for people without a photo.
export function Initials({ name, size = 40, tone = 'sky' }: { name: string; size?: number; tone?: 'sky' | 'gold' | 'tint' }) {
  const ini = name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join('').toUpperCase();
  const c = { sky: 'bg-sky-soft text-navy', gold: 'bg-gold-soft text-gold-ink', tint: 'bg-tint text-body' }[tone];
  return <span className={`inline-grid flex-none place-items-center rounded-full font-bold ${c}`} style={{ width: size, height: size, fontSize: size * 0.38 }}>{ini}</span>;
}

export function Shopkeeper({ size = 48 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 120 120" role="img" aria-label="Shopkeeper">
      <circle cx="60" cy="60" r="60" fill="#FFF4CC" />
      <path d="M16 120 C 20 93 40 83 60 83 C 80 83 100 93 104 120 Z" fill="#00BAF2" />
      <path d="M49 85 L60 99 L71 85" fill="none" stroke="#0077B6" strokeWidth="3" strokeLinejoin="round" />
      <rect x="52" y="70" width="16" height="17" rx="6" fill="#C98B5E" />
      <circle cx="38" cy="57" r="5.5" fill="#C98B5E" /><circle cx="82" cy="57" r="5.5" fill="#C98B5E" />
      <ellipse cx="60" cy="54" rx="22" ry="25" fill="#DDA078" />
      <path d="M38 52 C 36 32 48 25 60 25 C 73 25 85 32 82 52 C 79 42 71 37 60 38 C 49 37 41 42 38 52 Z" fill="#2B2F3A" />
      <path d="M41 41 C 44 37 47 35 50 34" fill="none" stroke="#8D93A3" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M46 48 Q51 45 55 48 M65 48 Q69 45 74 48" fill="none" stroke="#2B2F3A" strokeWidth="2.4" strokeLinecap="round" />
      <circle cx="51" cy="54" r="2.8" fill="#2B2F3A" /><circle cx="69" cy="54" r="2.8" fill="#2B2F3A" />
      <path d="M47 66 C 52 61 57 63 60 65.5 C 63 63 68 61 73 66 C 67 69 63 68 60 67 C 57 68 53 69 47 66 Z" fill="#2B2F3A" />
      <path d="M54 72 Q60 76 66 72" stroke="#8E4E33" strokeWidth="2" fill="none" strokeLinecap="round" />
      <rect x="58" y="40" width="4" height="7" rx="2" fill="#E25B4B" />
    </svg>
  );
}

export function RepAvatar({ size = 48 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 120 120" role="img" aria-label="Field rep">
      <circle cx="60" cy="60" r="60" fill="#E3F6FD" />
      <path d="M16 120 C 20 93 40 83 60 83 C 80 83 100 93 104 120 Z" fill="#002970" />
      <path d="M48 85 L56 112 M72 85 L64 112" stroke="#00BAF2" strokeWidth="3" /><rect x="53" y="106" width="14" height="10" rx="2" fill="#fff" />
      <rect x="52" y="70" width="16" height="17" rx="6" fill="#B87A50" />
      <circle cx="38" cy="58" r="5.5" fill="#B87A50" /><circle cx="82" cy="58" r="5.5" fill="#B87A50" />
      <ellipse cx="60" cy="56" rx="21" ry="24" fill="#CF9168" />
      <path d="M36 44 C 38 28 50 22 62 23 C 76 24 86 32 84 46 L 36 46 Z" fill="#00BAF2" />
      <path d="M60 42 L 96 44 C 96 49 88 50 82 49 L 60 48 Z" fill="#0077B6" />
      <circle cx="52" cy="56" r="2.7" fill="#2B2F3A" /><circle cx="68" cy="56" r="2.7" fill="#2B2F3A" />
      <path d="M52 68 Q60 74 68 68" stroke="#7A3F25" strokeWidth="2.4" fill="none" strokeLinecap="round" />
    </svg>
  );
}

export function SoundboxArt({ online }: { online: boolean }) {
  const dots = [];
  for (let r = 0; r < 6; r++) for (let c = 0; c < 7; c++) dots.push(<circle key={`${r}-${c}`} cx={62 + c * 16} cy={150 + r * 15} r="4.2" fill={online ? '#0B3C8F' : '#3A4660'} />);
  return (
    <svg viewBox="0 0 240 300" width="100%" height="100%" role="img" aria-label={online ? 'Soundbox online' : 'Soundbox offline'}>
      <ellipse cx="120" cy="284" rx="88" ry="12" fill="rgba(0,20,60,.16)" />
      <rect x="24" y="20" width="192" height="258" rx="44" fill={online ? '#002970' : '#2A3550'} />
      <rect x="24" y="20" width="192" height="120" rx="44" fill={online ? '#0B3C8F' : '#323E5A'} />
      <rect x="48" y="44" width="144" height="74" rx="14" fill={online ? '#E9F8FE' : '#C8CEDA'} />
      {dots}
      <circle cx="120" cy="257" r="7" fill={online ? '#2BD37B' : '#F2545B'} />
    </svg>
  );
}

export function ShopArt({ width = 360 }: { width?: number }) {
  return (
    <svg width={width} viewBox="0 0 720 500" role="img" aria-label="A kirana shop with a Soundbox" style={{ maxWidth: '100%', height: 'auto' }}>
      <rect x="40" y="170" width="640" height="300" fill="#DDEBF8" />
      {Array.from({ length: 8 }).map((_, i) => <rect key={'a' + i} x={20 + i * 85} y="80" width="85" height="90" fill={i % 2 ? '#fff' : '#00BAF2'} />)}
      {Array.from({ length: 8 }).map((_, i) => <circle key={'b' + i} cx={62.5 + i * 85} cy="170" r="42.5" fill={i % 2 ? '#fff' : '#00BAF2'} />)}
      <rect x="200" y="16" width="320" height="62" rx="14" fill="#FFC400" />
      <text x="360" y="58" textAnchor="middle" fontFamily="Poppins, sans-serif" fontWeight="800" fontSize="30" fill="#002970">Sharma Kirana</text>
      <rect x="40" y="300" width="640" height="12" fill="#002970" />
      <rect x="70" y="246" width="46" height="54" rx="10" fill="#FFC400" /><rect x="130" y="246" width="46" height="54" rx="10" fill="#00BAF2" />
      <rect x="190" y="246" width="46" height="54" rx="10" fill="#fff" /><rect x="268" y="230" width="70" height="70" fill="#00BAF2" />
      <rect x="420" y="222" width="34" height="78" rx="10" fill="#FFC400" /><rect x="470" y="240" width="80" height="60" fill="#002970" /><rect x="470" y="262" width="80" height="12" fill="#FFC400" />
      <rect x="570" y="246" width="46" height="54" rx="10" fill="#00BAF2" />
      <rect x="20" y="440" width="680" height="30" rx="8" fill="#FFC400" />
      <rect x="400" y="362" width="96" height="78" rx="20" fill="#002970" stroke="#fff" strokeWidth="4" /><circle cx="448" cy="420" r="6" fill="#FFC400" />
      <path d="M510 384 Q526 402 510 420" fill="none" stroke="#00BAF2" strokeWidth="5" strokeLinecap="round" /><path d="M524 370 Q548 402 524 434" fill="none" stroke="#00BAF2" strokeWidth="5" strokeLinecap="round" />
    </svg>
  );
}
