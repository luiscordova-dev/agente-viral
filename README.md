# 🤖 Agente Viral — tu primer agente en 20 minutos

Un agente de IA que trabaja en tu computadora. Le dices un nicho — cocina, finanzas, skincare, el que sea — y él solo:

1. **Busca** los videos virales de ese nicho en TikTok, YouTube e Instagram.
2. **Tira la basura**: memes, anuncios, clips de pura música.
3. **Lee lo que se dice** en cada video para quedarse con contenido de verdad.
4. **Te deja 3 tablas en tu Notion**: los virales con sus números, ideas adaptadas a tu canal (o al de tu cliente), y el análisis de qué está funcionando.

Necesitas Claude Code ya instalado — el Roadmap que te trajo aquí lo deja listo. ¿Llegaste directo a este repo? Instala Claude Code primero: [claude.com/claude-code](https://claude.com/claude-code).

## Instálalo (1 comando y un saludo)

```bash
git clone https://github.com/luiscordova-dev/agente-viral ~/.claude/skills/agente-viral
```

Abre una sesión nueva de Claude Code y salúdalo:

```
hola agente viral
```

Él se presenta y te lleva de la mano. Te dice exactamente dónde sacar cada llave. Te abre un archivo donde las pegas — nunca van en el chat. Revisa que funcionen. Y crea tus tablas de Notion solo. Eso se hace una sola vez — después, cada corrida es escribir una frase.

> Si el comando te dice que la carpeta ya existe, bórrala con `rm -rf ~/.claude/skills/agente-viral` y repítelo.

## Lo que necesitas (son 3 cuentas, las 3 gratis)

| Cuenta | Para qué | Costo |
|---|---|---|
| [Apify](https://console.apify.com/) | Corre los robots de búsqueda | Gratis (crédito mensual incluido) |
| [Supadata](https://supadata.ai/) | Lee lo que se dice en los videos | Gratis |
| [Notion](https://www.notion.so/) | Ahí viven tus tablas | Gratis |

El agente te guía para sacar cada llave cuando lo saludes. Cada corrida gasta menos de $0.50 USD de tu crédito de Apify.

## Cómo se ve una corrida

**Tú escribes:**

```
busca videos virales de finanzas personales
```

**Él te regresa** (además de las 3 tablas llenas en tu Notion):

> Encontré 214 videos, tiré 176 de basura, quedaron 14 de calidad.
>
> **Top 3:**
> 1. 🇲🇽 "El error que te tiene pobre" — 2.1M views, pegó por el hook de miedo + número concreto
> 2. 🇪🇸 "Ahorré $100k en 12 meses así" — 890k views, storytelling con prueba
> 3. 🇺🇸 "Stop doing this with your paycheck" — 1.4M views, lista de 3 errores
>
> 📊 Lista de Videos · 💡 Ideas para el canal · 🧠 Análisis de patrones

*(Los números de arriba son una muestra de cómo se ve el reporte — los tuyos saldrán de tu nicho.)*

## Qué acabas de armar (así se piensa un agente)

Un agente es un sistema donde la IA —no tú— decide el siguiente paso. Le das un objetivo y herramientas; él prueba, ve qué pasó y sigue hasta cumplirlo.

Una receta te dice cada paso y siempre hace lo mismo. Un cocinero no: le dices qué quieres comer, ve qué hay, prueba y saca el plato. Un flujo es la receta. **Un agente es el cocinero.**

Este repo es un agente completo, y puedes señalar cada parte:

| Parte del agente | Dónde vive aquí |
|---|---|
| **El objetivo** | "Encuentra los virales de este nicho y conviértelos en ideas para mí" |
| **Sus herramientas** | Los robots de búsqueda (Apify), el lector de lo que se dice en cada video (Supadata), tu Notion |
| **El bucle** | Busca → ve qué encontró → filtra → lee → clasifica → decide qué merece tu Notion y qué no |
| **Sus instrucciones** | [SKILL.md](SKILL.md) — léelo: es el "manual de empleado" del agente, en español |
| **Los frenos** | Confirma el hashtag contigo ANTES de gastar, valida las llaves antes de correr, y te dice el costo de cada corrida |

Fíjate en la diferencia: el archivo [pipeline.py](scripts/pipeline.py) es la parte de receta (siempre hace lo mismo). Las decisiones — qué video es basura, qué hook funciona, qué idea te sirve — las toma la IA en cada corrida. Esa mezcla es un agente.

## Adáptalo a otra cosa (cambia 2 archivos)

El patrón que acabas de armar — *buscar afuera → filtrar → analizar → escribir en Notion* — sirve para mucho más que videos:

- **Espiar a tu competencia**: mismas plataformas, pero el nicho es el nombre de tus 5 competidores.
- **Detectar tendencias de producto**: vuelve a correrlo sobre "gadgets de cocina" y compara los análisis de una corrida a otra.
- **Encontrar creadores para colaborar**: la tabla Lista ya trae autor y engagement — ordénala por Engagement Rate.

¿Y para cambiarle el cerebro? Solo se tocan 2 archivos:

1. **[SKILL.md](SKILL.md)** — las instrucciones del agente. Cambia el PASO 3 (cómo clasifica) y el PASO 5 (qué ideas genera) y tienes un agente distinto.
2. **[reference/notion_schema.md](reference/notion_schema.md)** — las columnas de tus tablas. Agrega o quita columnas según lo que quieras guardar.

Abre Claude Code y dile: *"lee el SKILL.md de agente-viral y ayúdame a adaptarlo para espiar competidores"*. Ese es el punto: ya entendiste el patrón, ahora Claude te ayuda a repetirlo.

## Lo honesto (qué NO hace)

- **Vive en tu computadora y corre cuando tú se lo pides.** Es tu primer agente.
- **No publica contenido.** Te da las ideas; grabar y publicar sigue siendo tuyo.
- **Depende de servicios externos.** Si TikTok cambia sus reglas o Apify falla, esa corrida sale coja. El agente te avisa en español, sin drama.
- **Los hashtags chicos dan resultados chicos.** Si tu nicho es muy de nicho, el agente te propondrá hashtags más grandes del mismo tema.
- **No es asesoría.** El score de viralidad es matemática sobre datos públicos, no una garantía de que tu video pegue.

## El siguiente

Armaste tu primer agente y ya está trabajando para ti.

El de verdad atiende tu WhatsApp y tus redes. Responde dudas, capta clientes y cobra. Para tu negocio, o para vendérselo a tus clientes. Ese lo construimos juntos en el workshop en vivo.

**Si te gustó armar este, ven a armar el de verdad → [Próximos workshops](https://luma.com/user/luiscordova_ia)**

---

Soy Luis Córdova — [@luiscordova.ia](https://instagram.com/luiscordova.ia)

Licencia MIT — ver [LICENSE](LICENSE).
