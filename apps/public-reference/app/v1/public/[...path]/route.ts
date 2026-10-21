import {NextRequest,NextResponse} from 'next/server';
import {apiUrl} from '../../../../lib/api';
export const dynamic='force-dynamic';
/** Only public image endpoints are proxied. Administrative paths and cookies never pass through. */
export async function GET(request:NextRequest,{params}:{params:Promise<{path:string[]}>}){
  const {path}=await params;
  if(path.length!==4 || path[0]!=='restaurants' || path[2]!=='images' || !/^[a-z0-9-]+$/.test(path[1]) || !/^[0-9a-f-]{36}$/.test(path[3])) return new NextResponse(null,{status:404});
  try {
    const upstream=await fetch(apiUrl(`v1/public/${path.map(encodeURIComponent).join('/')}/`),{cache:'no-store',credentials:'omit',signal:AbortSignal.timeout(10000),redirect:'error'});
    if(!upstream.ok)return new NextResponse(null,{status:upstream.status});
    const type=upstream.headers.get('content-type')||'';
    if(!['image/jpeg','image/png','image/webp'].includes(type.split(';')[0]))return new NextResponse(null,{status:502});
    return new NextResponse(upstream.body,{status:200,headers:{'Content-Type':type,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
  }catch{return new NextResponse(null,{status:502});}
}
