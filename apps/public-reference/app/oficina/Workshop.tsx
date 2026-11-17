'use client';

import {useEffect, useRef, useState, type FormEvent} from 'react';
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
  const [copyStatus, setCopyStatus] = useState<'idle' | 'copied' | 'failed'>('idle');
  const preview = useRef<HTMLTextAreaElement>(null);
  const searchField = useRef<HTMLInputElement>(null);
  const query = normalize(search.trim());
  const visible = parts.filter(part => (category === 'Todas' || category === part.category)
    && normalize(`${part.name} ${part.category} ${part.code}`).includes(query));

  useEffect(() => {
    if (message) preview.current?.focus();
  }, [message]);

  function clearMessage() {
    setMessage('');
    setCopyStatus('idle');
  }

  function choose(value: string) {
    setInterest(value);
    clearMessage();
  }

  function prepare(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const name = String(data.get('name') || '').trim();
    const vehicle = String(data.get('vehicle') || '').trim();
    if (!name || !vehicle) {
      const field = form.elements.namedItem(name ? 'vehicle' : 'name') as HTMLInputElement;
      field.setCustomValidity(name ? 'Informe o veículo, o ano e a versão.' : 'Informe seu nome.');
      field.reportValidity();
      return;
    }
    const notes = String(data.get('notes') || '').trim();
    setMessage(`Olá, Torque! Meu nome é ${name}. Gostaria de um orçamento para ${interest}. Meu veículo é ${vehicle}.${notes ? ` ${notes}` : ''} Podem confirmar a disponibilidade e os próximos horários?`);
    setCopyStatus('idle');
  }

  async function copyMessage() {
    const field = preview.current;
    try {
      await navigator.clipboard.writeText(message);
      if (field?.value === message && field.isConnected) setCopyStatus('copied');
    } catch {
      if (field?.value === message && field.isConnected) setCopyStatus('failed');
    }
  }

  return (
    <div className={styles.page}>
      <a className={styles.skip} href="#inicio">Pular para o conteúdo</a>
      <div className={styles.demo}>Demonstração Tavvo. Oficina, produtos e valores fictícios.</div>
      <header className={styles.header}>
        <a href="#inicio" className={styles.brand} translate="no">
          <span className={styles.brandMark} aria-hidden="true">T</span>
          <span>TORQUE <small>Oficina mecânica</small></span>
        </a>
        <nav aria-label="Navegação da oficina">
          <a href="#servicos">Serviços</a>
          <a href="#pecas">Peças</a>
          <a href="#oficina">A oficina</a>
          <a href="#orcamento" className={styles.headerQuote}>Pedir orçamento</a>
        </nav>
      </header>

      <main className={styles.main} id="inicio" tabIndex={-1}>
        <section className={styles.hero}>
          <div className={styles.heroCopy}>
            <h1>Seu carro pronto para o próximo caminho.</h1>
            <p>Da revisão ao diagnóstico, encontre o serviço ou a peça que seu carro precisa e consulte a oficina.</p>
            <div className={styles.heroActions}>
              <a className={styles.button} href="#orcamento">Solicitar orçamento <span aria-hidden="true">↗</span></a>
              <a className={styles.textLink} href="#servicos">Conhecer os serviços</a>
            </div>
          </div>
          <figure className={styles.heroPhoto}>
            <img src="/oficina/workshop.jpg" alt="Veículo com capô aberto em uma oficina mecânica" width={1400} height={933} fetchPriority="high"/>
          </figure>
        </section>

        <ul className={styles.promise}>
          <li>Orçamento antes do serviço</li>
          <li>Peças com aplicação conferida</li>
          <li>Atendimento pelo WhatsApp</li>
        </ul>

        <section id="servicos" className={styles.section} aria-labelledby="servicos-titulo">
          <div className={styles.sectionHeading}>
            <h2 id="servicos-titulo">Serviços de oficina</h2>
            <p>Da manutenção de rotina à investigação daquele barulho diferente.</p>
          </div>
          <div className={styles.services}>
            {services.map(service => (
              <article key={service.name}>
                <span className={styles.serviceLabel}>{service.label}</span>
                <h3>{service.name}</h3>
                <p>{service.detail}</p>
                <a className={styles.textLink} href="#orcamento" onClick={() => choose(service.name)}>
                  Consultar serviço <span className={styles.visuallyHidden}>{service.name}</span><span aria-hidden="true">↗</span>
                </a>
              </article>
            ))}
          </div>
        </section>

        <section id="pecas" className={`${styles.section} ${styles.catalog}`} aria-labelledby="pecas-titulo">
          <div className={styles.sectionHeading}>
            <h2 id="pecas-titulo">Catálogo de peças</h2>
            <p>Consulte a disponibilidade e confirme a compatibilidade com seu veículo.</p>
          </div>
          <div className={styles.catalogTools}>
            <label className={styles.search}>
              Buscar no catálogo
              <input ref={searchField} type="search" name="workshop-search" autoComplete="off" spellCheck={false} placeholder="Jogo de pastilhas ou TRQ-001…" value={search} onChange={event => setSearch(event.target.value)}/>
            </label>
            <div className={styles.filters} role="group" aria-labelledby="filtros-titulo">
              <span id="filtros-titulo">Categoria</span>
              <div>
                {categories.map(item => (
                  <button type="button" key={item} aria-pressed={category === item} onClick={() => setCategory(item)}>{item}</button>
                ))}
              </div>
            </div>
          </div>
          <p className={styles.results} role="status">{visible.length} {visible.length === 1 ? 'peça encontrada' : 'peças encontradas'}</p>
          {visible.length ? (
            <div className={styles.parts}>
              {visible.map(part => (
                <article key={part.id}>
                  <div className={styles.partTop}><span>{part.category}</span><span translate="no">{part.code}</span></div>
                  <h3>{part.name}</h3>
                  <p>{part.detail}</p>
                  <p className={styles.fit}>{part.fit}</p>
                  <div className={styles.partBottom}>
                    <strong>{money.format(part.price)}</strong>
                    <a className={styles.textLink} href="#orcamento" onClick={() => choose(`${part.name} (${part.code})`)}>
                      Consultar peça <span className={styles.visuallyHidden}>{part.name}</span><span aria-hidden="true">↗</span>
                    </a>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className={styles.empty}>
              <p>Nenhuma peça encontrada. Tente outro nome ou categoria.</p>
              <button type="button" className={styles.secondaryButton} onClick={() => {
                searchField.current?.focus();
                setSearch('');
                setCategory('Todas');
              }}>Limpar filtros</button>
            </div>
          )}
        </section>

        <section id="oficina" className={`${styles.section} ${styles.about}`} aria-labelledby="oficina-titulo">
          <div>
            <h2 id="oficina-titulo">A oficina</h2>
            <p>A Torque é uma oficina fictícia da Tavvo. Explore os serviços, consulte o catálogo e experimente preparar um orçamento.</p>
          </div>
          <dl>
            <div><dt>Localização de exemplo</dt><dd>São Paulo, SP</dd></div>
            <div><dt>Horários de exemplo</dt><dd>Segunda a sexta, 8h às 18h<br/>Sábado, 8h às 12h</dd></div>
          </dl>
        </section>

        <section id="orcamento" className={`${styles.section} ${styles.contact}`} aria-labelledby="orcamento-titulo">
          <div className={styles.contactIntro}>
            <h2 id="orcamento-titulo">Peça um orçamento</h2>
            <p>Informe seu veículo e o que você procura. Prepare uma mensagem para consultar valores e horários com a oficina.</p>
            {!whatsapp && <p className={styles.notice}>Nesta demonstração, você pode visualizar e copiar a mensagem. O WhatsApp da oficina ainda será cadastrado.</p>}
          </div>
          <form className={styles.form} onSubmit={prepare} onChange={clearMessage}>
            <label className={styles.shortField}>
              Seu nome
              <input name="name" autoComplete="given-name" required maxLength={80} onInput={event => event.currentTarget.setCustomValidity('')}/>
            </label>
            <label className={styles.shortField}>
              Veículo, ano e versão
              <input name="vehicle" autoComplete="off" required maxLength={120} placeholder="Ex.: Chevrolet Onix 2020 1.0…" onInput={event => event.currentTarget.setCustomValidity('')}/>
            </label>
            <label>
              Tenho interesse em
              <select name="interest" autoComplete="off" value={interest} onChange={event => choose(event.target.value)}>
                <optgroup label="Serviços">{services.map(service => <option key={service.name}>{service.name}</option>)}</optgroup>
                <optgroup label="Peças">{parts.map(part => <option key={part.id}>{part.name} ({part.code})</option>)}</optgroup>
                <option>Outro serviço ou peça</option>
              </select>
            </label>
            <label>
              Conte mais <span>(opcional)</span>
              <textarea name="notes" autoComplete="off" maxLength={600} rows={3}/>
            </label>
            <button type="submit" className={styles.button}>Preparar mensagem <span aria-hidden="true">↗</span></button>
            {message && (
              <div className={styles.preview}>
                <label>Mensagem preparada<textarea ref={preview} name="preview" readOnly value={message} rows={6}/></label>
                <p>A confirmação do serviço e do horário é feita pela oficina.</p>
                {whatsapp ? (
                  <a className={styles.button} target="_blank" rel="noopener noreferrer" href={`https://wa.me/${whatsapp}?text=${encodeURIComponent(message)}`}>Abrir no WhatsApp <span aria-hidden="true">↗</span></a>
                ) : (
                  <button type="button" className={styles.secondaryButton} onClick={copyMessage}>Copiar mensagem</button>
                )}
                <p className={styles.feedback} role="status">
                  {copyStatus === 'copied' && 'Mensagem copiada.'}
                  {copyStatus === 'failed' && 'Não foi possível copiar. Selecione o texto da mensagem e copie manualmente.'}
                </p>
              </div>
            )}
          </form>
        </section>
      </main>

      <footer className={styles.footer}>
        <span translate="no"><strong>TORQUE</strong> Oficina mecânica</span>
        <span>Uma demonstração <strong translate="no">TAVVO</strong></span>
        <a href="https://unsplash.com/photos/TCg8r4Z5Wu0" target="_blank" rel="noreferrer">Crédito da foto</a>
      </footer>
    </div>
  );
}
