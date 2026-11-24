/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens and the native-call seam live here with the route. */
import { useRef, useState, type FormEvent } from "react";
import { NativeToasts } from "./nativeParity";
import { prerequisiteFromForbidden } from "../webAccess";
import { internal, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import type { RouteDefinition } from "./types";

/**
 * AD02.02 complementary technical report (`comedores/admision/informe_complementario/<tipo>/<pk>/ver/`),
 * with the native template's markup. Data comes from
 * `/api/web/comedores/admisiones/informes/complementario/<tipo>/<pk>/`, which runs the native view
 * (`?origen=acompanamiento` included); the form posts the new values to the same URL, which runs the
 * native `post()` (empty values, the empty change set, the service and the transitions are its own).
 * The browser then opens the page the native redirect opened, where the flash messages wait.
 */
type Params = { tipo: string; id: string };
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Campo = { identificador: string; nombre: string; valor: string };
type Grupo =
  | { titulo: string; tipo: "campos"; campos: Campo[] }
  | { titulo: string; tipo: "matriz"; identificador: string; filas: { titulo: string; campos: Campo[] }[] };
type ComplementarioData = {
  id: number; tipo: string; comedor: string; origen_acompanamiento: boolean; observaciones_legales: string;
  grupos: Grupo[]; campos_modificados: Record<string, string>;
  urls: { volver: string; pagina: string; accion: string }; messages: Message[];
};

const LEVELS = ["success", "error", "warning", "info"];
const DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
const campoOk = (c: unknown): c is Campo => record(c) && text(c.identificador) && text(c.nombre) && text(c.valor);
const grupoOk = (g: unknown): g is Grupo => record(g) && text(g.titulo) && (
  (g.tipo === "campos" && Array.isArray(g.campos) && g.campos.every(campoOk)) ||
  (g.tipo === "matriz" && text(g.identificador) && Array.isArray(g.filas) &&
    g.filas.every((f) => record(f) && text(f.titulo) && Array.isArray(f.campos) && f.campos.every(campoOk))));
const complementarioValid = (v: unknown): v is ComplementarioData => record(v) && typeof v.id === "number" &&
  ["tipo", "comedor", "observaciones_legales"].every((k) => text(v[k])) && typeof v.origen_acompanamiento === "boolean" &&
  Array.isArray(v.grupos) && v.grupos.every(grupoOk) &&
  record(v.campos_modificados) && Object.values(v.campos_modificados).every(text) &&
  record(v.urls) && internal(v.urls.volver) && internal(v.urls.pagina) && internal(v.urls.accion) &&
  Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));

/** The seams of the form: the POST to the native view and the redirect it answers with. */
export const complementarioNative = {
  post: async (url: string, values: Record<string, string>): Promise<{ status: number; redirect: string | null; data: unknown }> => {
    const { data, status } = await webClient.post(url, { values }, { validateStatus: (s: number) => s >= 200 && s < 500 });
    const redirect = record(data) && internal(data.redirect) ? data.redirect : null;
    return { status, redirect, data };
  },
  navigate: (url: string) => window.location.assign(url),
};
type Fallar = (status: number, data: unknown) => void;

type Control = { marcado: boolean; valor: string; requerido: boolean };
type Controles = Record<string, Control>;
type Cambio = (campo: Campo, cambios: Partial<Control>) => void;
type Contexto = { controles: Controles; guardados: Record<string, string>; cambiar: Cambio };

/** The page's inline script: checking a field shows its input (required), unchecking hides and clears it. */
function Entrada({ campo, ctx, chico }: { campo: Campo; ctx: Contexto; chico: boolean }) {
  const control = ctx.controles[campo.nombre];
  return <div className="input-wrapper mt-2" id={`input_${campo.identificador}`} style={{ display: control.marcado ? "block" : "none" }}>
    <input type="text" className={chico ? "form-control form-control-sm" : "form-control"} name={`campo_${campo.nombre}`} id={`campo_${campo.identificador}`}
      value={control.valor} required={control.requerido} placeholder={chico ? "Nuevo valor" : "Escriba el nuevo valor"}
      aria-label={chico ? `Nuevo valor para ${campo.nombre}` : undefined} data-field-name={campo.nombre}
      onChange={(e) => ctx.cambiar(campo, { valor: e.target.value })} />
  </div>;
}

function Casilla({ campo, ctx }: { campo: Campo; ctx: Contexto }) {
  return <input className="form-check-input campo-subsanar" type="checkbox" name="campos_subsanar" value={campo.nombre} id={`check_${campo.identificador}`}
    checked={ctx.controles[campo.nombre].marcado}
    onChange={(e) => ctx.cambiar(campo, e.target.checked ? { marcado: true, requerido: true } : { marcado: false, valor: "", requerido: false })} />;
}

function Matriz({ grupo, ctx }: { grupo: Extract<Grupo, { tipo: "matriz" }>; ctx: Contexto }) {
  return <div className="table-responsive">
    <table id={`matriz-${grupo.identificador}`} className="table table-sm table-bordered align-middle text-center mb-0">
      <thead className="table-dark">
        <tr className="text-uppercase small">
          <th scope="col" className="fw-semibold">Comida</th>
          {DIAS.map((dia) => <th key={dia} scope="col">{dia}</th>)}
        </tr>
      </thead>
      <tbody>
        {grupo.filas.map((fila) => <tr key={fila.titulo}>
          <th scope="row" className="text-nowrap fw-semibold">{fila.titulo}</th>
          {fila.campos.map((campo) => <td key={campo.identificador} className="p-1">
            <p className="mb-1 small text-muted">{campo.valor}</p>
            {campo.nombre in ctx.guardados && <p className="mb-1 small text-info">{ctx.guardados[campo.nombre]}</p>}
            <div className="form-check d-flex justify-content-center">
              <Casilla campo={campo} ctx={ctx} />
              <label className="visually-hidden" htmlFor={`check_${campo.identificador}`}>Modificar {campo.nombre}</label>
            </div>
            <Entrada campo={campo} ctx={ctx} chico />
          </td>)}
        </tr>)}
      </tbody>
    </table>
  </div>;
}

function Campos({ campos, ctx }: { campos: Campo[]; ctx: Contexto }) {
  return <div className="row">
    {campos.map((campo) => <div key={campo.identificador} className="col-md-6 mb-3">
      <div className="border rounded p-3 h-100 d-flex flex-column gap-2">
        <div className="d-flex justify-content-between align-items-center">
          <div className="flex-grow-1">
            <h6 className="mb-1">{campo.nombre}</h6>
            <p className="mb-1 text-muted">
              <strong>Valor actual:</strong> {campo.valor}
            </p>
            {campo.nombre in ctx.guardados && <p className="mb-1 text-info">
              <strong>Valor modificado:</strong> {ctx.guardados[campo.nombre]}
            </p>}
          </div>
          <div className="form-check">
            <Casilla campo={campo} ctx={ctx} />{" "}
            <label className="form-check-label" htmlFor={`check_${campo.identificador}`}>Modificar campo</label>
          </div>
        </div>
        <Entrada campo={campo} ctx={ctx} chico={false} />
      </div>
    </div>)}
  </div>;
}

const todos = (grupos: Grupo[]): Campo[] => grupos.flatMap((g) => g.tipo === "matriz" ? g.filas.flatMap((f) => f.campos) : g.campos);

function ComplementarioPage({ data, accion, fallar }: { data: ComplementarioData; accion: string; fallar: Fallar }) {
  const guardados = data.campos_modificados;
  const [controles, setControles] = useState<Controles>(() => Object.fromEntries(
    todos(data.grupos).map((c) => [c.nombre, { marcado: c.nombre in guardados, valor: guardados[c.nombre] ?? "", requerido: false }])));
  const enviando = useRef(false);
  const cambiar: Cambio = (campo, cambios) => setControles((actuales) => ({ ...actuales, [campo.nombre]: { ...actuales[campo.nombre], ...cambios } }));
  const alEnviar = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (enviando.current) return;
    enviando.current = true;
    const values = Object.fromEntries(Object.entries(controles).map(([nombre, c]) => [nombre, c.valor]));
    try {
      const { status, redirect, data: cuerpo } = await complementarioNative.post(accion, values);
      if (redirect !== null && (status === 200 || status === 400)) { complementarioNative.navigate(redirect); return; }
      enviando.current = false;
      fallar(status, cuerpo);
    } catch {
      enviando.current = false;
      fallar(0, null);
    }
  };
  const ctx: Contexto = { controles, guardados, cambiar };
  return <>
    {/* Toastr appends its container to the body in the native page. */}
    <NativeToasts messages={data.messages} />
    <div className="container mt-4">
      {data.observaciones_legales !== "" && <div className="alert alert-warning mb-3">
        <h6>
          <i className="bi bi-exclamation-triangle" /> Observaciones de Legales:
        </h6>
        <p className="mb-0">{data.observaciones_legales}</p>
      </div>}
      <div className="row">
        <form method="post" onSubmit={(e) => void alEnviar(e)}>
          {data.grupos.map((grupo) => <div key={grupo.titulo} className="card mb-4">
            <div className="card-header">
              <h5 className="mb-0">{grupo.titulo}</h5>
            </div>
            <div className="card-body">
              {grupo.tipo === "matriz" ? <Matriz grupo={grupo} ctx={ctx} /> : <Campos campos={grupo.campos} ctx={ctx} />}
            </div>
          </div>)}
          <div className="mt-4">
            <a href={data.urls.volver} className="btn btn-secondary">Volver</a>{" "}
            <button type="submit" className="btn btn-primary">Guardar y Enviar para Validación</button>
          </div>
        </form>
      </div>
    </div>
  </>;
}

function ComplementarioRoute({ tipo, id }: Params) {
  const origen = new URLSearchParams(window.location.search).get("origen") === "acompanamiento" ? "?origen=acompanamiento" : "";
  const endpoint = `web/comedores/admisiones/informes/complementario/${tipo}/${id}/${origen}`;
  const [state, setState] = useMainResource(endpoint, complementarioValid);
  // Like the other screens: a 403 is the shared access screen, anything else the error screen.
  const fallar: Fallar = (status, body) => setState(status === 403 ? { status: "forbidden", prerequisite: prerequisiteFromForbidden(body) } : { status: "error" });
  return renderMain(state, "Cargando informe…", (data) => ({
    title: `Informe Complementario: ${data.comedor}`,
    heading: `Informe Complementario: ${data.comedor}`,
    breadcrumb: <ol className="breadcrumb float-sm-right">
      <div className="breadcrumb-item"><a href={data.urls.volver}>{data.comedor}</a></div>
      <div className="breadcrumb-item active">Informe Complementario</div>
    </ol>,
    content: <ComplementarioPage data={data} accion={endpoint} fallar={fallar} />,
  }));
}

// Native GET page of `admisiones/urls/web_urls.py`, same trailing slash.
const PATH = /^\/comedores\/admision\/informe_complementario\/([a-z]+)\/([0-9]+)\/ver\/$/;

export const admisionesInformeComplementarioRoute: RouteDefinition<Params> = {
  name: "comedores-informe-complementario",
  match(pathname) {
    const m = pathname.match(PATH);
    return m ? { tipo: m[1], id: m[2] } : null;
  },
  render({ tipo, id }) {
    return <ComplementarioRoute key={`${tipo}-${id}`} tipo={tipo} id={id} />;
  },
};
