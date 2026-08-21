#!/usr/bin/env python3
"""
Configuración del Agente Viral — ~/.agente-viral/config.json (permisos 600).

El flujo de llaves: el usuario las pega en el archivo .env de la raíz del repo
(creado con `init-env`), y `set-keys` las importa a ~/.agente-viral/ y limpia
el .env. Alternativa: pasarlas por VARIABLE DE ENTORNO (nunca como argumento).
Lo ideal es que el agente (Claude) corra estos comandos por ti; si tecleas tú
un comando con la llave pegada, la línea queda en el historial de tu shell.

Comandos:
  python3 config.py show        # estado actual (llaves enmascaradas)
  python3 config.py check       # valida Apify + Supadata contra sus APIs
  python3 config.py init-env    # crea el archivo .env para pegar las llaves
  python3 config.py set-keys    # importa las llaves del .env (o de variables de entorno)
  python3 config.py set-notion --parent <id> --lista <ds> --ideas <ds> --analisis <ds>
  python3 config.py set-cta --url <link>
  python3 config.py get-cta
"""
import json, os, sys, urllib.request, urllib.error, argparse

DIR = os.path.expanduser("~/.agente-viral")
PATH = os.path.join(DIR, "config.json")
# El .env en la raíz del repo: la puerta de entrada para pegar las llaves sin chat.
ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")

# La plantilla vive AQUÍ (no depende de ningún archivo externo).
ENV_TEMPLATE = '''# 🔑 Pega tus llaves entre las comillas y guarda este archivo.
#
# Este archivo vive solo en tu computadora. Nunca se sube a ningún lado.
# Cuando tu agente guarde las llaves en su lugar seguro, va a limpiar este archivo.

# Tu llave de Apify (allá le llaman "Personal API token")
# Se copia en: https://console.apify.com/settings/integrations
APIFY_TOKEN=""

# Tu llave de Supadata (allá le llaman "API key")
# Se copia en: https://dash.supadata.ai/ → API Keys
SUPADATA_API_KEY=""
'''

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

# El link del cierre (a dónde invita el agente al terminar). Se cambia con set-cta.
DEFAULT_CTA_URL = "https://luma.com/user/luiscordova_ia"


def read_env_file():
    """Lee el .env de la raíz del repo. Devuelve (llaves reconocidas, líneas sin reconocer)."""
    keys, leftovers = {}, []
    try:
        for line in open(ENV_PATH, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):  # por si copian de un tutorial
                line = line[7:]
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip()
            if v and not (v.startswith('"') or v.startswith("'")):
                v = v.split("#", 1)[0].strip()  # comentario en la misma línea
            v = v.strip('"').strip("'").strip()
            if not v:
                continue
            if k in ("APIFY_TOKEN", "SUPADATA_API_KEY"):
                keys[k] = v
            else:
                leftovers.append(k)
    except FileNotFoundError:
        pass
    except Exception:
        print(f"⚠ No pude leer {ENV_PATH}. Revisa que sea texto plano.")
    return keys, leftovers


def clean_env_file():
    """Regresa el .env a su plantilla vacía (las llaves ya viven seguras en config)."""
    try:
        with open(ENV_PATH, "w", encoding="utf-8") as f:
            f.write(ENV_TEMPLATE)
        return True
    except Exception:
        return False


def _read(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except Exception:
        print(f"⚠ El archivo {path} está dañado. Vuelve a guardar tus llaves con: config.py set-keys")
        return {}


def legacy_cli_keys():
    """Si ya usas el CLI de Apify (`apify login`) o dejaste la llave de Supadata
    a mano, las tomamos de ahí — así no tienes que sacarlas otra vez."""
    keys = {}
    try:
        t = json.load(open(os.path.expanduser("~/.apify/auth.json"), encoding="utf-8")).get("token")
        if t:
            keys["apify_token"] = t
    except Exception:
        pass
    try:
        k = json.load(open(os.path.expanduser("~/.supadata.json"), encoding="utf-8")).get("api_key")
        if k:
            keys["supadata_api_key"] = k
    except Exception:
        pass
    return keys


def load():
    cfg = _read(PATH)
    for k, v in legacy_cli_keys().items():  # relleno: llaves del CLI, solo si faltan
        cfg.setdefault(k, v)
    return cfg


def save(cfg):
    os.makedirs(DIR, exist_ok=True)
    os.chmod(DIR, 0o700)  # carpeta solo para el dueño
    tmp = PATH + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)  # nace con permisos cerrados
    with os.fdopen(fd, "w", encoding="utf-8") as f:
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
    print(f"  apify_token:      {mask(cfg.get('apify_token'))}")
    print(f"  supadata_api_key: {mask(cfg.get('supadata_api_key'))}")
    print(f"  notion.parent:    {n.get('parent_page_id', '(falta)')}")
    print(f"  notion.lista:     {n.get('lista_ds', '(falta)')}")
    print(f"  notion.ideas:     {n.get('ideas_ds', '(falta)')}")
    print(f"  notion.analisis:  {n.get('analisis_ds', '(falta)')}")
    print(f"  cta_url:          {cfg.get('cta_url', DEFAULT_CTA_URL)}")
    ready = bool(cfg.get("apify_token") and n.get("lista_ds") and n.get("ideas_ds") and n.get("analisis_ds"))
    print(f"  LISTO PARA CORRER: {'sí' if ready else 'no — falta setup'}")


def cmd_init_env():
    if os.path.exists(ENV_PATH):
        print(f"✓ el archivo .env ya existe: {ENV_PATH}")
    else:
        with open(ENV_PATH, "w", encoding="utf-8") as f:
            f.write(ENV_TEMPLATE)
        print(f"✓ archivo .env creado: {ENV_PATH}")
    print("  Pega tus llaves entre las comillas, guarda, y corre: python3 config.py set-keys")


def cmd_set_keys():
    cfg = load()
    env_keys, leftovers = read_env_file()
    # prioridad: variable de entorno > archivo .env
    apify = os.environ.get("APIFY_TOKEN") or env_keys.get("APIFY_TOKEN")
    supa = os.environ.get("SUPADATA_API_KEY") or env_keys.get("SUPADATA_API_KEY")
    if not apify and not supa:
        sys.exit("✗ No encontré ninguna llave que guardar.\n"
                 "  Pega tu llave en el archivo .env (entre las comillas), guarda el archivo,\n"
                 "  y vuelve a correr: python3 config.py set-keys\n"
                 "  (Si no tienes el archivo: python3 config.py init-env)")
    if apify:
        cfg["apify_token"] = apify.strip()
    if supa:
        cfg["supadata_api_key"] = supa.strip()
    save(cfg)
    print("✓ llaves guardadas en", PATH)
    if not apify:
        print("  (falta APIFY_TOKEN — pégala en el archivo .env y vuelve a correr set-keys)")
    if not supa:
        print("  (falta SUPADATA_API_KEY — opcional)")
    if env_keys:
        if leftovers:
            print(f"⚠ El .env trae líneas que no reconocí ({', '.join(leftovers)}). No lo limpié — revísalo tú.")
        elif clean_env_file():
            print("✓ limpié el archivo .env — tus llaves ya viven seguras en", DIR)
        else:
            print("⚠ No pude limpiar el .env — borra tú las llaves de ese archivo.")


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
            req = urllib.request.Request("https://api.apify.com/v2/users/me",
                                         headers={"Authorization": f"Bearer {t}"})
            with urllib.request.urlopen(req, timeout=20) as r:
                u = json.load(r)["data"]
            print(f"✓ Apify OK — usuario: {u.get('username')}")
        except urllib.error.HTTPError:
            print("✗ Apify: la llave no funciona. Revisa que la copiaste completa, sin espacios.")
            ok = False
        except Exception:
            print("✗ Apify: no se pudo conectar. Revisa tu internet y vuelve a intentar.")
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
                print("✓ Supadata: tu llave sí funciona. Solo se acabó el crédito de tu plan por ahora — revísalo en https://dash.supadata.ai/")
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
    sub.add_parser("init-env")
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
    elif a.cmd == "init-env":
        cmd_init_env()
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
