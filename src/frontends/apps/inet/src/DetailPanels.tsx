import { Box, Typography } from "@mui/material";
import LocationOn from "@mui/icons-material/LocationOn";
import type { InetItem } from "@sisoc/api";
import { classHours, detail, schedules } from "./design";
import { formatDate } from "./data";

export function CenterPanel({ item }: { item: InetItem }) {
  const address = detail(item, "Domicilio mapa") || detail(item, "Domicilio de actividades") || detail(item, "Domicilio");
  const mapQuery = address.trim() && item.localidad.trim() && item.provincia.trim()
    ? [address.trim(), item.localidad.trim(), item.provincia.trim(), "Argentina"].join(", ") : "";
  const groups = [
    { title: "Establecimiento", fields: [["CUE", item.cue], ["Sector de gestión", detail(item, "Tipo de Gestión")], ["Teléfono", detail(item, "Teléfono")], ["Celular", detail(item, "Celular")], ["Correo electrónico", detail(item, "Correo electrónico")]] },
    { title: "Domicilio", fields: [["Provincia", item.provincia], ["Localidad", item.localidad], ["Calle y altura", detail(item, "Domicilio de actividades") || detail(item, "Domicilio")], ["Código postal", detail(item, "Código Postal")]] },
    { title: "Referente del centro", fields: [["Nombre y apellido", detail(item, "Referente nombre")], ["DNI", detail(item, "Referente DNI")], ["Teléfono", detail(item, "Referente teléfono")], ["Correo electrónico", detail(item, "Referente correo")], ["Usuario del sistema", detail(item, "Referente usuario")]] },
  ];
  return <Box component="section" sx={{ bgcolor: "background.paper", border: 1, borderColor: "divider", borderRadius: (theme) => `${theme.radius.large}px`, p: 3, mb: 3 }}>
    <Typography variant="h6" component="h2">Información general</Typography>
    <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>Fuente: INET{detail(item, "Actualizado") ? ` · Actualizado el ${formatDate(detail(item, "Actualizado"))}` : ""}</Typography>
    <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", lg: "minmax(180px, 280px) repeat(3, minmax(0, 1fr))" }, gap: 3 }}>
      <Box aria-label="Mapa de la sede" sx={{ bgcolor: "action.hover", borderRadius: 1, minHeight: 250, overflow: "hidden", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", color: "text.secondary" }}>
        {mapQuery ? <Box component="iframe" title={`Mapa de la sede: ${item.nombre}`} loading="lazy" referrerPolicy="no-referrer-when-downgrade" allowFullScreen src={`https://www.google.com/maps?hl=es&q=${encodeURIComponent(mapQuery)}&output=embed`} sx={{ width: "100%", minHeight: 250, flex: 1, border: 0 }} />
          : <><LocationOn sx={{ color: "action.active" }} /><Typography variant="caption" sx={{ px: 2, textAlign: "center" }}>Sin datos suficientes para mostrar el mapa</Typography></>}
      </Box>
      {groups.map((group) => <Box key={group.title}><Typography variant="overline" color="text.primary">{group.title}</Typography><Box component="dl" sx={{ m: 0, mt: 1 }}>{group.fields.map(([label, value]) => <Box key={label} sx={{ mb: 1.5 }}><Typography component="dt" variant="caption" color="text.secondary">{label}</Typography><Typography component="dd" variant="body2" sx={{ m: 0, fontWeight: 500, overflowWrap: "anywhere" }}>{value || "—"}</Typography></Box>)}</Box></Box>)}
    </Box>
  </Box>;
}

export function CommissionPanel({ item }: { item: InetItem }) {
  const groups = [
    { title: "Comisión", fields: [["Curso", detail(item, "Curso nombre")], ["Plan curricular", detail(item, "Plan nombre")], ["Ubicación", detail(item, "Ubicación nombre")], ["Cupo", `${detail(item, "Cupo total")} estudiantes`]] },
    { title: "Período", fields: [["Fecha de inicio", formatDate(item.fecha_inicio)], ["Fecha de finalización", formatDate(item.fecha_fin)], ["Clases", String(item.clases_count)]] },
    { title: "Horarios", fields: [...(schedules(detail(item, "Horarios")).length ? schedules(detail(item, "Horarios")).map((row) => [row.day, `${row.from} a ${row.to} · ${classHours(row.from, row.to)} h`]) : [["Días y horas", detail(item, "Horarios")]]), ["Total semanal", detail(item, "Total semanal")]] },
  ];
  return <Box component="section" sx={{ bgcolor: "background.paper", border: 1, borderColor: "divider", borderRadius: (theme) => `${theme.radius.large}px`, p: 3, mb: 3 }}>
    <Typography variant="h6" component="h2" sx={{ mb: 3 }}>Datos de la comisión</Typography>
    <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(3, minmax(0, 1fr))" }, gap: 3 }}>
      {groups.map((group) => <Box key={group.title}><Typography variant="overline" color="text.secondary">{group.title}</Typography><Box component="dl" sx={{ m: 0, mt: 1 }}>{group.fields.map(([label, value]) => <Box key={label} sx={{ mb: 2 }}><Typography component="dt" variant="caption" color="text.secondary">{label}</Typography><Typography component="dd" variant="body2" sx={{ m: 0, fontWeight: 500 }}>{value || "—"}</Typography></Box>)}</Box></Box>)}
    </Box>
    {!!detail(item, "Observaciones") && <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>Observaciones: {detail(item, "Observaciones")}</Typography>}
  </Box>;
}
