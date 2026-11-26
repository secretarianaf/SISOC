import { Box } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { pasGet } from "./api";
import { Oculto } from "./componentes";
import { Cargando, ErrorPas } from "./Estado";

/**
 * Cursos PAS (Administración): módulo reservado. Por ahora solo ocupa el área
 * de contenido con el fondo estándar de SISOC (`background.default` del
 * theme); el contenido se agrega en una próxima versión.
 */
export function CursosPage() {
  const query = useQuery({ queryKey: ["pas", "cursos/"], queryFn: () => pasGet<{ titulo: string; subtitulo: string }>("cursos/") });
  if (query.isPending) return <Cargando />;
  if (query.isError) return <ErrorPas error={query.error} />;
  return <Box component="section" aria-label={query.data.titulo} sx={{ minHeight: "60vh", bgcolor: "background.default" }}>
    <Oculto component="h1">{query.data.titulo}</Oculto>
  </Box>;
}
