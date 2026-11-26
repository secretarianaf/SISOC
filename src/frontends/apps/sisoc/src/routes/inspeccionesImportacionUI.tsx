const labels = ["Archivo", "Revisión", "Resultado"] as const;

export function ImportSteps({ step }: { step: 1 | 2 | 3 }) {
  return <ol className="insp-pasos" aria-label="Pasos">
    {labels.map((label, index) => {
      const current = index + 1;
      return <li key={label} className={step > current ? "hecho" : step === current ? "actual" : ""} aria-current={step === current ? "step" : undefined}>
        <span className="insp-paso-num">{step > current ? "✓" : current}</span>{" "}{label}
      </li>;
    }).flatMap((element, index) => index === 0 ? [element] : [<li key={`line-${index}`} className="insp-paso-linea" aria-hidden="true" />, element])}
  </ol>;
}

export function EscuelasImportHelp() {
  return <p className="small text-muted">
    {"Columnas del padrón oficial: "}<strong>Jurisdicción</strong>{", "}<strong>Localidad</strong>{", "}
    <strong>Cueanexo</strong>{" y "}<strong>Nombre</strong>
    {" (obligatorias), Domicilio, C. P., Teléfono y Mail. Del Excel se lee sólo la primera hoja y el encabezado puede estar después de filas de título. El Cueanexo lleva 9 dígitos: dejá la columna como texto para conservar los ceros iniciales. Una escuela que ya está en el catálogo se actualiza; nada se borra. Antes de guardar vas a ver qué se importa y qué queda a revisar."}
  </p>;
}

export function AsignacionesImportHelp() {
  return <p className="small text-muted">
    {"Columnas: "}<strong>fecha</strong>{" (AAAA-MM-DD o DD/MM/AAAA), "}<strong>cueanexo</strong>{" e "}<strong>inspector</strong>
    {" (usuario, DNI o mail). El inspector tiene que tener la sección Inspecciones escolares con rol Inspector. Una asignación repetida no se duplica; si la escuela ya tiene otro inspector ese día, se asigna igual y cuenta como otra visita."}
  </p>;
}
