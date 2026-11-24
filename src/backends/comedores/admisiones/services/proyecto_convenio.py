"""Generación del documento único para Legales."""

import shutil
import subprocess
import tempfile
from pathlib import Path


def contexto_proyecto_convenio(admision, informe, proyecto):
    campos_informe = (
        "nombre_organizacion",
        "provincia_organizacion",
        "cuit_organizacion",
        "domicilio_electronico_espacio",
        "nombre_espacio",
        "domicilio_espacio",
        "localidad_espacio",
        "partido_espacio",
        "provincia_espacio",
        "responsable_tarjeta_nombre",
        "responsable_tarjeta_dni",
        "responsable_tarjeta_mail",
        "expediente_nro",
    )
    comidas = ("desayuno", "almuerzo", "merienda", "cena")
    dias = ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo")
    datos = {campo: getattr(informe, campo) or "" for campo in campos_informe}
    for comida in comidas:
        for dia in dias:
            campo = f"aprobadas_{comida}_{dia}"
            datos[campo] = getattr(informe, campo) or 0

    organizacion = admision.comedor.organizacion
    return {
        **datos,
        "subtipo_entidad": getattr(
            getattr(organizacion, "subtipo_entidad", None), "nombre", ""
        ),
        "autoridad_nombre": proyecto.autoridad_nombre,
        "autoridad_cargo": proyecto.autoridad_cargo,
        "autoridad_dni": proyecto.autoridad_dni,
        "autoridad_domicilio": proyecto.autoridad_domicilio,
        "autoridad_localidad": proyecto.autoridad_localidad.nombre,
        "autoridad_provincia": proyecto.autoridad_provincia.nombre,
        "judicializado": proyecto.es_judicializado,
        "mas_de_cinco": proyecto.cantidad_espacios == "mas_de_5",
        "caratula_causa": proyecto.caratula_causa or "",
        "juzgado": proyecto.juzgado or "",
        "borrador": informe.estado != "Validado",
    }


def convertir_convenio_a_pdf(contenido_docx):
    ejecutable = shutil.which("libreoffice") or shutil.which("soffice")
    if not ejecutable:
        raise RuntimeError("LibreOffice no está disponible.")

    with tempfile.TemporaryDirectory(prefix="proyecto-convenio-") as carpeta:
        ruta = Path(carpeta)
        entrada = ruta / "convenio.docx"
        salida = ruta / "convenio.pdf"
        entrada.write_bytes(contenido_docx)
        perfil = (ruta / "libreoffice-profile").as_uri()
        subprocess.run(
            [
                ejecutable,
                f"-env:UserInstallation={perfil}",
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                carpeta,
                str(entrada),
            ],
            capture_output=True,
            check=True,
            timeout=120,
        )
        pdf = salida.read_bytes()
        if not pdf.startswith(b"%PDF-"):
            raise RuntimeError("LibreOffice no generó un PDF válido.")
        return pdf
