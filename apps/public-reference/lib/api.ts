import 'server-only';
import {notFound} from 'next/navigation';
import type {PublicMenu, Restaurant, QrResolution} from '@tavvo/api-client';

export function apiOrigin(): string {
  const url = new URL(process.env.API_INTERNAL_URL || 'http://127.0.0.1:8000');
  if (!['http:', 'https:'].includes(url.protocol)) throw new Error('API_INTERNAL_URL inválida.');
  return url.origin;
}
async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${apiOrigin()}/v1/public/${path}`, {cache:'no-store', credentials:'omit', signal:AbortSignal.timeout(10000),headers:{Accept:'application/json'}});
  if(response.status===404)notFound();
  if(!response.ok)throw new Error('Não foi possível consultar o cardápio agora.');
  return response.json() as Promise<T>;
}
export function menu(slug:string){return get<PublicMenu>(`restaurants/${encodeURIComponent(slug)}/menu/`);}
export function resolveHost(hostname:string){return get<Restaurant>(`resolve/?hostname=${encodeURIComponent(hostname)}`);}
export function resolveQr(code:string){return get<QrResolution>(`qr/${encodeURIComponent(code)}/`);}
/** Images travel through a public-only proxy, never with an administrative cookie. */
export function imagePath(raw:string):string|undefined {
  try {const url=new URL(raw,apiOrigin());return url.pathname.startsWith('/v1/public/') ? url.pathname : undefined;}catch{return undefined;}
}
