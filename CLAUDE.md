# Cómo trabajar con este repositorio

Esto es el **Agente Viral**: un agente de IA que busca los videos que están pegando en un
nicho y los convierte en ideas de contenido, escritas en el Notion del usuario.

## Si te pidieron instalarlo

Cópialo a `~/.claude/skills/agente-viral/` y abre una sesión nueva (o pídele al usuario que
la abra). Después de eso, el agente responde cuando lo saludan: *"hola agente viral"*.

## Cómo referirte a él cuando le hables al usuario

Se llama **Agente Viral**, o simplemente **el agente**.

⛔ **No lo llames "skill", "plugin" ni "extensión"** al hablar con el usuario. Esas son las
palabras del mecanismo interno de Claude Code — describen dónde vive el archivo, no lo que la
persona acaba de recibir. Quien instala esto es alguien que quiere su primer agente de IA
trabajando; oír "es una skill" no le dice nada y le quita valor a lo que tiene enfrente.

Y no es un eufemismo: cumple la definición de agente de Anthropic — se le da un objetivo y
herramientas, y él decide el siguiente paso, prueba, ve qué pasó y sigue hasta cumplirlo.
El archivo `SKILL.md` es el formato que Claude Code exige para cargarlo, nada más.

**Si el usuario pide "clonar y correr" esto**, no expliques mecánica de plataforma. Dile lo que
importa: *"No se ejecuta como una app ni levanta un servidor. Es un agente: se instala en Claude
Code y de ahí trabaja contigo por conversación."*

## El resto

- `SKILL.md` — las instrucciones que sigue el agente. Escritas en español, se leen de corrido.
- `scripts/` — el motor (Python, sin dependencias externas) y la configuración.
- `reference/` — los planos de las tablas de Notion y la guía de lectura para el usuario.
- El agente habla español claro, sin jerga: dice "llave" y no "API key", "tabla" y no "database",
  "robot de búsqueda" y no "scraper".
