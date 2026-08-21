# Esquemas de Notion (para crear las tablas en el setup)

En el primer uso, Claude crea estas 3 tablas en el Notion del usuario (bajo la página
padre que el usuario elija, o en la raíz del workspace) usando el MCP de Notion
(`notion-create-database`), y guarda los `data_source_id` resultantes con:

```
python3 scripts/config.py set-notion --parent <PARENT_PAGE_ID> --lista <DS> --ideas <DS> --analisis <DS>
```

Crea **primero** la tabla Lista (las Ideas se relacionan a ella vía su `data_source_id`).

El orden de las columnas es deliberado: lo que el usuario quiere ver primero
(puntaje, ganchos, tipo) al frente; los números crudos y lo técnico al fondo.

---

## 1) 📊 Lista de Videos con Data

```sql
CREATE TABLE (
"Video" TITLE,
"Plataforma" SELECT('tiktok':pink, 'youtube':red, 'instagram':purple),
"Puntaje Viral" NUMBER COMMENT 'Que tan por encima del promedio quedo, comparado SOLO contra videos de su misma plataforma. 0 = promedio. Arriba de 1 = de los mejores.',
"Vistas" NUMBER,
"Gancho (lo que dice)" RICH_TEXT COMMENT 'La frase con la que arranca el video. Aqui vive el 80% del resultado.',
"Gancho (lo que se ve)" RICH_TEXT COMMENT 'Lo que aparece en la portada: la imagen y el texto en pantalla. Lo que detiene el scroll.',
"Tipo Contenido" SELECT('educativo':blue, 'storytelling':orange, 'promo':gray, 'reto/demo':green, 'motivacional':yellow, 'musica/baile':pink),
"Vistas por Seguidor" NUMBER COMMENT 'Cuantas vistas hizo por cada seguidor del autor. Si es alto, gano el FORMATO y no la fama: ese si lo puedes copiar tu.',
"Autor" RICH_TEXT,
"Link" URL,
"Interaccion %" NUMBER FORMAT 'percent' COMMENT 'De cada 100 personas que lo vieron, cuantas hicieron algo (like, comentario, compartir, guardar).',
"Likes" NUMBER,
"Comentarios" NUMBER,
"Compartidos" NUMBER,
"Guardados" NUMBER COMMENT 'La mejor senal de valor: la gente guarda lo que piensa usar despues.',
"Seguidores" NUMBER COMMENT 'Seguidores que tenia el autor el dia de la busqueda.',
"Duracion (s)" NUMBER COMMENT 'Cuanto dura el video, en segundos.',
"Antiguedad (dias)" NUMBER COMMENT 'Cuantos dias lleva publicado.',
"Palabras por minuto" NUMBER COMMENT 'Que tan rapido habla. Arriba de 150 es ritmo alto; abajo de 60 casi no habla (suele ser musica).',
"Idioma" RICH_TEXT,
"Audio" RICH_TEXT COMMENT 'Que cancion o sonido usa. TikTok e Instagram lo traen; YouTube no.',
"Nicho" RICH_TEXT,
"Lo que se dice" RICH_TEXT COMMENT 'Transcripcion de lo que se habla en el video.',
"Fecha de busqueda" DATE
)
```

## 2) 💡 Ideas de Videos
La columna `Basado en` es una RELATION al `data_source_id` de la tabla Lista (sustituir `<LISTA_DS>`).

```sql
CREATE TABLE (
"Idea" TITLE,
"Nicho Destino" RICH_TEXT,
"Formato" SELECT('video corto (TikTok/Reel)':pink, 'video largo (YouTube)':red, 'carrusel':purple),
"Hook Propuesto" RICH_TEXT COMMENT 'La frase de arranque propuesta para tu video.',
"Angulo" RICH_TEXT COMMENT 'El giro de la idea: que formato ganador imita.',
"Por que funciona" RICH_TEXT COMMENT 'La prueba: los numeros del video original en el que se basa.',
"Basado en" RELATION('<LISTA_DS>', DUAL 'Ideas derivadas'),
"Estado" SELECT('idea':gray, 'en produccion':yellow, 'publicado':green),
"Fecha" DATE
)
```

## 3) 🧠 Análisis

```sql
CREATE TABLE (
"Analisis" TITLE,
"Nicho" RICH_TEXT,
"Fecha" DATE,
"Videos Analizados" NUMBER,
"Plataformas" MULTI_SELECT('tiktok':pink, 'youtube':red, 'instagram':purple),
"Hooks Comunes" RICH_TEXT COMMENT 'Los ganchos que se repiten entre los ganadores.',
"Formatos que Funcionan" RICH_TEXT,
"Patrones Clave" RICH_TEXT COMMENT 'Lo que se repite: visual, hashtags, audio, cuentas chicas que la rompieron.',
"Insights y Recomendaciones" RICH_TEXT,
"Oportunidad de Adaptacion" RICH_TEXT COMMENT 'Como adaptar estos virales a otro nicho.'
)
```

---

## Notas para escribir filas (create-pages)
- Parent: `{type:"data_source_id", data_source_id:"<DS>"}`.
- Las fechas usan la forma expandida: `date:Fecha de busqueda:start`, `date:Fecha:start`.
- `Interaccion %` se guarda como fracción 0–1 (ej. 0.229 = 22.9%).
- `Basado en` (relación) se pasa como string JSON array con la URL de página que devolvió la API al crearla: `["<url tal cual la devolvió Notion>"]`. Nunca armes la URL a mano.
- `Plataformas` (multi-select) se pasa como string JSON array: `["tiktok","youtube"]`.
- Tablas de versiones anteriores usan nombres viejos (`Views`, `Hook`, `Transcript`, `URL` — que se referencia `userDefined:URL` —, `Fecha Scrape`): usa los nombres que existan en la tabla del usuario y omite lo que no exista.
