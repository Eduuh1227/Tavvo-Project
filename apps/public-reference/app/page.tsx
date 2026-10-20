import {headers} from 'next/headers';
import {menu,resolveHost} from '../lib/api';
import {Menu} from './Menu';
export const dynamic='force-dynamic';
export default async function Home(){
  const requestHeaders=await headers();
  // Host is public routing input only. Backend requires a verified domain and an active tenant.
  const host=requestHeaders.get('host') || '';
  const hostname=new URL(`http://${host}`).hostname;
  const restaurant=await resolveHost(hostname);
  return <Menu data={await menu(restaurant.slug)}/>;
}
