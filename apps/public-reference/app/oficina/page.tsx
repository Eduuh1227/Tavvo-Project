import type {Metadata} from 'next';
import {Workshop} from './Workshop';

export const dynamic = 'force-dynamic';

export const metadata: Metadata = {
  title: 'Torque Oficina — Demonstração Tavvo',
  description: 'Conheça o template de oficina mecânica da Tavvo, com serviços, peças e orçamento.',
  robots: {index: false, follow: false},
};

export default function WorkshopPage() {
  const phone = process.env.TAVVO_WORKSHOP_WHATSAPP || '';
  const whatsapp = /^[1-9]\d{9,14}$/.test(phone) ? phone : '';
  return <Workshop whatsapp={whatsapp}/>;
}
