import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

/** MUI no tiene componente Footer: es un Box con los tokens de `palette.nav`. */
export function Footer() {
  return (
    <Box
      component="footer"
      sx={{
        bgcolor: "nav.surface",
        color: "nav.textMuted",
        borderTop: (t) => `${t.border.accent}px solid ${t.palette.nav.accent}`,
        px: 3,
        py: 2,
        mt: "auto",
      }}
    >
      <Typography variant="caption">
        SISOC · Secretaría Nacional de Niñez, Adolescencia y Familia
      </Typography>
    </Box>
  );
}
