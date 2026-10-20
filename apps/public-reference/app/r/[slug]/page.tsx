import {Menu} from '../../Menu';
import {menu} from '../../../lib/api';
export const dynamic='force-dynamic';
export default async function RestaurantPage({params}:{params:Promise<{slug:string}>}){const {slug}=await params;return <Menu data={await menu(slug)}/>;}
