// URL → frame → estado. Fuente: sisoc-figma-ds/references/pantallas.md.
// null indica una extensión funcional sin frame dedicado en el archivo Figma.
export const frames = {
  search: "958:13058", searchFiltered: "967:12850",
  centerInfo: "976:14186", locations: "994:14440", contacts: "994:14741",
  courseNew: "1019:16705", courseEdit: "1019:17324", courseDelete: "1019:17941",
  courseDeleteEmpty: "1035:18591", courseSaved: "1019:18506",
  commissionNew: "1005:15406", commissionConfirm: "1007:15071", commissionEdit: "1055:18337",
  commissionDelete: "1056:18883", commissionDeleteEmpty: "1056:19708", commissionSaved: "1056:19117",
  commissionInfo: "1010:16185", enrollments: "1013:15889", classes: "1013:16341", attendance: "1013:16784",
  enrollmentNew: "1057:19985", enrollmentMissing: "1059:21669", enrollmentNoDocument: "1059:22248",
  enrollmentSaved: "1057:20509", enrollmentUnverified: "1059:22818", enrollmentEdit: "1057:20987",
  enrollmentCancel: "1057:21476", enrollmentCancelled: "1057:21939",
} as const;

export const fieldLabels: Record<string, string> = {
  fecha_nacimiento: "Fecha de nacimiento", telefono: "Teléfono", email: "Email",
  motivo_sin_dni: "Motivo de inscripción sin DNI", motivo_sin_dni_descripcion: "Descripción del motivo",
  nombre: "Nombre", apellido: "Apellido", cupo_total: "Cupo", ubicacion: "Ubicación",
  fecha_inicio: "Fecha de inicio", fecha_fin: "Fecha de finalización",
  dia_semana: "Día", hora_desde: "Desde", hora_hasta: "Hasta",
};

export function detail(item: { detalle: { label: string; value: string }[] }, label: string) {
  const normalized = (text: string) => text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  return item.detalle.find((field) => normalized(field.label) === normalized(label))?.value || "";
}

// "Horarios" llega como "Lunes, 14:00 a 17:00 · Miércoles, 14:00 a 17:00".
export function schedules(text: string) {
  return text.split(" · ").map((part) => part.match(/^(.+), (\d{2}:\d{2}) a (\d{2}:\d{2})$/)).flatMap((match) => match ? [{ day: match[1], from: match[2], to: match[3] }] : []);
}
export function classHours(from: string, to: string) {
  const minutes = (time: string) => Number(time.slice(0, 2)) * 60 + Number(time.slice(3, 5));
  return (minutes(to) - minutes(from)) / 60;
}
export function joinDays(days: string[]) {
  const names = days.map((day, index) => index ? day.toLowerCase() : day);
  return names.length > 1 ? `${names.slice(0, -1).join(", ")} y ${names[names.length - 1]}` : names[0] || "";
}
/** "Lunes y miércoles, 14:00 a 17:00" cuando todos los días comparten horario. */
export function scheduleSummary(text: string) {
  const rows = schedules(text);
  const shared = rows.length && rows.every((row) => row.from === rows[0].from && row.to === rows[0].to);
  return shared ? `${joinDays(rows.map((row) => row.day))}, ${rows[0].from} a ${rows[0].to}` : text;
}

export const darkFrames: Record<keyof typeof frames, string> = {
  search: "968:13713",
  searchFiltered: "968:13756",
  centerInfo: "1133:2",
  locations: "1133:74",
  contacts: "1133:157",
  courseNew: "1134:2",
  courseEdit: "1134:97",
  courseDelete: "1134:194",
  courseDeleteEmpty: "1134:277",
  courseSaved: "1134:360",
  commissionNew: "1135:2",
  commissionConfirm: "1135:65",
  commissionEdit: "1135:146",
  commissionDelete: "1135:209",
  commissionDeleteEmpty: "1135:356",
  commissionSaved: "1135:282",
  commissionInfo: "1136:2",
  enrollments: "1136:65",
  classes: "1136:127",
  attendance: "1136:189",
  enrollmentNew: "1137:2",
  enrollmentMissing: "1137:90",
  enrollmentNoDocument: "1137:186",
  enrollmentSaved: "1137:276",
  enrollmentUnverified: "1137:340",
  enrollmentEdit: "1137:404",
  enrollmentCancel: "1137:487",
  enrollmentCancelled: "1137:562",
};
