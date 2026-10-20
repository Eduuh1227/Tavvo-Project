'use client';
export default function ErrorPage({reset}:{reset:()=>void}){return <main><h1>Cardápio temporariamente indisponível</h1><p>Não foi possível consultar o restaurante. Tente novamente em alguns instantes.</p><button onClick={reset}>Tentar novamente</button></main>;}
