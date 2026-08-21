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

# ---------------- credenciales ----------------
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


# ---------------- apify ----------------
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


# ---------------- normalización ----------------
# Cada plataforma entrega su JSON con nombres distintos. En vez de escribir tres
# veces el mismo dict a mano, aquí se declara DE DÓNDE sale cada dato y un solo
# extractor recorre la tabla. Agregar una plataforma = agregar una entrada.

def antiguedad_en_dias(marca_de_tiempo):
    """Días transcurridos desde que se publicó. Mínimo 0.1 para no dividir entre cero."""
    if not marca_de_tiempo:
        return None
    try:
        publicado = dt.datetime.fromisoformat(str(marca_de_tiempo).replace("Z", "+00:00"))
    except Exception:
        return None
    transcurrido = (NOW - publicado).total_seconds() / 86400
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
        "author":       lambda i: _anidado(i, "authorMeta", "name"),
        "caption":      lambda i: i.get("text") or "",
        "hashtags":     lambda i: lista_de_etiquetas(i.get("hashtags")),
        "views":        lambda i: i.get("playCount") or 0,
        "likes":        lambda i: i.get("diggCount") or 0,
        "comments":     lambda i: i.get("commentCount") or 0,
        "shares":       lambda i: i.get("shareCount") or 0,
        "saves":        lambda i: i.get("collectCount") or 0,
        "duration":     lambda i: _anidado(i, "videoMeta", "duration"),
        "created":      lambda i: i.get("createTimeISO"),
        "lang":         lambda i: i.get("textLanguage"),
        "is_slideshow": lambda i: bool(i.get("isSlideshow")),
        "is_muted":     lambda i: bool(i.get("isMuted")),
        "is_ad":        lambda i: bool(i.get("isAd") or i.get("isSponsored")),
        "thumb":        lambda i: _anidado(i, "videoMeta", "coverUrl"),
        "followers":    lambda i: _anidado(i, "authorMeta", "fans"),
        "music":        lambda i: describir_audio(i.get("musicMeta"), "musicName", "musicAuthor", "musicOriginal"),
    },
    "youtube": {
        "id":           lambda i: str(i.get("id")),
        "url":          lambda i: i.get("url"),
        "author":       lambda i: i.get("channelName"),
        # el título manda; se le pega un pedazo de la descripción como contexto
        "caption":      lambda i: (i.get("title") or "") + " — " + (i.get("text") or "")[:300],
        "hashtags":     lambda i: lista_de_etiquetas(i.get("hashtags")),
        "views":        lambda i: i.get("viewCount") or 0,
        "likes":        lambda i: i.get("likes") or 0,
        "comments":     lambda i: i.get("commentsCount") or 0,
        "shares":       lambda i: 0,      # YouTube no publica compartidos
        "saves":        lambda i: 0,      # ni guardados
        "duration":     lambda i: a_segundos(i.get("duration")),
        "created":      lambda i: i.get("date"),
        "lang":         lambda i: None,
        "is_slideshow": lambda i: False,
        "is_muted":     lambda i: False,
        "is_ad":        lambda i: bool(i.get("isPaidContent")),
        "thumb":        lambda i: i.get("thumbnailUrl"),
        "followers":    lambda i: i.get("numberOfSubscribers"),
        "music":        lambda i: None,
    },
    "instagram": {
        "id":           lambda i: str(i.get("id")),
        "url":          lambda i: i.get("url"),
        "author":       lambda i: i.get("ownerUsername"),
        "caption":      lambda i: i.get("caption") or "",
        "hashtags":     lambda i: lista_de_etiquetas(i.get("hashtags")),
        "views":        lambda i: i.get("videoPlayCount") or i.get("igPlayCount") or 0,
        "likes":        lambda i: i.get("likesCount") or 0,
        "comments":     lambda i: i.get("commentsCount") or 0,
        "shares":       lambda i: 0,
        "saves":        lambda i: 0,
        "duration":     lambda i: i.get("videoDuration"),
        "created":      lambda i: i.get("timestamp"),
        "lang":         lambda i: None,
        "is_slideshow": lambda i: i.get("type") != "Video",
        "is_muted":     lambda i: False,
        "is_ad":        lambda i: bool(i.get("paidPartnership") or i.get("isSponsored")),
        "thumb":        lambda i: i.get("displayUrl"),
        "followers":    lambda i: None,   # el buscador por hashtag de IG no trae seguidores
        "music":        lambda i: describir_audio(i.get("musicInfo"), "song_name", "artist_name", "uses_original_audio"),
    },
}


def norm(plat, it):
    """Traduce un item crudo de cualquier plataforma al formato interno común."""
    fila = {"platform": plat}
    for campo, sacar in MAPEO[plat].items():
        fila[campo] = sacar(it)
    return fila


MEME_MARKERS = {"meme", "memes", "funny", "comedy", "fail", "lol", "joke", "prank", "shitpost", "ratio"}
MIN_DURATION, MAX_DURATION, MIN_VIEWS = 8, 3600, 1000


def quality_check(r):
    reasons = []
    if r["is_slideshow"]: reasons.append("slideshow/foto")
    if r["is_muted"]: reasons.append("muted")
    if r["is_ad"]: reasons.append("ad")
    d = r["duration"]
    if d is not None and d < MIN_DURATION: reasons.append("muy_corto")
    if d is not None and d > MAX_DURATION: reasons.append("muy_largo")
    if r["views"] < MIN_VIEWS: reasons.append("low_reach")
    cap_no_tags = re.sub(r"#\w+", "", r["caption"]).strip()
    if not cap_no_tags and (MEME_MARKERS & set(r["hashtags"])):
        reasons.append("meme")
    return reasons


def zscores(vals):
    vals = [v for v in vals if v is not None]
    if len(vals) < 2:
        return lambda x: 0.0
    mu = statistics.mean(vals)
    sd = statistics.pstdev(vals) or 1.0
    return lambda x: (x - mu) / sd


# ---------------- supadata ----------------
def fetch_transcript(url):
    """Pide a Supadata lo que se habla en un video.

    Devuelve el texto, o una marca "__ERR__<motivo>" si no se pudo. Nunca lanza
    excepción: un video sin transcript no debe tumbar la corrida.
    """
    if not SUPADATA_KEY:
        return "__ERR__no_key"
    if not url:
        return "__ERR__no_url"
    consulta = urllib.parse.urlencode({"url": url, "text": "true"})
    peticion = urllib.request.Request(
        "https://api.supadata.ai/v1/transcript?" + consulta,
        headers={"x-api-key": SUPADATA_KEY, "User-Agent": UA},  # sin UA de navegador contesta 403
    )
    try:
        with urllib.request.urlopen(peticion, timeout=90) as respuesta:
            cuerpo = json.load(respuesta)
    except urllib.error.HTTPError as e:
        return f"__ERR__{e.code}"
    except Exception as e:
        return f"__ERR__{e}"
    contenido = cuerpo.get("content")
    if isinstance(contenido, str):
        return contenido
    if isinstance(contenido, list):      # a veces llega por fragmentos con tiempos
        return " ".join(fragmento.get("text", "") for fragmento in contenido)
    return ""


MIN_WORDS, MIN_WPM = 25, 40


# ---------------- portadas (el gancho visual) ----------------
def download_thumbs(best, outdir):
    """Baja la portada de cada video finalista (una foto, no el video).
    El agente las mira después para leer el gancho visual. Mejor esfuerzo:
    una portada caída nunca detiene la corrida."""
    tdir = os.path.join(outdir, "thumbs")
    os.makedirs(tdir, exist_ok=True)
    n = 0
    for r in best:
        u = r.get("thumb")
        r["thumb_file"] = None
        if not u:
            continue
        fname = os.path.join(tdir, f"{r['platform']}_{r['id']}.jpg")
        try:
            if not os.path.exists(fname):
                req = urllib.request.Request(u, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = resp.read()
                with open(fname, "wb") as f:
                    f.write(data)
            r["thumb_file"] = fname
            n += 1
        except Exception:
            pass
    return n


# ---------------- main ----------------
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
        r["engagement"] = r["likes"] + r["comments"] + r["shares"] + r["saves"]
        r["eng_rate"] = r["engagement"] / r["views"] if r["views"] else 0
        ad = antiguedad_en_dias(r["created"])
        r["age_days"] = ad
        r["views_per_day"] = r["views"] / ad if ad else 0
        # vistas por seguidor: alto = el FORMATO ganó, no la fama del autor -> replicable.
        r["reach_ratio"] = round(r["views"] / r["followers"], 1) if r.get("followers") else None
        r["reject_reasons"] = quality_check(r)
        r["passed_prefilter"] = not r["reject_reasons"]
    for plat in plats:
        grp = [r for r in rows if r["platform"] == plat and r["passed_prefilter"]]
        if not grp:
            continue
        zv = zscores([math.log10(r["views"] + 1) for r in grp])
        zd = zscores([math.log10(r["views_per_day"] + 1) for r in grp])
        ze = zscores([r["eng_rate"] for r in grp])
        for r in grp:
            r["vir_score"] = round(0.35 * zv(math.log10(r["views"] + 1)) +
                                   0.30 * zd(math.log10(r["views_per_day"] + 1)) +
                                   0.35 * ze(r["eng_rate"]), 3)
    passed = [r for r in rows if r["passed_prefilter"]]
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
        cands = sorted([r for r in passed if r["platform"] == plat],
                       key=lambda r: r.get("vir_score", 0), reverse=True)[:args.top]
        for r in cands:
            gate_total += 1
            if r["url"] in CACHE:
                t = CACHE[r["url"]]
            else:
                t = fetch_transcript(r["url"])
                if not t.startswith("__ERR__"):
                    CACHE[r["url"]] = t
            err = t.startswith("__ERR__")
            words = re.findall(r"\w+", t.lower()) if not err else []
            n = len(words)
            wpm = (n / (r["duration"] / 60)) if r.get("duration") else None
            r["transcript"] = t[:4000] if not err else ""
            r["transcript_words"] = n
            r["wpm"] = round(wpm, 1) if wpm else None
            if err and SUPADATA_KEY and t not in ("__ERR__no_key",):
                api_fails += 1
                if t == "__ERR__429":     # Supadata contesta 429 cuando se acaba el plan
                    sin_credito += 1
            # si Supadata falló (o no hay llave), el video pasa por score y
            # Claude lo clasifica/limpia después — un fallo de API no descarta
            # un video bueno.
            r["quality_pass"] = True if err else (n >= MIN_WORDS and (wpm is None or wpm >= MIN_WPM))
            if r["quality_pass"]:
                best.append(r)
    json.dump(CACHE, open(f"{OUT}/transcripts.json", "w", encoding="utf-8"), ensure_ascii=False)
    if api_fails:
        if sin_credito == api_fails:
            print(f"  ⚠ Se acabó tu crédito de Supadata: no pude leer el audio de {api_fails} de {gate_total} videos.")
            print(f"    Revisa tu plan en https://dash.supadata.ai/ — se renueva solo cada mes.")
        else:
            print(f"  ⚠ No se pudo leer el audio de {api_fails} de {gate_total} videos (límite o falla del servicio).")
        print(f"    Esos pasaron por puntaje y Claude los revisará al clasificar.")
    best.sort(key=lambda r: r["vir_score"], reverse=True)

    print("5) bajando las portadas (el gancho visual)…")
    got = download_thumbs(best, OUT)
    print(f"   {got} de {len(best)} portadas en {OUT}/thumbs/")

    json.dump(rows, open(f"{OUT}/all_scored.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    json.dump(best, open(f"{OUT}/best.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    meta = dict(niche=args.niche, hashtag=hashtag, platforms=plats, scraped=len(rows),
                passed_prefilter=len(passed), quality_videos=len(best),
                transcript_api_fails=api_fails, run_date=NOW.date().isoformat())
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
