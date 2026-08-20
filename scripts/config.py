#!/usr/bin/env python3
"""
Configuración del Agente Viral — ~/.agente-viral/config.json (permisos 600).

Las llaves se pasan por VARIABLE DE ENTORNO para no exponerlas en el
historial de la shell.

Comandos:
  python3 config.py show        # estado actual (llaves enmascaradas)
  python3 config.py check       # valida Apify + Supadata contra sus APIs
  APIFY_TOKEN=.. SUPADATA_API_KEY=.. python3 config.py set-keys
  python3 config.py set-notion --parent <id> --lista <ds> --ideas <ds> --analisis <ds>
  python3 config.py set-cta --url <link>
  python3 config.py get-cta
"""
import json, os, sys, urllib.request, urllib.error, argparse

DIR = os.path.expanduser("~/.agente-viral")
PATH = os.path.join(DIR, "config.json")
# Compatibilidad: si existe una config vieja de videos-virales, se lee como respaldo.
LEGACY_PATH = os.path.expanduser("~/.videos-virales/config.json")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

# El link del cierre (a dónde invita el agente al terminar). Se cambia UNA vez con set-cta.
DEFAULT_CTA_URL = "CAMBIA_ESTE_LINK"


def _read(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except Exception:
        print(f"⚠ El archivo {path} está dañado. Vuelve a guardar tus llaves con: config.py set-keys")
        return {}


def load():
    cfg = _read(PATH)
    if cfg:
        return cfg
    # respaldo: config vieja (solo lectura; al guardar se escribe en la ruta nueva)
    return _read(LEGACY_PATH)


def save(cfg):
    os.makedirs(DIR, exist_ok=True)
    tmp = PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    os.replace(tmp, PATH)  # escritura atómica: nunca queda un config a medias
    os.chmod(PATH, 0o600)


def mask(s):
    if not s:
        return "(falta)"
    return s[:4] + "…" + s[-4:] if len(s) > 10 else "••••"


def cmd_show():
    cfg = load()
    n = cfg.get("notion") or {}
    print(f"config: {PATH}")
    if not _read(PATH) and _read(LEGACY_PATH):
        print(f"  (leyendo respaldo de {LEGACY_PATH} — al guardar se migra aquí)")
    print(f"  apify_token:      {mask(cfg.get('apify_token'))}")
    print(f"  supadata_api_key: {mask(cfg.get('supadata_api_key'))}")
    print(f"  notion.parent:    {n.get('parent_page_id', '(falta)')}")
    print(f"  notion.lista:     {n.get('lista_ds', '(falta)')}")
    print(f"  notion.ideas:     {n.get('ideas_ds', '(falta)')}")
    print(f"  notion.analisis:  {n.get('analisis_ds', '(falta)')}")
    print(f"  cta_url:          {cfg.get('cta_url', DEFAULT_CTA_URL)}")
    ready = bool(cfg.get("apify_token") and n.get("lista_ds") and n.get("ideas_ds") and n.get("analisis_ds"))
    print(f"  LISTO PARA CORRER: {'sí' if ready else 'no — falta setup'}")


def cmd_set_keys():
    cfg = load()
    apify = os.environ.get("APIFY_TOKEN")
    supa = os.environ.get("SUPADATA_API_KEY")
    if apify:
        cfg["apify_token"] = apify.strip()
    if supa:
        cfg["supadata_api_key"] = supa.strip()
    save(cfg)
    print("✓ llaves guardadas en", PATH)
    if not apify:
        print("  (no se pasó APIFY_TOKEN)")
    if not supa:
        print("  (no se pasó SUPADATA_API_KEY)")


def cmd_set_notion(a):
    cfg = load()
    n = cfg.get("notion") or {}
    cfg["notion"] = n
    if a.parent:
        n["parent_page_id"] = a.parent
    if a.lista:
        n["lista_ds"] = a.lista
    if a.ideas:
        n["ideas_ds"] = a.ideas
    if a.analisis:
        n["analisis_ds"] = a.analisis
    save(cfg)
    print("✓ tablas de Notion guardadas en", PATH)


def cmd_set_cta(a):
    cfg = load()
    cfg["cta_url"] = a.url.strip()
    save(cfg)
    print("✓ link del cierre guardado:", cfg["cta_url"])


def cmd_get_cta():
    print(load().get("cta_url", DEFAULT_CTA_URL))


def cmd_check():
    cfg = load()
    ok = True
    # Apify
    t = os.environ.get("APIFY_TOKEN") or cfg.get("apify_token")
    if not t:
        print("✗ Apify: sin llave. Consíguela en https://console.apify.com/ → Settings → API & Integrations")
        ok = False
    else:
        try:
            req = urllib.request.Request(f"https://api.apify.com/v2/users/me?token={t}")
            with urllib.request.urlopen(req, timeout=20) as r:
                u = json.load(r)["data"]
            print(f"✓ Apify OK — usuario: {u.get('username')}")
        except Exception:
            print("✗ Apify: la llave no funciona. Revisa que la copiaste completa, sin espacios.")
            ok = False
    # Supadata
    k = os.environ.get("SUPADATA_API_KEY") or cfg.get("supadata_api_key")
    if not k:
        print("• Supadata: sin llave (opcional, pero recomendada — con ella el agente filtra mejor)")
    else:
        try:
            url = "https://api.supadata.ai/v1/transcript?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ&text=true"
            req = urllib.request.Request(url, headers={"x-api-key": k, "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                json.load(r)
            print("✓ Supadata OK")
        except urllib.error.HTTPError as e:
            if e.code in (402, 429):
                print("✓ Supadata: tu llave sí funciona. Solo se acabó el crédito del plan gratis por ahora — se renueva solo.")
            else:
                print(f"✗ Supadata: la llave no funciona (error {e.code}). Revisa que la copiaste completa.")
                ok = False
        except Exception:
            print("✗ Supadata: no se pudo conectar. Revisa tu internet y vuelve a intentar.")
            ok = False
    sys.exit(0 if ok else 1)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show")
    sub.add_parser("check")
    sub.add_parser("set-keys")
    sn = sub.add_parser("set-notion")
    sn.add_argument("--parent")
    sn.add_argument("--lista")
    sn.add_argument("--ideas")
    sn.add_argument("--analisis")
    sc = sub.add_parser("set-cta")
    sc.add_argument("--url", required=True)
    sub.add_parser("get-cta")
    a = ap.parse_args()
    if a.cmd == "show":
        cmd_show()
    elif a.cmd == "check":
        cmd_check()
    elif a.cmd == "set-keys":
        cmd_set_keys()
    elif a.cmd == "set-notion":
        cmd_set_notion(a)
    elif a.cmd == "set-cta":
        cmd_set_cta(a)
    elif a.cmd == "get-cta":
        cmd_get_cta()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except KeyboardInterrupt:
        sys.exit("\n⏹ Cancelado.")
    except Exception:
        sys.exit("❌ Algo salió mal guardando o leyendo tu configuración.\n"
                 "   Revisa que la carpeta ~/.agente-viral no esté bloqueada y vuelve a intentar.")
