/** Shared transport; response types derive from the validated OpenAPI contract. */
import type {components} from './schema';
export type {components, paths, operations} from './schema';
type Schemas = components['schemas'];
export type ID = string;
export type Role = Schemas['MembershipRoleEnum'];
export type User = Schemas['IdentityUser'];
export type Restaurant = Schemas['RestaurantSummary'] & Partial<Schemas['Restaurant']>;
export type Membership = Schemas['Membership'];
// Django emits model defaults on every full response; requests may omit them.
export type Category = Required<Schemas['Category']>;
export type ProductImage = Schemas['ProductImage'];
export type Product = Required<Schemas['Product']>;
export type Table = Required<Schemas['MenuTable']>;
export type Domain = Required<Schemas['Domain']>;
export type Settings = Required<Schemas['Settings']>;
export type Audit = Schemas['Audit'];
export interface Page<T> {count: number; next: string | null; previous: string | null; results: T[]}
export type PublicMenu = Schemas['PublicMenu'];
export type QrResolution = Schemas['QRResolution'];
export type Order = Schemas['Order'];
export type PublicOrder = Required<Schemas['PublicOrder']>;
export type OrderCreated = Omit<Schemas['OrderCreated'],'order'> & {order:PublicOrder};
export type Ordering = Required<Schemas['OrderSettings']>;
export type BillingStatus = Omit<Schemas['BillingStatus'],'subscription'> & {subscription:Required<Schemas['Subscription']>};
export const orderLabels: Record<string, string> = {awaiting_payment:'Aguardando pagamento',received:'Recebido',accepted:'Aceito',preparing:'Em preparo',ready:'Pronto',dispatched:'Saiu para entrega',completed:'Concluído',cancelled:'Cancelado'};
export const paymentLabels: Record<string, string> = {unpaid:'Pendente',paid:'Pago',expired:'Expirado',failed:'Pagamento falhou',refunded:'Estornado',refund_pending:'Estorno pendente',review:'Em análise'};
export const fulfillmentLabels: Record<string, string> = {pickup:'Retirada',delivery:'Entrega',table:'Mesa'};

export class ApiError extends Error {
  constructor(public status: number, public detail: unknown) {
    super(errorMessage(detail));
  }
}
function errorMessage(value: unknown): string {
  if (typeof value === 'string') return value;
  if (Array.isArray(value)) return value.map(errorMessage).join('; ');
  if (value && typeof value === 'object') {
    if ('message' in value && typeof value.message === 'string') return value.message + ('errors' in value && value.errors ? ` ${errorMessage(value.errors)}` : '');
    return Object.entries(value).map(([key, item]) => key === 'detail' ? errorMessage(item) : `${key}: ${errorMessage(item)}`).join('; ');
  }
  return 'Não foi possível concluir a solicitação.';
}
export function csrfToken(): string {
  if (typeof document === 'undefined') return '';
  const value = document.cookie.split('; ').find(part => part.startsWith('csrftoken='));
  return value ? decodeURIComponent(value.slice('csrftoken='.length)) : '';
}
export async function request<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  if (!path.startsWith('/v1/')) throw new Error('A API deve usar uma rota relativa /v1/.');
  const multipart = body instanceof FormData;
  const headers: Record<string, string> = {'Accept': 'application/json'};
  if (body !== undefined && !multipart) headers['Content-Type'] = 'application/json';
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) headers['X-CSRFToken'] = csrfToken();
  const response = await fetch(path, {method, headers, credentials: 'same-origin', cache: 'no-store', body: body === undefined ? undefined : multipart ? body : JSON.stringify(body)});
  const type = response.headers.get('content-type') || '';
  const data: unknown = response.status === 204 ? undefined : type.includes('json') ? await response.json() : await response.text();
  if (!response.ok) {
    const code = data && typeof data === 'object' && 'code' in data ? data.code : undefined;
    if (typeof window !== 'undefined' && path !== '/v1/auth/me/' && (response.status === 401 || code === 'not_authenticated')) window.dispatchEvent(new Event('tavvo:session-expired'));
    throw new ApiError(response.status, data);
  }
  return data as T;
}
export async function all<T>(path: string): Promise<T[]> {
  const result: T[] = [];
  let next: string | null = path;
  while (next) {
    const page: Page<T> | T[] = await request<Page<T> | T[]>(next);
    if (Array.isArray(page)) return result.concat(page);
    result.push(...page.results);
    next = page.next ? new URL(page.next, 'http://api.invalid').pathname + new URL(page.next, 'http://api.invalid').search : null;
  }
  return result;
}
