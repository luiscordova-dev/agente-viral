# Las 3 tablas — cómo se arman

Esto es el plano de las tablas que el agente construye en el Notion del usuario, una
sola vez, con `notion-create-database`. Al crearlas devuelve un `data_source_id` por
tabla; esos identificadores se guardan con:

```
python3 scripts/config.py set-notion --parent <PARENT_PAGE_ID> --lista <DS> --ideas <DS> --analisis <DS>
```

⚠️ **La Lista va primero.** La tabla de Ideas apunta a ella, así que necesita su
identificador para poder crearse.

El orden de las columnas no es casual: adelante lo que el usuario quiere ver de un
vistazo (puntaje, ganchos, tipo), atrás los números finos y lo técnico.

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

Cada fila es una idea lista para grabar. `Video que la Inspiro` es una RELATION que apunta al `data_source_id` de la tabla Lista — hay que sustituir `<LISTA_DS>` por el que devolvió al crearla.

📝 **El guion completo NO es una columna: va como CONTENIDO de la página de cada idea** — gancho, cuerpo, puente y cierre en una sola caja de código, y debajo la mini shot-list. Así la tabla se lee de un vistazo y el guion está a un clic. Cómo se escribe: `SKILL.md` §PASO 5b.

```sql
CREATE TABLE (
"Idea" TITLE,
"Gancho Propuesto" RICH_TEXT COMMENT 'La frase de arranque, lista para decirla a camara.',
"Formato" SELECT('video corto (TikTok/Reel)':pink, 'video largo (YouTube)':red, 'carrusel':purple),
"Estado" SELECT('idea':gray, 'en produccion':yellow, 'publicado':green),
"Que Imita" RICH_TEXT COMMENT 'La mecanica del viral original que esta idea copia.',
"Por Que Deberia Funcionar" RICH_TEXT COMMENT 'La prueba: los numeros que hizo el video original.',
"Video que la Inspiro" RELATION('<LISTA_DS>', DUAL 'Ideas que salieron de aqui'),
"Para Que Nicho" RICH_TEXT COMMENT 'A que nicho esta adaptada.',
"Fecha" DATE
)
```

## 3) 🧠 Análisis

Una fila por búsqueda. Es el resumen que el usuario lee antes de decidir qué grabar.

```sql
CREATE TABLE (
"Busqueda" TITLE,
"Nicho" RICH_TEXT,
"Fecha" DATE,
"Videos Analizados" NUMBER,
"Plataformas" MULTI_SELECT('tiktok':pink, 'youtube':red, 'instagram':purple),
"Como Abren los que Ganan" RICH_TEXT COMMENT 'Las maneras de arrancar que se repiten entre los ganadores.',
"Formatos que Jalan" RICH_TEXT COMMENT 'Como estan hechos: duracion, a camara o pantalla, que estructura siguen.',
"Patrones que se Repiten" RICH_TEXT COMMENT 'Lo visual de las portadas, los hashtags de los ganadores, el audio, y cuantos eran cuentas chicas.',
"Que Hacer con Esto" RICH_TEXT COMMENT 'Recomendaciones concretas, no descripciones.',
"Donde Esta el Hueco" RICH_TEXT COMMENT 'Que esta funcionando en el nicho que el usuario todavia no aprovecha.'
)
```

---

## Al escribir cada fila

- El padre de la página va como `{type:"data_source_id", data_source_id:"<DS>"}`.
- Las fechas necesitan la forma larga, no basta el nombre de la columna: `date:Fecha de busqueda:start`, `date:Fecha:start`.
- `Interaccion %` se guarda como fracción, no como porcentaje: 0.229 significa 22.9%.
- `Video que la Inspiro` (la relación) se manda como texto con un arreglo JSON que contiene la URL que Notion devolvió al crear esa página: `["<url tal cual la devolvió la API>"]`. Nunca la armes tú desde el identificador.
- `Plataformas` (opciones múltiples) también va como texto con arreglo JSON: `["tiktok","youtube"]`.
- Si el usuario trae tablas de una versión anterior, sus columnas se llaman distinto (`Views`, `Hook`, `Transcript`, `URL` —que se referencia `userDefined:URL`—, `Fecha Scrape`). Usa los nombres que existan en SU tabla y omite lo que no exista.
