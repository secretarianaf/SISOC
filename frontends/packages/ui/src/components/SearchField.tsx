import TextField from "@mui/material/TextField";
import type { TextFieldProps } from "@mui/material/TextField";
import InputAdornment from "@mui/material/InputAdornment";
import SearchIcon from "@mui/icons-material/Search";

/** En MUI hay un solo TextField: el buscador es el mismo con el ícono de Search. */
export default function SearchField({
  placeholder = "Buscar...",
  sx,
  ...rest
}: TextFieldProps) {
  return (
    <TextField
      size="small"
      placeholder={placeholder}
      sx={{ minWidth: { xs: "100%", sm: 280 }, ...sx }}
      slotProps={{
        input: {
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon fontSize="small" />
            </InputAdornment>
          ),
        },
      }}
      {...rest}
    />
  );
}
