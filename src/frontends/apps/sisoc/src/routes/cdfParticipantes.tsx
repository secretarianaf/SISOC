/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens and validators live here with the route. */
import { useRef, useState, type FormEvent, type MouseEvent } from "react";
import { breadcrumb, renderWithNativeToasts } from "./cdfActividades";
import {
  CrispyField, CrispyFormErrors, errorsValid, fieldValid, type CrispyFieldData, type FormErrors,
} from "./cdfCrispy";
import { client, csrfToken, integer, internal, messagesValid, navigation, record, text, useCdfPage, type CdfMessage } from "./cdfFrame";
import { resetAfterRejectedPost } from "./nativeParity";
import type { RouteDefinition } from "./types";

/**
 * CDF-C: `centros/participanteactividad_form.html` (search by document, results with "Agregar" and the
 * citizen form) and `participanteactividad_confirm_delete.html`. The API runs the native views and
 * answers their redirect as JSON; the message they queued shows once on the native page we go to.
 * The native form posts to the page URL, query included (the invalid form is redrawn for that search).
 * The buttons keep the native `data-submit-with-spinner` behaviour (submit without browser validation,
 * disabled with a spinner) and a POST is never retried.
 */
const UNCERTAIN = "No se pudo confirmar el resultado. Verificá el estado antes de reintentar.";
const base = (centro: string, actividad: string) => `web/cdf/centros/${centro}/actividades/${actividad}/participantes/`;

type Ciudadano = { id: number; apellido: string; nombre: string; documento: string };
export type ParticipanteFormData = FormErrors & {
  query: string; ciudadanos: Ciudadano[]; no_resultados: boolean; fields: CrispyFieldData[];
  urls: { centro_list: string; actividad_list: string }; messages: CdfMessage[];
};
export type ParticipanteDeleteData = {
  participante: { id: number; apellido: string; nombre: string; documento: string };
  urls: { centro_list: string; actividad_list: string; detail: string }; messages: CdfMessage[];
};

export function formValid(v: unknown): v is ParticipanteFormData {
  return record(v) && text(v.query) && Array.isArray(v.ciudadanos) &&
    v.ciudadanos.every((c) => record(c) && integer(c.id) && text(c.apellido) && text(c.nombre) && text(c.documento)) &&
    typeof v.no_resultados === "boolean" && Array.isArray(v.fields) && v.fields.every(fieldValid) && errorsValid(v) &&
    record(v.urls) && internal(v.urls.centro_list) && internal(v.urls.actividad_list) && messagesValid(v.messages);
}

export function deleteValid(v: unknown): v is ParticipanteDeleteData {
  return record(v) && record(v.participante) && integer(v.participante.id) &&
    ["apellido", "nombre", "documento"].every((k) => text((v.participante as Record<string, unknown>)[k])) &&
    record(v.urls) && ["centro_list", "actividad_list", "detail"].every((k) => internal((v.urls as Record<string, unknown>)[k])) && messagesValid(v.messages);
}

type Phase = "idle" | "sending" | "uncertain";
const SPINNER = <><span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" />{" "}</>;

function Alerta({ message, level }: CdfMessage) {
  const [open, setOpen] = useState(true);
  if (!open) return null;
  return (
    <div className={`alert alert-${level} alert-dismissible fade show`} role="alert">
      {message}
      <button type="button" className="close" aria-label="Cerrar" onClick={() => setOpen(false)}><span aria-hidden="true">&times;</span></button>
    </div>
  );
}

export function ParticipanteFormContent({ data, centro, actividad }: { data: ParticipanteFormData; centro: string; actividad: string }) {
  const [form, setForm] = useState(data);
  const [phase, setPhase] = useState<Phase>("idle");
  const [rowBusy, setRowBusy] = useState<number | null>(null);
  const sending = useRef(false);
  const endpoint = base(centro, actividad);

  async function post(body: FormData, onInvalid?: (b: ParticipanteFormData) => void) {
    if (sending.current) return;
    sending.current = true;
    setPhase("sending");
    try {
      const { data: reply, status } = await client.post(`${endpoint}${window.location.search}`, body, { validateStatus: (s: number) => s === 200 || s === 400 });
      if (status === 200 && record(reply) && internal(reply.url)) { navigation.assign(reply.url); return; }
      if (status === 400 && formValid(reply) && onInvalid) { onInvalid(reply); sending.current = false; setPhase("idle"); resetAfterRejectedPost(); return; }
      setPhase("uncertain");
    } catch {
      setPhase("uncertain");
    }
    sending.current = false;
    setRowBusy(null);
  }

  function agregar(event: MouseEvent<HTMLButtonElement>, id: number) {
    event.preventDefault();
    if (sending.current || rowBusy !== null) return;
    setRowBusy(id);
    void post(new FormData(event.currentTarget.form as HTMLFormElement));
  }
  function crear(event: MouseEvent<HTMLButtonElement>) {
    event.preventDefault();
    if (sending.current) return;
    void post(new FormData(event.currentTarget.form as HTMLFormElement), setForm);
  }

  const showCreate = form.query !== "" && form.no_resultados;
  return (
    <div className="container">
      <h2 className="text-center display-4 mb-4">Nuevo Participante</h2>
      {form.messages.map((m, i) => <Alerta key={i} {...m} />)}
      {phase === "uncertain" && <div className="alert alert-warning" role="alert">{UNCERTAIN}</div>}
      <div className="card mb-3">
        <div className="card-header font-weight-bold">Buscar Participante</div>
        <div className="card-body">
          <form method="get" className="form-inline">
            <div className="form-group mr-2">
              <label htmlFor="busqueda-dni" className="sr-only">DNI</label>
              <input type="text" className="form-control" name="query" id="busqueda-dni" placeholder="Ingrese DNI (mín 4 dígitos)" defaultValue={form.query} />
            </div>
            <button className="btn btn-secondary mt-3" type="submit">Buscar</button>
          </form>
        </div>
      </div>
      {form.ciudadanos.length > 0 && (
        <div className="card mb-3">
          <div className="card-header font-weight-bold">Resultados de Búsqueda</div>
          <div className="card-body table-responsive">
            <table className="table table-bordered table-hover">
              <thead><tr><th>Apellido</th><th>Nombre</th><th>DNI</th><th>Acción</th></tr></thead>
              <tbody>
                {form.ciudadanos.map((c) => (
                  <tr key={c.id}>
                    <td>{c.apellido}</td>
                    <td>{c.nombre}</td>
                    <td>{c.documento}</td>
                    <td>
                      <form method="post" style={{ display: "inline" }}>
                        <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken()} />
                        <input type="hidden" name="ciudadano_id" value={c.id} />
                        <button type="submit" className="btn btn-sm btn-success" disabled={rowBusy === c.id || undefined} onClick={(e) => agregar(e, c.id)}>
                          {rowBusy === c.id ? <>{SPINNER}Agregando…</> : "Agregar"}
                        </button>
                      </form>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {showCreate && (
        <div className="card mb-3">
          <div className="card-header font-weight-bold">Crear Nuevo Ciudadano</div>
          <div className="card-body">
            {form.non_field_errors.length > 0 && (
              <div className="alert alert-danger"><ul className="errorlist nonfield">{form.non_field_errors.map((m, i) => <li key={i}>{m}</li>)}</ul></div>
            )}
            <form method="post" key={JSON.stringify(form.errors) + form.non_field_errors.join()}>
              <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken()} />
              <CrispyFormErrors messages={form.non_field_errors} />
              {form.fields.map((f) => <CrispyField key={f.name} field={f} errors={form.errors[f.name] ?? []} />)}
              <button id="btn-crear" type="submit" className="btn btn-primary" disabled={phase === "sending" || undefined} onClick={crear}>
                {phase === "sending" ? <>{SPINNER}Procesando…</> : "Crear y Asociar"}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

function ParticipanteForm({ centro, actividad }: { centro: string; actividad: string }) {
  const state = useCdfPage(`${base(centro, actividad)}${window.location.search}`, formValid);
  return renderWithNativeToasts(state, (data) => ({
    title: "Agregar Participante",
    breadcrumb: breadcrumb([["Centro de Familia", data.urls.centro_list], ["Actividades", data.urls.actividad_list], ["Nuevo Participante", null]]),
    content: <ParticipanteFormContent data={data} centro={centro} actividad={actividad} />,
  }));
}

export function ParticipanteDeleteContent({ data, centro, actividad }: { data: ParticipanteDeleteData; centro: string; actividad: string }) {
  const [phase, setPhase] = useState<Phase>("idle");
  const { participante: p } = data;
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (phase !== "idle") return;
    setPhase("sending");
    try {
      const { data: reply } = await client.post(`${base(centro, actividad)}${p.id}/eliminar/`, new FormData(event.currentTarget));
      if (record(reply) && internal(reply.url)) { navigation.assign(reply.url); return; }
      setPhase("uncertain");
    } catch {
      setPhase("uncertain");
    }
  }
  return (
    <div className="container mt-5">
      <div className="row justify-content-center">
        <div className="col-md-8">
          <div className="card shadow border-danger">
            <div className="card-header bg-danger text-white"><h4 className="mb-0">Confirmar Eliminación</h4></div>
            <div className="card-body">
              <p className="lead">¿Estás seguro que querés eliminar al siguiente participante?</p>
              <p className="mb-4">
                <strong>{p.apellido}, {p.nombre}</strong><br />
                DNI: <strong>{p.documento}</strong>
              </p>
              {phase === "uncertain" && <div className="alert alert-warning" role="alert">{UNCERTAIN}</div>}
              <form method="post" onSubmit={submit}>
                <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken()} />
                <div className="d-flex justify-content-between">
                  <a href={data.urls.detail} className="btn btn-secondary"><i className="fas fa-times" /> Cancelar</a>
                  <button type="submit" className="btn btn-danger" disabled={phase === "sending" || undefined}><i className="fas fa-trash-alt" /> Eliminar Participante</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ParticipanteDelete({ centro, actividad, id }: { centro: string; actividad: string; id: string }) {
  const state = useCdfPage(`${base(centro, actividad)}${id}/eliminar/`, deleteValid);
  return renderWithNativeToasts(state, (data) => ({
    title: "Confirmar Eliminación",
    breadcrumb: breadcrumb([
      ["Centro de Familia", data.urls.centro_list], ["Actividades", data.urls.actividad_list], ["Detalle Actividad", data.urls.detail], ["Confirmar Eliminación", null],
    ]),
    content: <ParticipanteDeleteContent data={data} centro={centro} actividad={actividad} />,
  }));
}

type Params = { centro: string; actividad: string; id?: string };

// Native URLs of the CDF participant search/create and delete confirmation (CDF-C).
export const cdfParticipantesRoute: RouteDefinition<Params> = {
  name: "cdf-participantes",
  match: (pathname) => {
    const m = /^\/centrodefamilia\/centros\/([1-9]\d*)\/actividades\/([1-9]\d*)\/participantes\/(?:crear|([1-9]\d*)\/eliminar)\/$/.exec(pathname);
    return m ? { centro: m[1], actividad: m[2], id: m[3] } : null;
  },
  render: ({ centro, actividad, id }) => (id ? <ParticipanteDelete centro={centro} actividad={actividad} id={id} /> : <ParticipanteForm centro={centro} actividad={actividad} />),
};
