import type {ReactNode} from 'react';

const paths: Record<string, ReactNode> = {
  categories: <><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></>,
  products: <><path d="M8 4H5a2 2 0 0 0-2 2v14h18V6a2 2 0 0 0-2-2h-3M8 3h8v4H8zM7 12h10M7 16h7"/></>,
  tables: <><rect x="3" y="3" width="6" height="6" rx="1"/><rect x="15" y="3" width="6" height="6" rx="1"/><rect x="3" y="15" width="6" height="6" rx="1"/><path d="M15 15h3v3h3v3h-6zM21 12v3M12 3v3M12 12h-1M3 12h4M12 18v3"/></>,
  settings: <><path d="M4 7h16M4 17h16"/><rect x="7" y="4" width="4" height="6" rx="1"/><rect x="14" y="14" width="4" height="6" rx="1"/></>,
  domains: <><circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/></>,
  audit: <><path d="M8 3H5v18h14V3h-3M8 2h8v4H8zM8 10h8M8 14h8M8 18h4"/></>,
  restaurants: <><path d="M3 10l2-7h14l2 7M4 10v11h16V10M3 10a3 3 0 0 0 6 0 3 3 0 0 0 6 0 3 3 0 0 0 6 0M9 21v-7h6v7"/></>,
  users: <><circle cx="9" cy="8" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3M16 5a3 3 0 0 1 0 6M18 14a5 5 0 0 1 3 4v3"/></>,
  arrow: <><path d="M6 18L18 6M7 6h11v11"/></>,
  plus: <path d="M12 5v14M5 12h14"/>,
  refresh: <><path d="M20 7a9 9 0 1 0 1 8M20 3v5h-5"/></>,
  edit: <><path d="M15 5l4 4M4 20l5-1L20 8a3 3 0 0 0-4-4L5 15z"/></>,
  shield: <><path d="M12 3l8 3v6c0 4-5 7-8 9-3-2-8-5-8-9V6zM8 12l3 3 5-6"/></>,
  close: <path d="M6 6l12 12M6 18L18 6"/>,
  check: <path d="M5 12l4 4L19 6"/>,
  logout: <><path d="M9 4H4v16h5M13 7l5 5-5 5M8 12h13"/></>,
  mail: <><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 6l9 7 9-7"/></>,
  lock: <><rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3"/></>,
};

export function Icon({name}: {name: keyof typeof paths}) {
  return <svg className="icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">{paths[name]}</svg>;
}
