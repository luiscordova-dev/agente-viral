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
  python3 config.py guia         # la guía de lectura, ya con el link puesto
  python3 config.py set-negocio --que-hace "..." --a-quien "..." --objetivo "..."
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


def mask(llave):
    """Deja ver solo las puntas de una llave, lo justo para reconocerla sin exponerla.
    Si es tan corta que las puntas la delatarían, se tapa entera."""
    if not llave:
        return "(falta)"
    if len(llave) <= 10:
        return "••••"
    return llave[:4] + "…" + llave[-4:]


def cmd_show():
    """Imprime el estado de la configuración, con las llaves tapadas."""
    cfg = load()
    notion = cfg.get("notion") or {}

    print(f"config: {PATH}")
    renglones = [
        ("apify_token:     ", mask(cfg.get("apify_token"))),
        ("supadata_api_key:", mask(cfg.get("supadata_api_key"))),
        ("notion.parent:   ", notion.get("parent_page_id", "(falta)")),
        ("notion.lista:    ", notion.get("lista_ds", "(falta)")),
        ("notion.ideas:    ", notion.get("ideas_ds", "(falta)")),
        ("notion.analisis: ", notion.get("analisis_ds", "(falta)")),
        ("cta_url:         ", cfg.get("cta_url", DEFAULT_CTA_URL)),
    ]
    for etiqueta, valor in renglones:
        print(f"  {etiqueta} {valor}")

    negocio = cfg.get("negocio") or {}
    if negocio:
        print("  perfil del negocio:")
        for llave, como_se_lee in (("que_hace", "a qué se dedica"),
                                   ("a_quien", "a quién le habla"),
                                   ("objetivo", "qué quiere lograr")):
            if negocio.get(llave):
                print(f"    {como_se_lee}: {negocio[llave]}")
    else:
        print("  perfil del negocio: (falta — las ideas saldrán genéricas)")

    puede_correr = bool(cfg.get("apify_token") and notion.get("lista_ds")
                        and notion.get("ideas_ds") and notion.get("analisis_ds"))
    print(f"  LISTO PARA CORRER: {'sí' if puede_correr else 'no — falta setup'}")


def cmd_init_env():
    if os.path.exists(ENV_PATH):
        print(f"✓ el archivo .env ya existe: {ENV_PATH}")
    else:
        with open(ENV_PATH, "w", encoding="utf-8") as f:
            f.write(ENV_TEMPLATE)
        print(f"✓ archivo .env creado: {ENV_PATH}")
    print("  Pega tus llaves entre las comillas, guarda, y corre: python3 config.py set-keys")


def cmd_set_keys():
    """Importa las llaves del .env (o de variables de entorno) y limpia el archivo."""
    cfg = load()
    del_env, sobrantes = read_env_file()
    # la variable de entorno gana sobre el archivo
    hallazgos = {
        "apify_token": os.environ.get("APIFY_TOKEN") or del_env.get("APIFY_TOKEN"),
        "supadata_api_key": os.environ.get("SUPADATA_API_KEY") or del_env.get("SUPADATA_API_KEY"),
    }
    if not any(hallazgos.values()):
        sys.exit("✗ No encontré ninguna llave que guardar.\n"
                 "  Pega tu llave en el archivo .env (entre las comillas), guarda el archivo,\n"
                 "  y vuelve a correr: python3 config.py set-keys\n"
                 "  (Si no tienes el archivo: python3 config.py init-env)")
    for campo, valor in hallazgos.items():
        if valor:
            cfg[campo] = valor.strip()
    save(cfg)
    print("✓ llaves guardadas en", PATH)
    if not hallazgos["apify_token"]:
        print("  (falta APIFY_TOKEN — pégala en el archivo .env y vuelve a correr set-keys)")
    if not hallazgos["supadata_api_key"]:
        print("  (falta SUPADATA_API_KEY — opcional)")
    if del_env:
        if sobrantes:
            print(f"⚠ El .env trae líneas que no reconocí ({', '.join(sobrantes)}). No lo limpié — revísalo tú.")
        elif clean_env_file():
            print("✓ limpié el archivo .env — tus llaves ya viven seguras en", DIR)
        else:
            print("⚠ No pude limpiar el .env — borra tú las llaves de ese archivo.")


def cmd_set_notion(a):
    """Guarda los identificadores de las 3 tablas y de la página que las contiene."""
    cfg = load()
    notion = cfg.get("notion") or {}
    cfg["notion"] = notion
    for bandera, campo in (("parent", "parent_page_id"), ("lista", "lista_ds"),
                           ("ideas", "ideas_ds"), ("analisis", "analisis_ds")):
        valor = getattr(a, bandera, None)
        if valor:
            notion[campo] = valor
    save(cfg)
    print("✓ tablas de Notion guardadas en", PATH)


def cmd_set_negocio(a):
    cfg = load()
    neg = cfg.get("negocio") or {}
    cfg["negocio"] = neg
    if a.que_hace:
        neg["que_hace"] = a.que_hace.strip()
    if a.a_quien:
        neg["a_quien"] = a.a_quien.strip()
    if a.objetivo:
        neg["objetivo"] = a.objetivo.strip()
    save(cfg)
    print("✓ perfil del negocio guardado. Tus ideas ahora salen a tu medida.")


def cmd_set_cta(a):
    cfg = load()
    cfg["cta_url"] = a.url.strip()
    save(cfg)
    print("✓ link del cierre guardado:", cfg["cta_url"])


def cmd_guia():
    """Imprime la guía de lectura de las tablas con el link ya sustituido.
    Así el agente la pega tal cual en Notion y el placeholder nunca sobrevive."""
    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "reference", "guia_lectura.md")
    try:
        texto = open(ruta, encoding="utf-8").read()
    except Exception:
        sys.exit(f"✗ No encontré la guía en {ruta}")
    link = load().get("cta_url", DEFAULT_CTA_URL)
    texto = texto.replace("{CTA_URL}", link)
    if "{CTA_URL}" in texto:
        sys.exit("✗ No pude sustituir el link en la guía.")
    print(texto)


def cmd_get_cta():
    print(load().get("cta_url", DEFAULT_CTA_URL))


def _probar_apify(llave):
    """Le pregunta a Apify quién es el dueño de la llave. Devuelve (ok, mensaje)."""
    if not llave:
        return False, "✗ Apify: sin llave. Consíguela en https://console.apify.com/ → Settings → API & Integrations"
    peticion = urllib.request.Request("https://api.apify.com/v2/users/me",
                                      headers={"Authorization": f"Bearer {llave}"})
    try:
        with urllib.request.urlopen(peticion, timeout=20) as respuesta:
            quien = json.load(respuesta)["data"]
        return True, f"✓ Apify OK — usuario: {quien.get('username')}"
    except urllib.error.HTTPError:
        return False, "✗ Apify: la llave no funciona. Revisa que la copiaste completa, sin espacios."
    except Exception:
        return False, "✗ Apify: no se pudo conectar. Revisa tu internet y vuelve a intentar."


def _probar_supadata(llave):
    """Pide el texto de un video conocido. Si contesta 402 o 429, la llave sirve
    pero el plan está topado — eso cuenta como buena. Devuelve (ok, mensaje)."""
    if not llave:
        return True, "• Supadata: sin llave (opcional, pero recomendada — con ella el agente filtra mejor)"
    # Cualquier video público sirve para saber si la llave autentica.
    # Se usa uno de la charla de presentación de Python, que lleva años en línea.
    sonda = "https://www.youtube.com/watch?v=YYXdXT2l-Gg"
    peticion = urllib.request.Request(
        f"https://api.supadata.ai/v1/transcript?url={sonda}&text=true",
        headers={"x-api-key": llave, "User-Agent": UA})
    try:
        with urllib.request.urlopen(peticion, timeout=30) as respuesta:
            json.load(respuesta)
        return True, "✓ Supadata OK"
    except urllib.error.HTTPError as e:
        if e.code in (402, 429):
            return True, "✓ Supadata: tu llave sí funciona. Solo se acabó el crédito de tu plan por ahora — revísalo en https://dash.supadata.ai/"
        return False, f"✗ Supadata: la llave no funciona (error {e.code}). Revisa que la copiaste completa."
    except Exception:
        return False, "✗ Supadata: no se pudo conectar. Revisa tu internet y vuelve a intentar."


def cmd_check():
    """Prueba cada llave contra su servicio de verdad y reporta una línea por cada una."""
    cfg = load()
    sondas = [
        (_probar_apify, os.environ.get("APIFY_TOKEN") or cfg.get("apify_token")),
        (_probar_supadata, os.environ.get("SUPADATA_API_KEY") or cfg.get("supadata_api_key")),
    ]
    todo_bien = True
    for probar, llave in sondas:
        sirve, mensaje = probar(llave)
        print(mensaje)
        todo_bien = todo_bien and sirve
    sys.exit(0 if todo_bien else 1)


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
    sg = sub.add_parser("set-negocio")
    sg.add_argument("--que-hace", dest="que_hace")
    sg.add_argument("--a-quien", dest="a_quien")
    sg.add_argument("--objetivo")
    sc = sub.add_parser("set-cta")
    sc.add_argument("--url", required=True)
    sub.add_parser("get-cta")
    sub.add_parser("guia")
    argumentos = ap.parse_args()
    SIN_ARGUMENTOS = {"show": cmd_show, "check": cmd_check, "init-env": cmd_init_env,
                      "set-keys": cmd_set_keys, "get-cta": cmd_get_cta, "guia": cmd_guia}
    CON_ARGUMENTOS = {"set-notion": cmd_set_notion, "set-cta": cmd_set_cta,
                      "set-negocio": cmd_set_negocio}
    if argumentos.cmd in SIN_ARGUMENTOS:
        SIN_ARGUMENTOS[argumentos.cmd]()
    else:
        CON_ARGUMENTOS[argumentos.cmd](argumentos)


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
