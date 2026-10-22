import type {ReactNode} from 'react';

export function AuthLayout({children}: {children: ReactNode}) {
  return <div className="auth-screen">
    <a className="skip-link" href="#auth-content">Ir para o formulário</a>
    <div className="auth-story">
      <div className="brand-identification"><strong>Tavvo</strong><span>Restaurants</span></div>
      <div className="auth-story-copy"><p className="eyebrow">Tecnologia autoral</p><p className="auth-statement">Para empresas<br/>que vão mais longe.</p><p className="auth-description">Seu cardápio, sua identidade.<br/>Uma gestão mais simples, todos os dias.</p></div>
      <div className="brand-geometry" aria-hidden="true"><span/><span/><span/></div>
      <p className="auth-signature">Mais clareza para gerir.<br/>Mais espaço para crescer.</p>
    </div>
    <main className="auth" id="auth-content">
      <p className="eyebrow auth-eyebrow">Acesso à plataforma</p>
      {children}
      <div className="auth-card-footer">Tavvo · Tecnologia autoral</div>
    </main>
  </div>;
}
