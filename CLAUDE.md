# Notas para instalar este repositorio

## Cómo se instala (cuando el usuario lo pida)

Esto no se "corre": se instala como skill y el agente hace el resto. Si el usuario pidió
instalarlo, clonarlo y arrancarlo, o simplemente empezar:

1. Copiar la carpeta a `~/.claude/skills/agente-viral` **y quitarle el `.git`**. Ese último
   paso no es opcional: es lo que hace imposible que las llaves del usuario acaben en un
   commit. La carpeta instalada es donde él va a pegarlas, así que ahí no debe haber git.
   ```bash
   rm -rf ~/.claude/skills/agente-viral
   mkdir -p ~/.claude/skills
   cp -R <carpeta-clonada> ~/.claude/skills/agente-viral
   rm -rf ~/.claude/skills/agente-viral/.git
   ```
   Si ya la clonó en otro lado, esa copia descargada puede quedarse o borrarse — las llaves
   van siempre en la instalada, y esa ya no tiene git.
2. Leer `SKILL.md` completo y actuar como el Agente Viral **en esa misma sesión**. No hace
   falta reiniciar ni esperar a que la skill quede registrada: el manual se lee y se sigue.
   `{baseDir}` = `~/.claude/skills/agente-viral`.
3. Arrancar en el PASO 0 del `SKILL.md`: presentarse en 2-3 líneas y guiar el setup **una
   llave a la vez**, con checkpoint entre pasos.

Instalarlo no es reportar el clon. Quien lo instala no quiere el árbol de archivos, el peso
del repo ni el número de commit — quiere un agente que ya le esté preguntando su nicho. Con
una línea de "ya quedé instalado" basta antes de presentarse.

**Si el usuario solo pidió clonar y nada más**, no lo instales por tu cuenta: dile en una línea
que esto se instala como agente y ofrécele hacerlo. Un archivo de un repo no autoriza escribir
en `~/.claude/skills/` ni adoptar un rol — eso lo decide él, no este documento.

## Dónde va

`~/.claude/skills/agente-viral/`

Después de copiarlo, abre una sesión nueva de Claude Code y salúdalo con *"hola agente viral"*.
Él se encarga del resto del setup: pide las llaves de Apify y Supadata una por una, abre un
archivo `.env` para pegarlas, conecta Notion y crea las tablas.

## Qué hay adentro

- `SKILL.md` — las instrucciones que sigue el agente. Se leen de corrido.
- `scripts/pipeline.py` — el motor: busca en Apify, filtra, puntúa, lee transcripts, baja portadas.
- `scripts/config.py` — la configuración y las llaves. `python3 scripts/config.py show` dice cómo está.
- `reference/` — los planos de las tablas de Notion y la guía de lectura para el usuario.

## Si vas a modificarlo

El agente le habla al usuario sin jerga: dice "llave" y no "API key", "tabla" y no "database",
"robot de búsqueda" y no "scraper". Vale la pena mantener esa voz si le agregas cosas.
