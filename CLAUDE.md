# Notas para instalar este repositorio

Es una skill de Claude Code: un `SKILL.md` con las instrucciones del agente escritas en
español, más dos scripts de Python que solo usan la biblioteca estándar.

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
