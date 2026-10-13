# -*- coding: utf-8 -*-
"""
🌾 Mapa de noticias del mercado de granos

- Busca noticias en Google News (RSS) y detecta los países mencionados.
- Muestra MÁXIMO 20 noticias por país (las más recientes).
- Al pasar el mouse sobre un círculo, se muestran las noticias en un panel lateral
  con links clickeables. Al hacer clic en el círculo, el panel queda "fijado"
  para que puedas moverte y abrir las noticias sin que cambie.
- Genera un archivo index.html listo para publicar en GitHub Pages.

En Colab: pegá cada bloque "# %%" en una celda. En la primera celda agregá:
    !pip install -q feedparser plotly
"""

# %% 1. Configuración
QUERIES = [
    "mercado de granos", "precio soja", "precio trigo", "precio maíz",
    "grain market", "soybean prices", "wheat prices", "corn prices", "barley prices",
    "malting", "grain taxes", "exportaciones soja", "cosecha gruesa", "aranceles granos",
    "cebada", "barley", "beer market", "biocombustibles", "grain prices", "grain",
    "harvest", "cosecha", "siembra", "Agriculture", "Breweries", "Beer Industry",
    "Agriculture sector", "crop", "war", "guerra", "conflicto armado",
]
DIAS = 7                 # noticias de los últimos N días
MAX_POR_PAIS = 20        # máximo de noticias que se guardan/muestran por país
ARCHIVO_SALIDA = "index.html"
IDIOMAS = [("es-419", "AR", "AR:es-419"), ("en-US", "US", "US:en")]  # (hl, gl, ceid)

# %% 2. Búsqueda de noticias (Google News RSS)
import re, json, urllib.parse
import feedparser
import pandas as pd
from datetime import datetime, timedelta, timezone
from time import mktime


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

# %% 4. Agrupar por país (máx. MAX_POR_PAIS, las más recientes)
conteo = {}   # país -> lista de noticias (ya vienen ordenadas de más nueva a más vieja)
for _, r in con_pais.iterrows():
    for p in r["paises"]:
        lista = conteo.setdefault(p, [])
        if len(lista) < MAX_POR_PAIS:
            lista.append({
                "t": r["titulo"],
                "l": r["link"],
                "f": r["fuente"],
                "d": r["fecha"].strftime("%d/%m %H:%M"),
            })

paises_ord = sorted(conteo, key=lambda p: len(conteo[p]), reverse=True)
total_mostradas = sum(len(v) for v in conteo.values())

# %% 5. Mapa
import plotly.graph_objects as go

lats = [PAISES[p][0] for p in paises_ord]
lons = [PAISES[p][1] for p in paises_ord]
cant = [len(conteo[p]) for p in paises_ord]
tams = [min(12 + 2 * n, 50) for n in cant]
hover = [f"<b>{p}</b> · {n} noticias<br><i>Clic para fijar y abrir las noticias</i>"
         for p, n in zip(paises_ord, cant)]

fig = go.Figure()

# Efecto "glow"
for escala, op in [(2.4, 0.10), (1.6, 0.20)]:
    fig.add_trace(go.Scattergeo(
        lat=lats, lon=lons, mode="markers", hoverinfo="skip", showlegend=False,
        marker=dict(size=[t * escala for t in tams], color="#ff2d2d", opacity=op, line=dict(width=0)),
    ))

# Punto principal (customdata = nombre del país, lo usa el JS para llenar el panel)
fig.add_trace(go.Scattergeo(
    lat=lats, lon=lons, mode="markers+text", showlegend=False,
    customdata=paises_ord,
    text=[p if n >= 2 else "" for p, n in zip(paises_ord, cant)],
    textposition="top center", textfont=dict(color="white", size=11, family="Arial"),
    hovertext=hover, hoverinfo="text",
    hoverlabel=dict(bgcolor="#1a1f2b", bordercolor="#ff2d2d", font=dict(color="white", size=12)),
    marker=dict(size=tams, color="#ff3b30", opacity=0.95, line=dict(width=2, color="white")),
))

fig.update_geos(
    projection_type="natural earth",
    showland=True, landcolor="#1f2937",
    showocean=True, oceancolor="#0b1220",
    showcountries=True, countrycolor="#3b4a61", countrywidth=0.6,
    showcoastlines=True, coastlinecolor="#4b5d78", coastlinewidth=0.6,
    showframe=False, bgcolor="#0b1220", lataxis_range=[-58, 80],
)
fig.update_layout(
    title=dict(
        text=f"<b>🌾 Mercado de granos: dónde está la noticia</b><br>"
             f"<span style='font-size:13px;color:#9ca3af'>{total_mostradas} noticias · "
             f"últimos {DIAS} días · máx. {MAX_POR_PAIS} por país · "
             f"actualizado {datetime.now().strftime('%d/%m/%Y %H:%M')}</span>",
        x=0.02, font=dict(color="white", size=20),
    ),
    paper_bgcolor="#0b1220", plot_bgcolor="#0b1220",
    margin=dict(l=10, r=10, t=80, b=10),
)

# JS que corre después de dibujar el mapa: llena el panel con links clickeables
POST_SCRIPT = """
var gd = document.getElementById('{plot_id}');
var DATA = __DATA__;
var panel = document.getElementById('lista');
var titulo = document.getElementById('titulo-panel');
var hint = document.getElementById('hint');
var fijado = null;

function mostrar(pais) {
  var items = DATA[pais] || [];
  titulo.textContent = pais + ' · ' + items.length + ' noticias';
  panel.innerHTML = '';
  items.forEach(function (n) {
    var li = document.createElement('li');
    var a = document.createElement('a');
    a.href = n.l; a.target = '_blank'; a.rel = 'noopener noreferrer'; a.textContent = n.t;
    var s = document.createElement('small');
    s.textContent = (n.f ? n.f + ' · ' : '') + n.d;
    li.appendChild(a); li.appendChild(s); panel.appendChild(li);
  });
  panel.scrollTop = 0;
}
function actualizarHint() {
  hint.textContent = fijado
    ? '📌 Mostrando las noticias de ' + fijado + '. Hacé clic en otro círculo para cambiar.'
    : 'Hacé clic en un círculo del mapa para ver sus noticias.';
}
gd.on('plotly_click', function (e) {
  var p = e.points[0];
  if (!p.customdata) return;
  fijado = p.customdata;
  mostrar(p.customdata);
  actualizarHint();
});
actualizarHint();
"""
post_script = (POST_SCRIPT
               .replace("__DATA__", json.dumps(conteo, ensure_ascii=False).replace("</", "<\\/")))

plot_html = fig.to_html(
    full_html=False, include_plotlyjs="cdn", div_id="mapa",
    default_height="100%", default_width="100%",
    config={"responsive": True, "displaylogo": False},
    post_script=post_script,
)

PAGINA = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mapa de noticias del mercado de granos</title>
<style>
  html, body { margin:0; height:100%; background:#0b1220; font-family: Arial, sans-serif; color:#e5e7eb; }
  #app { display:flex; height:100%; }
  #mapwrap { flex:1; min-width:0; height:100%; }
  #panel { width:380px; background:#111827; border-left:1px solid #1f2937; display:flex; flex-direction:column; }
  #panel h2 { margin:0; padding:16px 16px 4px; font-size:17px; color:#fff; }
  #hint { padding:0 16px 10px; font-size:12px; color:#9ca3af; }
  #lista { list-style:none; margin:0; padding:0 8px 16px; overflow-y:auto; flex:1; }
  #lista li { padding:10px 8px; border-bottom:1px solid #1f2937; }
  #lista a { color:#ff6b61; text-decoration:none; font-size:14px; line-height:1.35; }
  #lista a:hover { text-decoration:underline; }
  #lista small { display:block; margin-top:3px; color:#9ca3af; font-size:11px; }
  @media (max-width: 800px) {
    #app { flex-direction:column; }
    #mapwrap { height:55%; flex:none; }
    #panel { width:auto; flex:1; min-height:0; border-left:0; border-top:1px solid #1f2937; }
  }
</style>
</head>
<body>
<div id="app">
  <div id="mapwrap">__PLOT__</div>
  <aside id="panel">
    <h2 id="titulo-panel">Noticias</h2>
    <div id="hint"></div>
    <ul id="lista"><li>Pasá el mouse sobre un círculo del mapa.</li></ul>
  </aside>
</div>
</body>
</html>
"""

with open(ARCHIVO_SALIDA, "w", encoding="utf-8") as f:
    f.write(PAGINA.replace("__PLOT__", plot_html))
print(f"Listo: se generó {ARCHIVO_SALIDA}")



