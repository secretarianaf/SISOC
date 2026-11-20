/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { useRef, useState, type FormEvent } from "react";
import { Breadcrumb, accepted, internal, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import { NativeToasts, resetAfterRejectedPost } from "./nativeParity";
import { BUSCADOR_CSS } from "./vatBuscadorCiudadanoStyles";
import { CsrfInput, UNCERTAIN, useForbidden } from "./vatFormShared";
import { bool, integer, messagesValid, type Message } from "./vatShared";
import type { RouteDefinition } from "./types";

/**
 * V03.02 buscador por ciudadano: `vat/buscador/ciudadano.html`. Data comes from `/api/web/vat/buscador-ciudadano/`, which
 * runs the native view: the GET is the initial state and the POST `{q, ciudadano_id}` is the native search. The CSV/XLSX
 * downloads stay the native POST of the page (a plain form submit, as in the template).
 */
type Ciudadano = {
  id: number; iniciales: string; apellido: string; nombre: string; tipo_documento: string; documento: string; cuil_cuit: string; email: string; telefono: string;
};
type Fila = {
  fecha: string; unidad: string; estado_curso: string; comision_codigo: string; comision_nombre: string; comision_url: string | null; periodo_inicio: string;
  periodo_fin: string; centro: string; cue: string; provincia: string; localidad: string; direccion: string; estado: string; estado_label: string;
  estado_comision: string; resultado: string; asistencia_pct: string; presentes: number; total_sesiones: number; origen: string;
};
export type BuscadorData = {
  q: string; estado: "inicial" | "no_encontrado" | "candidatos" | "resultado"; scope_is_national: boolean;
  candidatos: { ciudadano: Ciudadano; total_inscripciones: number }[]; ciudadano: Ciudadano | null; legajo_url: string | null;
  resumen: Record<string, string> | null; inscripciones: Fila[]; urls: { buscador: string }; messages: Message[];
};

const API = "web/vat/buscador-ciudadano/";
const RESUMEN = ["total", "en_curso", "pre_inscriptas", "en_espera", "completadas", "abandonadas", "rechazadas", "aprobadas", "desaprobadas", "sin_calificar", "presentes", "ausentes", "porcentaje_asistencia"];

const ciudadanoValid = (c: unknown) => record(c) && integer(c.id) &&
  ["iniciales", "apellido", "nombre", "tipo_documento", "documento", "cuil_cuit", "email", "telefono"].every((k) => text(c[k]));
const filaValid = (f: unknown) => record(f) &&
  ["fecha", "unidad", "estado_curso", "comision_codigo", "comision_nombre", "periodo_inicio", "periodo_fin", "centro", "cue", "provincia", "localidad", "direccion", "estado", "estado_label", "estado_comision", "resultado", "asistencia_pct", "origen"].every((k) => text(f[k])) &&
  (f.comision_url === null || internal(f.comision_url)) && integer(f.presentes) && integer(f.total_sesiones);

export const buscadorValid = (v: unknown): v is BuscadorData => record(v) && text(v.q) && ["inicial", "no_encontrado", "candidatos", "resultado"].includes(v.estado as string) &&
  bool(v.scope_is_national) && Array.isArray(v.candidatos) && v.candidatos.every((c) => record(c) && ciudadanoValid(c.ciudadano) && integer(c.total_inscripciones)) &&
  (v.ciudadano === null || ciudadanoValid(v.ciudadano)) && (v.legajo_url === null || internal(v.legajo_url)) &&
  (v.resumen === null || (record(v.resumen) && RESUMEN.every((k) => text((v.resumen as Record<string, unknown>)[k])))) &&
  Array.isArray(v.inscripciones) && v.inscripciones.every(filaValid) && record(v.urls) && internal(v.urls.buscador) && messagesValid(v.messages);

const KPIS: [string, string, string][] = [
  ["total", "", "Inscripciones"], ["en_curso", "busc-kpi--blue", "En curso"], ["completadas", "busc-kpi--green", "Completadas"], ["abandonadas", "busc-kpi--red", "Abandonadas"],
  ["rechazadas", "busc-kpi--grey", "Rechazadas"], ["pre_inscriptas", "busc-kpi--grey", "Pre-inscriptas"], ["en_espera", "busc-kpi--grey", "En espera"],
  ["aprobadas", "busc-kpi--green", "Aprobadas"], ["desaprobadas", "busc-kpi--red", "Desaprobadas"], ["sin_calificar", "busc-kpi--grey", "Sin calificar"],
];

const RESULTADOS: Record<string, [string, string]> = { aprobado: ["aprobado", "Aprobado"], desaprobado: ["desaprobado", "Desaprobado"] };

function Export({ q, ciudadano, format, icon }: { q: string; ciudadano: Ciudadano; format: string; icon: string }) {
  return <form method="post" className="busc-inline-form">
    <CsrfInput />
    <input type="hidden" name="q" value={q} />
    <input type="hidden" name="ciudadano_id" value={ciudadano.id} />
    <input type="hidden" name="export" value={format} />
    <button type="submit" className="busc-btn busc-btn--ghost busc-btn--sm"><i className={`bi ${icon}`} />{format === "csv" ? "CSV" : "XLSX"}</button>
  </form>;
}

function Resultado({ data }: { data: BuscadorData }) {
  const c = data.ciudadano!;
  const r = data.resumen!;
  return <>
    <div className="busc-card">
      <div className="busc-card-head">
        <i className="bi bi-person-vcard" />
        <span>Ciudadano</span>
        {data.legajo_url && <div className="busc-card-head__right">
          <a href={data.legajo_url} className="busc-btn busc-btn--ghost busc-btn--sm"><i className="bi bi-box-arrow-up-right" />Ver legajo</a>
        </div>}
      </div>
      <div className="busc-card-body"><div className="busc-ficha">
        <div className="busc-avatar">{c.iniciales}</div>
        <dl className="busc-dgrid">
          <div><dt>Apellido y nombre</dt><dd>{c.apellido}, {c.nombre}</dd></div>
          <div><dt>Documento</dt><dd>{c.tipo_documento} {c.documento}</dd></div>
          <div><dt>CUIL / CUIT</dt><dd>{c.cuil_cuit}</dd></div>
          <div><dt>Email</dt><dd>{c.email}</dd></div>
          <div><dt>Teléfono</dt><dd>{c.telefono}</dd></div>
        </dl>
      </div></div>
    </div>
    <div className="busc-kpis">
      {KPIS.map(([key, klass, label]) => <div key={key} className={`busc-kpi ${klass}`.trimEnd()}>
        <div className="busc-kpi__n">{r[key]}</div>
        <div className="busc-kpi__l">{label}</div>
      </div>)}
      <div className="busc-kpi busc-kpi--teal">
        <div className="busc-kpi__n">{r.porcentaje_asistencia}%</div>
        <div className="busc-kpi__l">Asistencia global</div>
      </div>
    </div>
    <div className="busc-card">
      <div className="busc-card-head">
        <i className="bi bi-mortarboard" />
        <span>Trayectoria formativa</span>
        {data.inscripciones.length > 0 && <div className="busc-card-head__right">
          <Export q={data.q} ciudadano={c} format="csv" icon="bi-filetype-csv" />
          <Export q={data.q} ciudadano={c} format="xlsx" icon="bi-file-earmark-excel" />
        </div>}
      </div>
      {data.inscripciones.length > 0 ? <div className="busc-tbl-wrap"><table className="busc-tbl">
        <thead><tr>
          {["Fecha insc.", "Curso", "Comisión", "Período", "Centro / CUE", "Ubicación", "Estado", "Resultado", "Asistencia", "Origen"].map((h) => <th key={h}>{h}</th>)}
        </tr></thead>
        <tbody>
          {data.inscripciones.map((i, n) => <tr key={n}>
            <td className="busc-nowrap">{i.fecha}</td>
            <td>{i.unidad}{" "}<span className="busc-sub">Curso: {i.estado_curso}</span></td>
            <td>
              {i.comision_url ? <a href={i.comision_url}>{i.comision_codigo}</a> : i.comision_codigo}{" "}
              <span className="busc-sub">{i.comision_nombre}</span>
            </td>
            <td className="busc-nowrap">{i.periodo_inicio ? <>{i.periodo_inicio}{" "}<span className="busc-sub">→ {i.periodo_fin}</span></> : "—"}</td>
            <td>{i.centro}{" "}{i.cue && <span className="busc-sub">CUE {i.cue}</span>}</td>
            <td>{i.provincia} / {i.localidad}{" "}{i.direccion && <span className="busc-sub">{i.direccion}</span>}</td>
            <td>
              <span className={`busc-badge busc-badge--${i.estado}`}>{i.estado_label}</span>{" "}
              <span className="busc-sub">Comisión: {i.estado_comision}</span>
            </td>
            <td>{(() => {
              const [klass, label] = RESULTADOS[i.resultado] ?? ["sin-calificar", "Sin calificar"];
              return <span className={`busc-badge busc-badge--${klass}`}>{label}</span>;
            })()}</td>
            <td>{i.total_sesiones > 0 ? <>{i.asistencia_pct}{" "}<span className="busc-sub">{i.presentes} de {i.total_sesiones} sesiones</span></> : "Sin registros"}</td>
            <td><span className="busc-badge busc-badge--grey">{i.origen}</span></td>
          </tr>)}
        </tbody>
      </table></div> : <div className="busc-card-body"><div className="busc-empty">
        <i className="bi bi-clipboard-x" />
        <h4>El ciudadano no registra inscripciones en INET</h4>
        <p>Existe en SISOC pero no tiene inscripciones a cursos o comisiones dentro de tu alcance de acceso.</p>
      </div></div>}
    </div>
  </>;
}

function BuscadorContent({ initial, forbidden }: { initial: BuscadorData; forbidden: (d: unknown) => void }) {
  const [data, setData] = useState(initial);
  const [q, setQ] = useState(initial.q);
  const [uncertain, setUncertain] = useState(false);
  const busy = useRef(false);

  async function search(query: string, ciudadanoId?: number) {
    if (busy.current) return;
    busy.current = true;
    setUncertain(false);
    const body = new URLSearchParams({ q: query });
    if (ciudadanoId !== undefined) body.append("ciudadano_id", String(ciudadanoId));
    try {
      const response = await webClient.post(API, body, { validateStatus: accepted });
      if (response.status === 403) forbidden(response.data);
      else if (buscadorValid(response.data)) {
        setData(response.data);
        // The native POST reloads the page: it starts at the top with the focus at the start of the document.
        resetAfterRejectedPost();
      }
      else setUncertain(true);
    } catch {
      setUncertain(true);
    } finally {
      busy.current = false;
    }
  }
  const submit = (event: FormEvent) => { event.preventDefault(); void search(q.trim()); };

  return <>
    <NativeToasts messages={data.messages} />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
    <link href="https://fonts.googleapis.com/css2?family=Lora:wght@600;700&family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet" />
    <style>{BUSCADOR_CSS}</style>
    <div className="busc-page">
      <div className="busc-title-row"><div className="busc-title-block">
        <h1>Buscador por Ciudadano</h1>
        <p className="busc-title-sub">
          Trayectoria formativa completa de una persona en INET: a qué cursos se anotó, en qué comisión y centro, en qué estado quedó cada inscripción y cuál fue su resultado final.
        </p>
      </div></div>

      {data.estado === "resultado" && !data.scope_is_national && <div className="busc-note">
        <i className="bi bi-shield-lock" />
        <div>
          Estás viendo únicamente las inscripciones correspondientes a los centros dentro de tu alcance de acceso. Este listado no representa necesariamente la trayectoria completa del ciudadano en INET.
        </div>
      </div>}

      <div className="busc-card">
        <div className="busc-card-head"><i className="bi bi-search" /><span>Buscar ciudadano</span></div>
        <div className="busc-card-body">
          <form method="post" className="busc-search-row" autoComplete="off" onSubmit={submit}>
            <CsrfInput />
            <label className="busc-field" htmlFor="id_q">
              <span className="busc-field__label">DNI o CUIL / CUIT</span>
              <input type="search" id="id_q" name="q" autoComplete="off" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ej.: 30123456 · 20-30123456-5" />
            </label>
            <button type="submit" className="busc-btn busc-btn--primary"><i className="bi bi-search" />Buscar</button>
            {data.q && <a href={data.urls.buscador} className="busc-btn busc-btn--ghost"><i className="bi bi-x-lg" />Limpiar</a>}
          </form>
          {uncertain && <p role="alert">{UNCERTAIN}</p>}
          <p className="busc-hint">
            <i className="bi bi-info-circle" />{" "}
            Se admite documento (<code>30123456</code>) o CUIL/CUIT con o sin guiones (<code>20-30123456-5</code>, <code>20301234565</code>). Los puntos, guiones y espacios se ignoran.
          </p>
        </div>
      </div>

      {data.estado === "inicial" && <div className="busc-card"><div className="busc-card-body"><div className="busc-empty">
        <i className="bi bi-person-vcard" />
        <h4>Ingresá un documento para comenzar</h4>
        <p>El resultado muestra únicamente inscripciones de centros dentro de tu alcance de acceso.</p>
      </div></div></div>}

      {data.estado === "no_encontrado" && <div className="busc-card"><div className="busc-card-body"><div className="busc-empty">
        <i className="bi bi-person-x" />
        <h4>No se encontró un ciudadano con ese documento</h4>
        <p>Verificá el número ingresado. Si la persona no está registrada en SISOC, primero debe darse de alta desde el módulo de Ciudadanos.</p>
      </div></div></div>}

      {data.estado === "candidatos" && <>
        <div className="busc-note">
          <i className="bi bi-people" />
          <div>Se encontraron {data.candidatos.length} ciudadanos con ese número en distintos tipos de documento. Elegí cuál querés consultar.</div>
        </div>
        <div className="busc-card">
          <div className="busc-card-head"><i className="bi bi-list-check" /><span>Coincidencias</span></div>
          <div className="busc-card-body">
            {data.candidatos.map(({ ciudadano: c, total_inscripciones: total }) => <div key={c.id} className="busc-cand">
              <div className="busc-avatar">{c.iniciales}</div>
              <div className="busc-cand-who">
                <b>{c.apellido}, {c.nombre}</b>
                <span>{c.tipo_documento} {c.documento} · {total} inscripción{total === 1 ? "" : "es"} INET</span>
              </div>
              <form method="post" className="busc-inline-form" onSubmit={(e) => { e.preventDefault(); void search(data.q, c.id); }}>
                <CsrfInput />
                <input type="hidden" name="q" value={data.q} />
                <input type="hidden" name="ciudadano_id" value={c.id} />
                <button className="busc-btn busc-btn--primary busc-btn--sm" type="submit"><i className="bi bi-arrow-right" />Ver trayectoria</button>
              </form>
            </div>)}
          </div>
        </div>
      </>}

      {data.estado === "resultado" && <Resultado data={data} />}
    </div>
  </>;
}

function BuscadorPage() {
  const [state, setState] = useMainResource(API, buscadorValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando buscador…", (data) => ({
    title: "VAT - Buscador por Ciudadano",
    breadcrumb: <Breadcrumb items={[{ text: "VAT", url: "/vat/centros/" }, { text: "Buscador por Ciudadano", url: null }]} />,
    content: <BuscadorContent initial={data} forbidden={forbidden} />,
  }));
}

// Native URL of `VAT/urls.py`.
export const vatBuscadorCiudadanoRoute: RouteDefinition<Record<string, never>> = {
  name: "vat-buscador-ciudadano",
  match: (pathname) => (pathname === "/vat/buscador-ciudadano/" ? {} : null),
  render: () => <BuscadorPage />,
};
