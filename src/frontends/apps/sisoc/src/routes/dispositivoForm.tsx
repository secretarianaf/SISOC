/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screen, helpers and validators live here with the route. */
import { useCallback, useEffect, useRef, useState, type FormEvent, type MouseEvent, type ReactNode } from "react";
import InsumosAccessError from "../InsumosAccessError";
import { prerequisiteFromForbidden, type WebPrerequisite } from "../webAccess";
import { client, internal, messagesValid, navigation, record, renderCdf, text, useCdfPage, type CdfMessage } from "./cdfFrame";
import {
  archivoValid, campoValid, DocSlot, ESTADO_ICONO, esValidado, Field, grupoValid, leerCondicion, limpiarOtro, Multi, readProgress, SECCIONES, SOLO_NUMEROS,
  validarCampo, type Archivo, type Campo, type Choice, type Condicion, type Estado, type Grupo, type SeccionId,
} from "./dispositivoFormCampos";
import DispositivoMapa from "./dispositivoFormMapa";
import { TEXTOS, TOOLTIP_RAZON_SOCIAL } from "./dispositivoFormTextos";
import { Breadcrumb, breadcrumbValid, type Breadcrumbs } from "./MainFrame";
import { NativeToasts, resetAfterRejectedPost } from "./nativeParity";
import type { RouteDefinition } from "./types";

/**
 * DS03 (contract DS01-DS02, #2785): `dispositivos_form.html` (create and edit) on its native URLs. The data
 * is the projection of `DispositivoForm` (`web_api_dispositivo_form`): labels, widgets, choices, errors and the
 * saved documents come from the server; the nine section cards, the progress, the "otro" fields, the document
 * slots, the geography lists and the map preview (`dispositivoFormModerno.js`, `dispositivoUbicacion.js`) are
 * drawn here. Saving goes to `/api/web/dispositivos/`, which runs the native view; a saved device returns to
 * its legajo, where the queued message shows. A POST is sent once and never retried.
 */
export type DispositivoFormData = {
  is_edit: boolean; has_errors: boolean; fields: Campo[]; multiples: Record<string, Grupo>; files: Archivo[]; breadcrumb: Breadcrumbs;
  urls: { listar: string; municipios: string; localidades: string; address_preview: string; saved_location: string };
  messages: CdfMessage[];
};

const URLS = ["listar", "municipios", "localidades", "address_preview"] as const;
const ARCHIVOS = ["documentacion_dispositivo", "documentacion_dispositivo_adicional_1", "documentacion_dispositivo_adicional_2", "documentacion_dispositivo_adicional_3", "documentacion_dispositivo_adicional_4"];

export function formValid(v: unknown): v is DispositivoFormData {
  if (!record(v) || !record(v.urls) || !record(v.multiples)) return false;
  const urls = v.urls as Record<string, unknown>;
  return typeof v.is_edit === "boolean" && typeof v.has_errors === "boolean" && Array.isArray(v.fields) && v.fields.every(campoValid) &&
    Object.values(v.multiples).every(grupoValid) && Array.isArray(v.files) && v.files.length === ARCHIVOS.length && v.files.every(archivoValid) &&
    breadcrumbValid(v.breadcrumb) && URLS.every((k) => internal(urls[k])) && (urls.saved_location === "" || internal(urls.saved_location)) && messagesValid(v.messages);
}

const EMPTY: Choice = { value: "", label: "---------" };
const MAPS = "https://www.google.com/maps?q=";
const ESTADO_INICIAL = "Se priorizan latitud y longitud. Si ambas están vacías, se busca por domicilio. La previsualización no guarda cambios.";

type PostResult = { kind: "redirect"; to: string } | { kind: "invalid"; data: unknown } | { kind: "forbidden"; data: unknown } | { kind: "rejected"; detail: string | null } | { kind: "uncertain" };

/** POST once, multipart like the native form (the documents travel with it); an unconfirmed outcome is reported, never resubmitted. */
async function postOnce(endpoint: string, body: FormData): Promise<PostResult> {
  try {
    const { data, status } = await client.post(endpoint, body, { validateStatus: () => true });
    if (status === 400) return { kind: "invalid", data };
    if (status === 403 && record(data) && "state" in data) return { kind: "forbidden", data };
    if (status === 403 || status === 404) return { kind: "rejected", detail: record(data) && text(data.detail) ? data.detail : null };
    if (status >= 200 && status < 300 && record(data) && data.ok === true && internal(data.redirect)) return { kind: "redirect", to: data.redirect as string };
    return { kind: "uncertain" };
  } catch {
    return { kind: "uncertain" };
  }
}

const UNCERTAIN = "No se pudo confirmar el resultado. Verificá el estado antes de reintentar.";
export const geography = {
  load: async (url: string): Promise<{ id: number | string; nombre: string }[]> => {
    const response = await fetch(url);
    if (!response.ok) throw new Error("geografia");
    return response.json();
  },
};

function Seccion({ id, estado, abierta, alternar, children }: { id: SeccionId; estado: Estado; abierta: boolean; alternar: () => void; children: ReactNode }) {
  const t = TEXTOS[id];
  const { icon, label } = ESTADO_ICONO[estado];
  return (
    <div className="section-card" data-section={id}>
      <div className={`section-header${abierta ? "" : " collapsed"}`} data-toggle-section={id} tabIndex={0} role="button" aria-expanded={abierta}
        onClick={alternar} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); alternar(); } }}>
        <div className="section-header-left">
          <div className="section-icon"><i className={t.icon} /></div>
          <div className="section-title-group">
            <h3 className="section-title">{t.title}</h3>
            <p className="section-subtitle">{t.subtitle}</p>
          </div>
        </div>
        <div className="section-status">
          <span className={`status-badge ${estado}`} id={`status-${id}`}><i className={`fas ${icon}`} /> {label}</span>
          <div className="collapse-indicator"><i className="fas fa-chevron-down" /></div>
        </div>
      </div>
      <div className={`section-body collapse${abierta ? " show" : ""}`} id={`section-${id}`}>{children}</div>
    </div>
  );
}

function FormBody({ data, pending, onSubmit }: { data: DispositivoFormData; pending: boolean; onSubmit: (form: HTMLFormElement) => void }) {
  const form = useRef<HTMLFormElement>(null);
  const byName = new Map(data.fields.map((f) => [f.name, f]));
  const f = (name: string) => byName.get(name) as Campo;
  const g = (name: string) => data.multiples[name];
  const [abiertas, setAbiertas] = useState<Record<string, boolean>>({});
  const [estados, setEstados] = useState<Record<SeccionId, Estado>>(() => Object.fromEntries(SECCIONES.map((s) => [s, "empty"])) as Record<SeccionId, Estado>);
  const [condicion, setCondicion] = useState<Condicion>(() => ({
    selects: Object.fromEntries(["tipo_gestion", "tipo_dispositivo", "tiempo_permanencia_promedio", "modo_registro", "ofrece_actividades_formativas", "registra_informacion_personas"].map((n) => [n, f(n).value])),
    otro: Object.fromEntries(Object.entries(data.multiples).map(([n, grupo]) => [n, grupo.options.some((o) => o.value === "otro" && o.checked)])),
  }));
  const [visibles, setVisibles] = useState(() => data.files.map((a, i) => i === 0 || a.saved !== null));
  const [provincia, setProvincia] = useState(f("provincia").value);
  const [municipio, setMunicipio] = useState(f("municipio").value);
  const [localidad, setLocalidad] = useState(f("localidad").value);
  const [municipios, setMunicipios] = useState<Choice[]>(f("municipio").choices ?? [EMPTY]);
  const [localidades, setLocalidades] = useState<Choice[]>(f("localidad").choices ?? [EMPTY]);
  const [estadoMapa, setEstadoMapa] = useState(ESTADO_INICIAL);
  const [marco, setMarco] = useState(`${MAPS}Argentina&output=embed`);
  const generacion = useRef(0);
  const { municipios: urlMunicipios, localidades: urlLocalidades } = data.urls;

  const recalcular = useCallback(() => {
    setEstados(readProgress());
    if (form.current) setCondicion(leerCondicion(form.current));
  }, []);

  // `initializeProgressTracking` and `initializeConditionalFields` run when the page loads.
  // The reads need the drawn DOM, so they run right after the first paint, not inside the effect body.
  useEffect(() => { void Promise.resolve().then(recalcular); }, [recalcular]);

  const value = (name: string) => ((document.getElementById(`id_${name}`) as HTMLInputElement | null)?.value ?? "").trim();
  const nombreElegido = (name: string) => {
    const select = document.getElementById(`id_${name}`) as HTMLSelectElement | null;
    return select && select.value ? (select.selectedOptions[0]?.textContent ?? "").trim() : "";
  };
  function previsualizar(clic: boolean) {
    const lat = value("latitud");
    const lon = value("longitud");
    let consulta: string;
    if (lat || lon) {
      if (!lat || !lon || !Number.isFinite(Number(lat)) || !Number.isFinite(Number(lon)) || Math.abs(Number(lat)) > 90 || Math.abs(Number(lon)) > 180) {
        setEstadoMapa("Completá ambas coordenadas válidas: latitud entre -90 y 90 y longitud entre -180 y 180.");
        return;
      }
      consulta = `${lat},${lon}`;
    } else {
      const provinciaId = (document.getElementById("id_provincia") as HTMLSelectElement | null)?.value;
      const municipioId = (document.getElementById("id_municipio") as HTMLSelectElement | null)?.value;
      if (!value("calle") || !value("altura") || !provinciaId || !municipioId) {
        setEstadoMapa("Completá provincia, municipio, calle y altura para previsualizar el domicilio.");
        return;
      }
      consulta = [`${value("calle")} ${value("altura")}`, nombreElegido("localidad"), nombreElegido("municipio"), nombreElegido("provincia"), "Argentina"].filter(Boolean).join(", ");
    }
    setMarco(`${MAPS}${encodeURIComponent(consulta)}&output=embed`);
    setEstadoMapa("Ubicación previsualizada. Guardá el dispositivo para confirmar los datos.");
    if (clic) document.querySelector("[data-pin-editor]")?.dispatchEvent(new Event("pin:preview"));
  }
  // `if (...) preview();` at the end of the native script.
  useEffect(() => {
    const lat = value("latitud"), lon = value("longitud");
    if ((lat && lon) || (value("calle") && value("municipio") && value("provincia"))) void Promise.resolve().then(() => previsualizar(false));
    // Once, with the values the page loaded with.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function onProvincia(nuevo: string) {
    const mia = ++generacion.current;
    setProvincia(nuevo);
    setMunicipio("");
    setLocalidad("");
    setMunicipios([EMPTY]);
    setLocalidades([EMPTY]);
    if (!nuevo) return;
    try {
      const filas = await geography.load(`${urlMunicipios}?provincia_id=${encodeURIComponent(nuevo)}`);
      if (generacion.current === mia) setMunicipios([EMPTY, ...filas.map((m) => ({ value: String(m.id), label: m.nombre }))]);
    } catch {
      if (generacion.current === mia) setMunicipios([EMPTY]);
    }
  }
  async function onMunicipio(nuevo: string) {
    const mia = ++generacion.current;
    setMunicipio(nuevo);
    setLocalidad("");
    setLocalidades([EMPTY]);
    if (!nuevo) return;
    try {
      const filas = await geography.load(`${urlLocalidades}?municipio_id=${encodeURIComponent(nuevo)}`);
      if (generacion.current === mia) setLocalidades([EMPTY, ...filas.map((l) => ({ value: String(l.id), label: l.nombre }))]);
    } catch {
      if (generacion.current === mia) setEstadoMapa("No se pudieron cargar las localidades. Volvé a seleccionar el municipio para reintentar.");
    }
  }

  const alternar = (id: SeccionId) => setAbiertas((prev) => ({ ...prev, [id]: !(prev[id] ?? true) }));
  const sec = (id: SeccionId, children: ReactNode) => (
    <Seccion id={id} estado={estados[id]} abierta={abiertas[id] ?? true} alternar={() => alternar(id)}>{children}</Seccion>
  );
  const oculto = (visible: boolean) => (visible ? "" : " d-none");
  const otroMulti = (lista: string) => condicion.otro[lista];
  const back = (event: MouseEvent) => { event.preventDefault(); window.history.back(); };

  const completadas = SECCIONES.filter((s) => estados[s] === "complete").length;
  const adicionales = data.files.slice(1);
  const hayOculto = visibles.slice(1).some((v) => !v);

  return (
    <div className="row comedor-form">
      <div className="col-12">
        <form ref={form} method="post" id="dispositivoForm" className="w-100" encType="multipart/form-data" noValidate
          onSubmit={(e: FormEvent<HTMLFormElement>) => { e.preventDefault(); onSubmit(e.currentTarget); }}
          onChange={(e) => {
            const target = e.target as HTMLInputElement;
            if (target.type === "file") return;
            const siguiente = form.current ? leerCondicion(form.current) : condicion;
            limpiarOtro(target, siguiente);
            if (target.tagName === "SELECT" || target.type === "checkbox") validarCampo(target);
            recalcular();
          }}
          onInput={(e) => {
            const target = e.target as HTMLInputElement;
            if (SOLO_NUMEROS.includes(target.id)) {
              const limpio = target.value.replace(/\D/g, "");
              if (limpio !== target.value) target.value = limpio;
            }
            if (target.hasAttribute("required") && target.tagName !== "SELECT" && target.type !== "checkbox" && esValidado(target)) validarCampo(target);
            recalcular();
          }}
          onBlur={(e) => {
            const target = e.target as unknown as HTMLInputElement;
            if (target.hasAttribute?.("required") && target.tagName !== "SELECT" && target.type !== "checkbox") validarCampo(target);
          }}>
          {data.has_errors && <div className="alert alert-danger">No se pudo guardar el formulario. Revisá los campos marcados.</div>}

          <div className="progress-indicator">
            <div className="progress-header">
              <h4 className="progress-title"><i className="fas fa-clipboard-check mr-2" /> Progreso del Formulario</h4>
              <span className="progress-stats"><span id="completedSections">{completadas}</span>/9 secciones completadas</span>
            </div>
            <div className="progress-bar-container">
              <div className="progress-bar-fill" id="progressBarFill" style={{ width: `${(completadas / 9) * 100}%` }} />
            </div>
          </div>

          {sec("identificacion", <>
            <div className="form-group row">
              <div className="col-md-4"><Field f={f("nombre_institucion")} /></div>
              <div className="col-md-4"><Field f={f("tipo_gestion")} /></div>
            </div>
            <div className="form-group row">
              <div id="wrapper-tipo_gestion_otra" className={`col-md-4${oculto(condicion.selects.tipo_gestion === "otra")}`}><Field f={f("tipo_gestion_otra")} /></div>
              <div className="col-md-4">
                <Field f={f("razon_social")} tooltip={<span className="field-tooltip tooltip-in-label"><i className="fas fa-info-circle" /><span className="tooltip-text">{TOOLTIP_RAZON_SOCIAL}</span></span>} />
              </div>
            </div>
            <div className="form-group row"><div className="col-md-4"><Field f={f("cuit_institucion")} /></div></div>
            <fieldset>
              <legend className="h5">Ubicación</legend>
              <div className="form-group row">
                <div className="col-md-8"><Field f={f("calle")} /></div>
                <div className="col-md-4"><Field f={f("altura")} /></div>
              </div>
              <div className="form-group row">
                <div className="col-md-4"><Field f={f("provincia")} value={provincia} onChange={(v) => void onProvincia(v)} /></div>
                <div className="col-md-4"><Field f={f("municipio")} value={municipio} options={municipios} onChange={(v) => void onMunicipio(v)} /></div>
                <div className="col-md-4"><Field f={f("localidad")} value={localidad} options={localidades} onChange={setLocalidad} /></div>
              </div>
              <div className="form-group row">
                <div className="col-md-6"><Field f={f("latitud")} /></div>
                <div className="col-md-6"><Field f={f("longitud")} /></div>
              </div>
              <section className="card mb-3" aria-label="Ubicación en el mapa">
                <div className="card-body">
                  <h3 className="h5">Ubicación en el mapa</h3>
                  <button type="button" id="dispositivo-mapa-buscar" className="btn btn-secondary mb-2" onClick={() => previsualizar(true)}>Previsualizar ubicación</button>
                  <p id="dispositivo-mapa-estado" className="text-muted" role="status">{estadoMapa}</p>
                  <DispositivoMapa searchUrl={data.urls.address_preview} locationUrl={data.urls.saved_location} />
                  <iframe id="dispositivo-mapa" title="Ubicación del dispositivo" width="100%" height="320" loading="lazy" allowFullScreen src={marco} />
                </div>
              </section>
            </fieldset>
            <fieldset>
              <legend className="h5">Contacto y responsable</legend>
              <div className="form-group row">
                <div className="col-md-2"><Field f={f("telefono_prefijo")} /></div>
                <div className="col-md-4"><Field f={f("telefono_numero")} /></div>
                <div className="col-md-6"><Field f={f("correo_electronico")} /></div>
              </div>
              <div className="form-group row">
                <div className="col-md-8"><Field f={f("responsable_nombre_completo")} /></div>
                <div className="col-md-4"><Field f={f("responsable_dni")} /></div>
              </div>
            </fieldset>
          </>)}

          {sec("caracteristicas", <>
            <div className="form-group row">
              <div className="col-md-4"><Field f={f("tipo_dispositivo")} /></div>
              <div id="wrapper-tipo_dispositivo_otro" className={`col-md-4${oculto(condicion.selects.tipo_dispositivo === "otro")}`}><Field f={f("tipo_dispositivo_otro")} /></div>
            </div>
            <div className="form-group row">
              <div className="col-md-4"><Field f={f("modalidad_funcionamiento")} /></div>
              <div className="col-md-4"><Field f={f("capacidad_total_plazas")} /></div>
            </div>
            <div className="form-group row">
              <div className="col-md-4"><Multi g={g("dias_atencion")} /></div>
              <div className="col-md-4"><Multi g={g("horarios_funcionamiento")} /></div>
            </div>
          </>)}

          {sec("poblacion", (
            <div className="form-group row">
              <div className="col-md-4">
                <Multi g={g("poblacion_destinataria")} />
                <div className="row">
                  <div id="wrapper-poblacion_destinataria_otro" className={`col-md-8${oculto(otroMulti("poblacion_destinataria"))}`}><Field f={f("poblacion_destinataria_otro")} /></div>
                </div>
              </div>
              <div className="col-md-4">
                <Multi g={g("franja_etaria_destinataria")} />
                <div className="row">
                  <div className="col-md-6"><Field f={f("tiempo_permanencia_promedio")} /></div>
                  <div id="wrapper-tiempo_permanencia_otro" className={`col-md-6${oculto(condicion.selects.tiempo_permanencia_promedio === "otro")}`}><Field f={f("tiempo_permanencia_otro")} /></div>
                </div>
              </div>
            </div>
          ))}

          {sec("ingreso", <>
            <div className="form-group row">
              <div className="col-md-4">
                <Multi g={g("modalidad_ingreso")} />
                <div id="wrapper-modalidad_ingreso_otro" className={oculto(otroMulti("modalidad_ingreso")).trim()}><Field f={f("modalidad_ingreso_otro")} /></div>
              </div>
              <div className="col-md-4">
                <Multi g={g("documentacion_ingreso")} />
                <div id="wrapper-documentacion_ingreso_otro" className={oculto(otroMulti("documentacion_ingreso")).trim()}><Field f={f("documentacion_ingreso_otro")} /></div>
              </div>
            </div>
            <div className="form-group row">
              <div className="col-md-4">
                <Multi g={g("requisitos_ingreso")} />
                <div id="wrapper-requisitos_ingreso_otro" className={oculto(otroMulti("requisitos_ingreso")).trim()}><Field f={f("requisitos_ingreso_otro")} /></div>
              </div>
            </div>
          </>)}

          {sec("servicios", (
            <div className="form-group row">
              <div className="col-md-4">
                <Multi g={g("servicios_brindados")} />
                <div id="wrapper-servicios_brindados_otro" className={oculto(otroMulti("servicios_brindados")).trim()}><Field f={f("servicios_brindados_otro")} /></div>
              </div>
              <div className="col-md-4">
                <Field f={f("ofrece_actividades_formativas")} />
                <div id="actividades-detalle" className={oculto(condicion.selects.ofrece_actividades_formativas === "si").trim()}>
                  <Multi g={g("tipos_actividades_formativas")} />
                  <div id="wrapper-tipos_actividades_formativas_otro" className={oculto(otroMulti("tipos_actividades_formativas")).trim()}><Field f={f("tipos_actividades_formativas_otro")} /></div>
                  <Field f={f("actividades_certificacion_oficial")} />
                </div>
              </div>
            </div>
          ))}

          {sec("registro", <>
            <div className="form-group row"><div className="col-md-4"><Field f={f("registra_informacion_personas")} /></div></div>
            <div id="registro-detalle" className={oculto(condicion.selects.registra_informacion_personas === "si").trim()}>
              <div className="form-group row">
                <div className="col-md-4">
                  <Field f={f("modo_registro")} />
                  <div id="wrapper-modo_registro_otro" className={oculto(condicion.selects.modo_registro === "otro").trim()}><Field f={f("modo_registro_otro")} /></div>
                </div>
                <div className="col-md-4">
                  <Multi g={g("tipo_informacion_registrada")} />
                  <div id="wrapper-tipo_informacion_registrada_otro" className={oculto(otroMulti("tipo_informacion_registrada")).trim()}><Field f={f("tipo_informacion_registrada_otro")} /></div>
                </div>
              </div>
            </div>
          </>)}

          {sec("infraestructura", <>
            <div className="form-group row">
              <div className="col-md-4">
                <Multi g={g("infraestructura_disponible")} />
                <div id="wrapper-infraestructura_disponible_otro" className={oculto(otroMulti("infraestructura_disponible")).trim()}><Field f={f("infraestructura_disponible_otro")} /></div>
              </div>
              <div className="col-md-4">
                <Multi g={g("infraestructura_accesibilidad")} />
                <div id="wrapper-infraestructura_accesibilidad_otro" className={oculto(otroMulti("infraestructura_accesibilidad")).trim()}><Field f={f("infraestructura_accesibilidad_otro")} /></div>
              </div>
            </div>
            <div className="form-group row"><div className="col-md-12"><Field f={f("principales_limitaciones")} /></div></div>
            <div className="form-group row"><div className="col-md-12"><Field f={f("necesidades_prioritarias")} /></div></div>
          </>)}

          {sec("articulaciones", (
            <div className="form-group row">
              <div className="col-md-4">
                <Multi g={g("articulaciones_institucionales")} />
                <div id="wrapper-articulaciones_institucionales_otro" className={oculto(otroMulti("articulaciones_institucionales")).trim()}><Field f={f("articulaciones_institucionales_otro")} /></div>
              </div>
            </div>
          ))}

          {sec("final", <>
            <div className="form-group row"><div className="col-md-12"><Field f={f("observaciones_adicionales")} /></div></div>
            <p className="doc-section-title mt-3"><i className="fas fa-paperclip mr-1" /> Archivos adjuntos</p>
            <div className="doc-grid">
              <DocSlot file={data.files[0]} title="Documentación del dispositivo" icon="fas fa-file-contract" hidden={false} onChanged={recalcular} />
              {adicionales.map((archivo, i) => (
                <DocSlot key={archivo.name} file={archivo} title={`Documentación adicional ${i + 1}`} icon="fas fa-file" hidden={!visibles[i + 1]} onChanged={recalcular} />
              ))}
            </div>
            <button type="button" id="btn-add-doc" className={`btn btn-outline-primary mt-3${hayOculto ? "" : " d-none"}`}
              onClick={() => setVisibles((prev) => { const siguiente = prev.findIndex((v, i) => i > 0 && !v); return siguiente < 0 ? prev : prev.map((v, i) => v || i === siguiente); })}>
              <i className="fas fa-plus mr-1" /> Añadir archivo
            </button>
          </>)}

          <div className="sticky-actions">
            <div><a href={data.urls.listar} className="btn btn-secondary"><i className="fas fa-arrow-left mr-1" /> Volver</a></div>
            <div>
              <button type="button" data-history-back="true" className="btn btn-secondary mr-2" onClick={back}><i className="fas fa-times mr-1" /> Cancelar</button>{" "}
              <button className="btn btn-success" type="submit" disabled={pending || undefined}><i className="fas fa-save mr-1" /> Guardar dispositivo</button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

export function DispositivoFormContent({ data: initial, endpoint }: { data: DispositivoFormData; endpoint: string }) {
  const [data, setData] = useState(initial);
  const [version, setVersion] = useState(0);
  const [toasts, setToasts] = useState<CdfMessage[]>([]);
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [forbidden, setForbidden] = useState<{ prerequisite: WebPrerequisite | null } | null>(null);
  const sending = useRef(false);

  if (forbidden) return <InsumosAccessError prerequisite={forbidden.prerequisite} />;

  async function submit(target: HTMLFormElement) {
    if (sending.current) return;
    sending.current = true;
    setPending(true);
    const result = await postOnce(endpoint, new FormData(target));
    if (result.kind === "redirect") { navigation.assign(result.to); return; }
    if (result.kind === "invalid" && formValid(result.data)) {
      setData(result.data);
      setToasts(result.data.messages);
      setVersion((v) => v + 1);
      setUncertain(false);
      resetAfterRejectedPost();
    } else if (result.kind === "forbidden") setForbidden({ prerequisite: prerequisiteFromForbidden(result.data) });
    else if (result.kind === "rejected") window.alert(result.detail ?? "No se pudo completar la acción.");
    else setUncertain(true);
    sending.current = false;
    setPending(false);
  }

  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/comedorFormModerno.css" />
      <link rel="stylesheet" href="/static/custom/css/dispositivoFormModerno.css" />
      {toasts.length > 0 && <NativeToasts messages={toasts} />}
      {uncertain && <div className="alert alert-warning" role="alert">{UNCERTAIN}</div>}
      <div className="d-flex justify-content-between mb-3">
        <div><a href="#" data-history-back="true" className="btn btn-secondary" onClick={(e) => { e.preventDefault(); window.history.back(); }}>Cancelar</a></div>
      </div>
      <FormBody key={version} data={data} pending={pending} onSubmit={(form) => void submit(form)} />
    </>
  );
}

function DispositivoFormPage({ id }: { id?: string }) {
  const endpoint = id ? `web/dispositivos/${id}/editar/` : "web/dispositivos/crear/";
  const state = useCdfPage(endpoint, formValid);
  return renderCdf(state, (data) => ({
    title: id ? "Editar dispositivo" : "Nuevo dispositivo",
    heading: "Dispositivos",
    breadcrumb: <Breadcrumb items={data.breadcrumb} />,
    content: <DispositivoFormContent data={data} endpoint={endpoint} />,
  }));
}

const OWN = /^\/dispositivos\/(?:crear|([1-9]\d*)\/editar)$/;

// Native URLs of the Dispositivos create and edit; no trailing slash, like the Django routes.
export const dispositivoFormRoute: RouteDefinition<{ id?: string }> = {
  name: "dispositivo-form",
  match: (pathname) => {
    const own = OWN.exec(pathname);
    return own ? { id: own[1] } : null;
  },
  render: ({ id }) => <DispositivoFormPage id={id} />,
};
