# 🤖 Agente Viral — tu primer agente en 20 minutos

Un agente de IA que trabaja en tu computadora. Le dices un nicho — cocina, finanzas, skincare, el que sea — y él solo:

1. **Busca** los videos virales de ese nicho en TikTok, YouTube e Instagram.
2. **Tira la basura**: memes, anuncios, clips de pura música.
3. **Lee lo que se dice** en cada video para quedarse con contenido de verdad.
4. **Mira la portada** de cada finalista y lee el gancho visual: el texto en pantalla y lo que se ve en el primer segundo — lo que detiene el scroll.
5. **Detecta a las cuentas chicas que la rompieron**: videos con muchas más vistas que seguidores tiene su autor. Esos ganaron por el formato, no por la fama — y son los que tú sí puedes copiar.
6. **Te deja 3 tablas en tu Notion**: los virales con sus números, ideas escritas para tu negocio y tu cliente, y el análisis de qué está funcionando.

Necesitas Claude Code ya instalado — el mapa que te trajo aquí lo deja listo. ¿Llegaste directo a esta página sin pasar por el mapa? Instala Claude Code primero: [claude.com/claude-code](https://claude.com/claude-code).

## Instálalo (pídeselo a Claude)

Abre Claude Code y pégale esta frase — tal cual, completa:

```
Clona este repo, instálalo y preséntate: https://github.com/luiscordova-dev/agente-viral
```

Él lo descarga, lo instala y arranca contigo en el mismo chat: se presenta y te va pidiendo una llave a la vez.

⚠️ Si le dices solo *"clona este repo"*, va a hacer exactamente eso — descargarlo y ahí quedarse. No es que falle: un asistente no se instala cosas ni cambia de rol porque un archivo se lo pida, eso se lo tienes que pedir tú. Por eso la frase lleva **"instálalo"** y **"preséntate"**: eso ya lo autorizas tú.

¿No te contesta como Agente Viral? Pídeselo directo: *"léete ~/.claude/skills/agente-viral/SKILL.md y compórtate como ese agente"*.

Él se presenta y te lleva de la mano. Te dice exactamente dónde sacar cada llave. Te abre un archivo donde las pegas — nunca van en el chat. Revisa que funcionen. Crea tus tablas de Notion solo. Y te hace 3 preguntas rápidas sobre tu negocio, para que las ideas salgan a tu medida y no genéricas. Eso se hace una sola vez — después, cada corrida es escribir una frase.

<details>
<summary>¿Prefieres hacerlo a mano en la terminal?</summary>

```bash
git clone https://github.com/luiscordova-dev/agente-viral ~/.claude/skills/agente-viral
rm -rf ~/.claude/skills/agente-viral/.git
```

Ese segundo renglón importa: le quita el git a la carpeta instalada, que es donde vas a pegar tus llaves. Sin git, no hay forma de que se te vayan en un commit ni por accidente.

Si te dice que la carpeta ya existe, pídele a Claude que la borre y lo reinstale — es más seguro que borrarla tú a mano.
</details>

## Lo que necesitas (son 3 cuentas, las 3 gratis)

| Cuenta | Para qué | Costo |
|---|---|---|
| [Apify](https://console.apify.com/) | Corre los robots de búsqueda | Gratis (crédito mensual incluido) |
| [Supadata](https://supadata.ai/) | Lee lo que se dice en los videos | Gratis |
| [Notion](https://www.notion.so/) | Ahí viven tus tablas (se activa como conector en Claude Code, sin llave) | Gratis |

El agente te guía para sacar cada llave cuando lo saludes. Las tres cuentas son gratis y traen crédito incluido: las primeras corridas no te cuestan nada. Apify regala 5 dólares de crédito al mes y cada búsqueda completa gasta unos 70 centavos — te alcanza para unas 7 al mes sin pagar nada. ¿Quieres más cobertura? Pídele que revise más videos por plataforma — cuesta un poco más.

🔒 **Tus llaves nunca salen de tu computadora.** Las pegas en un archivo de tu disco (el agente te dice cuál y cómo abrirlo), él las guarda en una carpeta privada que solo tú puedes abrir y limpia el archivo. Nunca se suben a ningún lado ni pasan por el chat. Y si un día quieres cortar el acceso, las borras en Apify o Supadata y quedan muertas al momento.

También necesitas **Python 3** — ya viene en macOS y Linux. Si tu Mac te ofrece instalarlo la primera vez, acepta y espera.

## Cómo se ve una corrida

**Tú escribes:**

```
busca videos virales de finanzas personales
```

**Él te regresa** (además de las 3 tablas llenas en tu Notion):

> Encontré 214 videos y tiré 69 de basura. De los 145 que quedaron, revisé a fondo los mejores y 14 pasaron el filtro de contenido.
>
> **Top 3:**
> 1. 🇲🇽 "El error que te tiene pobre" — 2.1M views, pegó por el gancho de miedo + número concreto
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
| **Sus instrucciones** | [Su manual de trabajo](SKILL.md) — ábrelo: está escrito en español, y es lo que el agente lee para saber cómo actuar |
| **Los frenos** | Confirma el hashtag contigo ANTES de gastar, valida las llaves antes de correr, y te dice el costo de cada corrida |

Fíjate en la diferencia: el archivo [pipeline.py](scripts/pipeline.py) es la parte de receta (siempre hace lo mismo). Las decisiones — qué video es basura, qué hook funciona, qué idea te sirve — las toma la IA en cada corrida. Esa mezcla es un agente.

## Adáptalo a otra cosa (cambia 2 archivos)

El sistema que acabas de armar — *buscar afuera → filtrar → analizar → escribir en Notion* — sirve para mucho más que videos:

- **Espiar a tu competencia**: mismas plataformas, pero el nicho es el nombre de tus 5 competidores.
- **Detectar tendencias de producto**: vuelve a correrlo sobre "gadgets de cocina" y compara los análisis de una corrida a otra.
- **Encontrar creadores para colaborar**: la tabla Lista ya trae autor e interacción — ordénala por **Interacción %** (de cada 100 que vieron el video, cuántos hicieron algo).

¿Y para cambiarle el cerebro? Solo se tocan 2 archivos:

1. **[Su manual de trabajo](SKILL.md)** — lo que el agente lee para saber qué hacer. Cambia el PASO 3 (cómo clasifica) y el PASO 5 (qué ideas genera) y tienes un agente distinto.
2. **[reference/notion_schema.md](reference/notion_schema.md)** — las columnas de tus tablas. Agrega o quita columnas según lo que quieras guardar.

Abre Claude Code y dile: *"lee las instrucciones del Agente Viral y ayúdame a adaptarlo para espiar competidores"*. Ese es el punto: ya entendiste el sistema, ahora Claude te ayuda a repetirlo.

## Lo honesto (qué NO hace)

- **Vive en tu computadora y corre cuando tú se lo pides.** Es tu primer agente.
- **No publica contenido.** Te da las ideas; grabar y publicar sigue siendo tuyo.
- **Depende de servicios externos.** Si TikTok cambia sus reglas o Apify falla, esa corrida sale coja. El agente te avisa en español, sin drama.
- **Los hashtags chicos dan resultados chicos.** Si tu nicho es muy de nicho, el agente te propondrá hashtags más grandes del mismo tema.
- **De YouTube también llegan videos largos.** Los cortos salen de TikTok e Instagram; los formatos largos que funcionan también son oro para sacar ideas.
- **Las vistas-por-seguidor no aplican a Instagram.** TikTok y YouTube dicen cuántos seguidores tiene el autor; el buscador de Instagram no. Esa columna sale vacía en los reels — no es un error.
- **No ve el video completo — ve la portada.** El agente escucha lo que se dice y mira la imagen de entrada. Con eso lee el gancho hablado y el visual, que es donde vive la retención.
- **No es asesoría.** El score de viralidad es matemática sobre datos públicos, no una garantía de que tu video pegue. Compara cada video contra los de SU plataforma (un millón de views en TikTok no vale lo mismo que en YouTube), pero nadie puede prometerte que copiar un formato funcione.

## El siguiente

Armaste tu primer agente y ya trabaja para ti. Corre en tu computadora: trabaja cuando tú lo abres.

El que atiende a tus clientes trabaja aunque tú no estés. Responde dudas, capta clientes, agenda citas y manda links de cobro — en tu WhatsApp y en tus redes. Para tu negocio, o para vendérselo a tus clientes.

**Ese lo construimos juntos, en vivo → [Próximos workshops](https://lu.ma/luiscordova)**

---

Soy Luis Córdova — [@luiscordova.ia](https://instagram.com/luiscordova.ia)

Licencia MIT — ver [LICENSE](LICENSE).
