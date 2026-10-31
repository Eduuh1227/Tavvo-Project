import {useEffect, useState} from 'react';
import {request, type Order, type Ordering, type BillingStatus, type Page, orderLabels, paymentLabels, fulfillmentLabels} from '@tavvo/api-client';
import {Action, ErrorNotice, Form, useResource, type Field} from './ui';

const nextStatus: Record<string,string> = {received:'accepted',accepted:'preparing',preparing:'ready',dispatched:'completed'};
export function OrdersPanel({base,manager}:{base:string;manager:boolean}) {
  const [page,setPage]=useState(1);
  const {value,error,loading,reload}=useResource<Page<Order>|null>(`${base}orders/?page=${page}`,null);
  useEffect(()=>{const timer=setInterval(reload,15000);return()=>clearInterval(timer);},[base]); // bounded polling; the API rechecks membership
  return <section><div className="row section-heading"><div><h2>Pedidos</h2><p>Atualização automática a cada 15 segundos.</p></div><button className="secondary" onClick={reload}>Atualizar</button></div><ErrorNotice error={error}/>
    {loading&&!value?<p role="status">Carregando pedidos…</p>:null}{value?.count===0?<p className="empty-state">Nenhum pedido recebido. Ative os pedidos em Entrega e retirada.</p>:null}
    <div className="records">{value?.results.map(order=>{
      const path=`${base}orders/${order.id}/`;
      const target=order.status==='ready'?(order.fulfillment==='delivery'?'dispatched':'completed'):nextStatus[order.status];
      return <article className="record-card" key={order.id}><div className="row"><h3>#{order.id.slice(0,8)} · {order.customer_name}</h3><span className="badge badge-info">{orderLabels[order.status]}</span></div>
        <p>{fulfillmentLabels[order.fulfillment]} {order.table_label} · {new Date(order.created_at).toLocaleString('pt-BR')}</p><p>{order.customer_phone} · {paymentLabels[order.payment_status]||order.payment_status} · {order.payment_method==='stripe'?'Stripe (teste)':'Pagamento presencial'}</p>
        <ul>{order.items.map(item=><li key={item.id}>{item.quantity} × {item.name} — R$ {item.line_total}</li>)}</ul>
        {order.fulfillment==='delivery'?<p>Endereço: {Object.values(order.delivery_address as Record<string,string>).filter(Boolean).join(', ')}</p>:null}
        {order.notes?<p>Observação: {order.notes}</p>:null}<p><strong>Total: R$ {order.total}</strong> · Entrega: R$ {order.delivery_fee}</p>
        <div className="actions">{target?<Action run={()=>request(path+'transition/','POST',{status:target,version:order.version})} onDone={reload}>{orderLabels[target]}</Action>:null}
          {order.payment_method==='offline'&&order.payment_status==='unpaid'&&!['cancelled','completed'].includes(order.status)?<Action run={()=>request(path+'received-payment/','POST')} onDone={reload}>Confirmar pagamento recebido</Action>:null}
          {['received','accepted','preparing','ready'].includes(order.status)&&!(order.payment_method==='stripe'&&order.payment_status==='paid')?<Action run={async()=>{if(!window.confirm('Cancelar este pedido?'))return;await request(path+'transition/','POST',{status:'cancelled',version:order.version});}} onDone={reload}>Cancelar pedido</Action>:null}
          {manager&&order.payment_method==='stripe'&&order.payment_status==='paid'?<Action run={async()=>{if(!window.confirm('Estornar integralmente este pagamento de teste?'))return;await request(path+'refund/','POST');}} onDone={reload}>Estornar pagamento</Action>:null}</div>
      </article>;
    })}</div><div className="actions"><button className="secondary" disabled={page===1} onClick={()=>setPage(p=>p-1)}>Anterior</button><span>Página {page}</span><button className="secondary" disabled={!value?.next} onClick={()=>setPage(p=>p+1)}>Próxima</button></div>
  </section>;
}

const fields:Field[]=[{key:'accepting_orders',label:'Receber pedidos',type:'checkbox'}, {key:'pickup_enabled',label:'Permitir retirada',type:'checkbox'}, {key:'delivery_enabled',label:'Permitir entrega',type:'checkbox'}, {key:'table_enabled',label:'Permitir pedidos na mesa por QR Code',type:'checkbox'}, {key:'offline_payment_enabled',label:'Permitir pagamento presencial',type:'checkbox'}, {key:'delivery_fee',label:'Taxa de entrega (R$)',required:true}, {key:'minimum_subtotal',label:'Pedido mínimo, sem taxa (R$)',required:true}, {key:'estimated_minutes',label:'Prazo estimado em minutos',type:'number',min:'5',required:true}, {key:'prefixes',label:'Área de entrega: prefixos de CEP separados por vírgulas',help:'Exemplo: 010, 011. O CEP 01001000 será atendido; outros prefixos serão recusados.'}];
export function OrderingPanel({base}:{base:string}) {
  const {value,error,loading,reload}=useResource<Ordering|null>(base+'ordering/',null);const [saved,setSaved]=useState(false);
  return <section className="settings-card"><h2>Entrega e retirada</h2><p>Configure as modalidades, a taxa e a região atendida antes de abrir os pedidos.</p><ErrorNotice error={error}/>{loading&&!value?<p>Carregando…</p>:null}{value?<Form key={JSON.stringify(value)} fields={fields} initial={{...value,delivery_postal_prefixes:undefined,prefixes:(value.delivery_postal_prefixes as string[]).join(', ') } as unknown as import('./ui').Values} submit={async data=>{const {prefixes,...rest}=data;await request(base+'ordering/','PATCH',{...rest,delivery_postal_prefixes:String(prefixes).split(',').map(s=>s.trim()).filter(Boolean)});setSaved(true);reload();}}/>:null}{saved?<p role="status">Configurações salvas.</p>:null}</section>;
}

export function BillingPanel({base}:{base:string}) {
  const {value,error,reload}=useResource<BillingStatus|null>(base+'billing/',null);
  async function open(endpoint:string) {const result=await request<{url:string}>(base+`billing/${endpoint}/`,'POST');const url=new URL(result.url);if(url.protocol!=='https:'||!(url.hostname==='checkout.stripe.com'||url.hostname==='billing.stripe.com'))throw new Error('Endereço de pagamento inválido.');window.location.assign(url.href);}
  return <section className="settings-card"><h2>Assinatura Tavvo</h2><p className="badge badge-warning">Ambiente de testes — sem cobranças reais</p><ErrorNotice error={error}/>{value?<><h3>{value.plan_label}</h3><p>Status: {({none:'Não contratada',active:'Ativa',trialing:'Período de testes',past_due:'Pagamento pendente',canceled:'Cancelada',incomplete:'Aguardando pagamento',review:'Em análise'} as Record<string,string>)[value.subscription.status]||value.subscription.status}</p>{value.subscription.current_period_end?<p>Fim do período: {new Date(value.subscription.current_period_end).toLocaleDateString('pt-BR')}{value.subscription.cancel_at_period_end?' · Cancelamento agendado':''}</p>:null}<div className="actions">{value.available?<><Action run={()=>open('checkout')}>Contratar plano de teste</Action><Action run={()=>open('portal')}>Gerenciar assinatura</Action></>:<p>O checkout estará disponível após a configuração do plano e do webhook da Stripe.</p>}<button className="secondary" onClick={reload}>Atualizar status</button></div></>:null}</section>;
}
