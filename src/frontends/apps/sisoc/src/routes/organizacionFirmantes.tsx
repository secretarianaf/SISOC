/* eslint-disable react-refresh/only-export-components -- the module exports its validators and the legajo section next to the routes. */
import { useState, type FormEvent } from "react";
import { InsumosToastList } from "../InsumosToast";
import { CascadePreview, type Preview } from "./organizacionesBaja";
import { CrispyField, FLASH_KEY, freshPage, organizacionesNavigation, type Field, type Message } from "./organizacionesForm";
import { accepted, internal, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import type { RouteDefinition } from "./types";

/**
 * O03 `firmante_form.html` / `aval_form.html` (alta and edición through
 * `components/form_card.html`), the `*_confirm_delete.html` baja
 * (`components/delete_confirm.html`) and the "Firmantes" tables of the legajo
 * (`legajo/firmantes.html`). The API runs the native views: roles by tipo de
 * entidad, limited programs, one role per organization and the logical baja
 * come from Django. The organization of an alta travels in the hidden
 * `organizacion_id`, as the native form posts it. Kept as the native page
 * renders it: the alta's empty submit anchor in the top bar and the baja's
 * breadcrumb without text (its items read `label` where the component reads `text`).
 */
type Kind = "firmantes" | "avales";
type Mode = "crear" | "editar" | "eliminar";
type SignerForm = { title: string; organization_id: number | null; allow_another: boolean; fields: Field[]; non_field_errors: string[]; urls: { back: string | null }; messages: Message[] };
type BajaData = { id: number; title: string; message: string; cascade_preview: Preview | null; urls: { cancel: string }; messages: Message[] };

const LEVELS = ["success", "error", "warning", "info"];
const FAILED: Message = { message: "No se pudo guardar. Recargá la página para ver el estado actual.", level: "error" };
const FAILED_BAJA: Message = { message: "No se pudo dar de baja. Recargá la página para ver el estado actual.", level: "error" };
const messagesValid = (v: unknown) => Array.isArray(v) && v.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));

export function formularioValid(v: unknown): v is SignerForm {
  return record(v) && text(v.title) && Array.isArray(v.fields) && v.fields.every((f) => record(f) && text(f.name) && text(f.label) && text(f.type) && Array.isArray(f.errors)) &&
    Array.isArray(v.non_field_errors) && record(v.urls) && (v.urls.back === null || internal(v.urls.back)) && messagesValid(v.messages);
}

export function bajaValid(v: unknown): v is BajaData {
  return record(v) && typeof v.id === "number" && text(v.title) && text(v.message) && record(v.urls) && internal(v.urls.cancel) &&
    (v.cascade_preview === null || (record(v.cascade_preview) && Array.isArray(v.cascade_preview.desglose_por_modelo))) && messagesValid(v.messages);
}

function keep(messages: unknown) {
  if (Array.isArray(messages) && messages.length) { try { window.sessionStorage.setItem(FLASH_KEY, JSON.stringify(messages)); } catch { /* the message is optional */ } }
}

function FormContent({ kind, mode, id, initial }: { kind: Kind; mode: "crear" | "editar"; id: number; initial: SignerForm }) {
  const [form, setForm] = useState(initial);
  const [values, setValues] = useState<Record<string, unknown>>(() => Object.fromEntries(initial.fields.map((f) => [f.name, f.value])));
  const [toasts, setToasts] = useState<Message[]>(initial.messages);
  const [pending, setPending] = useState(false);
  const alta = mode === "crear";
  const set = (name: string, v: unknown) => setValues((cur) => ({ ...cur, [name]: v }));
  const field = (name: string) => form.fields.find((f) => f.name === name);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const another = ((event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null)?.name === "guardar_otro";
    const body = new URLSearchParams();
    if (alta) body.set("organizacion_id", String(id));
    for (const f of form.fields) body.set(f.name, values[f.name] == null ? "" : String(values[f.name]));
    if (another) body.set("guardar_otro", "true");
    setPending(true);
    try {
      const url = alta ? `web/comedores/organizaciones/${id}/${kind}/` : `web/comedores/organizaciones/${kind}/${id}/`;
      const { data, status } = await webClient.post(url, body, { validateStatus: (s: number) => accepted(s) || s === 400 });
      if ((status === 200 || status === 201) && record(data) && internal(data.redirect)) {
        keep(data.messages);
        organizacionesNavigation.assign(data.redirect);
        return;
      }
      if (status === 400 && record(data) && record(data.form) && formularioValid({ ...data.form, urls: { back: null }, messages: [] })) {
        const bound = data.form as unknown as SignerForm;
        setForm({ ...form, fields: bound.fields, non_field_errors: bound.non_field_errors });
        setValues(Object.fromEntries(bound.fields.map((f) => [f.name, f.value])));
        setToasts(messagesValid(data.messages) ? (data.messages as Message[]) : []);
        freshPage();
        return;
      }
      setToasts([FAILED]);
    } catch {
      setToasts([FAILED]);
    } finally { setPending(false); }
  }

  return (
    <>
      <InsumosToastList messages={toasts} />
      <div className="d-flex justify-content-between mb-4">
        {alta && form.urls.back && (
          <>
            <a href={form.urls.back} className="btn btn-outline-light">Volver</a>
            <div className="btn-group"><a href="" className="btn btn-submit " /></div>
          </>
        )}
      </div>
      <div className="card card-body shadow">
        <h2 className="text-center display-4 mb-4">{form.title}</h2>
        <form method="post" encType="multipart/form-data" onSubmit={submit}>
          {alta && <input type="hidden" name="organizacion_id" value={id} />}
          {form.non_field_errors.length > 0 && <div className="alert alert-block alert-danger">{form.non_field_errors.map((e) => <div key={e}>{e}</div>)}</div>}
          {["nombre", "rol", "cuit", "programa"].filter((name) => field(name)).map((name) => <CrispyField key={name} f={field(name)!} values={values} set={set} />)}
          <div className="text-center mt-4">
            <button type="submit" className="btn btn-primary" disabled={pending}>Guardar</button>
            {form.allow_another && " "}
            {form.allow_another && <button type="submit" name="guardar_otro" value="true" className="btn btn-primary ml-2" disabled={pending}>Guardar y agregar otro</button>}
          </div>
        </form>
      </div>
    </>
  );
}

function FormPage({ kind, mode, id }: { kind: Kind; mode: "crear" | "editar"; id: number }) {
  const endpoint = mode === "crear" ? `web/comedores/organizaciones/${id}/${kind}/formulario/` : `web/comedores/organizaciones/${kind}/${id}/formulario/`;
  const [state] = useMainResource(endpoint, formularioValid);
  return renderMain(state, "Cargando formulario…", (data) => ({
    title: "Organizaciones",
    heading: "Organizaciones",
    breadcrumb: <ol className="breadcrumb float-sm-right" />,
    content: <FormContent kind={kind} mode={mode} id={id} initial={data} />,
  }));
}

function BajaContent({ kind, data }: { kind: Kind; data: BajaData }) {
  const [toasts, setToasts] = useState<Message[]>(data.messages);
  const [pending, setPending] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    try {
      const { data: body, status } = await webClient.post(`web/comedores/organizaciones/${kind}/${data.id}/baja/`, new URLSearchParams(), { validateStatus: accepted });
      if (status === 200 && record(body) && internal(body.redirect)) { keep(body.messages); organizacionesNavigation.assign(body.redirect); return; }
      setToasts([FAILED_BAJA]);
    } catch {
      setToasts([FAILED_BAJA]);
    } finally { setPending(false); }
  }
  return (
    <>
      <InsumosToastList messages={toasts} />
      <div className="error-page mt-5 px-3">
        <div className="error-content">
          <h3><i className="fas fa-exclamation-triangle text-danger px-2" /> {data.title}</h3>
          <p>{data.message} <span className="font-weight-bold" />?</p>
          <CascadePreview preview={data.cascade_preview} />
          <div className="text-left">
            <form method="post" onSubmit={submit}>
              <button type="submit" className="btn btn-danger btn-sm" disabled={pending}>Dar de baja</button>{" "}
              <a href={data.urls.cancel} className="btn btn-secondary btn-sm">Cancelar</a>
            </form>
          </div>
        </div>
      </div>
    </>
  );
}

function BajaPage({ kind, id }: { kind: Kind; id: number }) {
  const [state] = useMainResource(`web/comedores/organizaciones/${kind}/${id}/baja/`, bajaValid);
  return renderMain(state, "Cargando baja…", (data) => ({
    title: "Confirmar Eliminación",
    // `delete_confirm` page: the native breadcrumb items carry `label`, which the component does not read: empty link and empty active item.
    breadcrumb: <ol className="breadcrumb float-sm-right"><li className="breadcrumb-item "><a href={data.urls.cancel} /></li><li className="breadcrumb-item active" /></ol>,
    content: <BajaContent kind={kind} data={data} />,
  }));
}

// --- legajo section (`legajo/firmantes.html`) -----------------------------------------------

type SignerRow = { id: number; name: string; role: string | null; cuit: string; program: string | null; edit_url: string; delete_url: string };
export type FirmantesSection = { kind: "firmantes"; title: string; color: string; show_program: boolean; can_manage: boolean; add_url: string | null; rows: SignerRow[] };

export const firmantesSectionValid = (v: unknown): v is FirmantesSection =>
  record(v) && v.kind === "firmantes" && text(v.title) && text(v.color) && (v.add_url === null || internal(v.add_url)) && Array.isArray(v.rows) &&
  v.rows.every((r) => record(r) && typeof r.id === "number" && text(r.name) && internal(r.edit_url) && internal(r.delete_url));

export function FirmantesSection({ section }: { section: FirmantesSection }) {
  return (
    <div className={`tabla-legajo card-programa card-${section.color}`}>
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h5 className="mb-0">{section.title}</h5>
        {section.add_url && <a href={section.add_url} className="btn btn-success btn-sm"><i className="fas fa-plus" /> Agregar Firmante</a>}
      </div>
      {section.rows.length > 0 ? (
        <table className="table table-sm">
          <thead>
            <tr>
              <th>Nombre</th><th>Rol</th><th>CUIT</th>
              {section.show_program && <th>Programa</th>}
              {section.can_manage && <th className="text-end">Acciones</th>}
            </tr>
          </thead>
          <tbody>
            {section.rows.map((row) => (
              <tr key={row.id}>
                <td>{row.name}</td>
                <td>{row.role ? <span className="badge badge-gold">{row.role}</span> : "-"}</td>
                <td>{row.cuit}</td>
                {section.show_program && (
                  <td>{row.program ? <span className="badge badge-gris">{row.program} (no cargado en la organización)</span> : <span className="badge badge-pendiente">Sin programa</span>}</td>
                )}
                {section.can_manage && (
                  <td className="text-end">
                    <a href={row.edit_url} className="btn btn-sm accion-editar" aria-label={`Editar firmante ${row.name}`}><i className="fas fa-edit" /></a>{" "}
                    <a href={row.delete_url} className="btn btn-sm accion-eliminar" aria-label={`Eliminar firmante ${row.name}`}><i className="fas fa-trash" /></a>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      ) : <p className="texto-vacio mb-0">No hay firmantes registrados.</p>}
    </div>
  );
}

// Native URLs of `urls.py`: no trailing slash.
const PAGES = { firmante: "firmantes", aval: "avales" } as const;
const MODES = { crear: "crear", editar: "editar", eliminar: "eliminar" } as const;
type Params = { kind: Kind; mode: Mode; id: number };

export const organizacionFirmantesRoute: RouteDefinition<Params> = {
  name: "comedores-organizaciones-firmantes",
  match(pathname) {
    const found = /^\/organizaciones\/(firmante|aval)\/(crear|editar|eliminar)\/([1-9]\d{0,14})$/.exec(pathname);
    return found ? { kind: PAGES[found[1] as keyof typeof PAGES], mode: MODES[found[2] as keyof typeof MODES], id: Number(found[3]) } : null;
  },
  render: ({ kind, mode, id }) => (mode === "eliminar" ? <BajaPage kind={kind} id={id} /> : <FormPage kind={kind} mode={mode} id={id} />),
};
