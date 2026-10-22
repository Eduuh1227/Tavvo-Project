'use client';
export default function ErrorPage({reset}:{reset:()=>void}){return <main className="menu-state"><div className="menu-state-card"><p className="menu-eyebrow">Cardápio digital</p><h1>Cardápio temporariamente indisponível</h1><p>Não foi possível consultar o restaurante. Tente novamente em alguns instantes.</p><button onClick={reset}>Tentar novamente</button></div></main>;}
