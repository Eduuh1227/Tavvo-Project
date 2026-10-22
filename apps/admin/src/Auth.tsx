import {useState} from 'react';
import {request, type User, type Restaurant, type Role} from '@tavvo/api-client';
import {Form, type Field} from './ui';
import {AuthLayout} from './AuthLayout';

export interface Access {restaurant: Restaurant; role: Role}
export interface Session extends User {memberships: Access[]; mfa_enrollment_required?: boolean}
type LoginResult = Session | {mfa_required: true} | {mfa_enrollment_required: true};
const loginFields: Field[] = [{key:'email',label:'E-mail',type:'email',required:true},{key:'password',label:'Senha',type:'password',required:true}];

export function Login({onSession,onEnrollment}: {onSession: (session: Session) => void;onEnrollment:()=>void}) {
  const [mfa, setMfa] = useState(false);
  const [recovery, setRecovery] = useState(false);
  const params = new URLSearchParams(window.location.search);
  const uid = params.get('uid'); const token = params.get('token');
  const [message, setMessage] = useState('');
  if (uid && token) return <AuthLayout><h1>Definir nova senha</h1><Form fields={[{key:'password',label:'Nova senha',type:'password',required:true}]} submit={async values => {await request('/v1/auth/csrf/'); await request('/v1/auth/password-reset/confirm/', 'POST', {uid,token,...values}); window.history.replaceState({},'',window.location.pathname); setMessage('Senha atualizada. Entre com sua nova senha.');}} button="Atualizar senha"/><p role="status">{message}</p><a href="/">Voltar ao login</a></AuthLayout>;
  if (recovery) return <AuthLayout><h1>Recuperar acesso</h1><Form fields={[loginFields[0]]} submit={async values => {await request('/v1/auth/csrf/'); await request('/v1/auth/password-reset/request/', 'POST', values); setMessage('Se o endereço estiver cadastrado, você receberá as instruções para recuperar o acesso.');}} button="Enviar instruções"/><p role="status">{message}</p><button className="secondary" onClick={() => {setRecovery(false);setMessage('');}}>Voltar</button></AuthLayout>;
  return <AuthLayout><h1>Tavvo Restaurants</h1><p>Acesse a administração do restaurante ou da plataforma.</p><Form fields={mfa ? [...loginFields, {key:'otp',label:'Código de autenticação ou recuperação',required:true}] : loginFields} submit={async values => {
    await request('/v1/auth/csrf/');
    const result = await request<LoginResult>('/v1/auth/login/','POST',values);
    if ('mfa_required' in result) {setMfa(true); return;}
    if ('mfa_enrollment_required' in result && result.mfa_enrollment_required) {onEnrollment(); return;}
    const session = await request<Session>('/v1/auth/me/');
    onSession(session);
  }} button="Entrar"/>{mfa ? <p>Informe o código do aplicativo autenticador ou um código de recuperação.</p> : null}{import.meta.env.VITE_DEMO_MODE === 'true' ? <p>Ambiente de demonstração. Recuperação por e-mail indisponível.</p> : <button className="secondary" onClick={() => setRecovery(true)}>Esqueci minha senha</button>}<p role="status">{message}</p></AuthLayout>;
}

export function MfaEnrollment({onSession}: {onSession: (session: Session) => void}) {
  const [enrollment, setEnrollment] = useState<{secret: string; otpauth_url: string}>();
  const [codes, setCodes] = useState<string[]>();
  const [completed, setCompleted] = useState<Session>();
  if (codes) return <section className="enrollment-card"><h2>Guarde seus códigos de recuperação</h2><p>Cada código só pode ser usado uma vez. Guarde-os em um local seguro antes de continuar.</p><pre>{codes.join('\n')}</pre><button onClick={() => completed && onSession(completed)}>Guardei os códigos, continuar</button></section>;
  return <section className="enrollment-card"><h2>Proteger a conta com MFA</h2><p>Contas administrativas precisam confirmar um segundo fator antes de acessar os dados.</p>{!enrollment ? <Form fields={[]} button="Configurar autenticador" submit={async () => setEnrollment(await request('/v1/auth/mfa/enroll/','POST',{}))}/> : <><p>Adicione esta chave ao seu aplicativo autenticador:</p><code className="secret">{enrollment.secret}</code><p><a href={enrollment.otpauth_url}>Abrir em um aplicativo autenticador</a></p><Form fields={[{key:'otp',label:'Código de seis dígitos',required:true}]} submit={async values => {const result = await request<{user: Session; recovery_codes: string[]}>('/v1/auth/mfa/confirm/','POST',values); setCodes(result.recovery_codes);setCompleted({...result.user,mfa_enrollment_required:false});}} button="Confirmar código"/></>}</section>;
}
