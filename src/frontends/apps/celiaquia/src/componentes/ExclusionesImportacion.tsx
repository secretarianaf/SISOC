import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import { Link as RouterLink } from "react-router-dom";
import Link from "@mui/material/Link";
import { SectionCard, Stack, StateChip } from "@sisoc/ui";
import type { ExclusionImportacion } from "@sisoc/api";

/**
 * Filas que el Excel traía bien pero que no se importaron.
 *
 * Son **distintas de los registros erróneos**: ahí la fila está mal formada y
 * se corrige. Acá la fila está bien, pero la persona ya está en el programa en
 * otro expediente. No hay nada que corregir en el Excel, así que no van a esa
 * grilla y antes se perdían en silencio: el usuario veía "se crearon N
 * legajos" sin saber por qué faltaban los otros.
 *
 * La regla la aplica `ImportacionService` al importar, con el documento como
 * clave. Acá solo se muestra el resultado.
 */
export function ExclusionesImportacion({
  exclusiones,
}: {
  exclusiones: ExclusionImportacion[];
}) {
  if (exclusiones.length === 0) return null;

  return (
    <SectionCard
      title={
        <Stack direction="row" spacing={1} alignItems="center">
          <span>Personas no incorporadas</span>
          <StateChip label={`${exclusiones.length}`} tone="warning" />
        </Stack>
      }
      subheader="Ya están en el programa: no se pueden cargar dos veces"
      disableGutters
    >
      <TableContainer sx={{ overflowX: "auto" }}>
        <Table size="small" sx={{ minWidth: 798 }}>
          <TableHead>
            <TableRow>
              <TableCell width="8%">Fila</TableCell>
              <TableCell width="34%">Persona</TableCell>
              <TableCell width="42%">Motivo</TableCell>
              <TableCell width="16%">Expediente</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {exclusiones.map((e) => (
              <TableRow key={`${e.fila}-${e.documento}`} hover>
                <TableCell>
                  <StateChip label={`${e.fila}`} tone="neutral" />
                </TableCell>
                <TableCell>
                  <Typography variant="body2">
                    {e.apellido || "—"}, {e.nombre || "—"}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {e.documento || "sin documento"}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2">{e.motivo}</Typography>
                  {e.estado_expediente_origen ? (
                    <Typography variant="caption" color="text.secondary">
                      Estado de origen: {e.estado_expediente_origen}
                    </Typography>
                  ) : null}
                </TableCell>
                <TableCell>
                  {e.expediente_origen_id ? (
                    <Link
                      component={RouterLink}
                      to={`/expedientes/${e.expediente_origen_id}`}
                      variant="body2"
                    >
                      #{e.expediente_origen_id}
                    </Link>
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      —
                    </Typography>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </SectionCard>
  );
}
