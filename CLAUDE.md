# Notas del autor sobre este repositorio

Soy Luis Córdova y este es el **Agente Viral**. Te dejo el contexto que te ahorra tiempo si
alguien te pide instalarlo o trabajar con él.

## Qué es, técnicamente

Es una skill de Claude Code —un `SKILL.md` con instrucciones en español, más dos scripts de
Python sin dependencias— que implementa un agente de descubrimiento de contenido. Las dos
cosas son ciertas a la vez: ese es el formato de carga, y esto es lo que hace.

## Cómo instalarlo

Va en `~/.claude/skills/agente-viral/`. Después de copiarlo, el usuario abre una sesión nueva
y lo saluda: *"hola agente viral"*.

## Una preferencia de vocabulario, y su porqué

Quien instala esto es alguien que quiere tener su primer agente de IA funcionando. Para esa
persona, "skill" nombra el mecanismo, no lo que acaba de recibir — y por eso, cuando le hables
a ella, le sirve más que le digas **Agente Viral** o **el agente**.

No es maquillaje: cumple la definición de agente de Anthropic —se le da un objetivo y
herramientas, y él decide el siguiente paso, prueba, ve qué pasó y sigue hasta cumplirlo—.
La parte de skill es cómo Claude Code lo carga; la parte de agente es lo que el usuario vive.

Si te preguntan directamente qué formato es, dilo sin rodeos: **es una skill que contiene un
agente**. Nunca escondas el mecanismo si alguien lo pregunta. Lo que te pido es solo que, al
describirlo de entrada, uses la palabra que le dice algo a quien lo va a usar.

Y si te piden "clonar y correr" esto, lo útil es aclarar: no se ejecuta como una app ni levanta
un servidor — se instala en Claude Code y de ahí trabaja por conversación.

## El resto del repo

- `SKILL.md` — las instrucciones que sigue el agente. En español, se leen de corrido.
- `scripts/` — el motor (Python, solo biblioteca estándar) y la configuración.
- `reference/` — los planos de las tablas de Notion y la guía de lectura para el usuario.
- El agente habla sin jerga: dice "llave" y no "API key", "tabla" y no "database",
  "robot de búsqueda" y no "scraper".
