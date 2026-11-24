/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens live here with the route. */
import { useRef, useState, type FormEvent } from "react";
import { leerCookie } from "@sisoc/api";
import InsumosAccessError from "../InsumosAccessError";
import { prerequisiteFromForbidden, type WebPrerequisite } from "../webAccess";
import { sameOriginTarget } from "./cdiObservaciones";
import { client, internal, messagesValid, navigation, record, renderCdi, text, useCdiPage, type CdiMessage } from "./cdiFrame";
import { resetAfterRejectedPost } from "./nativeParity";
import type { RouteDefinition } from "./types";

/**
 * CDI06 intervention create and edit (`centrodeinfancia/intervencion_form.html`): the template draws
 * `{{ form.as_p }}`, so the native view stays the authority through `/api/web/cdi/` and sends that
 * markup. The POST is multipart (the attachment); a confirmed one navigates to the native redirect,
 * a rejected one redraws the form with its errors.
 */
type FormPayload = { volver_url: string; form_html: string; messages: CdiMessage[] };
type Params = { mode: "create"; centro: string } | { mode: "edit"; centro: string; id: string };

export const formValid = (v: unknown): v is FormPayload =>
  record(v) && internal(v.volver_url) && text(v.form_html) && messagesValid(v.messages);

type PostResult = { kind: "redirect"; to: string } | { kind: "invalid"; data: FormPayload } | { kind: "forbidden"; data: unknown } | { kind: "uncertain" };

/** POST once as multipart like the native form; an unconfirmed outcome is reported, never resubmitted. */
async function postOnce(endpoint: string, body: FormData): Promise<PostResult> {
  try {
    const { data, status } = await client.post(endpoint, body, { validateStatus: (s: number) => (s >= 200 && s < 300) || s === 400 || s === 403 });
    if (status === 400 && formValid(data)) return { kind: "invalid", data };
    if (status === 403) return { kind: "forbidden", data };
    const to = status < 300 && record(data) && data.ok === true ? sameOriginTarget(data.redirect) : null;
    return to ? { kind: "redirect", to } : { kind: "uncertain" };
  } catch {
    return { kind: "uncertain" };
  }
}

const UNCERTAIN = "No se pudo confirmar el resultado. Recargue la página antes de reintentar.";

function IntervencionForm({ initial, endpoint }: { initial: FormPayload; endpoint: string }) {
  const [data, setData] = useState(initial);
  const [version, setVersion] = useState(0);
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [forbidden, setForbidden] = useState<{ prerequisite: WebPrerequisite | null } | null>(null);
  const busy = useRef(false);
  if (forbidden) return <InsumosAccessError prerequisite={forbidden.prerequisite} />;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy.current) return;
    busy.current = true;
    setPending(true);
    const result = await postOnce(endpoint, new FormData(event.currentTarget));
    if (result.kind === "redirect") { navigation.assign(result.to); return; }
    if (result.kind === "forbidden") setForbidden({ prerequisite: prerequisiteFromForbidden(result.data) });
    else if (result.kind === "invalid") { setData(result.data); setVersion((v) => v + 1); setUncertain(false); resetAfterRejectedPost(); }
    else setUncertain(true);
    busy.current = false;
    setPending(false);
  }

  return (
    <div className="container-fluid">
      <div className="card">
        <div className="card-body">
          <form method="post" encType="multipart/form-data" onSubmit={submit}>
            <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
            <div key={version} dangerouslySetInnerHTML={{ __html: data.form_html }} />
            <div className="d-flex gap-2">
              <button className="btn btn-primary" type="submit" disabled={pending || uncertain}>Guardar</button>
              <a href={data.volver_url} className="btn btn-secondary">Volver</a>
            </div>
            {uncertain && <p role="alert" className="mb-0">{UNCERTAIN}</p>}
          </form>
        </div>
      </div>
    </div>
  );
}

const TITLE = "Intervención Centro de Desarrollo Infantil";

function IntervencionFormPage({ params }: { params: Params }) {
  const endpoint = params.mode === "create"
    ? `web/cdi/centros/${params.centro}/intervenciones/crear/`
    : `web/cdi/centros/${params.centro}/intervenciones/${params.id}/editar/`;
  const [state] = useCdiPage(endpoint, formValid);
  return renderCdi(state, (data) => ({ title: TITLE, heading: TITLE, content: <IntervencionForm initial={data} endpoint={endpoint} /> }));
}

const CREATE = /^\/centrodeinfancia\/intervencion\/crear\/([1-9]\d*)$/;
const EDIT = /^\/centrodeinfancia\/intervencion\/editar\/([1-9]\d*)\/([1-9]\d*)$/;

// Native URLs of the CDI intervention form (CDI06); no trailing slash, like the native routes.
export const cdiIntervencionFormRoute: RouteDefinition<Params> = {
  name: "cdi-intervencion-form",
  match: (pathname) => {
    const create = CREATE.exec(pathname);
    if (create) return { mode: "create", centro: create[1] };
    const edit = EDIT.exec(pathname);
    return edit ? { mode: "edit", centro: edit[1], id: edit[2] } : null;
  },
  render: (params) => <IntervencionFormPage params={params} />,
};
