import '@fontsource/mukta/400.css';
import '@fontsource/mukta/500.css';
import '@fontsource/mukta/600.css';
import '@fontsource/mukta/700.css';
import '@fontsource/mukta/800.css';
import './index.css';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { LangProvider } from './lib/i18n';
import { ToastProvider } from './components/Toast';
import Start from './pages/Start';
import Merchant from './pages/Merchant';
import Soundbox from './pages/Soundbox';
import Rep from './pages/Rep';
import Console from './pages/Console';
import Join from './pages/Join';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <LangProvider>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Start />} />
            <Route path="/merchant" element={<Merchant />} />
            <Route path="/soundbox" element={<Soundbox />} />
            <Route path="/rep" element={<Rep />} />
            <Route path="/console" element={<Console />} />
            <Route path="/join" element={<Join />} />
            <Route path="*" element={<Start />} />
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </LangProvider>
  </StrictMode>,
);
