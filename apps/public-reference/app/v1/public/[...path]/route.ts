import {NextRequest,NextResponse} from 'next/server';
import {apiUrl} from '../../../../lib/api';
export const dynamic='force-dynamic';
type Context={params:Promise<{path:string[]}>};
/** Explicit public allowlist. No admin cookies, auth headers or arbitrary upstream URLs. */
async function proxy(request:NextRequest,{params}:Context){
  const {path}=await params;const route=path.join('/');
  const image=/^restaurants\/[a-z0-9-]+\/images\/[0-9a-f-]{36}$/.test(route);
  const ordering=/^restaurants\/[a-z0-9-]+\/ordering$/.test(route);
  const orders=/^restaurants\/[a-z0-9-]+\/orders$/.test(route);
  const detail=/^restaurants\/[a-z0-9-]+\/orders\/[0-9a-f-]{36}$/.test(route);
  const checkout=/^restaurants\/[a-z0-9-]+\/orders\/[0-9a-f-]{36}\/checkout$/.test(route);
  if(!(request.method==='GET'&&(image||ordering||detail)||request.method==='POST'&&(orders||checkout)))return new NextResponse(null,{status:404});
  try{
    const body=request.method==='POST'?await request.text():undefined;
    if(body&&body.length>32768)return NextResponse.json({detail:'Pedido muito grande.'},{status:413});
    const headers:Record<string,string>={'Content-Type':'application/json'};
    const token=request.headers.get('X-Order-Token');if(token)headers['X-Order-Token']=token.slice(0,128);
    const upstream=await fetch(apiUrl(`v1/public/${path.map(encodeURIComponent).join('/')}/`),{method:request.method,headers,body,cache:'no-store',credentials:'omit',signal:AbortSignal.timeout(55000),redirect:'error'});
    const type=upstream.headers.get('content-type')||'';
    if(!(image?['image/jpeg','image/png','image/webp'].includes(type.split(';')[0]):type.includes('application/json')))return NextResponse.json({detail:'Serviço temporariamente indisponível.'},{status:upstream.ok?502:upstream.status});
    return new NextResponse(upstream.body,{status:upstream.status,headers:{'Content-Type':type,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
  }catch{return NextResponse.json({detail:'Não foi possível acessar o serviço.'},{status:502});}
}
export const GET=proxy;
export const POST=proxy;
