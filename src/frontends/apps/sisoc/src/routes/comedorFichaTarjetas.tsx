/* eslint-disable react-refresh/only-export-components -- the unit surface is this module: the card types, their validation and the row. */
import { internal, record } from "./MainFrame";

/**
 * CO07.01 ficha, `comedor_transacciones_card.html` and `comedor_mes_ejecucion_card.html`: the row
 * the page draws under the details card. Data is the `transacciones` and `mes_ejecucion` keys of
 * the `tablero` block (`null` when the page does not draw the card).
 */
export type Transacciones = { periodo: string; movimientos: string; transferido: string; gastado: string; saldo: string; detalle: string };
export type MesEjecucion = {
  expediente: { convenio: string; pago: string; prestaciones: string; monto: string; mes_pago: string; ano: string; mes_ejecucion: string } | null;
  ver_mas: string;
};
export type Tarjetas = { transacciones?: Transacciones | null; mes_ejecucion?: MesEjecucion | null };

const strs = (v: unknown, keys: string[]) => record(v) && keys.every((k) => typeof v[k] === "string");

/** Both keys are optional for older payloads; when present they must be well formed. */
export function tarjetasValid(v: Record<string, unknown>): boolean {
  const t = v.transacciones, m = v.mes_ejecucion;
  const transacciones = t === undefined || t === null || (strs(t, ["periodo", "movimientos", "transferido", "gastado", "saldo"]) && internal((t as Transacciones).detalle));
  const mes = m === undefined || m === null || (record(m) && internal(m.ver_mas) &&
    (m.expediente === null || strs(m.expediente, ["convenio", "pago", "prestaciones", "monto", "mes_pago", "ano", "mes_ejecucion"])));
  return transacciones && mes;
}

function Linea({ label, children, upper }: { label: string; children: string; upper?: boolean }) {
  return <p className="mb-0 fs-7">{label}: <strong className={upper ? "text-uppercase" : undefined}>{children}</strong></p>;
}

function TransaccionesCard({ t }: { t: Transacciones }) {
  return (
    <div className="card bg-card h-100" id="card-transacciones">
      <div className="card-header py-1"><h6 className="fw-bold my-1 text-center">Transacciones - Nación Servicios</h6></div>
      <div className="card-body d-flex flex-column">
        <Linea label="Período">{t.periodo}</Linea>
        <Linea label="Movimientos">{t.movimientos}</Linea>
        <Linea label="Transferido">{t.transferido}</Linea>
        <Linea label="Gastado">{t.gastado}</Linea>
        <Linea label="Saldo Cereado">{t.saldo}</Linea>
        <div className="mt-auto pt-3 d-flex flex-column flex-sm-row justify-content-center gap-2">
          <a href={t.detalle} className="btn btn-primary px-2 py-1 fs-7 w-100 w-sm-auto">Ver detalles</a>
        </div>
      </div>
    </div>
  );
}

function MesEjecucionCard({ m }: { m: MesEjecucion }) {
  const e = m.expediente;
  return (
    <div className="card bg-card h-100" id="card-mes-ejecucion">
      <div className="card-header py-1"><h6 className="fw-bold my-1 text-center">Mes de ejecución</h6></div>
      <div className="card-body d-flex flex-column">
        {e ? (
          <>
            <Linea label="Expediente del convenio" upper>{e.convenio}</Linea>
            <Linea label="Expediente de pago" upper>{e.pago}</Linea>
            <Linea label="Cantidad de prestaciones">{e.prestaciones}</Linea>
            <Linea label="Monto total de prestaciones">{e.monto}</Linea>
            <Linea label="Mes de pago">{e.mes_pago}</Linea>
            <Linea label="Año">{e.ano}</Linea>
            <Linea label="Mes de ejecución">{e.mes_ejecucion}</Linea>
          </>
        ) : <p className="mb-0 fs-7">No hay expedientes de pago cargados para este comedor.</p>}
        <div className="mt-auto pt-3 d-flex flex-column flex-sm-row justify-content-center gap-2">
          <a href={m.ver_mas} className="btn btn-primary px-2 py-1 fs-7 w-100 w-sm-auto">Ver más</a>
        </div>
      </div>
    </div>
  );
}

/** The row under the details card: nothing when the page draws neither card. */
export function TarjetasFila({ data }: { data: Tarjetas }) {
  const t = data.transacciones ?? null, m = data.mes_ejecucion ?? null;
  if (!t && !m) return null;
  return (
    <div className="row mt-3">
      {t && <div className="col-12 col-lg-6 mb-3 mb-lg-0"><TransaccionesCard t={t} /></div>}
      {m && <div className={`col-12 col-lg-6${t ? "" : " ms-lg-auto"}`}><MesEjecucionCard m={m} /></div>}
    </div>
  );
}
