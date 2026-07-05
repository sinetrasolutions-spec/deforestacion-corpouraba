# Manual de Usuario

## Observatorio de Deforestación CORPOURABA 2000–2024

Guía práctica para conocer, navegar y aprovechar la plataforma web del monitoreo de bosques en los 19 municipios de la jurisdicción CORPOURABA.

---

## Introducción y a quién va dirigido

El **Observatorio de Deforestación CORPOURABA** es una plataforma web pública que reúne veinticuatro años de datos (2000–2024) sobre la pérdida de bosque en los **19 municipios** de la jurisdicción de CORPOURABA —Corporación para el Desarrollo Sostenible del Urabá—, en el Urabá y el Occidente antioqueño. Le permite explorar mapas, analizar cifras, aprender con material educativo y descargar todos los datos en abierto.

Este manual está pensado para **personas sin conocimientos técnicos**:

- **Funcionarios y funcionarias de CORPOURABA** que necesiten consultar cifras, comparar municipios o descargar datos para informes.
- **Docentes y estudiantes** que trabajen los PRAES (Proyectos Ambientales Escolares) con datos reales del territorio.
- **Público general, líderes comunitarios, periodistas e investigadores** interesados en el estado del bosque de la región.

No necesita instalar nada ni crear una cuenta. Basta con un navegador de internet.

---

## Cómo acceder

1. Abra un navegador de internet actualizado (Google Chrome, Microsoft Edge, Mozilla Firefox o Safari), en computador, tableta o teléfono.
2. Escriba la dirección de la plataforma en la barra de direcciones y presione Enter. La plataforma está publicada en Vercel; su institución le facilitará la dirección web (URL) definitiva del observatorio.
3. La página de **Inicio** se cargará automáticamente. No requiere usuario ni contraseña.

**Recomendaciones:**

- Una conexión estable mejora la carga de los mapas, que descargan capas geográficas.
- La plataforma se adapta a pantallas pequeñas: en el teléfono, el menú aparece como un botón con tres líneas (menú «hamburguesa»).

---

## Navegación general

### Barra superior (menú principal)

En la parte de arriba, siempre visible, encontrará el logotipo de CORPOURABA y los seis enlaces de navegación. El enlace de la sección en la que se encuentra queda resaltado:

| Enlace | Le lleva a |
| --- | --- |
| **Inicio** | Panorama general y cifras clave |
| **Dashboard** | Análisis de cifras, gráficos y comparaciones |
| **Mapa** | Mapa interactivo por municipio, con línea de tiempo |
| **Visor** | Visor de los polígonos de deforestación y capas oficiales |
| **Aprende** | Módulo educativo PRAES por niveles |
| **Datos** | Centro de descargas y metodología |

En el teléfono, toque el botón de menú (≡) para desplegar estos enlaces.

### Tema claro / oscuro

A la derecha de la barra superior hay un botón con un icono de **sol o luna**. Al tocarlo, la plataforma alterna entre modo claro y modo oscuro; su preferencia queda guardada para próximas visitas. Los mapas también cambian su fondo (claro u oscuro) para acompañar el tema.

### Pie de página

Al final de cada página encontrará los accesos a los módulos y recursos, la atribución cartográfica (© OpenStreetMap · © CARTO, coordenadas en WGS84) y la nota de honestidad sobre los datos estimados. La plataforma fue creada por **Alberto Vivas y Carlos Zuluaga**.

---

## Inicio (panorama y cifras clave)

La página de **Inicio** ofrece una visión de conjunto en cuatro partes:

1. **Portada (hero):** presenta el observatorio con dos botones de entrada rápida, «Explorar el mapa» y «Aprende con tu colegio», y tres datos de referencia: 19 municipios y 5 subregiones, 18 periodos de medición y ≈ 1,86 millones de hectáreas de jurisdicción.
2. **Franja de indicadores (KPIs):** cuatro tarjetas con contadores que se calculan en vivo sobre la serie completa:
   - **Total deforestado** (acumulado 2000–2024 en la jurisdicción).
   - **Promedio anual** (hectáreas perdidas por año, en promedio).
   - **Periodo más crítico**.
   - **Municipio más afectado**.
   Debajo se resume el número de periodos y municipios, el porcentaje de datos estimados y el periodo de menor pérdida.
3. **Las seis maneras de explorar:** tarjetas que describen cada módulo y le llevan a él con un clic.
4. **¿Cómo leer estos datos? (transparencia):** tres advertencias metodológicas clave (periodos de distinta duración, existencia de datos estimados y combinación de varias fuentes) y un aviso sobre la insignia **estimado** y el borde discontinuo.

**Cómo usarlo:** úselo como punto de partida. Lea las cifras de la franja de KPIs para hacerse una idea rápida y entre al módulo que necesite desde las tarjetas o desde la barra superior.

---

## Dashboard analítico

El **Dashboard** es la sección de análisis de cifras. Trabaja sobre la clase **Deforestación** de los 19 municipios y los 18 periodos, y todos los gráficos responden a los filtros que usted elija.

### Barra de filtros

En la parte superior, una barra fija (que le sigue al desplazarse) le permite acotar lo que ve:

- **Subregión:** elija una de las cinco (Caribe, Centro, Atrato, Nutibara, Urrao) o «Todas».
- **Rango de años:** una barra con dos manijas para fijar el año inicial y el año final (entre 2000 y 2024). El rango elegido se muestra sobre el control.
- **Incluir estimados:** casilla marcada por defecto. Desmárquela para excluir los periodos estimados del análisis.
- **Limpiar filtros:** devuelve todo a su estado inicial.
- **Municipios (fichas):** debajo, la lista de municipios como botones. Toque uno para seleccionarlo (se pinta de verde) y tóquelo otra vez, o la «✕», para quitarlo. Puede seleccionar varios.

### Qué muestra el Dashboard

1. **KPIs:** Total deforestado, Promedio anual (ha/año), Periodo más crítico y Municipio más afectado, recalculados según los filtros.
2. **Serie temporal de deforestación:** línea de hectáreas por año. Los periodos estimados aparecen con una franja sombreada y su punto dibujado con relleno blanco.
3. **Ranking de municipios:** las 10 municipalidades con mayor deforestación acumulada. **Es clicable:** al hacer clic en una barra, ese municipio se agrega o quita de la selección y todos los gráficos se ajustan.
4. **Predicción:** proyección a 3 años de la tasa anual (regional, o municipal si tiene un solo municipio seleccionado). Incluye una advertencia sobre las limitaciones de la proyección.
5. **Comparador de municipios:** al seleccionar entre **2 y 6 municipios** en los filtros, dibuja una línea por municipio (ha/año) para compararlos.
6. **Mapa de calor municipio × periodo:** una cuadrícula donde cada celda es un municipio (filas) y un periodo (columnas); el color indica la intensidad de deforestación anualizada. Pase el cursor sobre una celda para ver la cifra exacta.
7. **Hallazgos verificados:** tarjetas con resultados destacados de la investigación temática y del cruce con la cartografía oficial.
8. **Deforestación por territorio:** vea cuánta deforestación mapeada ocurre dentro de cada **área protegida, POMCA, resguardo indígena o consejo comunitario**. Elija el tipo de territorio y, si lo desea, un periodo específico; cada unidad muestra hectáreas, número de periodos y porcentaje del territorio.

### Cómo filtrar y exportar

- **Filtrar por municipio:** toque su ficha en la barra de filtros o haga clic en su barra del ranking.
- **Filtrar por periodo/años:** use la barra de rango de años.
- **Exportar:** cada gráfico tiene su botón de exportación (imagen y, en varios, CSV). La sección de territorio y el generador del Centro de descargas permiten bajar la tabla en CSV.

---

## Mapa interactivo

El **Mapa** colorea los 19 municipios según su deforestación (mapa de coropletas) y le permite recorrer los 18 periodos en el tiempo.

### Controles principales

- **Métrica** (arriba a la izquierda): elija **Hectáreas** (total del periodo) o **Ha/año** (anualizado, mejor para comparar periodos de distinta duración).
- **Ajustar** (arriba a la derecha): reencuadra el mapa sobre toda la jurisdicción.
- **Capas** (arriba a la derecha): abre el panel de capas de contexto.
- **Línea de tiempo** (abajo): una barra deslizante recorre los 18 periodos (2000–2024). El botón **▶ / ⏸** inicia o detiene el **timelapse**, que avanza automáticamente periodo tras periodo en bucle. La casilla «estimados» controla si se incluyen esos periodos.

### Cómo leer el mapa

- **Colores:** cuanto más intenso el color, mayor la deforestación del municipio en ese periodo. La **leyenda** (abajo a la izquierda) indica los rangos, incluyendo el color de «Sin dato».
- **Borde discontinuo:** un municipio con **borde a rayas y color más tenue** corresponde a un **periodo estimado** (no medido directamente). La leyenda muestra la insignia «periodo estimado» cuando aplica.
- **Ficha del municipio:** haga clic en un municipio para abrir un panel lateral con su posición regional (#/19), su total 2000–2024 y su deforestación por periodo (ha/año); desde ahí puede «Ver en el dashboard» o «Descargar CSV del municipio». Doble clic acerca el mapa a ese municipio.

### Capas de contexto

En el panel de **Capas** puede encender:

- **Deforestación (hotspots):** los polígonos de deforestación de deforestación (incluidos los de menos de 1 ha) del periodo activo (avisa cuando un periodo no tiene datos de polígonos).
- **Frentes persistentes (≥3 periodos):** zonas donde la deforestación se repite en varios periodos.
- Capas oficiales de contexto (áreas protegidas, resguardos, consejos, cuencas y demás), que se descargan al activarlas. Toque una unidad para ver su información.

---

## Visor de deforestación

El **Visor** muestra directamente los **polígonos de deforestación** (incluidos los focos de menos de 1 ha) sobre el mapa, con una nueva línea de tiempo visual y las capas de la cartografía oficial.

### Dos modos de visualización

En el recuadro «Visor de deforestación» (arriba a la izquierda) elija:

- **Un año a la vez:** muestra los polígonos de un solo periodo, en rojo. Aparece la línea de tiempo de barras (ver abajo).
- **Ver todo:** muestra todos los periodos a la vez, coloreando cada polígono según su año (de teal, más antiguo, a rojo/magenta, más reciente). La leyenda muestra la escala temporal 2000–2024.

Con el desplegable **Municipio** puede limitar la vista a un solo municipio o dejar «Toda la jurisdicción».

### La línea de tiempo de barras (modo «Un año a la vez»)

En la parte inferior encontrará una mini-gráfica donde **cada barra es un año** y su altura representa la deforestación de ese periodo. Tiene tres formas de usarla:

1. **Tocar una barra:** salta directamente a ese año.
2. **Barra deslizante:** arrástrela para avanzar o retroceder año por año.
3. **Reproducir (▶):** activa la reproducción automática, que recorre los periodos uno tras otro; **⏸** la pausa.

Junto al año seleccionado se muestra su número de focos y sus hectáreas.

### Capas oficiales y panel de datos

- **Capas:** el botón «Capas» abre el catálogo de la **cartografía oficial** (Áreas protegidas, Resguardos indígenas, Consejos comunitarios, Cuencas, POMCAS, Reserva forestal Ley 2ª, Títulos mineros, entre otras). Enciéndalas para verlas debajo de la deforestación; toque una unidad para su detalle. «Apagar todas» las quita de golpe.
- **Datos:** el botón «Datos» abre el panel de estadísticas de fragmentación: número de polígonos, área total, tamaño medio, mayor polígono y distribución por tamaño. En modo «Ver todo» incluye también los polígonos por periodo (clicables).
- **Descargar GeoJSON:** en modo «Un año a la vez», el panel de datos ofrece **«Descargar GeoJSON del periodo»** para llevar los polígonos a otro programa (por ejemplo, un SIG).

> **Nota importante del visor:** el visor contiene los polígonos de deforestación (incluidos los de menos de 1 ha) de **12 de los 18 periodos** (cerca del 64 % de la deforestación total). No incluye el pico de **2015-2016** ni otros cinco periodos, porque no se conservó su geometría. Por eso el visor no debe leerse como el total: para las cifras completas use el Dashboard.

---

## Aprende · PRAES

El módulo **Aprende** es el material educativo del observatorio, pensado para el aula y los PRAES. Cuenta la historia del bosque de Urabá con los datos reales de la plataforma.

### Tres niveles

En la parte superior elija su nivel (su elección se recuerda):

| Nivel | Emoji | Grado sugerido |
| --- | --- | --- |
| **Explorador** | 🌱 | Primaria |
| **Guardián** | 🌿 | Secundaria |
| **Científico** | 🌳 | Media |

El texto de cada sección se adapta al nivel elegido.

### Qué contiene

1. **Storytelling:** secciones ilustradas que explican qué es el bosque, por qué importa, sus impactos, el clima y las soluciones.
2. **Quiz:** ocho preguntas por nivel, con respuesta inmediata, explicación y resultado final.
3. **Juego «Salva el Bosque» (El reto del guardabosques):** un juego por turnos en el que sus acciones hacen crecer o proteger árboles mientras las amenazas se propagan; muestra los árboles vivos y relaciona el reto con cifras reales del territorio.
4. **Historias locales:** cuatro municipios (Turbo, Mutatá, Urrao y Vigía del Fuerte) con su gráfica real de deforestación (ha/año).
5. **Glosario del bosque:** definiciones en un acordeón desplegable.
6. **Guía docente:** enlace directo al Centro de datos para trabajar con las series y capas reales.

---

## Centro de descargas

El módulo **Datos** reúne todo lo descargable, con su metodología.

### Conjuntos de datos principales

| Dataset | Formatos | Contenido |
| --- | --- | --- |
| **Serie municipal** | CSV, Excel | Municipio × periodo × clase (1.123 filas) |
| **Serie regional** | CSV | Agregado de la jurisdicción por periodo y clase |
| **Límites municipales** | GeoJSON | Los 19 municipios (WGS84), con DANE y subregión |
| **Hotspots por periodo** | GeoJSON | Polígonos de deforestación de deforestación (incluidos los de menos de 1 ha) (12 periodos) |
| **Capas de contexto** | GeoJSON | Áreas protegidas, resguardos, consejos, cuencas y capas oficiales |
| **Paquete completo** | ZIP | Todos los datos procesados en un solo archivo |

También hay una sección con las **tablas y capas de la investigación temática**.

### Generador de extractos

Le permite bajar **solo lo que necesita**:

1. Elija **Municipio**, **Periodo** y **Clase**.
2. Descargue en **CSV** o **Excel**, o pulse **Vista previa** para revisar hasta 50 filas antes de descargar.

### Diccionario y metodología

- **Diccionario de datos:** explica cada columna de la serie municipal (código DANE, clase, hectáreas, hectáreas anuales, fuente, estimado, etc.).
- **Metodología y fuentes:** tabla periodo por periodo con la fuente utilizada y la diferencia frente a los cálculos oficiales, más las notas sobre datos estimados y sobre 2015-2016. Al final se indican el CRS de origen (EPSG:3115) y de salida (EPSG:4326) y la atribución sugerida.

---

## Cómo interpretar las cifras

Antes de sacar conclusiones, tenga presentes estas cuatro claves.

### 1. Dato medido vs. dato estimado

- La mayoría de periodos son **datos medidos** a partir de la cartografía oficial (shapefiles, hojas de cálculo o rásteres).
- Solo **tres periodos** son **estimados o calibrados**: **2010-2012, 2018-2019 y 2023-2024**. Se calcularon por tendencia porque no existe medición municipal directa. Se marcan **siempre** con la insignia **estimado**, con una franja sombreada en las gráficas o con **borde discontinuo** en el mapa. Úselos como referencia, no como cifra oficial.
- **2015-2016 sí es dato real (medido).** Se recuperó de la tabla municipal oficial y corresponde al **pico de deforestación del periodo: 5.771 ha**. No aparece como polígonos en el Visor porque no se conservó su geometría, pero sus cifras en el Dashboard y en las series son reales.

### 2. Hectáreas totales vs. hectáreas por año

- Los **cinco primeros periodos (2000–2010)** abarcan **dos años** cada uno; desde 2012 los periodos son **anuales**.
- El **total del periodo** (columna «hectáreas») suma todo lo perdido en su duración; las **hectáreas por año** («ha/año») lo dividen por el número de años.
- Para **comparar periodos entre sí en igualdad de condiciones, use siempre ha/año.**

### 3. Por qué las cifras del Dashboard y del Visor pueden diferir

- El **Dashboard** trabaja con la **serie completa** de los 18 periodos (incluidos los estimados y 2015-2016). Sus cifras representan el total.
- El **Visor** solo dibuja los **polígonos de deforestación (incluidos los de menos de 1 ha) de 12 periodos** con geometría disponible (cerca del 64 % del total); **no incluye 2015-2016 ni otros cinco periodos**. Por eso el área que suma el Visor es **menor** que el total del Dashboard.
- **Regla práctica:** para cifras oficiales y totales, consulte el **Dashboard** o el **Centro de descargas**; use el **Visor** para ver *dónde* ocurrió la deforestación, no *cuánta* en total.

### 4. Cifra de referencia del observatorio

La deforestación acumulada 2000–2024 en la jurisdicción es de **≈ 46.846 ha**. El periodo más crítico medido es **2015-2016 (5.771 ha)**; los de menor pérdida están al inicio de la serie (2000-2002, con 1.590 ha).

---

## Casos de uso de ejemplo

### Caso 1 — Un funcionario prepara un informe sobre un municipio

1. Entre a **Mapa** y haga clic en el municipio de interés para ver su ficha (posición regional y total 2000–2024).
2. Pulse **«Ver en el dashboard»**: el Dashboard se abre con ese municipio ya filtrado.
3. Revise la serie temporal y descargue el **CSV del municipio** desde la ficha del mapa, o use el **Generador de extractos** del Centro de datos para acotar por periodo y clase.

### Caso 2 — Un docente prepara una clase de PRAES

1. Entre a **Aprende** y elija el nivel según su grado (Explorador, Guardián o Científico).
2. Recorra el storytelling, aplique el **quiz** y use el juego **«Salva el Bosque»** con los estudiantes.
3. Muestre la **historia local** del municipio más cercano y, desde la **Guía docente**, descargue en el Centro de datos las series reales para trabajar en clase.

### Caso 3 — Comparar varios municipios y ver dónde deforestan

1. En el **Dashboard**, seleccione entre 2 y 6 municipios (con sus fichas o el ranking clicable) y observe el **Comparador** (ha/año).
2. Fije un **rango de años** para centrarse en un periodo de interés.
3. Pase al **Visor**, elija el modo **«Un año a la vez»**, use la **línea de tiempo de barras** para ubicar el año más crítico y encienda capas oficiales (por ejemplo, Áreas protegidas o Resguardos indígenas) para ver si la deforestación ocurre dentro de ellas. Descargue el **GeoJSON del periodo** si necesita los polígonos.

---

*Observatorio de Deforestación CORPOURABA · Monitoreo de bosques 2000–2024. Datos abiertos con fines de gestión ambiental y educación. Plataforma creada por Alberto Vivas y Carlos Zuluaga.*
