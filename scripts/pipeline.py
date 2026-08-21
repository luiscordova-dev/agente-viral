#!/usr/bin/env python3
"""
AGENTE VIRAL — el motor.

Qué hace, en orden:
  1. Lanza tres búsquedas en Apify (TikTok, YouTube, Instagram) y espera a que terminen.
  2. Traduce lo que devuelve cada una a un formato común.
  3. Descarta lo que no es contenido: fotos, mudos, anuncios, muy corto, muy largo, sin alcance.
  4. Puntúa qué tan viral es cada video COMPARÁNDOLO CONTRA SU PROPIA PLATAFORMA.
  5. De los mejores de cada plataforma, pide a Supadata lo que se dice en el video.
  6. Baja la portada de los finalistas y escribe data/best.json + data/meta.json.

El agente (Claude) toma esos archivos y hace lo que una máquina no puede: clasificar,
mirar las portadas, escribir las ideas y llenar Notion.

De dónde salen las llaves, en este orden:
  1. las variables de entorno APIFY_TOKEN y SUPADATA_API_KEY
  2. ~/.agente-viral/config.json
  3. lo que ya tengas del CLI de Apify (~/.apify/auth.json) o en ~/.supadata.json

Cosas que costó descubrir y no hay que volver a probar:
  · TikTok solo responde bien buscando por hashtag; por palabra clave falla.
  · El filtro de fecha del propio buscador de TikTok deja pasar casi nada: se filtra después.
  · Supadata rechaza las peticiones sin User-Agent de navegador.
  · Un nicho de varias palabras no sirve como hashtag; por eso --hashtag va aparte
    del nicho: el nicho completo se usa en YouTube y el hashtag en TikTok e Instagram.

Uso:
  python3 pipeline.py "<nicho>" [--hashtag <hashtag>] [--platforms ...] [--per-platform 80] [--top 6]
"""
import json, os, sys, time, math, re, statistics, argparse, datetime as dt
import urllib.request, urllib.parse, urllib.error

# ══════ De dónde saca las llaves ══════
CONFIG_PATH = os.path.expanduser("~/.agente-viral/config.json")


def load_config():
    # mismo criterio que config.py: manda ~/.agente-viral/config.json, y al final
    # rellena con las llaves del CLI de Apify (`apify login`) o de ~/.supadata.json
    # si el usuario ya las tiene guardadas ahí.
    cfg = {}
    if os.path.exists(CONFIG_PATH):
        try:
            cfg = json.load(open(CONFIG_PATH, encoding="utf-8")) or {}
        except Exception:
            print(f"⚠ El archivo {CONFIG_PATH} está dañado. Vuelve a guardar tus llaves con: config.py set-keys")
    for path, field, key in (("~/.apify/auth.json", "token", "apify_token"),
                             ("~/.supadata.json", "api_key", "supadata_api_key")):
        if cfg.get(key):
            continue
        try:
            v = json.load(open(os.path.expanduser(path), encoding="utf-8")).get(field)
            if v:
                cfg[key] = v
        except Exception:
            pass
    return cfg


CFG = load_config()
# El .env del repo NO es fuente de llaves en runtime: es solo la puerta de entrada
# que config.py set-keys importa y limpia. Fuente única: env var > config > legacy.
APIFY_TOKEN = os.environ.get("APIFY_TOKEN") or CFG.get("apify_token")
SUPADATA_KEY = os.environ.get("SUPADATA_API_KEY") or CFG.get("supadata_api_key")


def cta_url():
    """El link del cierre. Sale del config; si no está, del default de config.py.
    Nunca se escribe a mano aquí para que no se separe del resto."""
    if CFG.get("cta_url"):
        return CFG["cta_url"]
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import config
        return config.DEFAULT_CTA_URL
    except Exception:
        return None

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
NOW = dt.datetime.now(dt.timezone.utc)

ACTORS = {
    "tiktok":    "clockworks~tiktok-scraper",
    "youtube":   "streamers~youtube-scraper",
    "instagram": "apify~instagram-hashtag-scraper",
}


class FatalError(Exception):
    """Error que detiene la corrida con un mensaje en español."""


def actor_input(plat, niche, hashtag, per_platform):
    if plat == "tiktok":   # por HASHTAG, sin filtro de fecha
        return {"hashtags": [hashtag], "resultsPerPage": per_platform}
    if plat == "youtube":  # el nicho completo sí sirve como búsqueda
        return {"searchQueries": [niche], "maxResults": per_platform,
                "sortingOrder": "views", "dateFilter": "month", "videoType": "video",
                "downloadSubtitles": False}
    if plat == "instagram":
        return {"hashtags": [hashtag], "resultsType": "reels",
                "resultsLimit": per_platform}


# ══════ Hablar con Apify ══════
def api(method, path, body=None, timeout=120):
    # el token va por header, nunca en la URL (no aparece en logs ni errores)
    url = f"https://api.apify.com/v2/{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {APIFY_TOKEN}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def abort_run(rid):
    """Aborta una corrida de Apify para no gastar crédito de más. Mejor esfuerzo."""
    try:
        api("POST", f"actor-runs/{rid}/abort", timeout=30)
    except Exception:
        pass


def launch(plat, niche, hashtag, per_platform):
    actor = ACTORS[plat]
    try:
        rid = api("POST", f"acts/{actor}/runs", actor_input(plat, niche, hashtag, per_platform))["data"]["id"]
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise FatalError("❌ Apify rechazó la llave. Revisa que la copiaste completa y vuelve a guardarla:\n"
                             "   APIFY_TOKEN=\"<tu-llave>\" python3 config.py set-keys")
        if e.code == 402:
            raise FatalError("❌ Se acabó el crédito de Apify este mes.\n"
                             "   Entra a https://console.apify.com/billing para revisarlo. El plan gratis se renueva cada mes.")
        print(f"  ⚠ {plat}: Apify contestó con error {e.code}. Se salta esta plataforma.")
        return None
    except urllib.error.URLError:
        raise FatalError("❌ No hay conexión con Apify. Revisa tu internet y vuelve a correr el comando.")
    print(f"  ▶ {plat}: corrida {rid}")
    return rid


def wait_all(runs, timeout=600):
    deadline = time.time() + timeout
    done = {}
    while runs and time.time() < deadline:
        for plat, rid in list(runs.items()):
            try:
                st = api("GET", f"actor-runs/{rid}", timeout=30)["data"]["status"]
            except urllib.error.HTTPError as e:
                if e.code in (401, 403, 404):  # error permanente: no tiene caso seguir esperando
                    print(f"  ⚠ {plat}: Apify contestó error {e.code} al consultar la corrida. Se salta esta plataforma.")
                    runs.pop(plat)
                continue  # error pasajero de red: se reintenta en el siguiente ciclo
            except Exception:
                continue
            if st in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
                done[plat] = (rid, st)
                runs.pop(plat)
                dicho = {"SUCCEEDED": "terminó bien", "FAILED": "falló",
                         "ABORTED": "se canceló", "TIMED-OUT": "se pasó de tiempo"}[st]
                print(f"  ✓ {plat}: {dicho}")
        if runs:
            time.sleep(6)
    for plat, rid in runs.items():  # lo que no terminó a tiempo se aborta para no gastar
        print(f"  ⚠ {plat}: no terminó en {timeout // 60} minutos. Se cancela y se salta esta plataforma.")
        abort_run(rid)
    return done


def dataset(rid):
    return api("GET", f"actor-runs/{rid}/dataset/items?clean=true")


# ══════ Traducir lo que devuelve cada plataforma ══════
# Cada plataforma entrega su JSON con nombres distintos. En vez de escribir tres
# veces el mismo dict a mano, aquí se declara DE DÓNDE sale cada dato y un solo
# extractor recorre la tabla. Agregar una plataforma = agregar una entrada.

def antiguedad_en_dias(marca_de_tiempo):
    """Días transcurridos desde que se publicó. Mínimo 0.1 para no dividir entre cero.
    Devuelve None ante cualquier fecha que no se pueda restar (incluidas las que
    vienen sin zona horaria, como '2026-08-21')."""
    if not marca_de_tiempo:
        return None
    try:
        publicado = dt.datetime.fromisoformat(str(marca_de_tiempo).replace("Z", "+00:00"))
        transcurrido = (NOW - publicado).total_seconds() / 86400
    except Exception:
        return None
    return transcurrido if transcurrido > 0.1 else 0.1


def a_segundos(reloj):
    """Convierte '1:23:45', '12:34' o '45' a segundos. None si no se puede leer."""
    if not reloj:
        return None
    partes = str(reloj).split(":")
    try:
        numeros = [int(x) for x in partes]
    except ValueError:
        return None
    if len(numeros) > 3:              # h:m:s como máximo; más partes es basura
        return None
    total = 0
    for n in numeros:                 # cada posición vale 60 veces más que la anterior
        total = total * 60 + n
    return total


def etiqueta(h):
    """Un hashtag puede llegar como dict, como texto suelto o nulo. Sale en minúsculas."""
    if isinstance(h, dict):
        crudo = h.get("name") or ""
    else:
        crudo = str(h or "").lstrip("#")
    return crudo.lower()


def lista_de_etiquetas(bruto):
    return [e for e in (etiqueta(h) for h in (bruto or [])) if e]


def describir_audio(meta, llave_titulo, llave_autor, llave_original):
    """Arma 'Título — Autor (original)'. Las llaves cambian según la plataforma."""
    if not isinstance(meta, dict):
        return None
    titulo = meta.get(llave_titulo)
    if not titulo:
        return None
    firma = f"{titulo} — {meta.get(llave_autor, '')}".strip(" —")
    return firma + (" (original)" if meta.get(llave_original) else "")


def titulo_con_contexto(item):
    """YouTube separa título y descripción; para clasificar conviene tener los dos.
    El título va completo y de la descripción basta el arranque."""
    titulo = (item.get("title") or "").strip()
    descripcion = (item.get("text") or "").strip()
    if not descripcion:
        return titulo
    return f"{titulo}. {descripcion[:240]}"


def _anidado(item, *ruta):
    """Baja por llaves anidadas sin reventar si algún nivel viene nulo."""
    actual = item
    for llave in ruta:
        if not isinstance(actual, dict):
            return None
        actual = actual.get(llave)
    return actual


# La tabla: campo destino -> función que lo saca del item crudo de esa plataforma.
MAPEO = {
    "tiktok": {
        "id":           lambda i: str(i.get("id")),
        "url":          lambda i: i.get("webVideoUrl"),
        "autor":       lambda i: _anidado(i, "authorMeta", "name"),
        "descripcion":      lambda i: i.get("text") or "",
        "etiquetas":     lambda i: lista_de_etiquetas(i.get("hashtags")),
        "vistas":        lambda i: i.get("playCount") or 0,
        "megusta":        lambda i: i.get("diggCount") or 0,
        "comentarios":     lambda i: i.get("commentCount") or 0,
        "compartidos":       lambda i: i.get("shareCount") or 0,
        "guardados":        lambda i: i.get("collectCount") or 0,
        "duracion":     lambda i: _anidado(i, "videoMeta", "duration"),
        "publicado":      lambda i: i.get("createTimeISO"),
        "idioma":         lambda i: i.get("textLanguage"),
        "es_carrusel": lambda i: bool(i.get("isSlideshow")),
        "sin_audio":     lambda i: bool(i.get("isMuted")),
        "es_anuncio":        lambda i: bool(i.get("isAd") or i.get("isSponsored")),
        "portada":        lambda i: _anidado(i, "videoMeta", "coverUrl"),
        "seguidores":    lambda i: _anidado(i, "authorMeta", "fans"),
        "audio":        lambda i: describir_audio(i.get("musicMeta"), "musicName", "musicAuthor", "musicOriginal"),
    },
    "youtube": {
        "id":           lambda i: str(i.get("id")),
        "url":          lambda i: i.get("url"),
        "autor":       lambda i: i.get("channelName"),
        # el título manda; se le pega un pedazo de la descripción como contexto
        "descripcion":      lambda i: titulo_con_contexto(i),
        "etiquetas":     lambda i: lista_de_etiquetas(i.get("hashtags")),
        "vistas":        lambda i: i.get("viewCount") or 0,
        "megusta":        lambda i: i.get("likes") or 0,
        "comentarios":     lambda i: i.get("commentsCount") or 0,
        "compartidos":       lambda i: 0,      # YouTube no publica compartidos
        "guardados":        lambda i: 0,      # ni guardados
        "duracion":     lambda i: a_segundos(i.get("duration")),
        "publicado":      lambda i: i.get("date"),
        "idioma":         lambda i: None,
        "es_carrusel": lambda i: False,
        "sin_audio":     lambda i: False,
        "es_anuncio":        lambda i: bool(i.get("isPaidContent")),
        "portada":        lambda i: i.get("thumbnailUrl"),
        "seguidores":    lambda i: i.get("numberOfSubscribers"),
        "audio":        lambda i: None,
    },
    "instagram": {
        "id":           lambda i: str(i.get("id")),
        "url":          lambda i: i.get("url"),
        "autor":       lambda i: i.get("ownerUsername"),
        "descripcion":      lambda i: i.get("caption") or "",
        "etiquetas":     lambda i: lista_de_etiquetas(i.get("hashtags")),
        "vistas":        lambda i: i.get("videoPlayCount") or i.get("igPlayCount") or 0,
        "megusta":        lambda i: i.get("likesCount") or 0,
        "comentarios":     lambda i: i.get("commentsCount") or 0,
        "compartidos":       lambda i: 0,
        "guardados":        lambda i: 0,
        "duracion":     lambda i: i.get("videoDuration"),
        "publicado":      lambda i: i.get("timestamp"),
        "idioma":         lambda i: None,
        "es_carrusel": lambda i: i.get("type") != "Video",
        "sin_audio":     lambda i: False,
        "es_anuncio":        lambda i: bool(i.get("paidPartnership") or i.get("isSponsored")),
        "portada":        lambda i: i.get("displayUrl"),
        "seguidores":    lambda i: None,   # el buscador por hashtag de IG no trae seguidores
        "audio":        lambda i: describir_audio(i.get("musicInfo"), "song_name", "artist_name", "uses_original_audio"),
    },
}


def norm(plat, it):
    """Traduce un item crudo de cualquier plataforma al formato interno común."""
    if plat not in MAPEO:
        return None
    fila = {"plataforma": plat}
    for campo, sacar in MAPEO[plat].items():
        fila[campo] = sacar(it)
    return fila


# Videos que técnicamente son virales pero no sirven para aprender nada.
# La lista es mía y está pensada para español e inglés: cuando el único texto
# del post son etiquetas de humor, casi siempre es un meme reciclado.
ETIQUETAS_DE_HUMOR = {
    "meme", "memes", "humor", "chiste", "chistes", "gracioso", "risa", "comedia",
    "funny", "comedy", "joke", "lol", "fail", "prank", "broma", "shitpost", "ratio",
}

# Los límites de qué merece analizarse. Un video de 5 segundos no alcanza a
# enseñar nada; uno de más de una hora no es contenido corto; y por debajo de
# mil vistas no hay señal, hay ruido.
DURACION_MINIMA = 8
DURACION_MAXIMA = 3600
VISTAS_MINIMAS = 1000


def quality_check(fila):
    """Revisa un video contra todos los cortes. Devuelve la lista de razones por
    las que NO sirve; si vuelve vacía, el video pasa."""
    descartes = []

    # 1. Que sea un video hablado, no otra cosa
    if fila["es_carrusel"]:
        descartes.append("es_foto")
    if fila["sin_audio"]:
        descartes.append("sin_sonido")
    if fila["es_anuncio"]:
        descartes.append("publicidad")

    # 2. Que dure lo razonable (si la plataforma no dice cuánto, no lo castigamos)
    segundos = fila["duracion"]
    if segundos is not None:
        if segundos < DURACION_MINIMA:
            descartes.append("muy_corto")
        elif segundos > DURACION_MAXIMA:
            descartes.append("muy_largo")

    # 3. Que haya llegado a alguien
    if fila["vistas"] < VISTAS_MINIMAS:
        descartes.append("poco_alcance")

    # 4. Meme: el post no dice nada por sí mismo y sus etiquetas son de humor
    texto_sin_etiquetas = re.sub(r"#\w+", "", fila["descripcion"]).strip()
    if not texto_sin_etiquetas and ETIQUETAS_DE_HUMOR.intersection(fila["etiquetas"]):
        descartes.append("meme")

    return descartes


def zscores(valores):
    """Devuelve una función que convierte un valor en 'qué tan por encima del
    promedio está', medido en desviaciones. Con menos de dos datos no hay
    promedio que valga, así que todo queda en cero."""
    limpios = [x for x in valores if x is not None]
    if len(limpios) < 2:
        return lambda _: 0.0
    promedio = statistics.mean(limpios)
    desviacion = statistics.pstdev(limpios) or 1.0
    return lambda x: (x - promedio) / desviacion


# ══════ Escuchar lo que se dice ══════
def es_fallo(texto):
    """Los textos que no se pudieron leer vienen marcados entre corchetes."""
    return isinstance(texto, str) and texto.startswith(("[fallo:", "[sin-"))


def fetch_transcript(url):
    """Pide a Supadata lo que se habla en un video.

    Devuelve el texto, o una marca entre corchetes si no se pudo. Nunca lanza
    excepción: un video sin transcript no debe tumbar la corrida.
    """
    if not SUPADATA_KEY:
        return "[sin-llave]"
    if not url:
        return "[sin-url]"
    consulta = urllib.parse.urlencode({"url": url, "text": "true"})
    peticion = urllib.request.Request(
        "https://api.supadata.ai/v1/transcript?" + consulta,
        headers={"x-api-key": SUPADATA_KEY, "User-Agent": UA},  # sin UA de navegador contesta 403
    )
    try:
        with urllib.request.urlopen(peticion, timeout=90) as respuesta:
            cuerpo = json.load(respuesta)
        contenido = cuerpo.get("content")
        if isinstance(contenido, str):
            return contenido
        if isinstance(contenido, list):  # a veces llega por fragmentos con tiempos
            trozos = [f.get("text", "") for f in contenido if isinstance(f, dict)]
            if not trozos and contenido:   # llegó una lista, pero no de fragmentos
                return "[fallo:forma-inesperada]"
            return " ".join(trozos)
        return ""
    except urllib.error.HTTPError as e:
        return f"[fallo:{e.code}]"
    except Exception as e:               # respuesta con forma inesperada, JSON roto, red caída
        return f"[fallo:{e}]"


MIN_WORDS, MIN_WPM = 25, 40


# ══════ Bajar las portadas ══════
def download_thumbs(best, outdir):
    """Baja la portada de cada video finalista (una foto, no el video).
    El agente las mira después para leer el gancho visual. Mejor esfuerzo:
    una portada caída nunca detiene la corrida."""
    tdir = os.path.join(outdir, "thumbs")
    os.makedirs(tdir, exist_ok=True)
    n = 0
    for r in best:
        u = r.get("portada")
        r["portada_local"] = None
        if not u:
            continue
        fname = os.path.join(tdir, f"{r['plataforma']}_{r['id']}.jpg")
        try:
            if not os.path.exists(fname):
                req = urllib.request.Request(u, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = resp.read()
                with open(fname, "wb") as f:
                    f.write(data)
            r["portada_local"] = fname
            n += 1
        except Exception:
            pass
    return n


# ══════ El recorrido completo ══════
def run():
    ap = argparse.ArgumentParser()
    ap.add_argument("niche")
    ap.add_argument("--hashtag", default=None,
                    help="hashtag para TikTok/Instagram (sin #). Default: el nicho sin espacios")
    ap.add_argument("--platforms", default="tiktok,youtube,instagram")
    ap.add_argument("--per-platform", type=int, default=80)
    ap.add_argument("--top", type=int, default=6, help="candidatos/plataforma al gate de transcript")
    ap.add_argument("--outdir", default="data")
    args = ap.parse_args()

    if not APIFY_TOKEN:
        raise FatalError("❌ Falta la llave de Apify.\n"
                         "   Consíguela en https://console.apify.com/ → Settings → API & Integrations\n"
                         "   y pégasela a tu agente en Claude Code para que la guarde por ti.\n"
                         "   (El comando que él usa: APIFY_TOKEN=\"<tu-llave>\" python3 config.py set-keys)")

    plats = [p.strip() for p in args.platforms.split(",") if p.strip() in ACTORS]
    if not plats:
        raise FatalError("❌ Ninguna plataforma válida. Usa: --platforms tiktok,youtube,instagram")
    hashtag = (args.hashtag or args.niche).replace(" ", "").replace("#", "").lower()
    OUT = args.outdir
    os.makedirs(OUT, exist_ok=True)

    print(f"🎯 nicho: {args.niche}  |  hashtag: #{hashtag}  |  plataformas: {', '.join(plats)}")
    if " " in args.niche and not args.hashtag:
        print(f"⚠ El nicho tiene varias palabras y no pasaste --hashtag.")
        print(f"  TikTok e Instagram van a buscar #{hashtag} — si ese hashtag no existe, saldrá vacío.")
        print(f"  Mejor: dile a tu agente qué hashtag usar y él corre de nuevo.")
    if not SUPADATA_KEY:
        print("⚠ Sin llave de Supadata: el agente no puede leer lo que se dice en los videos y filtrará con más ruido.")

    print("1) lanzando los robots de búsqueda…")
    runs = {}
    try:
        for p in plats:
            rid = launch(p, args.niche, hashtag, args.per_platform)
            if rid:
                runs[p] = rid
    except FatalError:
        for rid in runs.values():  # no dejar corridas vivas gastando crédito
            abort_run(rid)
        raise
    if not runs:
        raise FatalError("❌ Ninguna plataforma arrancó. Revisa los mensajes de arriba.")
    done = wait_all(runs)

    print("2) descargando y ordenando resultados…")
    rows, malformed, plats_ok = [], 0, 0
    for plat, (rid, st) in done.items():
        if st != "SUCCEEDED":
            print(f"  ⚠ {plat}: la búsqueda no terminó bien. Se salta esta plataforma.")
            continue
        plats_ok += 1
        try:
            items = dataset(rid)
        except Exception:
            print(f"  ⚠ {plat}: no se pudieron descargar los resultados. Se salta esta plataforma.")
            continue
        json.dump(items, open(f"{OUT}/{plat}_raw.json", "w", encoding="utf-8"), ensure_ascii=False)
        for it in items:
            try:
                rows.append(norm(plat, it))
            except Exception:
                malformed += 1  # un item raro no tira la corrida completa
    if malformed:
        print(f"  • {malformed} resultados venían incompletos y se descartaron.")
    print(f"   total encontrado: {len(rows)}")
    if not rows:
        if plats_ok == 0:
            raise FatalError("❌ Las búsquedas fallaron — no es culpa de tu hashtag.\n"
                             "   Los robots no terminaron bien esta vez (falla pasajera del servicio).\n"
                             "   Espera un par de minutos y vuelve a correr el mismo comando.")
        raise FatalError(f"❌ No se encontró ningún video.\n"
                         f"   Lo más probable: el hashtag #{hashtag} casi no se usa.\n"
                         f"   Pídele a tu agente que lo intente con un hashtag más popular del mismo tema.")

    print("3) tirando la basura y puntuando viralidad…")
    for r in rows:
        r["interacciones"] = r["megusta"] + r["comentarios"] + r["compartidos"] + r["guardados"]
        r["tasa_interaccion"] = r["interacciones"] / r["vistas"] if r["vistas"] else 0
        ad = antiguedad_en_dias(r["publicado"])
        r["dias_publicado"] = ad
        r["vistas_por_dia"] = r["vistas"] / ad if ad else 0
        # vistas por seguidor: alto = el FORMATO ganó, no la fama del autor -> replicable.
        r["vistas_por_seguidor"] = round(r["vistas"] / r["seguidores"], 1) if r.get("seguidores") else None
        r["motivos_descarte"] = quality_check(r)
        r["paso_filtro"] = not r["motivos_descarte"]
    for plat in plats:
        grp = [r for r in rows if r["plataforma"] == plat and r["paso_filtro"]]
        if not grp:
            continue
        zv = zscores([math.log10(r["vistas"] + 1) for r in grp])
        zd = zscores([math.log10(r["vistas_por_dia"] + 1) for r in grp])
        ze = zscores([r["tasa_interaccion"] for r in grp])
        for r in grp:
            r["puntaje"] = round(0.35 * zv(math.log10(r["vistas"] + 1)) +
                                   0.30 * zd(math.log10(r["vistas_por_dia"] + 1)) +
                                   0.35 * ze(r["tasa_interaccion"]), 3)
    passed = [r for r in rows if r["paso_filtro"]]
    print(f"   pasaron el filtro: {len(passed)} / {len(rows)}")
    if not passed:
        raise FatalError(f"❌ Se encontraron {len(rows)} videos pero ninguno pasó el filtro de calidad\n"
                         f"   (todos eran fotos, anuncios, muy cortos o con muy pocas vistas).\n"
                         f"   Prueba con un hashtag más grande del mismo tema.")

    print("4) leyendo lo que se dice en cada video para quedarnos con contenido de verdad…")
    try:
        CACHE = json.load(open(f"{OUT}/transcripts.json", encoding="utf-8"))
    except Exception:
        CACHE = {}
    best = []
    api_fails, gate_total, sin_credito = 0, 0, 0
    for plat in plats:
        cands = sorted([r for r in passed if r["plataforma"] == plat],
                       key=lambda r: r.get("puntaje", 0), reverse=True)[:args.top]
        for r in cands:
            gate_total += 1
            if r["url"] in CACHE:
                t = CACHE[r["url"]]
            else:
                t = fetch_transcript(r["url"])
                if not es_fallo(t):
                    CACHE[r["url"]] = t
            err = es_fallo(t)
            words = re.findall(r"\w+", t.lower()) if not err else []
            n = len(words)
            wpm = (n / (r["duracion"] / 60)) if r.get("duracion") else None
            r["texto_hablado"] = t[:4000] if not err else ""
            r["palabras_dichas"] = n
            r["palabras_por_minuto"] = round(wpm, 1) if wpm else None
            if err and SUPADATA_KEY and t not in ("[sin-llave]",):
                api_fails += 1
                if t == "[fallo:429]":     # Supadata contesta 429 cuando se acaba el plan
                    sin_credito += 1
            # si Supadata falló (o no hay llave), el video pasa por score y
            # Claude lo clasifica/limpia después — un fallo de API no descarta
            # un video bueno.
            r["tiene_contenido"] = True if err else (n >= MIN_WORDS and (wpm is None or wpm >= MIN_WPM))
            if r["tiene_contenido"]:
                best.append(r)
    json.dump(CACHE, open(f"{OUT}/transcripts.json", "w", encoding="utf-8"), ensure_ascii=False)
    if api_fails:
        if sin_credito == api_fails:
            print(f"  ⚠ Se acabó tu crédito de Supadata: no pude leer el audio de {api_fails} de {gate_total} videos.")
            print(f"    Revisa tu plan en https://dash.supadata.ai/ — se renueva solo cada mes.")
        else:
            print(f"  ⚠ No se pudo leer el audio de {api_fails} de {gate_total} videos (límite o falla del servicio).")
        print(f"    Esos pasaron por puntaje y Claude los revisará al clasificar.")
    best.sort(key=lambda r: r["puntaje"], reverse=True)

    print("5) bajando las portadas (el gancho visual)…")
    got = download_thumbs(best, OUT)
    print(f"   {got} de {len(best)} portadas en {OUT}/thumbs/")

    json.dump(rows, open(f"{OUT}/all_scored.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    json.dump(best, open(f"{OUT}/best.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    meta = dict(nicho=args.niche, hashtag=hashtag, plataformas=plats,
                encontrados=len(rows), pasaron_filtro=len(passed), de_calidad=len(best),
                sin_audio_leido=api_fails, fecha=NOW.date().isoformat())
    json.dump(meta, open(f"{OUT}/meta.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if not best:
        # corrida vacía: ayudar a reintentar, NUNCA vender aquí.
        print(f"\n⚠ Ningún video pasó el filtro final (eran música o casi no hablaban).")
        print(f"   Los datos quedaron en {OUT}/all_scored.json por si quieres revisarlos.")
        print(f"   Pídele a tu agente que lo intente con otro hashtag o con más candidatos.")
        print(f"   resumen -> {OUT}/meta.json")
    else:
        print(f"\n✅ {len(best)} videos de CALIDAD -> {OUT}/best.json")
        print(f"   resumen -> {OUT}/meta.json")
        link = cta_url()
        if link:
            print()
            print("   Tu agente corre en tu computadora. Trabaja cuando tú lo abres.")
            print("   El que atiende a tus clientes trabaja aunque tú no estés:")
            print(f"   {link}")


def main():
    try:
        run()
    except FatalError as e:
        sys.exit(str(e))
    except SystemExit:
        raise
    except KeyboardInterrupt:
        sys.exit("\n⏹ Corrida cancelada.")
    except Exception:
        import traceback
        detail = "(no se pudo guardar el detalle)"
        try:
            os.makedirs("data", exist_ok=True)
            with open("data/error.txt", "w", encoding="utf-8") as f:
                f.write(traceback.format_exc())
            detail = "El detalle quedó en scripts/data/error.txt"
        except Exception:
            pass
        sys.exit("❌ Algo salió mal que no esperábamos.\n"
                 f"   {detail} — pídele a tu agente que lo lea y lo arregle.\n"
                 "   Luego vuelve a correr el comando.")


if __name__ == "__main__":
    main()
