export async function get<T = any>(path: string): Promise<T> {
  const r = await fetch(path);
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
  return r.json();
}
export async function post<T = any>(path: string, body?: unknown): Promise<T> {
  const r = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body ?? {}) });
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
  return r.json();
}
export async function sendVoice(blob: Blob, filename: string, merchantId: string, channel: string): Promise<string> {
  const fd = new FormData();
  fd.append('file', blob, filename);
  fd.append('merchant_id', merchantId);
  fd.append('channel', channel);
  const r = await fetch('/api/voice', { method: 'POST', body: fd });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.detail || 'Voice upload failed');
  return j.transcript;
}
export const inr = (n: number) => '₹' + Number(n || 0).toLocaleString('en-IN');
export const hhmm = (iso?: string) => (iso ? new Date(iso).toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' }) : '');

// Which shop this phone plays. Pages take ?m=M1002 so several phones can be different shops in the same area.
export const shopFromUrl = () => new URLSearchParams(location.search).get('m');
