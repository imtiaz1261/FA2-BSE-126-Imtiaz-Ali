const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export async function api(path:string, options:RequestInit = {}) {
  const token = localStorage.getItem('token');
  const headers = new Headers(options.headers || {});
  if (options.body && !headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type','application/json');
  }
  if (token) headers.set('Authorization', `Bearer ${token}`);
  const res = await fetch(`${API_BASE}${path}`, {...options, headers});
  const text = await res.text();
  let data:any = {};
  try { data = text ? JSON.parse(text) : {}; } catch { data = {detail:text}; }
  if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
  return data;
}

export async function upload(path:string, file:File) {
  const fd = new FormData();
  fd.append('file', file);
  return api(path, {method:'POST', body:fd});
}
