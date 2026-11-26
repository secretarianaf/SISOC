/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens live here with the route. */
import { useRef, useState, type FormEvent } from "react";
import { leerCookie } from "@sisoc/api";
import InsumosAccessError from "../InsumosAccessError";
import { prerequisiteFromForbidden, type WebPrerequisite } from "../webAccess";
import { client, internal, messagesValid, record, renderCdi, text, useCdiPage, type CdiMessage } from "./cdiFrame";
import { handleInvalid, RenaperBloque, bloqueValid, useRenaperBloque, type BloqueConfig } from "./cdiRenaperBloque";
import { campoValid, CampoCrispy, Col, type CampoWeb } from "./cdiRenaperBloqueCampos";
import { resetAfterRejectedPost } from "./nativeParity";
import type { RouteDefinition } from "./types";

/**
 * CDI01.01 "Generar usuario referente" (`centrodeinfancia/generar_usuario_cdi.html`) and its result
 * page (`usuario_cdi_generado.html`). The native view stays the authority through
 * `/api/web/cdi/centros/<pk>/usuarios/generar/`: a valid POST creates the user and answers what the
 * native result page shows, the temporary password included, in that single response. The password
 * lives only in this component's state: no storage, no URL, no history entry, not part of any GET.
 */
type Centro = { id: number; nombre: string; url: string };
type FormPage = {
  centro: Centro; usuarios_restantes: number; fields: CampoWeb[]; non_field_errors: string[]; renaper: BloqueConfig;
  urls: { cancelar: string }; messages: CdiMessage[];
};
type ResultPage = {
  ok: true; centro: Centro; usuario: { username: string; email: string }; password: string; email_enviado: boolean;
  puede_generar_otro: boolean; urls: { generar: string }; messages: CdiMessage[];
};
type Page = (FormPage & { seq?: number }) | ResultPage;

const FIELDS = ["dni", "first_name", "last_name", "cuil", "email"];
const UNCERTAIN = "No se pudo confirmar el resultado. Recargue la página antes de reintentar.";
const centroValid = (v: unknown): v is Centro => record(v) && Number.isSafeInteger(v.id) && text(v.nombre) && internal(v.url);

function formValid(v: unknown): v is FormPage {
  return record(v) && centroValid(v.centro) && Number.isSafeInteger(v.usuarios_restantes) && Array.isArray(v.fields) &&
    v.fields.length === FIELDS.length && v.fields.every(campoValid) && (v.fields as CampoWeb[]).every((f, i) => f.name === FIELDS[i]) &&
    Array.isArray(v.non_field_errors) && v.non_field_errors.every(text) && bloqueValid(v.renaper) &&
    record(v.urls) && internal(v.urls.cancelar) && messagesValid(v.messages);
}
function resultValid(v: unknown): v is ResultPage {
  return record(v) && v.ok === true && centroValid(v.centro) && record(v.usuario) && text(v.usuario.username) && text(v.usuario.email) &&
    text(v.password) && typeof v.email_enviado === "boolean" && typeof v.puede_generar_otro === "boolean" &&
    record(v.urls) && internal(v.urls.generar) && messagesValid(v.messages);
}
const pageValid = (v: unknown): v is Page => formValid(v);

function GenerarForm({ data, endpoint, onResult, onRejected }: {
  data: FormPage; endpoint: string; onResult: (r: ResultPage) => void; onRejected: (f: FormPage) => void;
}) {
  const [values, setValues] = useState<Record<string, string>>(() => Object.fromEntries(data.fields.map((f) => [f.name, f.value])));
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [forbidden, setForbidden] = useState<{ prerequisite: WebPrerequisite | null } | null>(null);
  const busy = useRef(false);
  const byName = new Map(data.fields.map((f) => [f.name, f]));
  const field = (name: string) => byName.get(name) as CampoWeb;
  const io = {
    get: (name: string) => values[name] ?? "",
    set: (name: string, value: string) => setValues((prev) => ({ ...prev, [name]: value })),
  };
  const block = useRenaperBloque({
    ...data.renaper, dni: "dni", scope: FIELDS,
    serverLocked: data.renaper.campos.filter((n) => byName.get(n)?.renaper && byName.get(n)?.disabled),
  }, io);
  const info = (name: string) => ({ label: field(name).label, type: field(name).widget, choices: field(name).choices });
  const bind = (name: string, dni = false) => ({
    field: field(name), value: values[name] ?? "", onChange: (v: string) => io.set(name, v), block: { api: block, dni },
  });

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current) return;
    busy.current = true; setPending(true);
    // Only the fields the native form renders and does not disable, plus the signed RENAPER token.
    const body = new URLSearchParams({ csrfmiddlewaretoken: leerCookie("csrftoken") ?? "" });
    data.fields.forEach((f) => { if (block.lock(f.name) !== "server" && !(f.disabled && !f.renaper)) body.set(f.name, values[f.name] ?? ""); });
    body.set(`renaper_token_${data.renaper.bloque}`, block.token);
    try {
      const { data: reply, status } = await client.post(endpoint, body, { validateStatus: (s: number) => (s >= 200 && s < 300) || s === 400 || s === 403 });
      if (status === 403) { setForbidden({ prerequisite: prerequisiteFromForbidden(reply) }); return; }
      if (status === 400 && formValid(reply)) { onRejected(reply); return; }
      if (status >= 200 && status < 300 && resultValid(reply)) { onResult(reply); return; }
      setUncertain(true);
    } catch {
      // The outcome is unknown: the user may exist already, so it is never resubmitted.
      setUncertain(true);
    } finally {
      busy.current = false; setPending(false);
    }
  }

  if (forbidden) return <InsumosAccessError prerequisite={forbidden.prerequisite} />;
  return (
    <div className="row">
      <div className="col-12 col-lg-8 mx-auto">
        <div className="card card-primary card-outline">
          <div className="card-header mb-3">
            <h3 className="card-title">
              Generar usuario referente para:{" "}<a href={data.centro.url}>{data.centro.nombre}</a>
            </h3>
          </div>
          <div className="card-body">
            <p className="text-muted">
              Se creará un usuario con el rol <strong>CDI - Referente centro</strong>{" "}
              (no editable) asociado a este centro.{" "}
              Cupo restante: <strong>{data.usuarios_restantes}</strong>.
            </p>
            <form method="post" className="w-100" onSubmit={submit} onInvalidCapture={(e) => handleInvalid(e, [block])}>
              {data.non_field_errors.length > 0 && <ul className="errorlist nonfield">{data.non_field_errors.map((m, i) => <li key={i}>{m}</li>)}</ul>}
              <div className="row">
                <Col className="col-md-6" hidden={block.hidden("dni")}><CampoCrispy {...bind("dni", true)} /></Col>
              </div>
              <RenaperBloque api={block} info={info} values={values} />
              <div className="row">
                <Col className="col-md-4" hidden={block.hidden("first_name")}><CampoCrispy {...bind("first_name")} /></Col>
                <Col className="col-md-4" hidden={block.hidden("last_name")}><CampoCrispy {...bind("last_name")} /></Col>
                <Col className="col-md-4" hidden={block.hidden("cuil")}><CampoCrispy {...bind("cuil")} /></Col>
              </div>
              <div className="row">
                <Col className="col-md-6" hidden={block.hidden("email")}><CampoCrispy {...bind("email")} /></Col>
              </div>
              <button className="btn btn-primary mx-1" type="submit" disabled={pending || uncertain}>Generar usuario</button>
              {" "}<a href={data.urls.cancelar} className="btn btn-secondary">Cancelar</a>
              {uncertain && <p role="alert" className="mb-0">{UNCERTAIN}</p>}
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

function ResultContent({ data }: { data: ResultPage }) {
  return (
    <div className="row">
      <div className="col-12 col-lg-8 mx-auto">
        <div className="card card-primary card-outline">
          <div className="card-header mb-3">
            <h3 className="card-title">
              Usuario generado para:{" "}<a href={data.centro.url}>{data.centro.nombre}</a>
            </h3>
          </div>
          <div className="card-body">
            {data.email_enviado ? (
              <p className="text-success">
                Se envió un correo con las credenciales a{" "}<strong>{data.usuario.email}</strong>.
              </p>
            ) : (
              <p className="text-warning">
                No se pudo enviar el correo de credenciales. Entregue estos datos al referente de forma segura.
              </p>
            )}
            <p className="text-muted">
              Esta contraseña temporal también queda visible en la edición del usuario hasta su primer cambio. Cópiela ahora.
            </p>
            <div className="mb-3">
              <label className="form-label" htmlFor="cred-usuario">Usuario</label>
              <input className="form-control" id="cred-usuario" type="text" value={data.usuario.username} readOnly />
            </div>
            <div className="mb-3">
              <label className="form-label" htmlFor="cred-email">Email</label>
              <input className="form-control" id="cred-email" type="text" value={data.usuario.email} readOnly />
            </div>
            <div className="mb-3">
              <label className="form-label" htmlFor="cred-password">Contraseña temporal</label>
              <input className="form-control fs-5" id="cred-password" type="text" value={data.password} readOnly />
              <small className="text-muted">Seleccione el texto del campo y cópielo (Ctrl+C) antes de salir.</small>
            </div>
            <div className="mt-3">
              {data.puede_generar_otro && <a href={data.urls.generar} className="btn btn-secondary">Generar otro</a>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function GenerarPage({ pk }: { pk: string }) {
  const endpoint = `web/cdi/centros/${pk}/usuarios/generar/`;
  const [state, setState] = useCdiPage(endpoint, pageValid);
  return renderCdi(state, (data) => {
    if ("ok" in data) {
      return { title: "Usuario generado - Centro de Desarrollo Infantil", heading: "Usuario referente generado", bodyToasts: true, content: <ResultContent data={data} /> };
    }
    const replace = (next: Page) => state.status === "ready" && setState({ ...state, data: next });
    return {
      title: "Generar usuario - Centro de Desarrollo Infantil", heading: "Generar usuario referente del CDI", bodyToasts: true,
      content: (
        <GenerarForm key={data.seq ?? 0} data={data} endpoint={endpoint} onResult={(result) => replace(result)}
          onRejected={(form) => { replace({ ...form, seq: (data.seq ?? 0) + 1 }); resetAfterRejectedPost(); }} />
      ),
    };
  });
}

// Native URL of "Generar usuario" (same trailing slash).
export const cdiUsuariosGenerarRoute: RouteDefinition<{ pk: string }> = {
  name: "cdi-usuarios-generar",
  match: (pathname) => {
    const match = /^\/centrodeinfancia\/(\d+)\/generar-usuario\/$/.exec(pathname);
    return match ? { pk: match[1] } : null;
  },
  render: ({ pk }) => <GenerarPage pk={pk} />,
};
