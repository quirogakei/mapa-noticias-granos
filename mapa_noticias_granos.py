# -*- coding: utf-8 -*-
"""
🌾 Mapa de noticias del mercado de granos

- Busca noticias en Google News (RSS) y detecta los países mencionados.
- Muestra MÁXIMO 20 noticias por país (las más recientes).
- Al pasar el mouse sobre un círculo, se muestran las noticias en un panel lateral
  con links clickeables. Al hacer clic en el círculo, el panel queda "fijado".
- 🆕 Traduce los títulos al español automáticamente.
- 🆕 Genera ALERTAS (suba/baja de granos, petróleo, gas natural y ataques bélicos).
- 🆕 Paleta de colores, logo e imagen de fondo configurables.
- Genera un archivo index.html listo para publicar en GitHub Pages.

En Colab: pegá cada bloque "# %%" en una celda. En la primera celda agregá:
    !pip install -q feedparser plotly deep-translator
"""

# %% 1. Configuración
QUERIES = [
    "mercado de granos", "precio soja", "precio trigo", "precio maíz",
    "grain market", "soybean prices", "wheat prices", "corn prices", "barley prices",
    "malting", "grain taxes", "exportaciones soja", "cosecha gruesa", "aranceles granos",
    "cebada", "barley", "beer market", "biocombustibles", "grain prices", "grain",
    "harvest", "cosecha", "siembra", "Agriculture", "Breweries", "Beer Industry",
    "Agriculture sector", "crop", "war", "guerra", "conflicto armado", "Sunflower seed", "Sunflower oil", "Sunflower pellets", "Sunflower prices", "milling", "soybean meal", "aceite de palma", "palma", "palm oil", "tariffs",
    # 🆕 para que las alertas de energía tengan material
    "precio petróleo", "oil prices", "gas natural", "natural gas prices",
]
DIAS = 7                 # noticias de los últimos N días
MAX_POR_PAIS = 20        # máximo de noticias que se guardan/muestran por país
MAX_ALERTAS = 12         # 🆕 máximo de alertas en el panel superior
ARCHIVO_SALIDA = "index.html"
IDIOMAS = [("es-419", "AR", "AR:es-419"), ("en-US", "US", "US:en")]  # (hl, gl, ceid)

# 🆕 Identidad visual. Reemplazá los hex por los colores reales del logo de la Bolsa
# (con un cuentagotas sobre el logo). Estos son valores de ejemplo.
COL = dict(
    fondo="#0a2540",      # fondo general / mar
    panel="#0f355c",      # panel lateral
    borde="#1d4d7e",      # bordes y divisores
    tierra="rgba(26,74,122,0.85)",   # continentes (semitransparente para que se vea la imagen de fondo)
    paises="#3b6ea5",     # límites entre países
    costa="#5a8fc4",      # costas
    marcador="#d4a017",   # círculos (dorado trigo)
    alerta="#e63946",     # círculos y avisos con alerta
    texto="#f1f5f9",
    suave="#a9bdd3",      # textos secundarios
    link="#f2c94c",       # links de noticias
)
LOGO = "logo.png"        # 🆕 archivo local (junto al script) o URL. "" = sin logo
FONDO_IMAGEN = ""        # 🆕 archivo local o URL de la imagen de fondo. "" = sin imagen
VELO_FONDO = "rgba(10,37,64,0.78)"   # 🆕 capa translúcida sobre la imagen para que se lea el mapa

# %% 2. Búsqueda de noticias (Google News RSS)
import re, json, urllib.parse, os, base64, mimetypes
import feedparser
import pandas as pd
from datetime import datetime, timedelta, timezone
from time import mktime
from concurrent.futures import ThreadPoolExecutor
from deep_translator import GoogleTranslator   # 🆕


def buscar_noticias(queries, dias, idiomas):
    desde = datetime.now(timezone.utc) - timedelta(days=dias)
    filas = []
    for q in queries:
        for hl, gl, ceid in idiomas:
            url = (f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}+when:{dias}d"
                   f"&hl={hl}&gl={gl}&ceid={ceid}")
            for e in feedparser.parse(url).entries:
                if not getattr(e, "published_parsed", None):
                    continue
                fecha = datetime.fromtimestamp(mktime(e.published_parsed), tz=timezone.utc)
                if fecha >= desde:
                    filas.append({"titulo": e.title, "link": e.link, "fecha": fecha,
                                  "fuente": getattr(e, "source", {}).get("title", "")})
    if not filas:
        return pd.DataFrame(columns=["titulo", "link", "fecha", "fuente"])
    df = pd.DataFrame(filas).drop_duplicates("titulo").sort_values("fecha", ascending=False)
    return df.reset_index(drop=True)


noticias = buscar_noticias(QUERIES, DIAS, IDIOMAS)
print(f"{len(noticias)} noticias encontradas")

# %% 3. Detección de países
PAISES = {  # nombre: (lat, lon, [alias])
    "Argentina": (-34.6, -64.0, ["argentina", "argentino", "argentinos", "rosario", "bolsa de cereales", "buenos aires"]),
    "Brasil": (-14.2, -51.9, ["brasil", "brazil", "brasileño", "brasileña", "mato grosso", "paranaguá"]),
    "Estados Unidos": (39.8, -98.6, ["estados unidos", "ee.uu", "eeuu", "usa", "u.s.", "united states", "usda", "chicago", "cbot", "iowa", "illinois", "midwest"]),
    "China": (35.9, 104.2, ["china", "chino", "china's", "chinese", "beijing", "pekín", "dalian"]),
    "India": (20.6, 79.0, ["india", "indian"]),
    "Rusia": (61.5, 105.3, ["rusia", "russia", "russian", "ruso", "rusa"]),
    "Ucrania": (48.4, 31.2, ["ucrania", "ukraine", "ukrainian", "ucraniano", "odesa", "odessa"]),
    "Canadá": (56.1, -106.3, ["canadá", "canada", "canadian", "canadiense"]),
    "Australia": (-25.3, 133.8, ["australia", "australian", "australiano"]),
    "Francia": (46.2, 2.2, ["francia", "france", "french", "francés"]),
    "Alemania": (51.2, 10.5, ["alemania", "germany", "german"]),
    "Unión Europea": (50.0, 10.0, ["unión europea", "european union", "eu ", "europa", "europe", "euronext"]),
    "Paraguay": (-23.4, -58.4, ["paraguay", "paraguayo"]),
    "Uruguay": (-32.5, -55.8, ["uruguay", "uruguayo"]),
    "Bolivia": (-16.3, -63.6, ["bolivia", "boliviano"]),
    "Chile": (-35.7, -71.5, ["chile", "chileno"]),
    "Colombia": (4.6, -74.1, ["colombia", "colombiano"]),
    "Perú": (-9.2, -75.0, ["perú", "peru", "peruano"]),
    "México": (23.6, -102.5, ["méxico", "mexico", "mexicano", "mexican"]),
    "Egipto": (26.8, 30.8, ["egipto", "egypt", "egyptian"]),
    "Turquía": (38.9, 35.2, ["turquía", "turkey", "turkish", "türkiye"]),
    "Irán": (32.4, 53.7, ["irán", "iran", "iranian"]),
    "Arabia Saudita": (23.9, 45.1, ["arabia saudita", "saudi"]),
    "Argelia": (28.0, 1.7, ["argelia", "algeria", "algerian"]),
    "Marruecos": (31.8, -7.1, ["marruecos", "morocco", "moroccan"]),
    "Nigeria": (9.1, 8.7, ["nigeria", "nigerian"]),
    "Sudáfrica": (-30.6, 22.9, ["sudáfrica", "south africa"]),
    "Kazajistán": (48.0, 66.9, ["kazajistán", "kazakhstan", "kazakh"]),
    "Rumania": (45.9, 25.0, ["rumania", "romania", "romanian"]),
    "Polonia": (51.9, 19.1, ["polonia", "poland", "polish"]),
    "Pakistán": (30.4, 69.3, ["pakistán", "pakistan"]),
    "Bangladesh": (23.7, 90.4, ["bangladesh", "bangladés"]),
    "Indonesia": (-0.8, 113.9, ["indonesia", "indonesian"]),
    "Vietnam": (14.1, 108.3, ["vietnam", "vietnamese"]),
    "Tailandia": (15.9, 100.99, ["tailandia", "thailand", "thai"]),
    "Filipinas": (12.9, 121.8, ["filipinas", "philippines", "philippine"]),
    "Japón": (36.2, 138.3, ["japón", "japan", "japanese"]),
    "Corea del Sur": (35.9, 127.8, ["corea del sur", "south korea", "korean"]),
}

patrones = {p: re.compile(r"(?<!\w)(" + "|".join(re.escape(a) for a in al) + r")(?!\w)", re.I)
            for p, (_, _, al) in PAISES.items()}


def detectar_paises(texto):
    return [p for p, rx in patrones.items() if rx.search(texto + " ")]


if len(noticias):
    noticias["paises"] = noticias["titulo"].apply(detectar_paises)
    con_pais = noticias[noticias["paises"].str.len() > 0]
else:
    con_pais = noticias.assign(paises=[])
print(f"{len(con_pais)} de {len(noticias)} noticias mencionan algún país")

# %% 3b. 🆕 Detección de alertas (se evalúa sobre el título ORIGINAL, en español o inglés)
_rx = lambda p: re.compile(p, re.I)
_ini, _fin = r"(?<!\w)(?:", r")(?!\w)"

RX_ACTIVOS = {
    "🌾 Granos": _rx(_ini + r"soja|soya|trigo|ma[ií]z|cebada|girasol|palma|granos?|soybeans?|wheat|corn|barley|grains?|sunflower|palm oil|oilseeds?" + _fin),
    "🛢️ Petróleo": _rx(_ini + r"petr[oó]leo|crudo|brent|wti|crude|barril(?:es)?|barrels?" + _fin
                       + r"|(?<!sunflower )(?<!palm )(?<!soybean )(?<!vegetable )(?<!olive )(?<!\w)oil prices?(?!\w)"),
    "🔥 Gas natural": _rx(_ini + r"gas natural|natural gas|gnl|lng" + _fin),
}
RX_SUBA = _rx(r"(?<!\w)(?:alz\w*|aument\w*|repunt\w*|sub[eií]\w*|suba|subas|rall?y|surge|surges|surging|soar\w*|jump\w*|rise|rises|rising|rose|climb\w*|gain\w*|higher|hike\w*)(?!\w)")
RX_BAJA = _rx(r"(?<!\w)(?:baj[aóe]\w*|cae|caen|caer|ca[ií]d\w*|cay[oó]\w*|desplom\w*|retroced\w*|derrump\w*|falls?|fell|falling|drop\w*|plung\w*|slump\w*|declin\w*|lower|tumbl\w*|slid\w*|sink\w*|sank)(?!\w)")
RX_BELICO = _rx(_ini + r"ataque\w*|atac[oó]\w*|atacan|bombarde\w*|misil\w*|dron(?:es)?|ofensiva|invasi[oó]n|attacks?|attacked|airstrikes?|air strikes?|missiles?|drones?|bombing|bombed|shelling|invasion|offensive" + _fin)


def clasificar(titulo):
    """Devuelve la lista de alertas que dispara un título (vacía si ninguna)."""
    out = []
    sube, baja = bool(RX_SUBA.search(titulo)), bool(RX_BAJA.search(titulo))
    if sube or baja:
        flecha = "▲" if (sube and not baja) else "▼" if (baja and not sube) else "▲▼"
        for nombre, rx in RX_ACTIVOS.items():
            if rx.search(titulo):
                out.append(f"{nombre} {flecha}")
    if RX_BELICO.search(titulo):
        out.append("⚔️ Ataque bélico")
    return out

# %% 4. Agrupar por país (máx. MAX_POR_PAIS, las más recientes)
conteo = {}   # país -> lista de noticias (ya vienen ordenadas de más nueva a más vieja)
for _, r in con_pais.iterrows():
    for p in r["paises"]:
        lista = conteo.setdefault(p, [])
        if len(lista) < MAX_POR_PAIS:
            lista.append({
                "t": r["titulo"],            # se reemplaza por la traducción en el paso 4b
                "o": r["titulo"],            # 🆕 título original
                "l": r["link"],
                "f": r["fuente"],
                "d": r["fecha"].strftime("%d/%m %H:%M"),
                "a": clasificar(r["titulo"]),  # 🆕 alertas
            })

# %% 4b. 🆕 Lista global de alertas + traducción al español
alertas_lista = []
for _, r in noticias.iterrows():
    a = clasificar(r["titulo"])
    if a:
        alertas_lista.append({"t": r["titulo"], "o": r["titulo"], "l": r["link"], "f": r["fuente"],
                              "d": r["fecha"].strftime("%d/%m %H:%M"), "a": a})
    if len(alertas_lista) >= MAX_ALERTAS:
        break


def traducir(texto):
    for _ in range(2):   # un reintento por si Google limita la consulta
        try:
            return GoogleTranslator(source="auto", target="es").translate(texto) or texto
        except Exception:
            pass
    return texto         # si falla, queda el título original


originales = list({n["o"] for v in conteo.values() for n in v} | {n["o"] for n in alertas_lista})
with ThreadPoolExecutor(8) as ex:
    traducciones = dict(zip(originales, ex.map(traducir, originales)))
for n in [x for v in conteo.values() for x in v] + alertas_lista:
    n["t"] = traducciones[n["o"]]
print(f"{len(originales)} títulos traducidos · {len(alertas_lista)} alertas")

paises_ord = sorted(conteo, key=lambda p: len(conteo[p]), reverse=True)
total_mostradas = sum(len(v) for v in conteo.values())

# %% 5. Mapa
import plotly.graph_objects as go

lats = [PAISES[p][0] for p in paises_ord]
lons = [PAISES[p][1] for p in paises_ord]
cant = [len(conteo[p]) for p in paises_ord]
n_alert = [sum(1 for x in conteo[p] if x["a"]) for p in paises_ord]          # 🆕
colores = [COL["alerta"] if k else COL["marcador"] for k in n_alert]          # 🆕
tams = [min(12 + 2 * n, 50) for n in cant]
hover = [f"<b>{p}</b> · {n} noticias" + (f" · 🚨 {k} alertas" if k else "")
         + "<br><i>Clic para fijar las noticias en el panel</i>"
         for p, n, k in zip(paises_ord, cant, n_alert)]

fig = go.Figure()

# Efecto "glow"
for escala, op in [(2.4, 0.10), (1.6, 0.20)]:
    fig.add_trace(go.Scattergeo(
        lat=lats, lon=lons, mode="markers", hoverinfo="skip", showlegend=False,
        marker=dict(size=[t * escala for t in tams], color=colores, opacity=op, line=dict(width=0)),
    ))

# Punto principal (customdata = nombre del país, lo usa el JS para llenar el panel)
fig.add_trace(go.Scattergeo(
    lat=lats, lon=lons, mode="markers+text", showlegend=False,
    customdata=paises_ord,
    text=[p if n >= 2 else "" for p, n in zip(paises_ord, cant)],
    textposition="top center", textfont=dict(color=COL["texto"], size=11, family="Arial"),
    hovertext=hover, hoverinfo="text",
    hoverlabel=dict(bgcolor=COL["panel"], bordercolor=COL["marcador"], font=dict(color=COL["texto"], size=12)),
    marker=dict(size=tams, color=colores, opacity=0.95, line=dict(width=2, color="white")),
))

# 🆕 Fondo transparente: el color/imagen de fondo lo pone el HTML (así se ve la imagen)
fig.update_geos(
    projection_type="natural earth",
    showland=True, landcolor=COL["tierra"],
    showocean=False,
    showcountries=True, countrycolor=COL["paises"], countrywidth=0.6,
    showcoastlines=True, coastlinecolor=COL["costa"], coastlinewidth=0.6,
    showframe=False, bgcolor="rgba(0,0,0,0)", lataxis_range=[-58, 80],
)
fig.update_layout(
    title=dict(
        text=f"<b>🌾 Mercado de granos: dónde está la noticia</b><br>"
             f"<span style='font-size:13px;color:{COL['suave']}'>{total_mostradas} noticias · "
             f"últimos {DIAS} días · máx. {MAX_POR_PAIS} por país · "
             f"actualizado {datetime.now().strftime('%d/%m/%Y %H:%M')}</span>",
        x=0.02, font=dict(color=COL["texto"], size=20),
    ),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=10, r=10, t=80, b=10),
)

# JS que corre después de dibujar el mapa: llena el panel con links clickeables
POST_SCRIPT = """
var gd = document.getElementById('{plot_id}');
var DATA = __DATA__;
var ALERTAS = __ALERTAS__;
var panel = document.getElementById('lista');
var listaAl = document.getElementById('lista-alertas');
var titulo = document.getElementById('titulo-panel');
var hint = document.getElementById('hint');
var fijado = null;
var actual = null;
var TOUCH = window.matchMedia('(hover: none)').matches;   // celular / tablet
var TIT_LARGO = __TIT_LARGO__;
var TIT_CORTO = __TIT_CORTO__;

// Crea un <li> con el título (traducido), la fuente/fecha y los avisos de alerta
function crearItem(n) {
  var li = document.createElement('li');
  if (n.a && n.a.length) li.className = 'alerta';
  var a = document.createElement('a');
  a.href = n.l; a.target = '_blank'; a.rel = 'noopener noreferrer'; a.textContent = n.t;
  if (n.o && n.o !== n.t) a.title = 'Original: ' + n.o;
  var s = document.createElement('small');
  s.textContent = (n.f ? n.f + ' · ' : '') + n.d;
  li.appendChild(a); li.appendChild(s);
  (n.a || []).forEach(function (t) {
    var b = document.createElement('span');
    b.className = 'badge' + (t.indexOf('bélico') >= 0 ? ' bel' : '');
    b.textContent = t;
    li.appendChild(b);
  });
  return li;
}
function mostrar(pais) {
  if (pais === actual) return;   // no redibujar la lista si ya es la misma (evita perder clics)
  actual = pais;
  var items = DATA[pais] || [];
  titulo.textContent = pais + ' · ' + items.length + ' noticias';
  panel.innerHTML = '';
  items.forEach(function (n) { panel.appendChild(crearItem(n)); });
  panel.scrollTop = 0;
}
// Panel de alertas
document.getElementById('cuenta-alertas').textContent = ALERTAS.length;
if (!ALERTAS.length) {
  listaAl.innerHTML = '<li>Sin alertas en este período.</li>';
} else {
  ALERTAS.forEach(function (n) { listaAl.appendChild(crearItem(n)); });
}
function actualizarHint() {
  hint.textContent = fijado
    ? (TOUCH ? '📌 Mostrando las noticias de ' + fijado + '. Tocá otro círculo para cambiar.'
             : '📌 Fijado: ' + fijado + '. Clic en el mismo círculo para soltar, o en otro para cambiar.')
    : (TOUCH ? 'Tocá un círculo del mapa para ver sus noticias. Rojo = tiene alertas.'
             : 'Pasá el mouse sobre un círculo para ver sus noticias. Clic para fijarlas. Rojo = tiene alertas.');
}
// Al pasar el mouse: muestra las noticias (salvo que haya un país fijado)
gd.on('plotly_hover', function (e) {
  var p = e.points[0];
  if (!p.customdata || fijado) return;
  mostrar(p.customdata);
});
// Abrir noticias: pestaña nueva; si el navegador la bloquea, abre en la misma pestaña
function abrirLink(ev) {
  var a = ev.target.closest('a');
  if (!a) return;
  ev.preventDefault();
  var w = window.open(a.href, '_blank');
  if (w) { w.opener = null; } else { window.location.href = a.href; }
}
panel.addEventListener('click', abrirLink);
listaAl.addEventListener('click', abrirLink);
// Clic: fija el país (otro clic en el mismo lo suelta)
gd.on('plotly_click', function (e) {
  var p = e.points[0];
  if (!p.customdata) return;
  if (!TOUCH && fijado === p.customdata) {
    fijado = null;
  } else {
    fijado = p.customdata;
    mostrar(p.customdata);
  }
  actualizarHint();
});
actualizarHint();
// Ajustes para pantallas chicas (título corto, textos más chicos)
function ajustar() {
  var m = window.innerWidth <= 800;
  Plotly.relayout(gd, m
    ? {'title.text': TIT_CORTO, 'title.font.size': 15, 'margin.t': 56, 'margin.l': 4, 'margin.r': 4}
    : {'title.text': TIT_LARGO, 'title.font.size': 20, 'margin.t': 80, 'margin.l': 10, 'margin.r': 10});
  Plotly.restyle(gd, {'textfont.size': m ? 9 : 11}, [2]);
  Plotly.Plots.resize(gd);
}
ajustar();
setTimeout(ajustar, 150);
window.addEventListener('resize', ajustar);
"""
titulo_largo = fig.layout.title.text
titulo_corto = (f"<b>🌾 Noticias de granos</b><br>"
                f"<span style='font-size:11px;color:{COL['suave']}'>{total_mostradas} noticias · "
                f"{DIAS} días · act. {datetime.now().strftime('%d/%m %H:%M')}</span>")
_js = lambda obj: json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")
post_script = (POST_SCRIPT
               .replace("__DATA__", _js(conteo))
               .replace("__ALERTAS__", _js(alertas_lista))
               .replace("__TIT_LARGO__", json.dumps(titulo_largo, ensure_ascii=False))
               .replace("__TIT_CORTO__", json.dumps(titulo_corto, ensure_ascii=False)))

plot_html = fig.to_html(
    full_html=False, include_plotlyjs="cdn", div_id="mapa",
    default_height="100%", default_width="100%",
    config={"responsive": True, "displaylogo": False},
    post_script=post_script,
)


# 🆕 Logo e imagen de fondo: si es un archivo local, se incrusta en el HTML (base64)
def src_imagen(ruta):
    if not ruta:
        return ""
    if ruta.startswith("http"):
        return ruta
    if os.path.exists(ruta):
        mime = mimetypes.guess_type(ruta)[0] or "image/png"
        with open(ruta, "rb") as fh:
            return f"data:{mime};base64," + base64.b64encode(fh.read()).decode()
    print(f"⚠️ No encontré la imagen '{ruta}': se omite.")
    return ""


logo_src, fondo_src = src_imagen(LOGO), src_imagen(FONDO_IMAGEN)
css_root = ":root{" + ";".join(f"--{k}:{v}" for k, v in COL.items()) + "}"
css_fondo = (f"background-image:linear-gradient({VELO_FONDO},{VELO_FONDO}),url('{fondo_src}');"
             "background-size:cover;background-position:center;background-repeat:no-repeat;"
             if fondo_src else "")
logo_html = f'<div id="cab"><img src="{logo_src}" alt="Bolsa de Cereales de Bahía Blanca"></div>' if logo_src else ""

PAGINA = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mapa de noticias del mercado de granos</title>
<style>
  __ROOT__
  html, body { margin:0; height:100%; overflow:hidden; background:var(--fondo); font-family: Arial, sans-serif; color:var(--texto); }
  body { __FONDO__ }
  #app { display:flex; height:100%; width:100%; }
  #mapwrap { flex:1 1 0; min-width:0; height:100%; overflow:hidden; }
  #mapwrap .plotly-graph-div { width:100% !important; height:100% !important; }
  #panel { flex:0 0 380px; width:380px; max-width:45vw; min-width:0; background:var(--panel); border-left:1px solid var(--borde); display:flex; flex-direction:column; }
  #cab { padding:12px 16px 0; }
  #cab img { max-height:52px; max-width:100%; display:block; }
  #panel h2 { margin:0; padding:16px 16px 4px; font-size:17px; color:#fff; }
  #hint { padding:0 16px 10px; font-size:12px; color:var(--suave); }
  #alertas { margin:10px 8px 0; border:1px solid var(--alerta); border-radius:6px; background:rgba(230,57,70,.10); }
  #alertas summary { cursor:pointer; padding:8px 10px; font-weight:bold; font-size:14px; color:var(--alerta); }
  #lista-alertas { list-style:none; margin:0; padding:0 6px 6px; max-height:210px; overflow-y:auto; overscroll-behavior:contain; }
  #lista { list-style:none; margin:0; padding:0 8px 16px; overflow-y:auto; flex:1; }
  #lista li, #lista-alertas li { padding:10px 8px; border-bottom:1px solid var(--borde); }
  #lista li.alerta { border-left:3px solid var(--alerta); }
  #lista a, #lista-alertas a { color:var(--link); text-decoration:none; font-size:14px; line-height:1.35; }
  #lista a:hover, #lista-alertas a:hover { text-decoration:underline; }
  #lista small, #lista-alertas small { display:block; margin-top:3px; color:var(--suave); font-size:11px; }
  .badge { display:inline-block; margin:4px 4px 0 0; padding:1px 7px; border-radius:10px; font-size:11px; background:var(--marcador); color:#1a1a1a; font-weight:bold; }
  .badge.bel { background:var(--alerta); color:#fff; }
  #app { height:100%; height:100dvh; }
  #lista { overscroll-behavior:contain; -webkit-overflow-scrolling:touch; }
  @media (max-width: 800px) {
    #app { flex-direction:column; }
    #mapwrap { flex:0 0 48%; height:48%; }
    #panel { flex:1 1 0; width:auto; max-width:none; min-height:0; border-left:0; border-top:1px solid var(--borde); }
    #cab { padding:6px 12px 0; } #cab img { max-height:32px; }
    #panel h2 { font-size:15px; padding:10px 12px 2px; }
    #hint { padding:0 12px 6px; font-size:11px; }
    #lista-alertas { max-height:110px; }
    #lista li, #lista-alertas li { padding:12px 8px; }
    #lista a, #lista-alertas a { font-size:15px; }
    .modebar-container { display:none !important; }
  }
</style>
</head>
<body>
<div id="app">
  <div id="mapwrap">__PLOT__</div>
  <aside id="panel">
    __LOGO__
    <details id="alertas" open>
      <summary>🚨 Alertas (<span id="cuenta-alertas">0</span>)</summary>
      <ul id="lista-alertas"></ul>
    </details>
    <h2 id="titulo-panel">Noticias</h2>
    <div id="hint"></div>
    <ul id="lista"><li>Pasá el mouse sobre un círculo del mapa.</li></ul>
  </aside>
</div>
</body>
</html>
"""

html_final = (PAGINA.replace("__ROOT__", css_root)
                    .replace("__FONDO__", css_fondo)
                    .replace("__LOGO__", logo_html)
                    .replace("__PLOT__", plot_html))
with open(ARCHIVO_SALIDA, "w", encoding="utf-8") as f:
    f.write(html_final)
print(f"Listo: se generó {ARCHIVO_SALIDA}")








