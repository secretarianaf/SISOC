/*
 * Tablero en vivo de Inspecciones escolares.
 *
 * Consulta periódica (cada 10 s) al endpoint JSON del tablero; sin WebSockets
 * ni SSE (gunicorn síncrono, sin Redis). Pausa con la pestaña oculta, avisa
 * la desconexión con la última hora buena y reintenta. Todo el texto que viene
 * del servidor se inserta con textContent (nunca innerHTML).
 */
(function () {
    "use strict";

    var raiz = document.getElementById("insp-tablero");
    if (!raiz) {
        return;
    }

    var URL_DATOS = raiz.dataset.urlDatos;
    var URL_EXPORTAR = raiz.dataset.urlExportar;
    var INTERVALO = parseInt(raiz.dataset.intervaloMs, 10) || 5000;
    var DURACION_NUEVA = 8000;
    var ARGENTINA = [[-55.1, -73.6], [-21.7, -53.6]];
    var COLORES = {
        teal: "#3b8681",
        tealClaro: "#8fd6d0",
        naranja: "#c26a00",
        marron: "#7a3a00",
        gris: "#9e9e9e",
        grisClaro: "#d6d6d6"
    };
    var COLOR_RESULTADO = {
        constatado: COLORES.teal,
        parcial: COLORES.tealClaro,
        cerrada: COLORES.naranja,
        no_ingreso: COLORES.marron,
        sin_dato: COLORES.grisClaro
    };
    var COLOR_PRESENCIA = {
        si: COLORES.teal,
        no: COLORES.naranja,
        no_constatado: COLORES.gris,
        sin_dato: COLORES.grisClaro
    };

    var formulario = raiz.querySelector("[data-tablero-filtros]");
    var selectProvincia = formulario.elements.provincia;
    var selectLocalidad = formulario.elements.localidad;
    var enlaceExportar = raiz.querySelector("[data-tablero-exportar]");
    var vivo = raiz.querySelector("[data-tablero-vivo]");
    var textoEstado = raiz.querySelector("[data-tablero-estado]");
    var textoHace = raiz.querySelector("[data-tablero-hace]");
    var aviso = raiz.querySelector("[data-tablero-desconexion]");
    var textoAviso = raiz.querySelector("[data-tablero-desconexion-texto]");

    var estado = {
        temporizador: null,
        controlador: null,
        ultimaOk: null,
        falloDesde: null,
        vistos: null,
        ajustarMapa: true,
        firmaPuntos: null,
        localidad: selectLocalidad.dataset.valorInicial || ""
    };

    // --- Utilidades ---------------------------------------------------------

    var formatoNumero = new Intl.NumberFormat("es-AR");
    var formatoPorcentaje = new Intl.NumberFormat("es-AR", {
        minimumFractionDigits: 1,
        maximumFractionDigits: 1
    });

    function numero(valor) {
        return valor === null || valor === undefined ? "–" : formatoNumero.format(valor);
    }

    function hora(fecha) {
        // Horario de Argentina, como la hora oficial de las actas.
        return fecha.toLocaleTimeString("es-AR", {
            timeZone: "America/Argentina/Buenos_Aires",
            hourCycle: "h23",
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit"
        });
    }

    function elemento(etiqueta, clase, texto) {
        var nodo = document.createElement(etiqueta);
        if (clase) {
            nodo.className = clase;
        }
        if (texto !== undefined && texto !== null) {
            nodo.textContent = texto;
        }
        return nodo;
    }

    function fijarTexto(selector, texto) {
        raiz.querySelectorAll(selector).forEach(function (nodo) {
            nodo.textContent = texto;
        });
    }

    function querystring() {
        var parametros = new URLSearchParams();
        new FormData(formulario).forEach(function (valor, clave) {
            if (valor) {
                parametros.set(clave, valor);
            }
        });
        if (!selectLocalidad.disabled && estado.localidad) {
            parametros.set("localidad", estado.localidad);
        }
        return parametros.toString();
    }

    // --- Estado de la conexión ----------------------------------------------

    function actualizarHace() {
        if (!estado.ultimaOk) {
            textoHace.textContent = "";
            return;
        }
        var segundos = Math.max(0, Math.round((Date.now() - estado.ultimaOk) / 1000));
        textoHace.textContent = "· actualizado hace " + segundos + " s";
    }

    function marcarEstado(clave, texto) {
        vivo.dataset.estado = clave;
        if (textoEstado.textContent !== texto) {
            textoEstado.textContent = texto;
        }
    }

    function marcarOk() {
        estado.ultimaOk = Date.now();
        estado.falloDesde = null;
        aviso.classList.add("d-none");
        marcarEstado("vivo", "En vivo");
        actualizarHace();
    }

    function marcarError(sesionVencida) {
        if (!estado.falloDesde) {
            estado.falloDesde = Date.now();
        }
        marcarEstado("desconectado", "Sin conexión");
        if (sesionVencida) {
            textoAviso.textContent =
                "La sesión venció o ya no tiene permiso. Recargá la página para volver a ingresar.";
        } else {
            var ultima = estado.ultimaOk
                ? "Los datos son de las " + hora(new Date(estado.ultimaOk)) + " (última consulta correcta). "
                : "Todavía no se pudo cargar el tablero. ";
            textoAviso.textContent =
                ultima + "Se reintenta cada " + Math.round(INTERVALO / 1000) + " s.";
        }
        aviso.classList.remove("d-none");
    }

    // --- Consulta periódica -------------------------------------------------

    function programar() {
        clearTimeout(estado.temporizador);
        if (document.hidden) {
            return;
        }
        estado.temporizador = setTimeout(consultar, INTERVALO);
    }

    function consultar() {
        clearTimeout(estado.temporizador);
        if (estado.controlador) {
            estado.controlador.abort();
        }
        var controlador = new AbortController();
        estado.controlador = controlador;
        var pedido = querystring();
        fetch(URL_DATOS + (pedido ? "?" + pedido : ""), {
            credentials: "same-origin",
            cache: "no-store",
            headers: { Accept: "application/json", "X-Requested-With": "XMLHttpRequest" },
            signal: controlador.signal
        })
            .then(function (respuesta) {
                if (respuesta.redirected || respuesta.status === 401 || respuesta.status === 403) {
                    var error = new Error("sesion");
                    error.sesion = true;
                    throw error;
                }
                if (!respuesta.ok) {
                    throw new Error("HTTP " + respuesta.status);
                }
                return respuesta.json();
            })
            .then(function (datos) {
                if (controlador.signal.aborted) {
                    return;
                }
                pintar(datos);
                marcarOk();
            })
            .catch(function (error) {
                if (controlador.signal.aborted || error.name === "AbortError") {
                    return;
                }
                marcarError(Boolean(error.sesion));
            })
            .finally(function () {
                if (estado.controlador === controlador) {
                    estado.controlador = null;
                    programar();
                }
            });
    }

    document.addEventListener("visibilitychange", function () {
        if (document.hidden) {
            clearTimeout(estado.temporizador);
            if (estado.controlador) {
                estado.controlador.abort();
                estado.controlador = null;
            }
            marcarEstado("pausado", "En pausa (pestaña oculta)");
        } else {
            marcarEstado("cargando", "Actualizando…");
            consultar();
        }
    });

    setInterval(actualizarHace, 1000);

    // --- Filtros ------------------------------------------------------------

    function alCambiarFiltros(evento) {
        if (evento && evento.target === selectProvincia) {
            estado.localidad = "";
            vaciarLocalidades();
            selectLocalidad.disabled = !selectProvincia.value;
        }
        if (evento && evento.target === selectLocalidad) {
            estado.localidad = selectLocalidad.value;
        }
        var pedido = querystring();
        history.replaceState(null, "", window.location.pathname + (pedido ? "?" + pedido : ""));
        enlaceExportar.href = URL_EXPORTAR + (pedido ? "?" + pedido : "");
        estado.vistos = null;
        estado.ajustarMapa = true;
        estado.firmaPuntos = null;
        marcarEstado("cargando", "Actualizando…");
        consultar();
    }

    function vaciarLocalidades() {
        while (selectLocalidad.options.length > 1) {
            selectLocalidad.remove(1);
        }
    }

    function pintarLocalidades(localidades) {
        if (!selectProvincia.value) {
            vaciarLocalidades();
            selectLocalidad.disabled = true;
            return;
        }
        selectLocalidad.disabled = false;
        var actual = estado.localidad;
        vaciarLocalidades();
        var presente = false;
        (localidades || []).forEach(function (localidad) {
            var opcion = new Option(localidad.nombre, String(localidad.id));
            if (String(localidad.id) === actual) {
                opcion.selected = true;
                presente = true;
            }
            selectLocalidad.add(opcion);
        });
        if (actual && !presente) {
            // La localidad elegida ya no tiene actas con los demás filtros.
            selectLocalidad.add(new Option("Localidad elegida (sin actas)", actual, true, true));
        }
    }

    formulario.addEventListener("change", alCambiarFiltros);
    formulario.addEventListener("submit", function (evento) {
        evento.preventDefault();
        alCambiarFiltros();
    });

    // --- Indicadores --------------------------------------------------------

    function pintarIndicadores(indicadores) {
        fijarTexto('[data-kpi="escuelas_unicas"]', numero(indicadores.escuelas_unicas));
        fijarTexto('[data-kpi="actas_validas"]', numero(indicadores.actas_validas));
        fijarTexto(
            '[data-kpi="escuelas_con_mas_de_una_visita"]',
            numero(indicadores.escuelas_con_mas_de_una_visita)
        );
        fijarTexto('[data-kpi="inspectores_con_actividad"]', numero(indicadores.inspectores.con_actividad));
        fijarTexto('[data-kpi="inspectores_habilitados"]', numero(indicadores.inspectores.habilitados));
        fijarTexto('[data-kpi="inspectores_sin_actividad"]', numero(indicadores.inspectores.sin_actividad));
        fijarTexto('[data-kpi="con_firma"]', numero(indicadores.con_firma));
        fijarTexto('[data-kpi="sin_firma"]', numero(indicadores.sin_firma));
        var motivos = indicadores.sin_firma_por_motivo
            .filter(function (m) {
                return m.cantidad > 0;
            })
            .map(function (m) {
                return numero(m.cantidad) + " " + m.etiqueta;
            });
        fijarTexto(
            '[data-kpi="sin_firma_por_motivo"]',
            motivos.length ? "sin firma: " + motivos.join(" · ") : "sin excepciones de firma"
        );
        fijarTexto('[data-kpi="borradores_en_curso"]', numero(indicadores.borradores_en_curso));
        fijarTexto('[data-kpi="notificacion_pendiente"]', numero(indicadores.notificacion_pendiente));
        fijarTexto('[data-kpi="notificacion_cargada"]', numero(indicadores.notificacion_cargada));
    }

    function pintarIndice(prefijo, indice) {
        fijarTexto(
            '[data-indice="' + prefijo + '-porcentaje"]',
            indice.porcentaje === null ? "Sin datos computables" : formatoPorcentaje.format(indice.porcentaje) + " %"
        );
        fijarTexto('[data-indice="' + prefijo + '-computables"]', numero(indice.computables));
        fijarTexto('[data-indice="' + prefijo + '-excluidas"]', numero(indice.excluidas));
    }

    // --- Barras en el DOM (sin librería; anchos por CSSOM, la CSP lo permite) -

    function fijarAncho(nodo, porcentaje) {
        nodo.style.width = Math.max(0, Math.min(100, porcentaje)) + "%";
    }

    function pintarTurnos(turnos) {
        var contenedor = raiz.querySelector("[data-tablero-turnos]");
        if (!contenedor) {
            return;
        }
        var maximo = turnos.reduce(function (m, t) {
            return Math.max(m, t.cantidad || 0);
        }, 0);
        var filas = document.createDocumentFragment();
        turnos.forEach(function (turno) {
            var fila = elemento("div", "insp-barra");
            fila.appendChild(elemento("span", "insp-barra-etiqueta", turno.etiqueta));
            var pista = elemento("div", "insp-barra-pista");
            var relleno = elemento("div", "insp-barra-relleno");
            fijarAncho(relleno, maximo ? (turno.cantidad / maximo) * 100 : 0);
            pista.appendChild(relleno);
            fila.appendChild(pista);
            fila.appendChild(elemento("span", "insp-barra-valor", numero(turno.cantidad)));
            filas.appendChild(fila);
        });
        contenedor.replaceChildren(filas);
    }

    function pintarSegmentos(contenedor, leyenda, categorias, colores) {
        if (!contenedor) {
            return;
        }
        var total = categorias.reduce(function (s, c) {
            return s + (c.cantidad || 0);
        }, 0);
        var barra = elemento("div", "insp-segmentos");
        barra.setAttribute("role", "img");
        barra.setAttribute(
            "aria-label",
            categorias.map(function (c) { return numero(c.cantidad) + " " + c.etiqueta; }).join(", ")
        );
        categorias.forEach(function (categoria) {
            var tramo = elemento("span", "insp-segmento");
            tramo.style.backgroundColor = colores[categoria.valor] || COLORES.gris;
            fijarAncho(tramo, total ? (categoria.cantidad / total) * 100 : 0);
            barra.appendChild(tramo);
        });
        contenedor.replaceChildren(barra);
        if (!leyenda) {
            return;
        }
        var items = document.createDocumentFragment();
        categorias.forEach(function (categoria) {
            var item = elemento("span", "insp-leyenda-item");
            var punto = elemento("i", "insp-leyenda-punto");
            punto.setAttribute("aria-hidden", "true");
            punto.style.backgroundColor = colores[categoria.valor] || COLORES.gris;
            item.appendChild(punto);
            item.appendChild(document.createTextNode(categoria.etiqueta + " · " + numero(categoria.cantidad)));
            items.appendChild(item);
        });
        leyenda.replaceChildren(items);
    }

    function pintarResultados(resultados) {
        pintarSegmentos(
            raiz.querySelector("[data-tablero-resultados]"),
            raiz.querySelector("[data-tablero-resultados-leyenda]"),
            resultados,
            COLOR_RESULTADO
        );
    }

    function pintarPresencia(presencia) {
        ["personal", "estudiantes"].forEach(function (clave) {
            var serie = presencia[clave];
            pintarSegmentos(
                raiz.querySelector('[data-tablero-presencia="' + clave + '"]'),
                raiz.querySelector('[data-tablero-presencia-leyenda="' + clave + '"]'),
                serie.categorias,
                COLOR_PRESENCIA
            );
            fijarTexto('[data-tablero-presencia-total="' + clave + '"]', "(" + numero(serie.denominador) + ")");
        });
        var personal = presencia.personal;
        var estudiantes = presencia.estudiantes;
        raiz.querySelector("[data-tablero-presencia-denominador]").textContent =
            "Base: " + numero(personal.denominador) + " actas con la pregunta respondida (personal) y " +
            numero(estudiantes.denominador) + " (estudiantes), de " + numero(personal.total) +
            ". «No constatado» y «Sin dato» se cuentan aparte: no son cero.";
    }

    // --- Mapa (Leaflet + markercluster) -------------------------------------

    var mapa = null;
    var capaPuntos = null;

    function iniciarMapa() {
        var contenedor = raiz.querySelector("[data-tablero-mapa]");
        if (typeof window.L === "undefined" || !window.L.markerClusterGroup) {
            contenedor.textContent = "No se pudo cargar el mapa.";
            return;
        }
        var L = window.L;
        mapa = L.map(contenedor, { scrollWheelZoom: false });
        mapa.fitBounds(ARGENTINA);
        L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        }).addTo(mapa);
        capaPuntos = L.markerClusterGroup({
            showCoverageOnHover: false,
            maxClusterRadius: 50,
            chunkedLoading: true,
            iconCreateFunction: iconoDeGrupo
        });
        mapa.addLayer(capaPuntos);
        // Habilitar la rueda sólo cuando el usuario interactúa con el mapa.
        mapa.on("focus click", function () {
            mapa.scrollWheelZoom.enable();
        });
        mapa.on("blur mouseout", function () {
            mapa.scrollWheelZoom.disable();
        });
    }

    function iconoDeGrupo(grupo) {
        var marcadores = grupo.getAllChildMarkers();
        var constatadas = marcadores.filter(function (m) {
            return m.options.constatada;
        }).length;
        var clase = "insp-tablero-grupo";
        if (constatadas === 0) {
            clase += " insp-tablero-grupo-sin-constatacion";
        } else if (constatadas < marcadores.length) {
            clase += " insp-tablero-grupo-mixto";
        }
        var total = marcadores.length;
        var lado = total < 10 ? 30 : total < 100 ? 38 : 48;
        var cuerpo = document.createElement("span");
        cuerpo.textContent = formatoNumero.format(total);
        return window.L.divIcon({
            html: cuerpo,
            className: clase,
            iconSize: window.L.point(lado, lado)
        });
    }

    function contenidoPopup(punto) {
        var caja = elemento("div", "insp-tablero-popup");
        caja.appendChild(elemento("strong", null, punto.escuela || "Escuela sin nombre"));
        var lista = elemento("dl");
        function fila(titulo, valor) {
            lista.appendChild(elemento("dt", null, titulo));
            var dato = elemento("dd");
            if (valor instanceof Node) {
                dato.appendChild(valor);
            } else {
                dato.textContent = valor || "–";
            }
            lista.appendChild(dato);
        }
        fila("Cueanexo", punto.cueanexo);
        fila("Turno", punto.turno);
        fila("Inspector", punto.inspector);
        fila("Acta", enlaceActa(punto));
        fila("Resultado", punto.resultado);
        caja.appendChild(lista);
        return caja;
    }

    function enlaceActa(item) {
        if (!item.url) {
            return elemento("span", "insp-tablero-numero", item.numero);
        }
        var enlace = elemento("a", "insp-tablero-numero", item.numero);
        enlace.href = item.url;
        return enlace;
    }

    function pintarMapa(datosMapa) {
        var sinGps = datosMapa.sin_coordenadas;
        raiz.querySelector("[data-tablero-sin-gps]").textContent = sinGps
            ? numero(sinGps) + " actas sin ubicación GPS, fuera del mapa (" + numero(datosMapa.manual) +
              " con ubicación manual · " + numero(datosMapa.sin_ubicacion) + " sin ubicación)"
            : "Todas las actas tienen ubicación GPS";
        if (!mapa) {
            return;
        }
        var L = window.L;
        var firma = datosMapa.puntos
            .map(function (p) {
                return p.numero + (p.constatada ? "+" : "-");
            })
            .join(",");
        if (firma !== estado.firmaPuntos) {
            estado.firmaPuntos = firma;
            capaPuntos.clearLayers();
            capaPuntos.addLayers(
                datosMapa.puntos.map(function (punto) {
                    var color = punto.constatada ? COLORES.teal : COLORES.naranja;
                    var marcador = L.circleMarker([punto.lat, punto.lng], {
                        radius: 7,
                        color: "#ffffff",
                        weight: 2,
                        fillColor: color,
                        fillOpacity: 0.95,
                        constatada: punto.constatada
                    });
                    marcador.bindPopup(function () {
                        return contenidoPopup(punto);
                    });
                    return marcador;
                })
            );
        }
        if (estado.ajustarMapa) {
            estado.ajustarMapa = false;
            var filtraTerritorio = selectProvincia.value || estado.localidad;
            if (filtraTerritorio && datosMapa.puntos.length) {
                mapa.fitBounds(capaPuntos.getBounds(), { padding: [30, 30], maxZoom: 13 });
            } else {
                mapa.fitBounds(ARGENTINA);
            }
        }
    }

    // --- Últimas actas ------------------------------------------------------

    function insignia(texto, clase) {
        return elemento("span", "insp-tablero-badge " + clase, texto);
    }

    function pintarUltimas(ultimas) {
        var cuerpo = raiz.querySelector("[data-tablero-ultimas]");
        var ahora = Date.now();
        var primeraVez = estado.vistos === null;
        if (primeraVez) {
            estado.vistos = new Map();
        }
        var filas = document.createDocumentFragment();
        if (!ultimas.length) {
            var vacia = elemento("tr");
            var celda = elemento("td", "text-center text-body-secondary py-3", "Sin actas con estos filtros.");
            celda.colSpan = 8;
            vacia.appendChild(celda);
            filas.appendChild(vacia);
        }
        var hayNuevas = false;
        ultimas.forEach(function (acta) {
            if (!estado.vistos.has(acta.numero)) {
                estado.vistos.set(acta.numero, primeraVez ? 0 : ahora);
            }
            var nueva = ahora - estado.vistos.get(acta.numero) < DURACION_NUEVA;
            var tr = elemento("tr", nueva ? "insp-tablero-nueva" : "");
            var celdaHora = elemento("td", null, acta.hora);
            if (nueva) {
                hayNuevas = true;
                celdaHora.appendChild(insignia("nueva", "insp-tablero-badge-nueva"));
            }
            tr.appendChild(celdaHora);
            var celdaActa = elemento("td");
            celdaActa.appendChild(enlaceActa(acta));
            tr.appendChild(celdaActa);
            tr.appendChild(elemento("td", "insp-tablero-escuela", acta.escuela));
            tr.appendChild(elemento("td", null, acta.provincia || "–"));
            tr.appendChild(elemento("td", null, acta.turno));
            tr.appendChild(elemento("td", null, acta.inspector));
            var celdaFirma = elemento("td");
            celdaFirma.appendChild(
                insignia(acta.firma.etiqueta, acta.firma.tipo === "firma" ? "insp-tablero-badge-ok" : "insp-tablero-badge-alerta")
            );
            tr.appendChild(celdaFirma);
            var celdaNotificacion = elemento("td");
            celdaNotificacion.appendChild(
                insignia(
                    acta.notificacion.etiqueta,
                    acta.notificacion.estado === "cargada" ? "insp-tablero-badge-ok" : "insp-tablero-badge-alerta"
                )
            );
            tr.appendChild(celdaNotificacion);
            filas.appendChild(tr);
        });
        cuerpo.replaceChildren(filas);
        if (hayNuevas) {
            setTimeout(function () {
                cuerpo.querySelectorAll("tr.insp-tablero-nueva").forEach(function (tr) {
                    tr.classList.remove("insp-tablero-nueva");
                    var marca = tr.querySelector(".insp-tablero-badge-nueva");
                    if (marca) {
                        marca.remove();
                    }
                });
            }, DURACION_NUEVA);
        }
    }

    // --- Pintado completo ---------------------------------------------------

    function pintar(datos) {
        pintarIndicadores(datos.indicadores);
        pintarIndice("ausentismo", datos.ausentismo);
        pintarIndice("aulas", datos.aulas);
        pintarTurnos(datos.turnos);
        pintarResultados(datos.resultados);
        pintarPresencia(datos.presencia);
        pintarMapa(datos.mapa);
        pintarUltimas(datos.ultimas);
        pintarLocalidades(datos.opciones.localidades);
    }

    enlaceExportar.href = URL_EXPORTAR + (querystring() ? "?" + querystring() : "");
    iniciarMapa();
    consultar();
})();
