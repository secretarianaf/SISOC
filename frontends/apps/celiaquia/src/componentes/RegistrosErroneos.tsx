import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import { SectionCard, Stack, StateChip } from "@sisoc/ui";
import type { RegistroErroneo } from "@sisoc/api";

/**
 * Filas del Excel que no se pudieron importar.
 *
 * Por ahora es **solo lectura**: editar y reprocesar una fila sigue estando
 * unicamente en la pantalla Django, porque esas reglas todavia viven dentro de
 * la vista y no se extrajeron a un service.
 */
export function RegistrosErroneos({
  registros,
}: {
  registros: RegistroErroneo[];
}) {
  return (
    <SectionCard
      title={
        <Stack direction="row" spacing={1} alignItems="center">
          <span>Registros con error</span>
          <StateChip label={`${registros.length}`} tone="error" />
        </Stack>
      }
      subheader="Se corrigen desde la pantalla anterior de Celiaquía"
      disableGutters
    >
      <TableContainer sx={{ overflowX: "auto" }}>
        <Table size="small" sx={{ minWidth: 798 }}>
          <TableHead>
            <TableRow>
              <TableCell width="8%">Fila</TableCell>
              <TableCell width="42%">Datos</TableCell>
              <TableCell width="50%">Error</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {registros.map((r) => {
              const fila = (r.datos_raw ?? {}) as Record<string, string>;
              return (
              <TableRow key={r.id} hover>
                <TableCell>
                  <StateChip label={`${r.fila_excel}`} tone="neutral" />
                </TableCell>
                <TableCell>
                  <Typography variant="body2">
                    {fila.apellido || "—"}, {fila.nombre || "—"}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {fila.documento || "sin documento"}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2" sx={{ color: "error.text" }}>
                    {r.mensaje_error}
                  </Typography>
                  {r.campo_error ? (
                    <Typography variant="caption" color="text.secondary">
                      Campo: {r.campo_error}
                    </Typography>
                  ) : null}
                </TableCell>
              </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
    </SectionCard>
  );
}
