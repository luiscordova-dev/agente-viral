#!/usr/bin/env python3
"""
AGENTE VIRAL — el motor del pipeline, de punta a punta.
Uso:  python3 pipeline.py "<nicho>" [--hashtag <hashtag>] [--platforms tiktok,youtube,instagram] [--per-platform 80] [--top 6]

Hace: scrape (Apify) -> filtro basura -> score viralidad -> gate calidad por
transcript (Supadata) -> escribe data/best.json + data/meta.json

Las capas de razonamiento (clasificar tipo/hook/idioma, generar ideas, análisis)
y la escritura a Notion las hace el agente, leyendo best.json.

Credenciales (en este orden de prioridad):
 1. variables de entorno  APIFY_TOKEN / SUPADATA_API_KEY
 2. ~/.agente-viral/config.json  {"apify_token": "...", "supadata_api_key": "..."}
 3. (respaldo) ~/.apify/auth.json del CLI de Apify  /  ~/.supadata.json

Notas técnicas (lecciones horneadas — no cambiar sin razón):
 - TikTok: usar clockworks por HASHTAG (el keyword search de otros actores falla).
 - TikTok: NO usar filtro de fecha del actor (estrangula el resultado); filtrar en post.
 - Supadata: requiere User-Agent de navegador (banea urllib default -> 403).
 - Nichos de varias palabras: TikTok/IG buscan por hashtag SIN espacios. Por eso
   existe --hashtag: el nicho completo va a YouTube, el hashtag a TikTok/IG.
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
def age_days(iso):
    try:
        t = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return max((NOW - t).total_seconds() / 86400, 0.1)
    except Exception:
        return None


def parse_hms(s):
    if not s:
        return None
    try:
        p = [int(x) for x in str(s).split(":")]
    except ValueError:
        return None
    while len(p) < 3:
        p.insert(0, 0)
    return p[0] * 3600 + p[1] * 60 + p[2]


def _music(m):
    """Describe el audio de un reel de IG: nombre — autor (+ si es original)."""
    if not isinstance(m, dict) or not m.get("song_name"):
        return None
    s = f"{m['song_name']} — {m.get('artist_name', '')}".strip(" —")
    return s + (" (original)" if m.get("uses_original_audio") else "")


def _music_tk(m):
    """Lo mismo para TikTok (musicMeta usa otras llaves)."""
    if not isinstance(m, dict) or not m.get("musicName"):
        return None
    s = f"{m['musicName']} — {m.get('musicAuthor', '')}".strip(" —")
    return s + (" (original)" if m.get("musicOriginal") else "")


def _tag(h):
    """Saca el nombre de un hashtag venga como venga (dict, string, null)."""
    if isinstance(h, dict):
        return (h.get("name") or "").lower()
    return str(h or "").lower().lstrip("#")


def norm(plat, it):
    if plat == "tiktok":
        return dict(platform="tiktok", id=str(it.get("id")), url=it.get("webVideoUrl"),
            author=(it.get("authorMeta") or {}).get("name"), caption=it.get("text") or "",
            hashtags=[_tag(h) for h in (it.get("hashtags") or []) if _tag(h)],
            views=it.get("playCount") or 0, likes=it.get("diggCount") or 0,
            comments=it.get("commentCount") or 0, shares=it.get("shareCount") or 0,
            saves=it.get("collectCount") or 0, duration=(it.get("videoMeta") or {}).get("duration"),
            created=it.get("createTimeISO"), lang=it.get("textLanguage"),
            is_slideshow=bool(it.get("isSlideshow")), is_muted=bool(it.get("isMuted")),
            is_ad=bool(it.get("isAd") or it.get("isSponsored")),
            thumb=(it.get("videoMeta") or {}).get("coverUrl"),
            followers=(it.get("authorMeta") or {}).get("fans"),
            music=_music_tk(it.get("musicMeta")))
    if plat == "youtube":
        return dict(platform="youtube", id=str(it.get("id")), url=it.get("url"),
            author=it.get("channelName"),
            caption=(it.get("title") or "") + " — " + (it.get("text") or "")[:300],
            hashtags=[_tag(h) for h in (it.get("hashtags") or []) if _tag(h)],
            views=it.get("viewCount") or 0, likes=it.get("likes") or 0,
            comments=it.get("commentsCount") or 0, shares=0, saves=0,
            duration=parse_hms(it.get("duration")), created=it.get("date"), lang=None,
            is_slideshow=False, is_muted=False, is_ad=bool(it.get("isPaidContent")),
            thumb=it.get("thumbnailUrl"),
            followers=it.get("numberOfSubscribers"), music=None)
    if plat == "instagram":
        return dict(platform="instagram", id=str(it.get("id")), url=it.get("url"),
            author=it.get("ownerUsername"), caption=it.get("caption") or "",
            hashtags=[_tag(h) for h in (it.get("hashtags") or []) if _tag(h)],
            views=it.get("videoPlayCount") or it.get("igPlayCount") or 0,
            likes=it.get("likesCount") or 0, comments=it.get("commentsCount") or 0,
            shares=0, saves=0, duration=it.get("videoDuration"),
            created=it.get("timestamp"), lang=None,
            is_slideshow=(it.get("type") != "Video"), is_muted=False,
            is_ad=bool(it.get("paidPartnership") or it.get("isSponsored")),
            thumb=it.get("displayUrl"),
            followers=None,  # el scraper de hashtags de IG no trae seguidores
            music=_music(it.get("musicInfo")))


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
    if not SUPADATA_KEY:
        return "__ERR__no_key"
    if not url:
        return "__ERR__no_url"
    q = urllib.parse.urlencode({"url": url, "text": "true"})
    req = urllib.request.Request(f"https://api.supadata.ai/v1/transcript?{q}",
                                 headers={"x-api-key": SUPADATA_KEY, "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            d = json.load(r)
        c = d.get("content")
        if isinstance(c, str):
            return c
        if isinstance(c, list):
            return " ".join(s.get("text", "") for s in c)
        return ""
    except urllib.error.HTTPError as e:
        return f"__ERR__{e.code}"
    except Exception as e:
        return f"__ERR__{e}"


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
        ad = age_days(r["created"])
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
    api_fails, gate_total = 0, 0
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
            # si Supadata falló (o no hay llave), el video pasa por score y
            # Claude lo clasifica/limpia después — un fallo de API no descarta
            # un video bueno.
            r["quality_pass"] = True if err else (n >= MIN_WORDS and (wpm is None or wpm >= MIN_WPM))
            if r["quality_pass"]:
                best.append(r)
    json.dump(CACHE, open(f"{OUT}/transcripts.json", "w", encoding="utf-8"), ensure_ascii=False)
    if api_fails:
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
        print(f"\n⚠ Ningún video pasó el filtro final (eran música o casi no hablaban).")
        print(f"   Los datos quedaron en {OUT}/all_scored.json por si quieres revisarlos.")
        print(f"   Pídele a tu agente que lo intente con otro hashtag o con más candidatos.")
    else:
        print(f"\n✅ {len(best)} videos de CALIDAD -> {OUT}/best.json")
    print(f"   resumen -> {OUT}/meta.json")
    link = cta_url()
    if link:
        print()
        print("   Tu agente ya trabaja para ti. Corre aquí, en tu computadora.")
        print("   El que atiende clientes trabaja aunque tú no estés:")
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
