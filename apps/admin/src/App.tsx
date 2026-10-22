import {useEffect,useState} from 'react';
import {ApiError,request, type Restaurant} from '@tavvo/api-client';
import {Login,MfaEnrollment,type Session,type Access} from './Auth';
import {Action,ErrorNotice} from './ui';
import {RestaurantPanel} from './RestaurantPanel';
import {PlatformPanel} from './PlatformPanel';
import {Icon} from './Icon';

export function App(){
  const [session,setSession]=useState<Session|null>(null); const [loading,setLoading]=useState(true);const [error,setError]=useState<unknown>();
  const [enrolling,setEnrolling]=useState(false);
  const [access,setAccess]=useState<Access[]>([]);const [selected,setSelected]=useState<Restaurant|null>(null);const [central,setCentral]=useState(false);
  useEffect(()=>{const expired=()=>{setSession(null);setSelected(null);setAccess([]);setCentral(false);setEnrolling(false);setError(new Error('Sua sessão terminou. Entre novamente.'));};window.addEventListener('tavvo:session-expired',expired);return()=>window.removeEventListener('tavvo:session-expired',expired);},[]);
  useEffect(()=>{let active=true; request<Session>('/v1/auth/me/').then(value=>{if(active)setSession(value);}).catch(err=>{if(!active)return;if(err instanceof ApiError && typeof err.detail==='object' && err.detail!==null && 'code' in err.detail && err.detail.code==='mfa_required')setEnrolling(true);else if(err.status!==401 && err.status!==403)setError(err);}).finally(()=>{if(active)setLoading(false);});return()=>{active=false;};},[]);
  useEffect(()=>{if(!session || session.mfa_enrollment_required || session.is_platform_admin && !session.mfa_enabled)return;let active=true;request<Access[]>('/v1/me/restaurants/').then(value=>{if(active){setAccess(value);setSelected(current=>current || value[0]?.restaurant || null);setCentral(session.is_platform_admin);}}).catch(err=>{if(active)setError(err);});return()=>{active=false;};},[session]);
  if(loading)return <main className="session-loading"><span className="loading-indicator" aria-hidden="true"/><p role="status">Carregando sessão…</p></main>;
  if(enrolling)return <div className="enrollment-screen"><header className="app-topbar"><div className="brand-identification"><strong>Tavvo</strong><span>Restaurants</span></div><div className="topbar-account"><Action run={()=>request('/v1/auth/logout/','POST',{})} onDone={()=>setEnrolling(false)}><Icon name="logout"/>Sair</Action></div></header><main className="enrollment-main"><MfaEnrollment onSession={value=>{setSession(value);setEnrolling(false);}}/></main></div>;
  if(!session)return <><div className="auth-global-notice"><ErrorNotice error={error}/></div><Login onEnrollment={()=>setEnrolling(true)} onSession={value=>{setError(undefined);setSession(value);}}/></>;
  return <div className="app-shell">
    <a className="skip-link" href="#workspace">Ir para o conteúdo</a>
    <header className="app-topbar"><div className="brand-identification"><strong>Tavvo</strong><span>Restaurants</span></div><div className="topbar-account"><div className="session-identity"><span className="eyebrow">Seu espaço de gestão</span><span>{session.name || session.email}</span></div><Action run={()=>request('/v1/auth/logout/','POST',{})} onDone={()=>{setSession(null);setSelected(null);setAccess([]);setCentral(false);}}><Icon name="logout"/>Sair</Action></div></header>
    <main className="workspace" id="workspace"><ErrorNotice error={error}/>{session.mfa_enrollment_required || session.is_platform_admin && !session.mfa_enabled ? <MfaEnrollment onSession={setSession}/> : <><div className="scope"><label>Restaurante<select aria-label="Restaurante selecionado" value={central ? '' : selected?.id || ''} onChange={event=>{setCentral(false);setSelected(access.find(item=>item.restaurant.id===event.target.value)?.restaurant || null);}}><option value="">Selecione um restaurante</option>{access.map(item=><option key={item.restaurant.id} value={item.restaurant.id}>{item.restaurant.name} — {item.role}</option>)}</select></label>{session.is_platform_admin ? <button className="secondary central-access" onClick={()=>{setSelected(null);setCentral(true);}}><Icon name="shield"/>Administração central</button> : null}</div>{central && session.is_platform_admin ? <PlatformPanel onRestaurant={restaurant=>{setSelected(restaurant);setCentral(false);}}/> : selected ? <RestaurantPanel key={selected.id} restaurant={selected} role={access.find(item=>item.restaurant.id===selected.id)?.role} platform={session.is_platform_admin}/> : <p className="empty-workspace">Nenhum restaurante selecionado. Uma associação ativa é necessária para acessar a administração.</p>}</>}</main>
  </div>;
}
