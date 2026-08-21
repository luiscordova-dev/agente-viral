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

## Al escribir cada fila

- El padre de la página va como `{type:"data_source_id", data_source_id:"<DS>"}`.
- Las fechas necesitan la forma larga, no basta el nombre de la columna: `date:Fecha de busqueda:start`, `date:Fecha:start`.
- `Interaccion %` se guarda como fracción, no como porcentaje: 0.229 significa 22.9%.
- `Basado en` (la relación) se manda como texto con un arreglo JSON que contiene la URL que Notion devolvió al crear esa página: `["<url tal cual la devolvió la API>"]`. Nunca la armes tú desde el identificador.
- `Plataformas` (opciones múltiples) también va como texto con arreglo JSON: `["tiktok","youtube"]`.
- Si el usuario trae tablas de una versión anterior, sus columnas se llaman distinto (`Views`, `Hook`, `Transcript`, `URL` —que se referencia `userDefined:URL`—, `Fecha Scrape`). Usa los nombres que existan en SU tabla y omite lo que no exista.
