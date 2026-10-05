import Stack from "./Stack";
import Typography from "@mui/material/Typography";
import Breadcrumbs from "@mui/material/Breadcrumbs";
import Link from "@mui/material/Link";
import { Link as RouterLink } from "react-router-dom";

export type Crumb = { label: string; href?: string };

export default function PageHeader({
  title,
  crumbs = [],
  actions,
}: {
  title: React.ReactNode;
  crumbs?: Crumb[];
  actions?: React.ReactNode;
}) {
  return (
    <Stack spacing={1.5} sx={{ mb: 3 }}>
      {crumbs.length > 0 ? (
        <Breadcrumbs sx={{ typography: "caption" }}>
          {crumbs.map((c) =>
            c.href ? (
              <Link
                key={c.label}
                component={RouterLink}
                to={c.href}
                underline="hover"
                color="inherit"
              >
                {c.label}
              </Link>
            ) : (
              <Typography key={c.label} variant="caption" color="text.primary">
                {c.label}
              </Typography>
            ),
          )}
        </Breadcrumbs>
      ) : null}
      <Stack
        direction={{ xs: "column", md: "row" }}
        spacing={2}
        justifyContent="space-between"
        alignItems={{ xs: "stretch", md: "center" }}
      >
        <Typography variant="h5" component="h1">
          {title}
        </Typography>
        {actions ? (
          <Stack
            direction="row"
            spacing={1}
            flexWrap="wrap"
            useFlexGap
            justifyContent={{ xs: "flex-start", md: "flex-end" }}
          >
            {actions}
          </Stack>
        ) : null}
      </Stack>
    </Stack>
  );
}
