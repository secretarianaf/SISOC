import { Alert, Button, Card, Checkbox, Dialog, DialogActions, DialogContent, DialogTitle, FormControlLabel, MenuItem, Stack, TextField, Typography } from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { pasGet, pasPost, type Ficha } from "./api";
import { Cargando, ErrorPas } from "./Estado";

type Opcion = { value: string; label: string };
type Avisos = Record<string, { id: number; text: string }[]>;
type Opciones = {
  initial?: Record<string, string>;
  provincias: Opcion[];
  municipios: Opcion[];
  estados: Opcion[];
  generos: Opcion[];
  avisos_por_estado: Avisos;
};

function AvisosEstado({ options, estado }: { options: Avisos; estado: string }) {
  return <Stack component="fieldset" key={estado} sx={{ border: 0, m: 0, p: 0 }}>
    <legend>Avisos</legend>
    {(options[estado] ?? []).map(({ id, text }) => <FormControlLabel key={id} label={text}
      control={<Checkbox name="avisos" value={String(id)} />} />)}
  </Stack>;
}

/**
 * Alta y edición de un titular. Con `volver` (alta desde el Buscador) el
 * formulario queda en ese módulo: Cancelar vuelve ahí y, al guardar, el
 * Buscador abre filtrado por el DNI del titular creado.
 */
function FormularioTitular({ id, opciones, volver }: { id?: string; opciones: Opciones; volver?: string }) {
  const initial = opciones.initial ?? {};
  const [provincia, setProvincia] = useState(initial.provincia ?? "");
  const [municipio, setMunicipio] = useState(initial.municipio ?? "");
  const [estado, setEstado] = useState("");
  const navigate = useNavigate();
  const cache = useQueryClient();
  const municipios = useQuery({
    queryKey: ["pas", "municipios", provincia],
    queryFn: () => pasGet<Opciones>(`personas/opciones/?${new URLSearchParams({ provincia })}`),
    enabled: Boolean(provincia) && provincia !== initial.provincia,
  });
  const [dniGuardado, setDniGuardado] = useState("");
  const guardar = useMutation({
    mutationFn: (body: FormData) => pasPost<{ id: number; message: string }>(
      id ? `personas/${id}/editar/` : "personas/crear/", body),
    onSuccess: async (data) => {
      await cache.invalidateQueries({ queryKey: ["pas"] });
      navigate(volver && !id ? `${volver}?${new URLSearchParams({ q: dniGuardado })}` : `/titulares/${data.id}`);
    },
  });
  const campos = [
    ["id_persona", "IdPersona", "text"], ["apellidos", "Apellidos", "text"], ["nombres", "Nombres", "text"],
    ["dni", "DNI", "text"], ["cuit", "CUIT", "text"], ["domicilio", "Domicilio", "text"],
    ["correo_electronico", "Correo electrónico", "email"], ["telefono_celular", "Teléfono celular", "tel"],
  ];
  return <Card variant="outlined" sx={{ p: 3 }}>
    <Stack spacing={2} component="form" onSubmit={(event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (guardar.isPending) return;
      const datos = new FormData(event.currentTarget);
      setDniGuardado(String(datos.get("dni") ?? "").trim());
      guardar.mutate(datos);
    }}>
      <Typography component="h1" variant="h5">{id ? "Editar titular PAS" : "Nuevo titular PAS"}</Typography>
      {guardar.isError && <ErrorOperacion error={guardar.error} />}
      {campos.map(([name, label, type]) => <TextField key={name} name={name} label={label} type={type} defaultValue={initial[name] ?? ""} />)}
      <TextField select name="genero" label="Género" defaultValue={initial.genero ?? ""}>
        <MenuItem value="">Sin informar</MenuItem>
        {opciones.generos.map(({ value, label }) => <MenuItem key={value} value={value}>{label}</MenuItem>)}
      </TextField>
      <TextField select name="provincia" label="Provincia" value={provincia} onChange={(event) => {
        setProvincia(event.target.value);
        setMunicipio("");
      }}>
        <MenuItem value="">Seleccionar provincia</MenuItem>
        {opciones.provincias.map(({ value, label }) => <MenuItem key={value} value={value}>{label}</MenuItem>)}
      </TextField>
      {municipios.isError && <ErrorPas error={municipios.error} />}
      <TextField select name="municipio" label="Municipio" value={municipio} disabled={!provincia || municipios.isFetching}
        onChange={(event) => setMunicipio(event.target.value)}>
        <MenuItem value="">Seleccionar municipio</MenuItem>
        {(provincia === initial.provincia ? opciones.municipios : municipios.data?.municipios ?? []).map(({ value, label }) =>
          <MenuItem key={value} value={value}>{label}</MenuItem>)}
      </TextField>
      {!id && <>
        <TextField select name="estado" label="Estado" value={estado} onChange={(event) => setEstado(event.target.value)}>
          <MenuItem value="">Seleccionar estado</MenuItem>
          {opciones.estados.map(({ value, label }) => <MenuItem key={value} value={value}>{label}</MenuItem>)}
        </TextField>
        <AvisosEstado options={opciones.avisos_por_estado} estado={estado} />
      </>}
      <Stack direction="row" spacing={1}>
        <Button type="submit" variant="contained" disabled={guardar.isPending}>Guardar</Button>
        <Button component={Link} to={id ? `/titulares/${id}` : volver ?? "/"}>Cancelar</Button>
      </Stack>
    </Stack>
  </Card>;
}

export function TitularFormPage({ volver }: { volver?: string }) {
  const { id } = useParams();
  const path = id ? `personas/${id}/` : "personas/opciones/";
  const query = useQuery({ queryKey: ["pas", path], queryFn: () => pasGet<Opciones>(path) });
  if (query.isPending) return <Cargando />;
  if (query.isError) return <ErrorPas error={query.error} />;
  return <FormularioTitular key={id ?? "nuevo"} id={id} opciones={query.data} volver={volver} />;
}

export function ErrorOperacion({ error }: { error: unknown }) {
  const payload = (error as { response?: { data?: { message?: string; errors?: Record<string, (string | { message: string })[]> } } }).response?.data;
  const errores = Object.entries(payload?.errors ?? {}).flatMap(([campo, valores]) =>
    valores.map((valor) => `${campo}: ${typeof valor === "string" ? valor : valor.message}`));
  return errores.length || payload?.message ? <Alert severity="error">
    {payload?.message}{errores.length > 0 && <ul>{errores.map((texto, index) => <li key={index}>{texto}</li>)}</ul>}
  </Alert> : <ErrorPas error={error} />;
}

/**
 * Diálogo de cambio de estado. Desde la bandeja de Cruces se usa con el
 * `endpoint` de la alerta y un texto de `confirmacion`: al guardar pide
 * confirmar y la alerta queda confirmada.
 */
export function CambiarEstado({ id, opciones, open, onClose, endpoint, confirmacion, titulo = "Cambiar estado" }: {
  id: string; opciones: NonNullable<Ficha["cambio_estado"]>; open: boolean; onClose: () => void;
  endpoint?: string; confirmacion?: string; titulo?: string;
}) {
  const [estado, setEstado] = useState("");
  const cache = useQueryClient();
  const cambio = useMutation({
    mutationFn: (body: FormData) => pasPost<{ message: string }>(endpoint ?? `personas/${id}/cambiar-estado/`, body),
    onSuccess: async () => {
      await cache.invalidateQueries({ queryKey: ["pas"] });
      setEstado("");
      onClose();
    },
  });
  const cerrar = () => { setEstado(""); cambio.reset(); onClose(); };
  return <>
    {cambio.isSuccess && <Alert severity="success">{cambio.data.message}</Alert>}
    <Dialog open={open} onClose={() => { if (!cambio.isPending) cerrar(); }} aria-labelledby="cambiar-estado-titulo">
      <Stack component="form" onSubmit={(event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (!estado || cambio.isPending) return;
        if (confirmacion && !window.confirm(confirmacion)) return;
        cambio.mutate(new FormData(event.currentTarget));
      }}>
        <DialogTitle id="cambiar-estado-titulo">{titulo}</DialogTitle>
        <DialogContent><Stack spacing={2} sx={{ pt: 1 }}>
          {cambio.isError && <ErrorOperacion error={cambio.error} />}
          <TextField select name="estado" label="Estado" value={estado} onChange={(event) => setEstado(event.target.value)}>
            <MenuItem value="">Seleccionar estado</MenuItem>
            {opciones.estados.map((item) => <MenuItem key={item.id} value={String(item.id)}>{item.nombre}</MenuItem>)}
          </TextField>
          <AvisosEstado options={opciones.avisos_por_estado} estado={estado} />
        </Stack></DialogContent>
        <DialogActions>
          <Button disabled={cambio.isPending} onClick={cerrar}>Cancelar</Button>
          <Button type="submit" variant="contained" disabled={!estado || cambio.isPending}>Guardar cambio</Button>
        </DialogActions>
      </Stack>
    </Dialog>
  </>;
}
