# -*- coding: utf-8 -*-
"""
Mapa de noticias del mercado de granos

- Busca noticias en Google News (RSS) y se queda solo con las de los medios de la lista FUENTES.
- Descarta las que no tratan de agro, energía o logística de granos, y detecta el país principal.
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
QUERIES_BASE = [
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
DIAS = 2                  # noticias de los últimos N días
MAX_POR_PAIS = 30         # máximo de noticias que se MUESTRAN por país
MAX_GUARDAR = 40          # noticias que se guardan por país para poder filtrar
MAX_ALERTAS = 15          # máximo de alertas que se MUESTRAN en el panel superior
MAX_ALERTAS_GUARDAR = 60  # alertas guardadas para poder filtrarlas
ARCHIVO_SALIDA = "index.html"
IDIOMAS = [("es-419", "AR", "AR:es-419"), ("en-US", "US", "US:en")]  # (hl, gl, ceid)
ED_ES = IDIOMAS[0]
ED_EN = IDIOMAS[1]
ED_PT = ("pt-BR", "BR", "BR:pt-419")
ED_DE = ("de", "DE", "DE:de")

# ---- Fuentes: solo se muestran noticias de estos medios (nombre, dominio, tipo) ----
# Tipos:  agro = medio agropecuario (entra todo lo que publique)
#         mercados / general / logistica = medios que publican de todo: solo entran las notas
#         que tratan de agro, energía o logística de granos (ver es_relevante más abajo)
SOLO_FUENTES_CONFIABLES = True     # False = acepta cualquier medio (no recomendado)
FUENTES = [
    # Agro y granos
    ("Agri-Pulse", "agri-pulse.com", "agro"),
    ("AgWeb", "agweb.com", "agro"),
    ("Successful Farming", "agriculture.com", "agro"),
    ("DTN Agriculture", "dtn.com", "agro"),
    ("Fastmarkets", "fastmarkets.com", "mercados"),
    ("Grain Journal", "grainjournal.com", "agro"),
    ("Global Agriculture", "global-agriculture.com", "agro"),
    ("The Western Producer", "producer.com", "agro"),
    ("Grain Central", "graincentral.com", "agro"),
("Reuters", "reuters.com", "noticias"),
("Associated Press", "apnews.com", "noticias"),
("AgWeb", "agweb.com", "agro"),
("Brownfield Ag News", "brownfieldagnews.com", "agro"),
("DTN Agriculture", "dtnpf.com", "mercados"),
("Successful Farming", "agriculture.com", "agro"),
("Farm Progress", "farmprogress.com", "agro"),
("Agri-Pulse", "agri-pulse.com", "agro"),
("Pro Farmer", "profarmer.com", "mercados"),
("USDA", "usda.gov", "oficial"),
("USDA Foreign Agricultural Service", "fas.usda.gov", "comercio exterior"),
("USDA Agricultural Marketing Service", "ams.usda.gov", "mercados"),
("USDA National Agricultural Statistics Service", "nass.usda.gov", "estadisticas"),
("USDA Economic Research Service", "ers.usda.gov", "estadisticas"),
("U.S. Wheat Associates", "uswheat.org", "agro"),
("U.S. Grains Council", "grains.org", "agro"),
("National Corn Growers Association", "ncga.com", "agro"),
("American Soybean Association", "soygrowers.com", "agro"),
("U.S. International Trade Commission", "usitc.gov", "comercio exterior"),
("CME Group", "cmegroup.com", "mercados"),
("Interfax", "interfax.com", "noticias"),
("TASS", "tass.com", "noticias"),
("IKAR - Institute for Agricultural Market Studies", "ikar.ru", "mercados"),
("Agroinvestor", "agroinvestor.ru", "agro"),
("AgroXXI", "agroxxi.ru", "agro"),
("Ministerio de Agricultura de Rusia", "mcx.gov.ru", "oficial"),
("Servicio Federal de Estadísticas de Rusia (Rosstat)", "rosstat.gov.ru", "estadisticas"),
("Servicio Federal de Supervisión Veterinaria y Fitosanitaria", "fsvps.gov.ru", "oficial"),
("The Hindu BusinessLine", "thehindubusinessline.com", "economia"),
("The Economic Times", "economictimes.indiatimes.com", "economia"),
("Agriwatch", "agriwatch.com", "mercados"),
("Krishi Jagran", "krishijagran.com", "agro"),
("Agriculture Today", "agriculturetoday.in", "agro"),
("AGMARKNET", "agmarknet.gov.in", "mercados"),
("Ministerio de Agricultura y Bienestar de los Agricultores", "agricoop.nic.in", "oficial"),
("Agricultural and Processed Food Products Export Development Authority (APEDA)", "apeda.gov.in", "comercio exterior"),
("Directorate General of Foreign Trade", "dgft.gov.in", "comercio exterior"),
("Ministerio de Comercio e Industria de India", "commerce.gov.in", "oficial"),
("Ministerio de Estadística e Implementación de Programas", "mospi.gov.in", "estadisticas"),
("India Meteorological Department", "mausam.imd.gov.in", "clima"),
("Terre-net", "terre-net.fr", "agro"),
("La France Agricole", "lafranceagricole.fr", "agro"),
("Réussir", "reussir.fr", "agro"),
("Agra Presse", "agra.fr", "agro"),
("FranceAgriMer", "franceagrimer.fr", "mercados"),
("Ministerio de Agricultura de Francia", "agriculture.gouv.fr", "oficial"),
("Arvalis", "arvalis.fr", "agro"),
("Les Échos", "lesechos.fr", "economia"),
("Franceinfo", "franceinfo.fr", "noticias"),
("Agra Europe", "agra-europe.com", "agro"),
("Euractiv", "euractiv.com", "politica comercial"),
("Politico Europe", "politico.eu", "noticias"),
("Comisión Europea - Agricultura y Desarrollo Rural", "agriculture.ec.europa.eu", "oficial"),
("Eurostat", "ec.europa.eu", "estadisticas"),
("Comisión Europea - Comercio", "policy.trade.ec.europa.eu", "comercio exterior"),
("Copa-Cogeca", "copa-cogeca.eu", "agro"),
("Parlamento Europeo", "europarl.europa.eu", "oficial"),
("Consejo de la Unión Europea", "consilium.europa.eu", "oficial"),
("Autoridad Europea de Seguridad Alimentaria (EFSA)", "efsa.europa.eu", "oficial"),
("European CAP Network", "eu-cap-network.ec.europa.eu", "agro"),
("Latifundist", "latifundist.com", "agro"),
("AgroPortal.ua", "agroportal.ua", "agro"),
("APK-Inform", "apk-inform.com", "mercados"),
("Ukrinform", "ukrinform.net", "noticias"),
("UkrAgroConsult", "ukragroconsult.com", "mercados"),
("Ukrainian Grain Association", "uga.ua", "agro"),
("Ministerio de Política Agraria y Alimentación de Ucrania", "minagro.gov.ua", "oficial"),
("Servicio Estatal de Estadística de Ucrania", "ukrstat.gov.ua", "estadisticas"),
("AgroTimes", "agrotimes.ua", "agro"),
("The Western Producer", "producer.com", "agro"),
("RealAgriculture", "realagriculture.com", "agro"),
("Grain News", "grainnews.ca", "agro"),
("Farms.com", "farms.com", "agro"),
("Agriculture and Agri-Food Canada", "agriculture.canada.ca", "oficial"),
("Statistics Canada", "statcan.gc.ca", "estadisticas"),
("Canadian Grain Commission", "grainscanada.gc.ca", "oficial"),
("Canadian International Grains Institute", "cigi.ca", "agro"),
("Canola Council of Canada", "canolacouncil.org", "agro"),
("Canadian Canola Growers Association", "canolagrowers.com", "agro"),
("Canadian Broadcasting Corporation (CBC)", "cbc.ca", "noticias"),
("Xinhua", "english.news.cn", "noticias"),
("China Daily", "chinadaily.com.cn", "noticias"),
("China News Service", "ecns.cn", "noticias"),
("CGTN", "cgtn.com", "noticias"),
("Global Times", "globaltimes.cn", "noticias"),
("Caixin Global", "caixinglobal.com", "economia"),
("Yicai Global", "yicaiglobal.com", "economia"),
("South China Morning Post", "scmp.com", "economia"),
("China Economic Net", "en.ce.cn", "economia"),
("China.org.cn", "china.org.cn", "noticias"),
("China Briefing", "china-briefing.com", "comercio exterior"),
("China Agricultural Information Network", "agri.cn", "agro"),
("Ministry of Agriculture and Rural Affairs of China", "english.moa.gov.cn", "oficial"),
("National Bureau of Statistics of China", "stats.gov.cn", "estadisticas"),
("General Administration of Customs of China", "customs.gov.cn", "comercio exterior"),
("Ministry of Commerce of China", "mofcom.gov.cn", "comercio exterior"),
("MOFCOM Agricultural Trade Statistics", "wms.mofcom.gov.cn", "estadisticas"),
("National Grain Trade Center", "grainmarket.com.cn", "mercados"),
("Dalian Commodity Exchange", "dce.com.cn", "mercados"),
("Zhengzhou Commodity Exchange", "czce.com.cn", "mercados"),
    ("Farmers Weekly", "fwi.co.uk", "agro"),
    ("Agrarheute", "agrarheute.com", "agro"),
    ("AF News", "afnews.com.br", "agro"),
    ("Canal Rural", "canalrural.com.br", "agro"),
    ("Rural News", "ruralnews.agr.br", "agro"),
    ("Agrolink", "agrolink.com.br", "agro"),
    ("Globo Rural", "globorural.globo.com", "agro"),
    ("Globo Rural", "globoplay.globo.com", "agro"),
    ("Fertilizer International", "fertilizerinternational.com", "agro"),
    ("FeedNavigator", "feednavigator.com", "agro"),
    ("AgriBusiness Global", "agribusinessglobal.com", "agro"),
    # Mercados de commodities y energía
    ("Argus Media", "argusmedia.com", "mercados"),
    ("ICIS", "icis.com", "mercados"),
    ("CRU Group", "crugroup.com", "mercados"),
    # Prensa internacional
    ("Associated Press", "apnews.com", "general"),
    ("AFP", "afp.com", "general"),
    ("BBC News", "bbc.com", "general"),
    ("BBC News", "bbc.co.uk", "general"),
    ("CNBC", "cnbc.com", "general"),
    ("The Wall Street Journal", "wsj.com", "general"),
    ("The Economist", "economist.com", "general"),
    ("Nikkei Asia", "asia.nikkei.com", "general"),
    ("South China Morning Post", "scmp.com", "general"),
    ("Al Jazeera", "aljazeera.com", "general"),
    ("POLITICO Europe", "politico.eu", "general"),
    ("Euractiv", "euractiv.com", "general"),
    ("The Guardian", "theguardian.com", "general"),
("Agrofy News", "news.agrofy.com.ar", "agro"),
("Infocampo", "infocampo.com.ar", "agro"),
("Bichos de Campo", "bichosdecampo.com", "agro"),
("Agrositio", "agrositio.com.ar", "agro"),
("Ruralnet", "ruralnet.com.ar", "agro"),
("Agritotal", "agritotal.com", "agro"),
("Agroempresario", "agroempresario.com", "agro"),
("Clarín Rural", "clarin.com", "agro"),
("La Nación Campo", "lanacion.com.ar", "agro"),
("Revista Chacra", "revistachacra.com.ar", "agro"),
("Agrovoz", "lavoz.com.ar", "agro"),
("Agencia Tierra Viva", "agenciatierraviva.com.ar", "agro"),
("Infobae", "infobae.com", "economia"),
("Ámbito", "ambito.com", "economia"),
("El Cronista", "cronista.com", "economia"),
("Noticias Argentinas", "noticiasargentinas.com", "noticias"),
("La Nueva", "lanueva.com", "regional"),
("La Brújula 24", "labrujula24.com", "regional"),
("DataPortuaria", "dataportuaria.com", "logistica"),
("Bolsa de Comercio de Rosario", "bcr.com.ar", "mercados"),
("Bolsa de Cereales de Buenos Aires", "bolsadecereales.com", "agro"),
("Secretaría de Agricultura, Ganadería y Pesca", "argentina.gob.ar", "oficial"),
("Instituto Nacional de Tecnología Agropecuaria (INTA)", "inta.gob.ar", "oficial"),
("Servicio Nacional de Sanidad y Calidad Agroalimentaria (SENASA)", "argentina.gob.ar", "oficial"),
("Instituto Nacional de Estadística y Censos (INDEC)", "indec.gob.ar", "estadisticas"),
("CIARA-CEC", "ciaracec.com.ar", "agro"),
("Consorcio de Gestión del Puerto de Bahía Blanca", "puertobahiablanca.com", "logistica"),
("Agencia Noticias Argentinas", "noticiasargentinas.com", "noticias"),

    # Logística y transporte marítimo
    ("The Maritime Executive", "maritime-executive.com", "logistica"),
    ("gCaptain", "gcaptain.com", "logistica"),
    ("Splash", "splash247.com", "logistica"),
    ("TradeWinds", "tradewindsnews.com", "logistica"),
    ("Lloyd's List", "lloydslist.com", "logistica"),
    ("Port Technology International", "porttechnology.org", "logistica"),

]
# Para los medios que publican de todo, la búsqueda por sitio se limita a estos temas
KW_SITE = '(grain OR wheat OR corn OR soybeans OR "crude oil" OR "natural gas" OR fertilizer OR "Black Sea" OR "bulk carrier")'

# ---- Búsquedas por tema (se buscan en la edición de Google News del mismo idioma) ----
QUERIES_ES = """
oferta y demanda mundial de granos
balance mundial de trigo
balance mundial de maíz
balance mundial de soja
stocks mundiales de cereales
estimaciones USDA de granos
informe WASDE
exportaciones agropecuarias argentinas
exportaciones argentinas de trigo
exportaciones argentinas de maíz
exportaciones argentinas de soja
exportaciones argentinas de cebada
embarques de granos argentinos
embarques de granos en Bahía Blanca
embarques de granos en Quequén
volumen de exportación de cereales
ventas externas de productos agroindustriales
competitividad exportadora de granos
participación argentina en el comercio mundial de granos
principales exportadores mundiales de trigo
principales exportadores mundiales de maíz
principales exportadores mundiales de soja
compras de granos por China
demanda china de soja
importaciones chinas de cereales
importaciones de trigo de Brasil
demanda internacional de cebada cervecera
comercio internacional de malta
precios internacionales de commodities agrícolas
cotizaciones de futuros agrícolas
futuros de trigo CBOT
futuros de maíz CBOT
futuros de soja CBOT
mercado de trigo de Chicago
mercado de maíz de Chicago
mercado de soja de Chicago
precios FOB de granos argentinos
precios FAS de granos argentinos
cotización de trigo argentino
cotización de maíz argentino
cotización de soja argentina
prima de exportación de trigo
prima de exportación de soja
márgenes de exportación de granos
relación entre precios FOB y FAS
arbitrajes internacionales de granos
diferenciales de precios entre mercados agrícolas
volatilidad de futuros agrícolas
posicionamiento de fondos en commodities agrícolas
liquidación de posiciones en futuros agrícolas
derechos de exportación agropecuarios
modificaciones de retenciones a los granos
reglamentación de exportaciones agropecuarias
Declaraciones Juradas de Ventas al Exterior
cambios regulatorios en el comercio de granos
aranceles a las importaciones de productos agrícolas
aranceles estadounidenses a productos agropecuarios
restricciones comerciales a las exportaciones agrícolas
acuerdos comerciales sobre productos agropecuarios
acuerdos comerciales entre Argentina y China
acuerdos comerciales entre Mercosur y Unión Europea
barreras fitosanitarias al comercio agrícola
restricciones sanitarias a las exportaciones de granos
investigaciones antidumping sobre productos agropecuarios
impacto de sanciones internacionales en el comercio de granos
restricciones rusas a las exportaciones de trigo
exportaciones agrícolas de Ucrania
interrupciones de exportaciones en el Mar Negro
impacto de la guerra en los mercados agrícolas
conflictos geopolíticos y precios de los cereales
bloqueos de rutas marítimas comerciales
riesgos geopolíticos para el comercio agroindustrial
fletes marítimos para granos
costos de transporte de cereales
tarifas de transporte ferroviario de granos
costos logísticos de exportación agropecuaria
capacidad de carga de los puertos cerealeros
restricciones operativas en terminales portuarias
paros en puertos cerealeros argentinos
conflictos gremiales en terminales portuarias
demoras en embarques de cereales
calado del puerto de Bahía Blanca
infraestructura portuaria para exportación de granos
interrupciones del transporte de granos
obras de infraestructura logística agropecuaria
estimaciones de producción agrícola argentina
proyecciones de cosecha de trigo argentino
proyecciones de cosecha de maíz argentino
proyecciones de cosecha de soja argentina
estimaciones de rendimiento de cultivos argentinos
avance de siembra de cultivos argentinos
avance de cosecha de cereales argentinos
impacto de la sequía en los rendimientos agrícolas
impacto de las lluvias en la cosecha argentina
pronósticos climáticos para la región pampeana
balance hídrico de los cultivos
condición de los cultivos en el sudoeste bonaerense
producción agrícola del sudoeste bonaerense
estimaciones de cosecha de Bahía Blanca y su zona de influencia
superficie sembrada con trigo en Buenos Aires
superficie sembrada con cebada en Buenos Aires
rendimientos agrícolas del sudoeste bonaerense
disponibilidad hídrica para trigo y cebada
emergencias agropecuarias por sequía o inundación
precios internacionales de fertilizantes
precio internacional de la urea granulada
mercado internacional de fertilizantes nitrogenados
mercado internacional de fertilizantes fosfatados
exportaciones de fertilizantes de China
importaciones argentinas de fertilizantes
disponibilidad de fertilizantes para la campaña agrícola
relación insumo producto en trigo y maíz
costos de producción de trigo y cebada
costos de producción de maíz y soja
impacto del precio del gas en los fertilizantes
precios internacionales de combustibles y costos agrícolas
precio del petróleo y costos de transporte marítimo
mercado internacional de aceites vegetales
balance mundial de aceite de soja
balance mundial de aceite de girasol
precios internacionales del aceite de girasol
exportaciones argentinas de aceite de girasol
mercado mundial de pellets de girasol
molienda de soja en Argentina
molienda de girasol en Argentina
producción argentina de harina de soja
exportaciones argentinas de subproductos oleaginosos
capacidad de crushing de oleaginosas
mercado internacional de biodiésel
regulaciones comerciales sobre biocombustibles
mercado internacional de malta y cebada cervecera
exportaciones argentinas de malta
mercado internacional de cebada forrajera
política cambiaria y competitividad exportadora agropecuaria
tipo de cambio real y rentabilidad agrícola
tasas de interés y financiamiento agropecuario
crédito bancario para productores agropecuarios
financiamiento de la campaña agrícola argentina
política fiscal y sector agropecuario argentino
medidas económicas con impacto en las exportaciones agropecuarias
cambios impositivos para productores agropecuarios
liquidación de divisas del complejo cerealero oleaginoso
ingreso de divisas por exportaciones agroindustriales
costos de producción agropecuaria en Argentina
rentabilidad de los cultivos agrícolas argentinos
perspectivas económicas del sector agroindustrial argentino
actividad económica vinculada al complejo portuario de Bahía Blanca
conflictos laborales con impacto en la actividad portuaria
nuevas inversiones en terminales cerealeras argentinas
ampliaciones de capacidad de almacenamiento de granos
obras ferroviarias vinculadas al transporte de cereales
proyectos de inversión en infraestructura agroindustrial
""".strip().splitlines()

QUERIES_EN = """
global grain market outlook
global grain supply and demand
world grain stocks
global cereal production forecast
global agricultural commodity prices
international grain trade
global grain exports
world wheat production forecast
world corn production forecast
world soybean production forecast
world barley production forecast
global oilseed production
global vegetable oil market
international grain price movements
global grain futures market
CBOT wheat futures prices
CBOT corn futures prices
CBOT soybean futures prices
Euronext wheat futures
global agricultural commodity outlook
USDA WASDE report
USDA global grain production estimates
USDA export sales report
USDA crop progress report
USDA quarterly grain stocks
International Grains Council grain forecast
FAO cereal price index
FAO global cereal supply outlook
OECD-FAO Agricultural Outlook
global wheat export competition
global corn export competition
global soybean export competition
global barley export market
international malting barley trade
global feed grain demand
global soybean meal trade
global sunflower oil trade
global sunflower meal exports
global palm oil prices
global canola production
global rapeseed prices
global rice export restrictions
international agricultural trade flows
China soybean import demand
China grain import policies
Chinese purchases of US soybeans
China agricultural import tariffs
Brazil soybean export forecast
Brazil corn export forecast
Brazil soybean harvest progress
Brazil safrinha corn crop
Brazil agricultural export competitiveness
US corn export sales
US soybean export sales
US winter wheat crop conditions
US grain export inspections
Canadian wheat production forecast
Canadian canola export outlook
Australian wheat export forecast
Australian barley export restrictions
European Union grain production forecast
European wheat export outlook
Black Sea grain export volumes
Russian wheat export quota
Russian grain export tax
Ukraine grain export corridor
Ukraine agricultural export restrictions
Black Sea shipping disruptions
global grain export disruptions
international grain shipment delays
global agricultural trade restrictions
US agricultural tariff policy
US tariffs on agricultural imports
China tariffs on agricultural products
US-China agricultural trade tensions
retaliatory tariffs on agricultural goods
new tariffs affecting grain exports
international agricultural trade agreements
EU-Mercosur agricultural trade agreement
Mercosur agricultural export access
EU agricultural import regulations
EU agricultural trade barriers
EU deforestation regulation agricultural commodities
EUDR compliance for soybean exports
international phytosanitary trade restrictions
agricultural export quotas
grain export bans
agricultural export licensing requirements
international sanctions affecting grain exports
sanctions on Russian agricultural trade
impact of geopolitical tensions on grain prices
geopolitical risks to agricultural commodity markets
Red Sea shipping disruptions grain trade
Black Sea freight rates grain exports
international bulk carrier freight rates
Panamax freight rates grain trade
global port congestion grain shipments
international grain shipping costs
global fertilizer price outlook
international urea prices
global nitrogen fertilizer market
international phosphate fertilizer prices
global potash supply and demand
China fertilizer export restrictions
natural gas prices and fertilizer production
global fertilizer trade disruptions
international biofuel blending mandates
US biofuel policy soybean oil demand
US renewable fuel standard soybean oil
EU biodiesel import regulations
global ethanol production corn demand
global biodiesel feedstock demand
international vegetable oil stocks
global crush margins soybean processing
international soybean meal prices
global oilseed crushing capacity
international agricultural input costs
global crop yield forecasts
El Niño impact on global crop production
La Niña impact on global grain production
global drought impact on wheat production
extreme weather impact on grain supply
US Midwest drought crop conditions
Brazil drought impact on soybean production
Argentine drought impact on grain exports
Australian drought wheat production
European heatwave crop yields
global agricultural production disruptions
international food security and cereal supply
global food commodity price index
agricultural commodity fund positioning
managed money positions in grain futures
speculative trading in agricultural commodities
US dollar impact on grain export competitiveness
exchange rate movements and agricultural exports
interest rates and agricultural commodity markets
global economic growth and grain demand
China economic growth and commodity demand
international trade policy affecting agricultural exports
global trade tensions and commodity prices
international grain market volatility
global supply chain disruptions agricultural commodities
major grain exporter production revisions
international grain import demand
global grain import tenders
international wheat import tenders
international corn import tenders
international soybean import tenders
Egypt wheat import tender
Algeria wheat import tender
Saudi Arabia grain import tender
China soybean import purchases
global barley import demand
international grain procurement tenders
Argentina grain export competitiveness
Argentine wheat export prices international market
Argentine corn export competitiveness
Argentine soybean export premiums
Argentina global grain market share
South American grain export competition
Brazil Argentina grain export competition
global grain trade flows from South America
international demand for Argentine agricultural products
""".strip().splitlines()

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
# Tipografía del manual de la BCP: Franklin Gothic (Heavy para títulos, Medium para texto).
# Si el navegador no la tiene instalada, usa Libre Franklin (Google Fonts), que es muy parecida.
FUENTE = "Franklin Gothic Medium, Libre Franklin, Arial Narrow, Arial, sans-serif"
FUENTE_T = "Franklin Gothic Heavy, Libre Franklin, Arial Black, sans-serif"
GOOGLE_FONTS = "Libre+Franklin:wght@400;500;900"
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
import time
from concurrent.futures import ThreadPoolExecutor
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


def _host(url):
    m = re.match(r"https?://([^/\s]+)", url or "")
    h = (m.group(1) if m else "").lower()
    return h[4:] if h.startswith("www.") else h


_norm_nombre = lambda n: re.sub(r"[^a-z0-9]+", "", (n or "").lower())
_POR_NOMBRE = {_norm_nombre(n): (n, c) for n, d, c in FUENTES}


def fuente_valida(href, nombre):
    """Devuelve (nombre, tipo) si el medio está en FUENTES, o None. Se compara el dominio
    que informa Google News y, si falta, el nombre del medio."""
    h = _host(href)
    for n, d, c in FUENTES:
        if h == d or h.endswith("." + d):
            return n, c
    return _POR_NOMBRE.get(_norm_nombre(nombre))


def _trabajos():
    """Lista de (búsqueda, edición de Google News) sin repetir."""
    vistos, out = set(), []

    def add(q, ed):
        if (q, ed) not in vistos:
            vistos.add((q, ed)); out.append((q, ed))
    for q in QUERIES_BASE:
        for ed in IDIOMAS:
            add(q, ed)
    for q in QUERIES_ES:
        add(q, ED_ES)
    for q in QUERIES_EN:
        add(q, ED_EN)
    for n, d, c in FUENTES:      # últimas notas de cada medio de la lista
        ed = ED_PT if (d.endswith(".br") or "globo.com" in d) else ED_DE if d == "agrarheute.com" else ED_EN
        add(f"site:{d}" if c == "agro" else f"site:{d} {KW_SITE}", ed)
    return out


def _pedir(trabajo):
    q, (hl, gl, ceid) = trabajo
    url = (f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}+when:{DIAS}d"
           f"&hl={hl}&gl={gl}&ceid={ceid}")
    for intento in range(2):
        try:
            ent = feedparser.parse(url).entries
            if ent:
                return ent
        except Exception:
            pass
        time.sleep(1)
    return []


def buscar_noticias(dias):
    desde = datetime.now(timezone.utc) - timedelta(days=dias)
    trabajos = _trabajos()
    print(f"{len(trabajos)} búsquedas en Google News (puede tardar un par de minutos)...")
    with ThreadPoolExecutor(max_workers=8) as ex:
        resultados = list(ex.map(_pedir, trabajos))
    filas, fuera_de_lista = [], 0
    for ents in resultados:
        for e in ents:
            if not getattr(e, "published_parsed", None):
                continue
            fecha = datetime.fromtimestamp(mktime(e.published_parsed), tz=timezone.utc)
            if fecha < desde:
                continue
            src = getattr(e, "source", None) or {}
            valida = fuente_valida(src.get("href", ""), src.get("title", ""))
            if valida is None:
                if SOLO_FUENTES_CONFIABLES:
                    fuera_de_lista += 1
                    continue
                valida = (src.get("title", ""), "otra")
            filas.append({"titulo": " ".join(e.title.split()), "link": e.link, "fecha": fecha,
                          "fuente": valida[0], "cat": valida[1]})
    print(f"{fuera_de_lista} noticias descartadas por no ser de las fuentes de la lista")
    if not filas:
        return pd.DataFrame(columns=["titulo", "link", "fecha", "fuente", "cat"])
    df = pd.DataFrame(filas).sort_values("fecha", ascending=False).drop_duplicates("link")
    df = quitar_repetidas(df, "titulo", UMBRAL_ORIGINAL)
    return df.sort_values("fecha", ascending=False).reset_index(drop=True)


noticias = buscar_noticias(DIAS)
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
    "Granos": _rx(_ini + r"soja|soya|trigo|ma[ií]z|cebada|girasol|aceite de palma|granos?|soybeans?|wheat|corn|barley|grains?|sunflower|palm oil|oilseeds?" + _fin),
    "Petróleo": _rx(_ini + r"petr[oó]leo|crudo|brent|wti|crude|barril(?:es)?|barrels?" + _fin
                    + r"|(?<!sunflower )(?<!palm )(?<!soybean )(?<!vegetable )(?<!olive )(?<!\w)oil prices?(?!\w)"),
    "Gas natural": _rx(_ini + r"gas natural|natural gas|gnl|lng" + _fin),
}
RX_SUBA = _rx(r"(?<!\w)(?:alz\w*|aument\w*|repunt\w*|sub[eií]\w*|suba|subas|rall?y|surge|surges|surging|soar\w*|jump\w*|rise|rises|rising|rose|climb\w*|gain\w*|higher|hike\w*)(?!\w)")
RX_BAJA = _rx(r"(?<!\w)(?:baj[aóe]\w*|cae|caen|caer|ca[ií]d\w*|cay[oó]\w*|desplom\w*|retroced\w*|derrump\w*|falls?|fell|falling|drop\w*|plung\w*|slump\w*|declin\w*|lower|tumbl\w*|slid\w*|sink\w*|sank)(?!\w)")
# Contexto de agro, energía y logística (lo usan las alertas bélicas y el filtro de relevancia)
RX_CTX = _rx(_ini + r"grains?|granos?|cereal\w*|agr[ií]\w*|agro\w*|farm\w*|crops?|cultivos?|oilseeds?|oleaginos\w*|commodit\w*|fertiliz\w*|harina|molienda|crush\w*|silos?|food (?:security|prices?)|seguridad alimentaria|black sea|mar negro|red sea|mar rojo|hormuz|ormuz|shipping|vessels?|tankers?|bulk|freight|fletes?|oil|petr[oó]leo|crudo|crude|gas|energ\w*|lng|gnl|puertos?|ports?" + _fin)

# Ataque bélico = acción militar + zona o actor de guerra + vínculo con agro/energía/logística,
# y sin términos de deportes, delitos o ciberataques.
RX_MIL = _rx(_ini + r"ataque\w*|atac[oó]\w*|atacan|bombarde\w*|misil\w*|dron(?:es)?|ofensiva|invasi[oó]n|attacks?|attacked|attacking|airstrikes?|air strikes?|missiles?|drones?|bombing|bombed|shelling|invasion|offensive" + _fin)
RX_CONFLICTO = _rx(_ini + r"guerra|war|militar\w*|military|army|ej[eé]rcito|troops|tropas|armed forces|fuerzas armadas|ucrania|ukraine|ukrainian|rusia|russia|russian|israel|gaza|ir[aá]n|iran|hamas|hamás|hezbol\w*|hezbollah|houthis?|hut[ií]es?|yemen|mar rojo|red sea|mar negro|black sea|hormuz|ormuz|odesa|odessa|crimea|kherson|jers[oó]n|siria|syria|l[ií]bano|lebanon|cisjordania|west bank" + _fin)
RX_NO_BELICO = _rx(_ini + r"f[uú]tbol|football|soccer|partido|match|nba|nfl|ciberataque\w*|cyber\w*|hackers?|ransomware|ataque card[ií]aco|heart attack|panic attack|ataque de p[aá]nico|tibur[oó]n|shark|polic[ií]a|police|robo|asalto|ataque de (?:asma|ansiedad)|asthma attack|anxiety attack" + _fin)
RX_GUERRA_COMERCIAL = _rx(r"trade wars?|guerras? comercial\w*|price wars?|guerras? de precios|currency wars?|guerra cambiaria")


def clasificar(titulo):
    """Devuelve la lista de alertas que dispara un título (vacía si ninguna)."""
    out = []
    sube, baja = bool(RX_SUBA.search(titulo)), bool(RX_BAJA.search(titulo))
    if sube or baja:
        flecha = "▲" if (sube and not baja) else "▼" if (baja and not sube) else "▲▼"
        for nombre, rx in RX_ACTIVOS.items():
            if rx.search(titulo):
                out.append(f"{nombre} {flecha}")
    t = RX_GUERRA_COMERCIAL.sub(" ", titulo)
    if RX_MIL.search(t) and RX_CONFLICTO.search(t) and RX_CTX.search(t) and not RX_NO_BELICO.search(t):
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
    "palma": ("Aceite de palma", r"aceite de palma|palm oil"),
    "petroleo": ("Petróleo", r"petr[oó]leo|crudo|brent|wti|crude|barril(?:es)?|barrels?"
                             r"|(?<!sunflower )(?<!palm )(?<!soybean )(?<!vegetable )(?<!olive )oil prices?"),
    "gas": ("Gas natural", r"gas natural|natural gas|gnl|lng"),
    "fertil": ("Fertilizantes", r"fertilizantes?|fertilizers?|urea|potasa|potash|fosfatad\w*|phosphates?|nitrogenad\w*"),
    "futuros": ("Futuros y commodities", r"cbot|matba|euronext|chicago board|(?:grain|wheat|corn|soybean|agricultural|crop|oilseed) futures"
                                          r"|futuros (?:de )?(?:granos|trigo|ma[ií]z|soja|agr[ií]colas)|agricultural commodit\w+|commodities agr\w+|crush margins?|m[aá]rgenes? de molienda"),
    "bio": ("Biocombustibles", r"biocombustibles?|biodi[eé]sel|bioetanol|etanol|ethanol|biofuels?"),
    "cosecha": ("Cosecha y siembra", r"cosecha\w*|harvest\w*|siembra|planting|sowing|crop progress|crop conditions?|crop yields?|production forecasts?|estimaciones de producci[oó]n"),
    "clima": ("Clima", r"sequ[ií]as?|droughts?|el ni[nñ]o|la ni[nñ]a|inundaci\w*|floods?|heat ?waves?|ola de calor|lluvias?|rainfall|heladas?|frost|clima|weather|balance h[ií]drico"),
    "export": ("Exportaciones", r"exportaci\w*|exports?|exportad\w*|exporters?|export sales"),
    "import": ("Importaciones y licitaciones", r"licitaci\w+|tenders?|importaciones?|imports?|import demand|importadores?|importers?"),
    "fletes": ("Fletes y puertos", r"fletes? mar[ií]timos?|bulk carriers?|dry bulk|panamax|capesize|handysize|supramax|bulkers?|puertos? cerealer\w*"
                                   r"|grain (?:ports?|terminals?|shipments?|vessels?)|embarques?|calado|canal de panam\w*|red sea|mar rojo|ormuz|hormuz|black sea|mar negro"
                                   r"|bah[ií]a blanca port|puerto de bah[ií]a blanca|quequ[eé]n|hidrov[ií]a|paran[aá] river"),
    "aranceles": ("Aranceles e impuestos", r"aranceles?|tariffs?|retenciones|derechos de exportaci[oó]n|export (?:tax|taxes|duty|duties)|impuestos?"),
    "acuerdos": ("Acuerdos y sanciones", r"acuerdos? comercial\w*|trade (?:agreements?|deals?|talks)|mercosur|sanciones|sanctions?|cuotas?|quotas?"
                                         r"|prohibici[oó]n de exportaci\w+|export bans?|restricciones comercial\w*|trade restrictions?|antidumping|fitosanitari\w*|phytosanitary"),
    "guerra": ("Guerra y conflictos", r"guerras?|wars?|conflicto armado|armed conflicts?|militar\w*|military|invasi[oó]n|invasion|misil\w*|missiles?"
                                      r"|bombard\w*|airstrikes?|air strikes?|ofensiva|offensive|alto el fuego|ceasefire|hostilidades|hostilities"),
}
# Etiquetas que por sí solas indican agro o energía. Las demás (aranceles, guerra, clima, fletes...)
# solo cuentan si el título además menciona agro, energía o logística (RX_CTX).
NUCLEO = {"trigo", "maiz", "soja", "cebada", "girasol", "sorgo", "arroz", "palma", "petroleo", "gas",
          "fertil", "futuros", "bio", "cosecha"}
RX_PRODUCTOS = {k: _rx(_ini + v[1] + _fin) for k, v in PRODUCTOS.items()}


def etiquetar(texto):
    """Lista de ids de productos/temas que menciona un texto (las 'guerras comerciales' no cuentan como guerra)."""
    texto = RX_GUERRA_COMERCIAL.sub(" ", texto)
    return [k for k, rx in RX_PRODUCTOS.items() if rx.search(texto)]


def es_relevante(titulo, tipo):
    """Los medios agropecuarios entran completos. En los demás, la nota tiene que tratar de un
    producto o de energía, o de un tema comercial/bélico/climático que mencione agro, energía o logística."""
    if tipo == "agro":
        return True
    tags = set(etiquetar(titulo))
    if tags & NUCLEO:
        return True
    return bool(tags) and bool(RX_CTX.search(titulo))

# %% 4. Candidatas, traducción y segunda pasada contra repetidas
_n0 = len(noticias)
_ok = pd.Series([es_relevante(t, c) for t, c in zip(noticias["titulo"], noticias["cat"])],
                index=noticias.index, dtype=bool)
noticias = noticias[_ok].reset_index(drop=True)
print(f"{_n0 - len(noticias)} noticias descartadas por no tratar de agro, energía o logística de granos")

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
  #cab h1 { margin:0; font-family:var(--fuente-t); font-size:30px; line-height:1.12; font-weight:900; color:var(--titulo); }
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
  #panel h2 { margin:0; padding:16px 16px 4px; font-family:var(--fuente-t); font-weight:900; font-size:17px; color:var(--titulo); }
  #hint { padding:0 16px 10px; font-size:12px; color:var(--suave); }
  #alertas { margin:12px 8px 0; border:1px solid #efc3c3; border-left:4px solid var(--alerta); border-radius:3px; background:#fdf6f6; }
  #alertas summary { cursor:pointer; padding:8px 10px; font-family:var(--fuente-t); font-weight:900; font-size:14px; color:var(--titulo); }
  #lista-alertas { list-style:none; margin:0; padding:0 6px 6px; max-height:210px; overflow-y:auto; overscroll-behavior:contain; }
  #lista { list-style:none; margin:0; padding:0 8px 16px; overflow-y:auto; flex:1; }
  #lista li, #lista-alertas li { padding:10px 8px; border-bottom:1px solid var(--borde); }
  #lista li.alerta { border-left:3px solid var(--alerta); }
  #lista a, #lista-alertas a { color:var(--link); text-decoration:none; font-size:14px; line-height:1.35; font-weight:500; }
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
    #lista a, #lista-alertas a { font-size:15px; }
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






