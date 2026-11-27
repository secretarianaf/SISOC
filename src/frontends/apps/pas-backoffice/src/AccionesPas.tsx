import { IconButton, Menu, MenuItem, Tooltip } from "@mui/material";
import MoreVert from "@mui/icons-material/MoreVert";
import { useId, useState } from "react";
import { Link } from "react-router-dom";

type Accion = { label: string; to?: string; href?: string; run?: () => void; disabled?: boolean };

export function AccionesPas({ label, items }: { label: string; items: Accion[] }) {
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  const id = useId();
  if (!items.length) return null;
  return <>
    <Tooltip title={label}><IconButton size="small" id={id} aria-label={label} aria-haspopup="menu" aria-expanded={Boolean(anchor)}
      onClick={(event) => setAnchor(event.currentTarget)}><MoreVert /></IconButton></Tooltip>
    <Menu anchorEl={anchor} open={Boolean(anchor)} onClose={() => setAnchor(null)} slotProps={{ list: { "aria-labelledby": id } }}>
      {items.map((item) => {
        const onClick = () => { setAnchor(null); item.run?.(); };
        if (item.to) return <MenuItem key={item.label} component={Link} to={item.to} onClick={onClick}>{item.label}</MenuItem>;
        if (item.href) return <MenuItem key={item.label} component="a" href={item.href} onClick={onClick}>{item.label}</MenuItem>;
        return <MenuItem key={item.label} disabled={item.disabled} onClick={onClick}>{item.label}</MenuItem>;
      })}
    </Menu>
  </>;
}
