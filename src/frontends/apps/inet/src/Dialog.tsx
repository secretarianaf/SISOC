import { Dialog, type DialogProps } from "@mui/material";

/** Modal INET: mismo ancho y posición que los estados exportados de Figma. */
export function InetDialog(props: DialogProps) {
  return <Dialog {...props} sx={{ "& .MuiDialog-container": { alignItems: "flex-start" }, "& .MuiDialogTitle-root .MuiIconButton-root": { color: "text.primary" }, "& .MuiDialog-paper": { borderRadius: (theme) => `${theme.radius.large}px`, mt: { xs: 2, md: 12 }, maxHeight: { xs: "calc(100% - 32px)", md: "calc(100% - 128px)" } } }} />;
}
