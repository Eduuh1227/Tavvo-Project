'use client';

import {useState, type FormEvent} from 'react';
import {parts, services} from './catalog';
import styles from './workshop.module.css';

const categories = ['Todas', ...new Set(parts.map(part => part.category))];
const money = new Intl.NumberFormat('pt-BR', {style: 'currency', currency: 'BRL'});
const normalize = (value: string) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();

export function Workshop({whatsapp}: {whatsapp: string}) {
  const [category, setCategory] = useState('Todas');
  const [search, setSearch] = useState('');
  const [interest, setInterest] = useState('Revisão preventiva');
  const [message, setMessage] = useState('');
  const [copied, setCopied] = useState(false);
  const visible = parts.filter(part => (category === 'Todas' || category === part.category)
    && normalize(`${part.name} ${part.category} ${part.code}`).includes(normalize(search.trim())));

  function choose(value: string) {
    setInterest(value);
    setMessage('');
    setCopied(false);
  }

  function prepare(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const name = String(data.get('name') || '').trim();
    const vehicle = String(data.get('vehicle') || '').trim();
    if (!name || !vehicle) return;
    const notes = String(data.get('notes') || '').trim();
    setMessage(`Olá, Torque! Meu nome é ${name}. Gostaria de um orçamento para ${interest}. Meu veículo é ${vehicle}.${notes ? ` ${notes}` : ''} Podem confirmar a disponibilidade e os próximos horários?`);
    setCopied(false);
  }

  async function copyMessage() {
    try {
      await navigator.clipboard.writeText(message);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return <div className={styles.page}>
    <div className={styles.demo}>Demonstração Tavvo · Oficina, produtos e valores fictícios</div>
    <header className={styles.header}>
      <a href="#inicio" className={styles.brand} aria-label="Torque Oficina, início"><span className={styles.brandMark}>T</span><span>TORQUE<small>OFICINA MECÂNICA</small></span></a>
      <nav aria-label="Navegação da oficina"><a href="#servicos">Serviços</a><a href="#pecas">Peças</a><a href="#oficina">A oficina</a></nav>
      <a href="#orcamento" className={styles.button}>Pedir orçamento <span aria-hidden="true">↗</span></a>
    </header>
    <main className={styles.main} id="inicio">
      <section className={styles.hero}>
        <div className={styles.heroCopy}><p className={styles.eyebrow}>CUIDADO EM CADA QUILÔMETRO</p><h1>Seu carro pronto<br/>para o próximo<br/><em>caminho.</em></h1><p>Manutenção, diagnóstico e peças. Conte o que seu carro precisa e converse com a nossa equipe.</p><div className={styles.heroActions}><a className={styles.button} href="#orcamento">Solicitar orçamento ↗</a><a className={styles.textLink} href="#servicos">Conhecer os serviços ↓</a></div></div>
        <div className={styles.heroPhoto}><img src="/oficina/workshop.jpg" alt="Veículo com capô aberto em uma oficina mecânica" width="1200" height="800" fetchPriority="high"/><div className={styles.photoCaption}><span>DA REVISÃO AO REPARO</span><strong>Cuidado que começa<br/>com uma boa conversa.</strong></div></div>
      </section>
      <div className={styles.promise}><span>Orçamento antes do serviço</span><span>Peças com aplicação conferida</span><span>Atendimento pelo WhatsApp</span></div>
      <section id="servicos" className={styles.section}>
        <div className={styles.sectionHeading}><div><p className={styles.eyebrow}>O QUE FAZEMOS</p><h2>Seu carro em boas mãos.</h2></div><p>Do cuidado de rotina à investigação daquele barulho diferente.</p></div>
        <div className={styles.services}>{services.map(service => <article key={service.name}><span className={styles.serviceLabel}>{service.label}</span><h3>{service.name}</h3><p>{service.detail}</p><a href="#orcamento" onClick={() => choose(service.name)}>Consultar serviço <span aria-hidden="true">↗</span></a></article>)}</div>
      </section>
      <section id="pecas" className={`${styles.section} ${styles.catalog}`}>
        <div className={styles.sectionHeading}><div><p className={styles.eyebrow}>CATÁLOGO DE PEÇAS</p><h2>A peça certa faz diferença.</h2></div><p>Consulte a disponibilidade e confirme a compatibilidade com seu veículo.</p></div>
        <label className={styles.search}>Buscar no catálogo<input type="search" placeholder="Nome da peça ou código" value={search} onChange={event => setSearch(event.target.value)}/></label>
        <div className={styles.filters} aria-label="Filtrar peças por categoria">{categories.map(item => <button type="button" key={item} aria-pressed={category === item} onClick={() => setCategory(item)}>{item}</button>)}</div>
        <p className={styles.results} role="status">{visible.length} {visible.length === 1 ? 'peça encontrada' : 'peças encontradas'}</p>
        <div className={styles.parts}>{visible.map(part => <article key={part.id}><div className={styles.partTop}><span>{part.category}</span><small>{part.code}</small></div><h3>{part.name}</h3><p>{part.detail}</p><p className={styles.fit}>{part.fit}</p><div className={styles.partBottom}><strong>{money.format(part.price)}</strong><a href="#orcamento" onClick={() => choose(`${part.name} (${part.code})`)}>Consultar peça ↗</a></div></article>)}</div>
        {!visible.length && <div className={styles.empty}><p>Nenhuma peça encontrada. Tente outro nome ou categoria.</p><button type="button" onClick={() => {setSearch(''); setCategory('Todas');}}>Limpar filtros</button></div>}
      </section>
      <section id="oficina" className={`${styles.section} ${styles.about}`}><div><p className={styles.eyebrow}>A OFICINA</p><h2>Você entende o serviço.<br/>A gente cuida do carro.</h2></div><div><p>A Torque é a oficina fictícia desta demonstração. Aqui, você pode explorar serviços, consultar peças e preparar uma mensagem de orçamento.</p><dl><div><dt>Localização de exemplo</dt><dd>São Paulo · SP</dd></div><div><dt>Horários de exemplo</dt><dd>Segunda a sexta, 8h às 18h<br/>Sábado, 8h às 12h</dd></div></dl></div></section>
      <section id="orcamento" className={`${styles.section} ${styles.contact}`}>
        <div><p className={styles.eyebrow}>VAMOS CONVERSAR</p><h2>O próximo passo<br/>é simples.</h2><p>Informe seu veículo e o que você procura. Prepare a mensagem para consultar valores e horários com a oficina.</p>{!whatsapp && <p className={styles.notice}>Nesta demonstração, você pode visualizar e copiar a mensagem. O WhatsApp da oficina ainda será cadastrado.</p>}</div>
        <form className={styles.form} onSubmit={prepare} onChange={() => {setMessage(''); setCopied(false);}}>
          <label>Seu nome<input name="name" autoComplete="given-name" required maxLength={80} placeholder="Como podemos chamar você?"/></label>
          <label>Veículo, ano e versão<input name="vehicle" required maxLength={120} placeholder="Ex.: Chevrolet Onix 2020 1.0"/></label>
          <label>Tenho interesse em<select value={interest} onChange={event => choose(event.target.value)}>{services.map(service => <option key={service.name}>{service.name}</option>)}{parts.map(part => <option key={part.id}>{part.name} ({part.code})</option>)}<option>Outro serviço ou peça</option></select></label>
          <label>Conte mais <span>(opcional)</span><textarea name="notes" maxLength={600} rows={3} placeholder="Descreva o que precisa ou o que percebeu no carro."/></label>
          <button type="submit" className={styles.button}>Preparar mensagem ↗</button>
          {message && <div className={styles.preview}><label>Mensagem preparada<textarea readOnly value={message} rows={5}/></label>{whatsapp ? <a className={styles.button} target="_blank" rel="noopener noreferrer" href={`https://wa.me/${whatsapp}?text=${encodeURIComponent(message)}`}>Abrir no WhatsApp ↗</a> : <button type="button" className={styles.button} onClick={copyMessage}>Copiar mensagem</button>}<p role="status">{copied ? 'Mensagem copiada.' : 'A confirmação do serviço e do horário é feita pela oficina.'}</p></div>}
        </form>
      </section>
    </main>
    <footer className={styles.footer}><span>TORQUE <small>OFICINA MECÂNICA</small></span><span>Uma demonstração <strong>TAVVO</strong></span><a href="https://unsplash.com/photos/TCg8r4Z5Wu0" target="_blank" rel="noreferrer">Fotografia · Unsplash</a></footer>
  </div>;
}
