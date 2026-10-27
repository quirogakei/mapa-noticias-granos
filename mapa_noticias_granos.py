# -*- coding: utf-8 -*-
"""
Mapa de noticias del mercado de granos

- Busca noticias en Google News (RSS) y detecta el país principal de cada una.
- Sin noticias repetidas: se descartan las que cuentan la misma historia (aunque cambie la
  fuente o la redacción, y también si una está en inglés y otra en español).
- Filtros por producto o tema (trigo, maíz, soja, petróleo, gas, guerra, etc.).
- Muestra como máximo 20 noticias por país. Al pasar el mouse sobre un círculo se ven en el
  panel lateral; con un clic el panel queda fijado.
- Traduce los títulos al español y genera alertas (suba/baja de granos, petróleo, gas natural
  y ataques bélicos).
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
    "Agriculture sector", "crop", "war", "guerra", "conflicto armado", "Sunflower seed",
    "Sunflower oil", "Sunflower pellets", "Sunflower prices", "milling", "soybean meal",
    "aceite de palma", "palma", "palm oil", "tariffs",
    "precio petróleo", "oil prices", "gas natural", "natural gas prices",
    "sorgo", "sorghum", "arroz", "rice prices",
]
DIAS = 7                  # noticias de los últimos N días
MAX_POR_PAIS = 20         # máximo de noticias que se MUESTRAN por país
MAX_GUARDAR = 40          # noticias que se guardan por país para poder filtrar
MAX_ALERTAS = 12          # máximo de alertas que se MUESTRAN en el panel superior
MAX_ALERTAS_GUARDAR = 60  # alertas guardadas para poder filtrarlas
ARCHIVO_SALIDA = "index.html"
IDIOMAS = [("es-419", "AR", "AR:es-419"), ("en-US", "US", "US:en")]  # (hl, gl, ceid)

# Qué tan parecidos tienen que ser dos títulos para considerarlos la misma noticia (0 a 1).
# Más bajo = descarta más repetidas (riesgo: junta noticias distintas). Más alto = descarta menos.
UMBRAL_ORIGINAL = 0.60    # se compara el título tal cual vino de Google News
UMBRAL_TRADUCIDO = 0.50   # se compara de nuevo ya traducido (junta la versión en inglés y la en español)

# Colores. Fondo más claro que antes; el rojo queda reservado para las alertas.
COL = dict(
    fondo="#f8faf5",      # fondo de la página y del mar
    panel="#ffffff",
    borde="#e6ebdd",      # divisores
    tierra="#dfe8d4",     # continentes
    paises="#dfe8d4",
    costa="#c4d3b6",      # costas
    marcador="#2a8a43",   # círculos normales
    alerta="#D62828",     # SOLO alertas
    verde="#94C24A",
    turquesa="#1CAB9E",
    titulo="#1E612C",
    texto="#4a4a4a",
    suave="#7d7d7d",
    link="#1E612C",
)
# Tipografía: serif de estilo diario para titulares y sans neutra para el resto
# (Google Fonts, se cargan solas). Para volver a Franklin Gothic, cambiá estas dos líneas.
FUENTE = "Source Sans 3, Segoe UI, Helvetica Neue, Arial, sans-serif"
FUENTE_T = "Source Serif 4, Georgia, Times New Roman, serif"
GOOGLE_FONTS = "Source+Sans+3:wght@400;500;600&family=Source+Serif+4:wght@400;600;700"
LOGO = "logo.png"         # logo (subilo al repo junto al script). "" = sin logo
FONDO_IMAGEN = ""         # opcional: imagen de fondo
VELO_FONDO = "rgba(248,250,245,0.92)"   # capa clara sobre la imagen de fondo

# %% 2. Búsqueda de noticias (Google News RSS)
import re, json, urllib.parse, os, base64, mimetypes, unicodedata
import feedparser
import pandas as pd
from datetime import datetime, timedelta, timezone
from time import mktime
from deep_translator import GoogleTranslator
ART = timezone(timedelta(hours=-3))   # hora de Argentina (sin horario de verano)

_STOP = set("""de la el los las y en a un una unos unas que por con para del al se su sus es son lo le les
 the of and in to for on at as by from with is are an its it this that after amid over new more than
 un una ante sobre entre como mas más pero sin tras desde hasta hacia segun según""".split())


def _singular(w):
    """Saca la 's' / 'es' del plural para que 'tension' y 'tensions' cuenten como la misma palabra."""
    if len(w) > 4 and w.endswith("es"):
        return w[:-2]
    if len(w) > 3 and w.endswith("s"):
        return w[:-1]
    return w


def tokens(titulo):
    """Palabras 'importantes' de un título (sin la fuente del final, tildes, mayúsculas ni conectores)."""
    t = re.sub(r"\s+[-–|]\s+[^-–|]{2,40}$", "", titulo)
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return frozenset(_singular(w) for w in re.findall(r"[a-z0-9]+", t) if len(w) > 2 and w not in _STOP)


def quitar_repetidas(df, col, umbral):
    """Se queda con la versión MÁS NUEVA de cada noticia y descarta las que son (casi) la misma
    historia: similitud de Jaccard entre las palabras del título >= umbral."""
    if not len(df):
        return df
    df = df.sort_values("fecha", ascending=False)
    vistos, keep = [], []
    for idx, t in zip(df.index, df[col]):
        tk = tokens(t)
        if tk and any(v and len(tk & v) / len(tk | v) >= umbral for v in vistos):
            continue
        vistos.append(tk)
        keep.append(idx)
    return df.loc[keep]


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
                    filas.append({"titulo": " ".join(e.title.split()), "link": e.link, "fecha": fecha,
                                  "fuente": getattr(e, "source", {}).get("title", "")})
    if not filas:
        return pd.DataFrame(columns=["titulo", "link", "fecha", "fuente"])
    df = pd.DataFrame(filas).sort_values("fecha", ascending=False).drop_duplicates("link")
    df = quitar_repetidas(df, "titulo", UMBRAL_ORIGINAL)
    return df.sort_values("fecha", ascending=False).reset_index(drop=True)


noticias = buscar_noticias(QUERIES, DIAS, IDIOMAS)
print(f"{len(noticias)} noticias distintas encontradas")

# %% 3. Detección de países
# Solo países que importan para el agro o para la geopolítica de granos y energía.
# Un alias que empieza con "=" distingue mayúsculas (así "US" no matchea "us" en otro idioma).
# Para agregar un país: sumá una línea con (lat, lon, [alias]).
PAISES = {
    # Grandes productores y exportadores
    "Argentina": (-34.6, -64.0, ["argentina", "argentino", "argentinos", "argentinas", "rosario",
                                 "bolsa de cereales", "buenos aires", "bahía blanca", "bahia blanca"]),
    "Brasil": (-14.2, -51.9, ["brasil", "brazil", "brasileño", "brasileña", "mato grosso", "paranaguá", "conab"]),
    "Estados Unidos": (39.8, -98.6, ["estados unidos", "ee.uu", "eeuu", "united states", "usda", "chicago",
                                     "cbot", "iowa", "illinois", "midwest", "washington", "trump",
                                     "casa blanca", "white house", "=US", "=USA", "=U.S.", "=U.S.A."]),
    "Canadá": (56.1, -106.3, ["canadá", "canada", "canadian", "canadiense"]),
    "Australia": (-25.3, 133.8, ["australia", "australian", "australiano"]),
    "Rusia": (61.5, 105.3, ["rusia", "russia", "russian", "ruso", "rusa", "kremlin", "moscú", "moscow", "putin"]),
    "Ucrania": (48.4, 31.2, ["ucrania", "ukraine", "ukrainian", "ucraniano", "odesa", "odessa", "kiev",
                             "kyiv", "zelensky", "zelenski"]),
    "Unión Europea": (50.0, 10.0, ["unión europea", "european union", "europa", "europe", "euronext",
                                   "bruselas", "brussels", "=EU", "=UE"]),
    "Indonesia": (-0.8, 113.9, ["indonesia", "indonesian"]),
    "Malasia": (4.2, 102.0, ["malasia", "malaysia", "malaysian"]),
    # Grandes compradores
    "China": (35.9, 104.2, ["china", "chino", "china's", "chinese", "beijing", "pekín", "dalian", "xi jinping"]),
    "India": (20.6, 79.0, ["india", "indian"]),
    "Egipto": (26.8, 30.8, ["egipto", "egypt", "egyptian"]),
    # Energía y conflictos
    "Arabia Saudita": (23.9, 45.1, ["arabia saudita", "saudi", "riad", "riyadh"]),
    "Irán": (32.4, 53.7, ["irán", "iran", "iranian", "teherán", "tehran", "ormuz", "hormuz"]),
    "Israel": (31.0, 34.9, ["israel", "israeli", "israelí", "gaza", "hamás", "hamas", "tel aviv"]),
}


def _compilar(aliases, flags):
    if not aliases:
        return None
    return re.compile(r"(?<![\w$])(" + "|".join(re.escape(a) for a in aliases) + r")(?![\w$])", flags)


patrones = {}
for _p, (_, _, _al) in PAISES.items():
    _cs = [a[1:] for a in _al if a.startswith("=")]
    _ci = [a for a in _al if not a.startswith("=")]
    patrones[_p] = (_compilar(_ci, re.I), _compilar(_cs, 0))


def detectar_pais(texto):
    """Devuelve UN solo país: el que aparece primero en el título (así una noticia no se repite en varios países)."""
    mejor, pos = None, 10**9
    for p, rxs in patrones.items():
        for rx in rxs:
            m = rx.search(texto) if rx else None
            if m and m.start() < pos:
                mejor, pos = p, m.start()
    return mejor

# %% 3b. Detección de alertas (se evalúa sobre el título ORIGINAL, en español o inglés)
_rx = lambda p: re.compile(p, re.I)
_ini, _fin = r"(?<!\w)(?:", r")(?!\w)"

RX_ACTIVOS = {
    "Granos": _rx(_ini + r"soja|soya|trigo|ma[ií]z|cebada|girasol|palma|granos?|soybeans?|wheat|corn|barley|grains?|sunflower|palm oil|oilseeds?" + _fin),
    "Petróleo": _rx(_ini + r"petr[oó]leo|crudo|brent|wti|crude|barril(?:es)?|barrels?" + _fin
                    + r"|(?<!sunflower )(?<!palm )(?<!soybean )(?<!vegetable )(?<!olive )(?<!\w)oil prices?(?!\w)"),
    "Gas natural": _rx(_ini + r"gas natural|natural gas|gnl|lng" + _fin),
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
        out.append("Ataque bélico")
    return out

# %% 3c. Productos y temas para el filtro (se detectan en el título original y en el traducido)
PRODUCTOS = {  # id: (etiqueta del botón, expresión regular)
    "trigo": ("Trigo", r"trigo|wheat"),
    "maiz": ("Maíz", r"ma[ií]z|corn"),
    "soja": ("Soja", r"soja|soya|soybeans?|soy meal|soy oil|soymeal|soybean"),
    "cebada": ("Cebada y malta", r"cebada|barley|malta|malting|malt|cerveza|beer|brewer\w*|cervecer\w*"),
    "girasol": ("Girasol", r"girasol|sunflower"),
    "sorgo": ("Sorgo", r"sorgo|sorghum"),
    "arroz": ("Arroz", r"arroz|rice"),
    "palma": ("Aceite de palma", r"aceite de palma|palm oil|palma|palm"),
    "petroleo": ("Petróleo", r"petr[oó]leo|crudo|brent|wti|crude|barril(?:es)?|barrels?"
                             r"|(?<!sunflower )(?<!palm )(?<!soybean )(?<!vegetable )(?<!olive )oil prices?"),
    "gas": ("Gas natural", r"gas natural|natural gas|gnl|lng"),
    "guerra": ("Guerra y conflictos", r"guerras?|wars?|conflicto\w*|conflicts?|ataque\w*|attacks?|attacked|misil\w*|missiles?|dron(?:es)?|drones?|invasi[oó]n|invasion|bombard\w*|bombing|ofensiva|offensive|airstrikes?"),
    "bio": ("Biocombustibles", r"biocombustibles?|biodi[eé]sel|bioetanol|etanol|ethanol|biofuels?"),
    "aranceles": ("Aranceles e impuestos", r"aranceles?|tariffs?|retenciones|derechos de exportaci[oó]n|export (?:tax|taxes|duty|duties)|impuestos?"),
    "cosecha": ("Cosecha y siembra", r"cosecha\w*|harvest\w*|siembra|planting|sowing|sequ[ií]a|drought"),
}
RX_PRODUCTOS = {k: _rx(_ini + v[1] + _fin) for k, v in PRODUCTOS.items()}


def etiquetar(texto):
    """Lista de ids de productos/temas que menciona un texto."""
    return [k for k, rx in RX_PRODUCTOS.items() if rx.search(texto)]

# %% 4. Candidatas, traducción y segunda pasada contra repetidas
noticias["pais"] = [detectar_pais(t) for t in noticias["titulo"]]
noticias["alertas"] = [clasificar(t) for t in noticias["titulo"]]
print(f"{noticias['pais'].notna().sum()} de {len(noticias)} noticias mencionan algún país del mapa")

# Para no traducir cientos de títulos de más, se arma una lista corta de candidatas
# (las más nuevas de cada país + las más nuevas con alerta). Ya vienen ordenadas por fecha.
_idx = set()
for _p, _g in noticias[noticias["pais"].notna()].groupby("pais"):
    _idx |= set(_g.head(MAX_GUARDAR + 20).index)
_idx |= set(noticias[noticias["alertas"].map(bool)].head(MAX_ALERTAS_GUARDAR + 30).index)
cand = noticias.loc[sorted(_idx)].copy()

import time
errores_trad = []


def _traducir_uno(t):
    return GoogleTranslator(source="auto", target="es").translate(t) or t


def traducir_lote(textos):
    """Traduce varios títulos en UNA sola consulta (uno por línea). Así se hacen pocas consultas
    en vez de cientos, y Google no bloquea por exceso de pedidos."""
    for intento in range(3):
        try:
            res = GoogleTranslator(source="auto", target="es").translate("\n".join(textos))
            partes = (res or "").split("\n")
            if len(partes) == len(textos):
                return partes
            break                      # Google unió/partió líneas: se resuelve uno por uno
        except Exception as e:
            errores_trad.append(repr(e)[:200])
            time.sleep(2 * (intento + 1))
    out = []                           # plan B: de a uno (se omite si ya hay muchos errores)
    for t in textos:
        if len(errores_trad) > 5:
            out.append(t); continue
        try:
            out.append(_traducir_uno(t))
        except Exception as e:
            errores_trad.append(repr(e)[:200]); out.append(t)
    return out


originales = list(dict.fromkeys(cand["titulo"]))
lotes, actual_l, largo = [], [], 0
for t in originales:
    if actual_l and (largo + len(t) > 3800 or len(actual_l) >= 40):
        lotes.append(actual_l); actual_l, largo = [], 0
    actual_l.append(t); largo += len(t) + 1
if actual_l:
    lotes.append(actual_l)
traducciones = {}
for lote in lotes:
    for t_orig, t_es in zip(lote, traducir_lote(lote)):
        traducciones[t_orig] = t_es
    time.sleep(0.5)
cand["es"] = [traducciones.get(t, t) for t in cand["titulo"]]
print(f"{len(originales)} títulos · {sum(1 for t in originales if traducciones.get(t, t).strip() != t.strip())} traducidos")
if errores_trad:
    print(f"Aviso: {len(errores_trad)} errores de traducción. Primero: {errores_trad[0]}")

# Segunda pasada: ya en español, la versión en inglés y la en español de una misma noticia se parecen
_antes = len(cand)
cand = quitar_repetidas(cand, "es", UMBRAL_TRADUCIDO)
print(f"{_antes - len(cand)} repetidas más descartadas tras traducir")


def _item(r):
    return {
        "t": r["es"],                       # título en español
        "o": r["titulo"],                   # título original
        "l": r["link"],
        "f": r["fuente"],
        "d": r["fecha"].astimezone(ART).strftime("%d/%m %H:%M"),
        "a": r["alertas"],                  # alertas
        "p": etiquetar(r["titulo"] + " " + r["es"]),   # productos/temas (para el filtro)
    }


# Cada noticia va en UN solo país (de más nueva a más vieja)
conteo = {}
for _, r in cand[cand["pais"].notna()].iterrows():
    lista = conteo.setdefault(r["pais"], [])
    if len(lista) < MAX_GUARDAR:
        lista.append(_item(r))

alertas_lista = [_item(r) for _, r in cand[cand["alertas"].map(bool)].head(MAX_ALERTAS_GUARDAR).iterrows()]
print(f"{len(alertas_lista)} alertas")

paises_ord = sorted(conteo, key=lambda p: len(conteo[p]), reverse=True)
vis = {p: conteo[p][:MAX_POR_PAIS] for p in paises_ord}      # lo que se muestra sin filtros
total_mostradas = sum(len(v) for v in vis.values())

# %% 5. Mapa
import plotly.graph_objects as go

lats = [PAISES[p][0] for p in paises_ord]
lons = [PAISES[p][1] for p in paises_ord]
cant = [len(vis[p]) for p in paises_ord]
n_alert = [sum(1 for x in vis[p] if x["a"]) for p in paises_ord]
colores = [COL["alerta"] if k else COL["marcador"] for k in n_alert]
bordes = ["#ffffff"] * len(n_alert)
tams = [min(12 + 2 * n, 50) for n in cant]
hover = [f"<b>{p}</b> · {n} noticias"
         + (f" · <span style='color:{COL['alerta']}'>{k} alerta{'s' if k > 1 else ''}</span>" if k else "")
         + "<br><i>Clic para fijar las noticias en el panel</i>"
         for p, n, k in zip(paises_ord, cant, n_alert)]

fig = go.Figure()

# Efecto de halo
for escala, op in [(2.4, 0.10), (1.6, 0.20)]:
    fig.add_trace(go.Scattergeo(
        lat=lats, lon=lons, mode="markers", hoverinfo="skip", showlegend=False,
        marker=dict(size=[t * escala for t in tams], color=colores, opacity=op, line=dict(width=0)),
    ))

# Punto principal (customdata = nombre del país, lo usa el JS para llenar el panel)
fig.add_trace(go.Scattergeo(
    lat=lats, lon=lons, mode="markers+text", showlegend=False,
    customdata=paises_ord,
    text=paises_ord,
    textposition="top center", textfont=dict(color=COL["titulo"], size=11, family=FUENTE),
    hovertext=hover, hoverinfo="text",
    hoverlabel=dict(bgcolor="#ffffff", bordercolor=COL["marcador"], font=dict(color=COL["texto"], size=12, family=FUENTE)),
    marker=dict(size=tams, color=colores, opacity=0.95, line=dict(width=2, color=bordes)),
))

# Fondo transparente: el color/imagen de fondo lo pone el HTML
fig.update_geos(
    projection_type="natural earth",
    showland=True, landcolor=COL["tierra"],
    showocean=False,
    showcountries=False,
    showcoastlines=True, coastlinecolor=COL["costa"], coastlinewidth=0.6,
    showframe=False, bgcolor="rgba(0,0,0,0)", lataxis_range=[-58, 80],
)
fig.update_layout(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(family=FUENTE),
    margin=dict(l=10, r=10, t=10, b=10),
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
  var items = visibles(pais);
  titulo.textContent = pais + ' · ' + items.length + ' noticias';
  panel.innerHTML = '';
  items.forEach(function (n) { panel.appendChild(crearItem(n)); });
  if (!items.length) panel.innerHTML = '<li>Sin noticias para este filtro.</li>';
  panel.scrollTop = 0;
}
// ----- Filtros por producto / tema -----
var MAXP = __MAXP__, MAXA = __MAXA__;
var COL_AL = '__COL_AL__', COL_OK = '__COL_OK__';
var PAISES = __PAISES__;
var TAGS = __TAGS__;
var sel = {}, soloAl = false;
function pasa(n) {
  if (soloAl && !(n.a && n.a.length)) return false;
  if (!Object.keys(sel).length) return true;
  return (n.p || []).some(function (t) { return sel[t]; });
}
function visibles(pais) { return (DATA[pais] || []).filter(pasa).slice(0, MAXP); }
function renderAlertas() {
  var it = ALERTAS.filter(pasa).slice(0, MAXA);
  document.getElementById('cuenta-alertas').textContent = it.length;
  listaAl.innerHTML = '';
  if (!it.length) { listaAl.innerHTML = '<li>Sin alertas para este filtro.</li>'; return; }
  it.forEach(function (n) { listaAl.appendChild(crearItem(n)); });
}
// Recalcula tamaño, color y cartel de cada círculo según el filtro (los países sin noticias se ocultan)
function aplicarFiltro() {
  var sizes = [], cols = [], txt = [], hov = [], total = 0;
  PAISES.forEach(function (p) {
    var it = visibles(p), n = it.length;
    var k = it.filter(function (x) { return x.a && x.a.length; }).length;
    total += n;
    sizes.push(n ? Math.min(12 + 2 * n, 50) : 0);
    cols.push(k ? COL_AL : COL_OK);
    txt.push(n ? p : '');
    hov.push(n ? '<b>' + p + '</b> · ' + n + ' noticias'
      + (k ? " · <span style='color:" + COL_AL + "'>" + k + ' alerta' + (k > 1 ? 's' : '') + '</span>' : '')
      + '<br><i>Clic para fijar las noticias en el panel</i>' : '');
  });
  var glow = function (f) { return sizes.map(function (x) { return x * f; }); };
  Plotly.restyle(gd, {'marker.size': [glow(2.4)], 'marker.color': [cols]}, [0]);
  Plotly.restyle(gd, {'marker.size': [glow(1.6)], 'marker.color': [cols]}, [1]);
  Plotly.restyle(gd, {'marker.size': [sizes], 'marker.color': [cols], 'text': [txt], 'hovertext': [hov]}, [2]);
  var nt = document.getElementById('n-total'); if (nt) nt.textContent = total;
}
function refrescarPanel() { var p = fijado || actual; actual = null; if (p) mostrar(p); }
// Barra de botones
var barra = document.getElementById('filtros');
var cuenta = {};
Object.keys(DATA).forEach(function (p) {
  DATA[p].forEach(function (n) { (n.p || []).forEach(function (t) { cuenta[t] = (cuenta[t] || 0) + 1; }); });
});
function chip(txt, cls, fn) {
  var b = document.createElement('button');
  b.type = 'button'; b.className = 'chip ' + cls; b.textContent = txt;
  b.addEventListener('click', fn); barra.appendChild(b); return b;
}
var btnTodos = chip('Todos', '', function () { sel = {}; soloAl = false; cambiar(); });
var chips = {};
TAGS.forEach(function (t) {
  chips[t[0]] = chip(t[1] + (cuenta[t[0]] ? ' (' + cuenta[t[0]] + ')' : ''), cuenta[t[0]] ? '' : 'vacio', function () {
    if (sel[t[0]]) { delete sel[t[0]]; } else { sel[t[0]] = true; }
    cambiar();
  });
});
var btnAl = chip('Solo alertas', 'al', function () { soloAl = !soloAl; cambiar(); });
function cambiar() {
  btnTodos.classList.toggle('on', !Object.keys(sel).length && !soloAl);
  Object.keys(chips).forEach(function (k) { chips[k].classList.toggle('on', !!sel[k]); });
  btnAl.classList.toggle('on', soloAl);
  aplicarFiltro(); renderAlertas(); refrescarPanel();
}
cambiar();
function actualizarHint() {
  hint.textContent = fijado
    ? (TOUCH ? 'Mostrando las noticias de ' + fijado + '. Tocá otro círculo para cambiar.'
             : 'Fijado: ' + fijado + '. Clic en el mismo círculo para soltar, o en otro para cambiar.')
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
// Ajustes para pantallas chicas (textos más chicos)
function ajustar() {
  var m = window.innerWidth <= 800;
  Plotly.relayout(gd, {'margin.l': m ? 4 : 10, 'margin.r': m ? 4 : 10});
  Plotly.restyle(gd, {'textfont.size': m ? 9 : 11}, [2]);
  Plotly.Plots.resize(gd);
}
ajustar();
setTimeout(ajustar, 150);
window.addEventListener('resize', ajustar);
"""
_js = lambda obj: json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")
post_script = (POST_SCRIPT
               .replace("__DATA__", _js(conteo))
               .replace("__ALERTAS__", _js(alertas_lista))
               .replace("__PAISES__", _js(paises_ord))
               .replace("__TAGS__", _js([[k, v[0]] for k, v in PRODUCTOS.items()]))
               .replace("__MAXP__", str(MAX_POR_PAIS)).replace("__MAXA__", str(MAX_ALERTAS))
               .replace("__COL_AL__", COL["alerta"]).replace("__COL_OK__", COL["marcador"]))

plot_html = fig.to_html(
    full_html=False, include_plotlyjs="cdn", div_id="mapa",
    default_height="100%", default_width="100%",
    config={"responsive": True, "displaylogo": False},
    post_script=post_script,
)


# Logo e imagen de fondo: si es un archivo local, se incrusta en el HTML (base64)
def src_imagen(ruta):
    if not ruta:
        return ""
    if ruta.startswith("http"):
        return ruta
    if os.path.exists(ruta):
        mime = mimetypes.guess_type(ruta)[0] or "image/png"
        with open(ruta, "rb") as fh:
            return f"data:{mime};base64," + base64.b64encode(fh.read()).decode()
    print(f"Aviso: no encontré la imagen '{ruta}', se omite.")
    return ""


logo_src, fondo_src = src_imagen(LOGO), src_imagen(FONDO_IMAGEN)
css_root = ":root{" + ";".join(f"--{k}:{v}" for k, v in COL.items()) + f";--fuente:{FUENTE};--fuente-t:{FUENTE_T}" + "}"
css_fondo = (f"background-image:linear-gradient({VELO_FONDO},{VELO_FONDO}),url('{fondo_src}');"
             "background-size:cover;background-position:center;background-repeat:no-repeat;"
             if fondo_src else "")
ahora = datetime.now(ART).strftime("%d/%m/%Y %H:%M")
cab_html = ('<div id="cab">'
            + (f'<img src="{logo_src}" alt="Bolsa de Cereales y Productos de Bahía Blanca"><div class="sep"></div>' if logo_src else "")
            + '<div><h1>Noticias del mercado de granos</h1>'
            + f'<p><span id="n-total">{total_mostradas}</span> noticias &nbsp;·&nbsp; últimos {DIAS} días &nbsp;·&nbsp; actualizado {ahora}</p></div></div>')

PAGINA = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Noticias del mercado de granos</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=__GFONTS__&display=swap" rel="stylesheet">
<style>
  __ROOT__
  html, body { margin:0; height:100%; overflow:hidden; background:var(--fondo); font-family:var(--fuente); color:var(--texto); }
  body { __FONDO__ }
  #app { display:flex; height:100%; width:100%; }
  #mapwrap { display:flex; flex-direction:column; flex:1 1 0; min-width:0; height:100%; overflow:hidden; }
  #mapcont { position:relative; flex:1 1 0; min-height:0; }
  #mapcont .plotly-graph-div { width:100% !important; height:100% !important; }
  #cab { display:flex; align-items:center; gap:18px; padding:16px 24px 4px; }
  #cab img { height:60px; width:auto; display:block; }
  #cab .sep { width:1px; align-self:stretch; background:var(--costa); }
  #cab h1 { margin:0; font-family:var(--fuente-t); font-size:27px; line-height:1.15; font-weight:700; color:var(--titulo); }
  #cab p { margin:6px 0 0; font-size:13px; color:var(--suave); }
  #filtros { display:flex; flex-wrap:wrap; gap:6px; padding:10px 24px 0; }
  .chip { font:inherit; font-size:13px; cursor:pointer; padding:4px 10px; border-radius:3px; border:1px solid #cfd8c4; background:#fff; color:var(--texto); }
  .chip:hover { border-color:var(--titulo); color:var(--titulo); }
  .chip.on { background:var(--titulo); border-color:var(--titulo); color:#fff; }
  .chip.al { border-color:#e3a3a3; color:var(--alerta); }
  .chip.al:hover { border-color:var(--alerta); }
  .chip.al.on { background:var(--alerta); border-color:var(--alerta); color:#fff; }
  .chip.vacio { opacity:.45; }
  #panel { flex:0 0 380px; width:380px; max-width:45vw; min-width:0; background:var(--panel); border-left:1px solid var(--borde); display:flex; flex-direction:column; }
  #panel h2 { margin:0; padding:16px 16px 4px; font-family:var(--fuente-t); font-weight:700; font-size:18px; color:var(--titulo); }
  #hint { padding:0 16px 10px; font-size:12px; color:var(--suave); }
  #alertas { margin:12px 8px 0; border:1px solid #efc3c3; border-left:4px solid var(--alerta); border-radius:3px; background:#fdf6f6; }
  #alertas summary { cursor:pointer; padding:8px 10px; font-family:var(--fuente-t); font-weight:700; font-size:15px; color:var(--titulo); }
  #lista-alertas { list-style:none; margin:0; padding:0 6px 6px; max-height:210px; overflow-y:auto; overscroll-behavior:contain; }
  #lista { list-style:none; margin:0; padding:0 8px 16px; overflow-y:auto; flex:1; }
  #lista li, #lista-alertas li { padding:10px 8px; border-bottom:1px solid var(--borde); }
  #lista li.alerta { border-left:3px solid var(--alerta); }
  #lista a, #lista-alertas a { font-family:var(--fuente-t); color:var(--link); text-decoration:none; font-size:15px; line-height:1.35; font-weight:400; }
  #lista a:hover, #lista-alertas a:hover { text-decoration:underline; }
  #lista small, #lista-alertas small { display:block; margin-top:3px; color:var(--suave); font-size:12px; }
  .badge { display:inline-block; margin:4px 4px 0 0; padding:1px 6px; border-radius:2px; font-size:11px; background:var(--alerta); color:#fff; font-weight:600; }
  .badge.bel { background:#9d1c1c; color:#fff; }
  #app { height:100%; height:100dvh; }
  #lista { overscroll-behavior:contain; -webkit-overflow-scrolling:touch; }
  @media (max-width: 800px) {
    #app { flex-direction:column; }
    #mapwrap { flex:0 0 50%; height:50%; }
    #cab { gap:10px; padding:8px 12px 0; }
    #cab img { height:34px; }
    #cab h1 { font-size:16px; }
    #cab p { font-size:10px; margin-top:3px; }
    #filtros { flex-wrap:nowrap; overflow-x:auto; padding:6px 12px 0; }
    .chip { white-space:nowrap; flex:0 0 auto; font-size:12px; padding:3px 9px; }
    #panel { flex:1 1 0; width:auto; max-width:none; min-height:0; border-left:0; border-top:1px solid var(--borde); }
    #panel h2 { font-size:16px; padding:10px 12px 2px; }
    #hint { padding:0 12px 6px; font-size:11px; }
    #lista-alertas { max-height:110px; }
    #lista li, #lista-alertas li { padding:12px 8px; }
    #lista a, #lista-alertas a { font-size:16px; }
    .modebar-container { display:none !important; }
  }
</style>
</head>
<body>
<div id="app">
  <div id="mapwrap">__CAB__<div id="filtros"></div><div id="mapcont">__PLOT__</div></div>
  <aside id="panel">
    <details id="alertas" open>
      <summary>Alertas (<span id="cuenta-alertas">0</span>)</summary>
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
                    .replace("__GFONTS__", GOOGLE_FONTS)
                    .replace("__FONDO__", css_fondo)
                    .replace("__CAB__", cab_html)
                    .replace("__PLOT__", plot_html))
with open(ARCHIVO_SALIDA, "w", encoding="utf-8") as f:
    f.write(html_final)
print(f"Listo: se generó {ARCHIVO_SALIDA}")







