'use client';
import {createContext, useContext, useEffect, useRef, useState, type FormEvent, type ReactNode} from 'react';
import {ApiError, type Ordering, type OrderCreated, type PublicOrder, orderLabels, paymentLabels} from '@tavvo/api-client';

type Item={id:string;name:string;price:string;quantity:number};
type Access={id:string;token:string};
const CartContext=createContext<{add:(item:Omit<Item,'quantity'>)=>void;enabled:boolean}>({add:()=>{},enabled:false});
const money=(cents:number)=>new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(cents/100);
const cents=(value:string)=>Math.round(Number(value)*100);
async function api<T>(path:string, method='GET', body?:unknown, token?:string):Promise<T>{
  const response=await fetch(path,{method,cache:'no-store',credentials:'omit',headers:{'Content-Type':'application/json',...(token?{'X-Order-Token':token}:{})},body:body===undefined?undefined:JSON.stringify(body)});
  const data=await response.json();if(!response.ok)throw new ApiError(response.status,data);return data as T;
}
export function AddToCart({id,name,price}:{id:string;name:string;price:string}){
  const cart=useContext(CartContext);return cart.enabled?<button type="button" className="order-button" onClick={()=>cart.add({id,name,price})}>Adicionar ao pedido</button>:null;
}
export function OrderingProvider({slug,tableCode,children}:{slug:string;tableCode?:string;children:ReactNode}){
  const base=`/v1/public/restaurants/${encodeURIComponent(slug)}/`;
  const [policy,setPolicy]=useState<Ordering>();const [items,setItems]=useState<Item[]>([]);
  const [access,setAccess]=useState<Access>();const [order,setOrder]=useState<PublicOrder>();
  const [error,setError]=useState('');const [busy,setBusy]=useState(false);const [mode,setMode]=useState(tableCode?'table':'pickup');
  const attempt=useRef<{body:string;key:string}|undefined>(undefined);const sending=useRef(false);
  useEffect(()=>{let active=true;api<Ordering>(base+'ordering/').then(value=>{if(active){setPolicy(value);setMode(tableCode&&value.table_enabled?'table':value.pickup_enabled?'pickup':'delivery');}}).catch(()=>{if(active)setError('Não foi possível consultar a disponibilidade de pedidos. Atualize a página.');});
    try{const saved=sessionStorage.getItem(`tavvo-order-${slug}`);if(saved){const parsed=JSON.parse(saved) as Access;if(typeof parsed.id==='string'&&typeof parsed.token==='string')setAccess(parsed);}}catch{/* Storage may be disabled. */}
    return()=>{active=false;};},[base,slug,tableCode]);
  useEffect(()=>{if(!access)return;let active=true;const update=()=>api<PublicOrder>(base+`orders/${access.id}/`,'GET',undefined,access.token).then(value=>{if(active)setOrder(value);}).catch(()=>{if(active)setError('Não foi possível atualizar o pedido. Tente novamente em instantes.');});void update();const timer=setInterval(update,10000);return()=>{active=false;clearInterval(timer);};},[access,base]);
  async function checkout(current:Access){const result=await api<{url:string}>(base+`orders/${current.id}/checkout/`,'POST',undefined,current.token);const url=new URL(result.url);if(url.protocol!=='https:'||url.hostname!=='checkout.stripe.com')throw new Error('Checkout indisponível.');window.location.assign(url.href);}
  async function submit(event:FormEvent<HTMLFormElement>){
    event.preventDefault();if(sending.current||!items.length)return;sending.current=true;setBusy(true);setError('');
    const data=new FormData(event.currentTarget);const value=(key:string)=>String(data.get(key)||'').trim();
    const body={items:items.map(item=>({product_id:item.id,quantity:item.quantity})),customer_name:value('name'),customer_phone:value('phone'),customer_email:value('email'),fulfillment:mode,payment_method:value('payment'),notes:value('notes'),...(mode==='table'?{table_code:tableCode}:{}),...(mode==='delivery'?{delivery_address:{street:value('street'),number:value('number'),neighborhood:value('neighborhood'),city:value('city'),postal_code:value('postal_code').replace(/\D/g,''),complement:value('complement')}}:{})};
    const serialized=JSON.stringify(body);if(attempt.current?.body!==serialized)attempt.current={body:serialized,key:crypto.randomUUID()};
    try{const result=await api<OrderCreated>(base+'orders/','POST',{...body,idempotency_key:attempt.current.key});const current={id:result.order.id,token:result.access_token};
      try{sessionStorage.setItem(`tavvo-order-${slug}`,JSON.stringify(current));}catch{setError('Mantenha esta página aberta para acompanhar seu pedido.');}
      setAccess(current);setOrder(result.order);setItems([]);attempt.current=undefined;
      if(body.payment_method==='stripe')await checkout(current);
    }catch(err){setError(err instanceof Error?err.message:'Não foi possível enviar o pedido.');}finally{sending.current=false;setBusy(false);}
  }
  const subtotal=items.reduce((sum,item)=>sum+cents(item.price)*item.quantity,0);
  return <CartContext.Provider value={{enabled:Boolean(policy?.accepting_orders)&&!access&&!busy,add:item=>setItems(old=>{const found=old.find(x=>x.id===item.id);return found?old.map(x=>x.id===item.id?{...x,quantity:Math.min(50,x.quantity+1)}:x):old.length>=30?old:[...old,{...item,quantity:1}];})}}>{children}
    <section className="order-panel" id="pedido" aria-labelledby="order-title"><h2 id="order-title">{access?'Acompanhe seu pedido':'Seu pedido'}</h2>
      {error?<p role="alert" className="order-error">{error}</p>:null}
      {access?<>{order?<><p><strong>{orderLabels[order.status]}</strong> · {paymentLabels[order.payment_status]||order.payment_status}</p><p>Pedido #{order.id.slice(0,8)} · Estimativa: {order.estimated_minutes} min</p><ul>{order.items.map(item=><li key={item.id}>{item.quantity} × {item.name} — {money(cents(item.line_total))}</li>)}</ul><p><strong>Total: {money(cents(order.total))}</strong></p><p>Esta página atualiza a cada 10 segundos. Guarde esta aba para acompanhar.</p>{order.status==='awaiting_payment'?<button className="order-button" disabled={busy} onClick={async()=>{setBusy(true);setError('');try{await checkout(access);}catch(err){setError(err instanceof Error?err.message:'Checkout indisponível.');}finally{setBusy(false);}}}>Continuar pagamento de teste</button>:null}{['completed','cancelled'].includes(order.status)?<button className="order-button" onClick={()=>{try{sessionStorage.removeItem(`tavvo-order-${slug}`);}catch{}setAccess(undefined);setOrder(undefined);setError('');}}>Fazer outro pedido</button>:null}</>:<p role="status">Consultando pedido…</p>}</>:
      !policy?<p>Consultando disponibilidade…</p>:!policy.accepting_orders?<p>O restaurante não está recebendo pedidos pelo site neste momento.</p>:<>
        <p className="order-test">Demonstração: os pagamentos online usam o ambiente de testes da Stripe.</p>
        {!items.length?<p>Adicione produtos do cardápio para começar.</p>:<><ul className="cart-items">{items.map(item=><li key={item.id}><span>{item.name} · {money(cents(item.price)*item.quantity)}</span><label>Quantidade de {item.name}<input type="number" min="1" max="50" value={item.quantity} onChange={event=>{const quantity=Math.max(1,Math.min(50,Number(event.target.value)||1));setItems(old=>old.map(x=>x.id===item.id?{...x,quantity}:x));}}/></label><button type="button" onClick={()=>setItems(old=>old.filter(x=>x.id!==item.id))} aria-label={`Remover ${item.name}`}>Remover</button></li>)}</ul>
          <form onSubmit={submit}><fieldset disabled={busy}><label>Modalidade<select value={mode} onChange={event=>setMode(event.target.value)}>{policy.pickup_enabled?<option value="pickup">Retirada</option>:null}{policy.delivery_enabled?<option value="delivery">Entrega</option>:null}{tableCode&&policy.table_enabled?<option value="table">Na mesa</option>:null}</select></label>
            <div className="order-fields"><label>Seu nome<input name="name" autoComplete="name" required maxLength={120}/></label><label>Telefone<input name="phone" type="tel" autoComplete="tel" required maxLength={30}/></label><label>E-mail (opcional)<input name="email" type="email" autoComplete="email"/></label></div>
            {mode==='delivery'?<div className="order-fields">{[['postal_code','CEP'],['street','Rua'],['number','Número'],['neighborhood','Bairro'],['city','Cidade'],['complement','Complemento (opcional)']].map(([key,label])=><label key={key}>{label}<input name={key} required={key!=='complement'} maxLength={key==='postal_code'?9:160}/></label>)}</div>:null}
            <label>Observações<textarea name="notes" maxLength={500}/></label><label>Pagamento<select name="payment" required>{policy.offline_payment_enabled?<option value="offline">Na entrega, retirada ou mesa</option>:null}{policy.online_payment_available?<option value="stripe">Online pela Stripe (teste)</option>:null}</select></label>
            <p>Subtotal: {money(subtotal)} · Entrega: {money(mode==='delivery'?cents(policy.delivery_fee):0)}</p><p><strong>Total estimado: {money(subtotal+(mode==='delivery'?cents(policy.delivery_fee):0))}</strong></p><p>Pedido mínimo: {money(cents(policy.minimum_subtotal))}. O restaurante confirma os preços e a área de entrega no envio.</p>
            <button className="order-button" disabled={!policy.offline_payment_enabled&&!policy.online_payment_available}>{busy?'Enviando…':'Enviar pedido'}</button>
          </fieldset></form></>}
      </>}
    </section>{items.length&&!access?<a className="cart-shortcut" href="#pedido">Ver pedido · {items.reduce((n,item)=>n+item.quantity,0)} itens</a>:null}
  </CartContext.Provider>;
}
