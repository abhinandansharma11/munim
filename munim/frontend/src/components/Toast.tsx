import { AnimatePresence, motion } from 'framer-motion';
import { createContext, ReactNode, useCallback, useContext, useRef, useState } from 'react';

const Ctx = createContext<(msg: string, ms?: number) => void>(() => {});
export const useToast = () => useContext(Ctx);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [msg, setMsg] = useState<string | null>(null);
  const timer = useRef<number>();
  const show = useCallback((m: string, ms = 2800) => {
    setMsg(m); clearTimeout(timer.current); timer.current = window.setTimeout(() => setMsg(null), ms);
  }, []);
  return (
    <Ctx.Provider value={show}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 z-[80] flex justify-center px-4" style={{ bottom: 'calc(24px + env(safe-area-inset-bottom, 0px))' }} role="status">
        <AnimatePresence>
          {msg && (
            <motion.div key={msg} initial={{ opacity: 0, y: 20, scale: .96 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 10 }}
              className="max-w-md rounded-2xl bg-navy-ink px-5 py-3 text-sm text-white shadow-lift">{msg}</motion.div>
          )}
        </AnimatePresence>
      </div>
    </Ctx.Provider>
  );
}
