import {Menu} from '../../Menu';
import {menu,resolveQr} from '../../../lib/api';
export const dynamic='force-dynamic';
export default async function QrPage({params}:{params:Promise<{code:string}>}){const {code}=await params;const resolved=await resolveQr(code);return <Menu data={await menu(resolved.restaurant.slug)} table={resolved.table.label}/>;}
