import {useEffect, useId, useState, type FormEvent, type ReactNode} from 'react';
import {all, request} from '@tavvo/api-client';
import {Icon} from './Icon';

export type Values = Record<string, string | number | boolean>;
export interface Field {key: string; label: string; type?: 'text' | 'email' | 'password' | 'number' | 'checkbox' | 'textarea' | 'select'; required?: boolean; options?: {value: string; label: string}[]; step?: string; min?: string; maxLength?: number; help?: string}
export function ErrorNotice({error}: {error: unknown}) {return error ? <p role="alert" className="error">{error instanceof Error ? error.message : String(error)}</p> : null;}
export function useResource<T>(path: string, fallback: T) {
  const [value, setValue] = useState<T>(fallback);
  const [error, setError] = useState<unknown>();
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true); setError(undefined);
    request<T>(path).then(data => {if (active) setValue(data);}).catch(err => {if (active) setError(err);}).finally(() => {if (active) setLoading(false);});
    return () => {active = false;};
  }, [path, revision]);
  return {value, error, loading, reload: () => setRevision(v => v + 1)};
}
export function Form({fields, initial = {}, submit, button = 'Salvar', children}: {fields: Field[]; initial?: Values; submit: (values: Values) => Promise<void>; button?: string; children?: ReactNode}) {
  const formId = useId();
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  async function handle(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const values: Values = {};
    for (const field of fields) values[field.key] = field.type === 'checkbox' ? data.get(field.key) === 'on' : field.type === 'number' ? Number(data.get(field.key)) : String(data.get(field.key) || '');
    setBusy(true); setError(undefined);
    try {await submit(values);} catch (err) {setError(err);} finally {setBusy(false);}
  }
  return <form className="tavvo-form" onSubmit={handle}><fieldset disabled={busy}><div className="fields">{fields.map(field => {
    const id = `${formId}-${field.key}`;
    const description = field.help ? `${id}-help` : undefined;
    return <div className={field.type === 'checkbox' ? 'field field-check' : field.type === 'textarea' ? 'field field-wide' : 'field'} key={field.key}>
      {field.type === 'checkbox' ? <label className="check" htmlFor={id}><input id={id} type="checkbox" name={field.key} defaultChecked={Boolean(initial[field.key])} aria-describedby={description}/>{field.label}</label> : <>
        <label htmlFor={id}>{field.label}</label>
        {field.type === 'textarea' ? <textarea id={id} name={field.key} defaultValue={String(initial[field.key] || '')} required={field.required} aria-describedby={description}/> : field.type === 'select' ? <select id={id} name={field.key} defaultValue={String(initial[field.key] || '')} required={field.required} aria-describedby={description}><option value="">Selecione</option>{field.options?.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}</select> : <input id={id} name={field.key} type={field.type || 'text'} defaultValue={String(initial[field.key] ?? '')} required={field.required} step={field.step} min={field.min} maxLength={field.maxLength} aria-describedby={description} autoComplete={field.type === 'password' ? 'new-password' : undefined}/>}
      </>}
      {field.help ? <small className="field-help" id={description}>{field.help}</small> : null}
    </div>;
  })}</div>{children}<ErrorNotice error={error}/><button className="form-submit" type="submit">{busy ? <span className="loading-dot" aria-hidden="true"/> : null}{busy ? 'Salvando…' : button}</button></fieldset></form>;
}

export function Crud<T extends {id: string}>({title, path, fields, describe, initial = {}, prepare, extras, canWrite = true, canDelete = false, canCreate = true}: {title: string; path: string; fields: Field[]; describe: (item: T) => ReactNode; initial?: Values; prepare?: (item: T) => Values; extras?: (item: T, reload: () => void) => ReactNode; canWrite?: boolean; canDelete?: boolean; canCreate?: boolean}) {
  const [items, setItems] = useState<T[]>([]);
  const [editing, setEditing] = useState<T | null>();
  const [error, setError] = useState<unknown>();
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  const [deleting, setDeleting] = useState<string>();
  const reload = () => setRevision(v => v + 1);
  useEffect(() => {
    let active = true; setLoading(true); setError(undefined);
    all<T>(path).then(data => {if (active) setItems(data);}).catch(err => {if (active) setError(err);}).finally(() => {if (active) setLoading(false);});
    return () => {active = false;};
  }, [path, revision]);
  return <section className="crud-section"><div className="row section-heading"><h2>{title}</h2><div className="actions">{canWrite && canCreate ? <button onClick={() => setEditing(null)}><Icon name="plus"/>Adicionar</button> : null}<button className="secondary" onClick={reload}><Icon name="refresh"/>Atualizar</button></div></div><ErrorNotice error={error}/>{loading ? <p className="loading-state" role="status"><span className="loading-dot" aria-hidden="true"/>Carregando…</p> : items.length === 0 && !error ? <div className="empty-state"><Icon name="categories"/><p>Nenhum registro.</p></div> : null}
    {editing !== undefined && canWrite ? <article className="editor"><div className="editor-heading"><span className="editor-icon"><Icon name={editing ? 'edit' : 'plus'}/></span><h3>{editing ? 'Editar registro' : 'Novo registro'}</h3></div><Form key={editing?.id || 'new'} fields={fields} initial={editing ? prepare ? prepare(editing) : editing as unknown as Values : initial} submit={async values => {await request(editing ? `${path}${editing.id}/` : path, editing ? 'PATCH' : 'POST', values); setEditing(undefined); reload();}}/><button className="secondary" onClick={() => setEditing(undefined)}>Cancelar</button></article> : null}
    <div className="records">{items.map(item => <article className="record-card" key={item.id}><div className="row record-main"><div className="record-summary">{describe(item)}</div><div className="actions record-actions">{canWrite ? <button className="secondary" onClick={() => setEditing(item)}><Icon name="edit"/>Editar</button> : null}{canDelete && canWrite ? <button className="danger" disabled={deleting === item.id} onClick={async () => {if (!window.confirm('Excluir este registro? Esta ação não pode ser desfeita.')) return; setDeleting(item.id); setError(undefined); try {await request(`${path}${item.id}/`, 'DELETE'); reload();} catch (err) {setError(err);} finally {setDeleting(undefined);}}}>Excluir</button> : null}</div></div><div className="record-extras">{extras?.(item, reload)}</div></article>)}</div>
  </section>;
}
export function Action({children, run, onDone}: {children: ReactNode; run: () => Promise<unknown>; onDone?: () => void}) {
  const [busy, setBusy] = useState(false); const [error, setError] = useState<unknown>();const [done,setDone]=useState(false);
  return <><button disabled={busy} className="secondary" onClick={async () => {setBusy(true); setError(undefined);setDone(false); try {await run();setDone(true);onDone?.();} catch (err) {setError(err);} finally {setBusy(false);}}}>{busy ? 'Aguarde…' : children}</button>{done?<small className="success-message" role="status"><Icon name="check"/>Operação concluída.</small>:null}<ErrorNotice error={error}/></>;
}
