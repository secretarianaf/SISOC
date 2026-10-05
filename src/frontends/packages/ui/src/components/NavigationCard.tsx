import ButtonBase from "@mui/material/ButtonBase";
import Stack from "./Stack";
import Typography from "@mui/material/Typography";
import { Link as RouterLink } from "react-router-dom";

/**
 * Navigation card — `ButtonBase` sobre `nav.surface`, no sobre `primary`.
 * Es un `button`, así que todo lo que tenga adentro es display.
 */
export default function NavigationCard({
  title,
  description,
  href,
  icon,
  selected = false,
}: {
  title: string;
  description: string;
  href: string;
  icon?: React.ReactNode;
  selected?: boolean;
}) {
  return (
    <ButtonBase
      component={RouterLink}
      to={href}
      sx={{
        width: "100%",
        height: "100%",
        p: 2.5,
        borderRadius: (t) => `${t.radius.medium}px`,
        bgcolor: selected ? "nav.surfaceSelected" : "nav.surface",
        color: "nav.text",
        textAlign: "left",
        alignItems: "flex-start",
        justifyContent: "flex-start",
        transition: "background-color 120ms ease",
        "&:hover": { bgcolor: "nav.surfaceSelected" },
      }}
    >
      <Stack spacing={1}>
        {icon}
        <Typography variant="subtitle1Medium">{title}</Typography>
        <Typography variant="body2" sx={{ color: "nav.textMuted" }}>
          {description}
        </Typography>
      </Stack>
    </ButtonBase>
  );
}
