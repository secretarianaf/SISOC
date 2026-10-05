import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CardHeader from "@mui/material/CardHeader";
import Divider from "@mui/material/Divider";

/**
 * Panel con encabezado. `Card` y no `Paper outlined` porque tiene header,
 * contenido y a veces acciones. `CardContent` trae padding propio: se
 * sobreescribe acá y con `disableGutters` se apaga del todo (tablas).
 */
export default function SectionCard({
  title,
  subheader,
  action,
  children,
  disableGutters = false,
}: {
  title: React.ReactNode;
  subheader?: React.ReactNode;
  action?: React.ReactNode;
  children: React.ReactNode;
  disableGutters?: boolean;
}) {
  return (
    <Card>
      <CardHeader
        title={title}
        subheader={subheader}
        action={action}
        slotProps={{
          title: { variant: "subtitle1Medium" },
          subheader: { variant: "caption" },
        }}
        sx={{ py: 1.5, px: 2, "& .MuiCardHeader-action": { m: 0 } }}
      />
      <Divider />
      <CardContent
        sx={
          disableGutters
            ? { p: 0, "&:last-child": { pb: 0 } }
            : { p: 2, "&:last-child": { pb: 2 } }
        }
      >
        {children}
      </CardContent>
    </Card>
  );
}
