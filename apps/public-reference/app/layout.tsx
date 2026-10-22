import type {Metadata} from 'next';
import type {ReactNode} from 'react';
import './style.css';
export const metadata: Metadata={title:'Cardápio — Tavvo Restaurants',description:'Consulte o cardápio publicado do restaurante.'};
export default function Layout({children}:{children:ReactNode}){return <html lang="pt-BR"><body>{children}<footer className="menu-footer"><span>Cardápio digital</span><span className="footer-platform">Tavvo Restaurants</span></footer></body></html>;}
