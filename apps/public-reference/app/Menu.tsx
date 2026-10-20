import type {PublicMenu} from '@tavvo/api-client';
import {imagePath} from '../lib/api';

function money(price:string,currency:string):string {
  const [whole,fraction='00']=price.split('.');
  try{return `${currency==='BRL'?'R$':currency} ${new Intl.NumberFormat('pt-BR',{maximumFractionDigits:0}).format(BigInt(whole))},${fraction.padEnd(2,'0')}`;}catch{return `${price} ${currency}`;}
}
export function Menu({data,table}:{data:PublicMenu;table?:string}){
  const settings=data.restaurant.settings;const config=settings?.public_config || {};
  return <main><header><h1>{data.restaurant.name}</h1>{config.description?<p>{config.description}</p>:null}{config.address?<p>{config.address}</p>:null}{config.phone?<p>Telefone: {config.phone}</p>:null}{table?<p className="table">Mesa: {table}</p>:null}</header>{data.categories.length ? <><nav aria-label="Categorias do cardápio">{data.categories.map(category=><a key={category.id} href={`#category-${category.id}`}>{category.name}</a>)}</nav>{data.categories.map(category=><section key={category.id} id={`category-${category.id}`}><h2>{category.name}</h2>{category.description?<p>{category.description}</p>:null}<div className="products">{category.products.map(product=><article key={product.id}><div className="product-text"><h3>{product.name}</h3>{product.description?<p>{product.description}</p>:null}<strong>{money(product.price,product.currency)}</strong>{!product.is_available?<p className="unavailable">Indisponível no momento</p>:null}</div>{product.images.map(image=>{const src=imagePath(image.url);return src?<img key={image.id} src={src} alt={product.name} width="160" height="120" loading="lazy"/>:null;})}</article>)}</div>{category.products.length===0?<p>Nenhum produto publicado nesta categoria.</p>:null}</section>)}</>:<p>O restaurante ainda não publicou seu cardápio.</p>}</main>;
}
