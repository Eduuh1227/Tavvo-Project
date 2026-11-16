import type {Metadata} from 'next';
import type {ReactNode} from 'react';
import './style.css';
export const metadata: Metadata={title:'Tavvo',description:'Sites e catálogos digitais para negócios.'};
export default function Layout({children}:{children:ReactNode}){return <html lang="pt-BR"><body>{children}</body></html>;}
