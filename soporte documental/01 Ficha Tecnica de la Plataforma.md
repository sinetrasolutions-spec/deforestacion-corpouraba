# Ficha Técnica de la Plataforma

## 1. Identificación

| Campo | Valor |
| --- | --- |
| **Nombre** | Observatorio de Deforestación CORPOURABA 2000–2024 |
| **Entidad** | CORPOURABA — Corporación para el Desarrollo Sostenible del Urabá |
| **Jurisdicción** | 19 municipios de Urabá y el occidente de Antioquia (Colombia) |
| **Repositorio** | GitHub: `sinetrasolutions-spec/deforestacion-corpouraba` |
| **Despliegue** | Vercel (aplicación web pública) |
| **Autores de la plataforma** | Alberto Vivas y Carlos Zuluaga |
| **Versión** | 1.0.0 |
| **Fecha de corte del dato** | 2026-07-04 (campo `generado`: `2026-07-04T23:53:06Z`) |

## 2. Objetivo y alcance

- Poner a disposición del público, de forma clara y navegable, la información de deforestación de la jurisdicción de CORPOURABA para el periodo 2000–2024.
- Integrar en una sola plataforma la serie estadística municipal y regional, la cartografía oficial de la Corporación y material educativo para PRAES.
- **Alcance:** consolidación, visualización y descarga de los datos de cambio de bosque ya procesados; no realiza monitoreo satelital en tiempo real ni sustituye los reportes oficiales de deforestación de la Corporación.
- Público objetivo: funcionarios de CORPOURABA, entes territoriales, instituciones educativas (PRAES), academia y ciudadanía.

## 3. Cobertura temporal y territorial

- **Cobertura temporal:** 2000–2024, organizada en **18 periodos** de comparación de cobertura de bosque.
- **Cobertura territorial:** **19 municipios** de la jurisdicción, agrupados por territorial:

| Municipio | Código DANE | Territorial |
| --- | --- | --- |
| Abriaquí | 05004 | Nutibara |
| Apartadó | 05045 | Centro |
| Arboletes | 05051 | Caribe |
| Cañasgordas | 05138 | Nutibara |
| Carepa | 05147 | Centro |
| Chigorodó | 05172 | Centro |
| Dabeiba | 05234 | Nutibara |
| Frontino | 05284 | Nutibara |
| Giraldo | 05306 | Nutibara |
| Murindó | 05475 | Atrato |
| Mutatá | 05480 | Centro |
| Necoclí | 05490 | Caribe |
| Peque | 05543 | Nutibara |
| San Juan de Urabá | 05659 | Caribe |
| San Pedro de Urabá | 05665 | Caribe |
| Turbo | 05837 | Centro |
| Uramita | 05842 | Nutibara |
| Urrao | 05847 | Urrao |
| Vigía del Fuerte | 05873 | Atrato |

## 4. Cifras clave

| Indicador | Valor |
| --- | --- |
| Deforestación total acumulada (2000–2024) | **46.845,52 ha** |
| Periodo pico | **2015-2016** — 5.771,04 ha |
| Periodo de menor deforestación | **2020-2021** — 1.090,76 ha |
| Número de municipios | 19 |
| Número de periodos | 18 |
| Periodos estimados | 3 de 18 (**16,7 %** de los periodos) |
| Registros municipales estimados | 57 de 1.131 (**5,0 %** de los registros) |

*Cifras verificadas sobre `serie_regional.csv` y `serie_municipal.csv` (clase Deforestación).*

## 5. Módulos de la plataforma

| Módulo | Descripción |
| --- | --- |
| **Inicio** | Portada con resumen, cifras destacadas y acceso a los demás módulos. |
| **Dashboard** | Indicadores, series temporales y gráficas de deforestación por municipio, territorial y unidad de gestión. |
| **Mapa** | Mapa interactivo (react-leaflet) de los 19 municipios con las capas de contexto. |
| **Visor de deforestación** | Explorador de parches con línea de tiempo visual (barras clicables por año, barra deslizante y reproducción) y capas oficiales de la cartografía. |
| **Aprende (PRAES)** | Contenido educativo orientado a los Proyectos Ambientales Escolares. |
| **Centro de descargas** | Descarga de la serie, metadatos y capas geográficas en formatos abiertos. |

## 6. Fuentes principales

- **Serie estadística municipal y regional:** shapefiles, tablas Excel (.xls) y tabla municipal .dbf del paquete original de monitoreo de bosque de CORPOURABA (2000–2024).
- **Periodo 2015-2016:** tabla de atributos municipal oficial `Defor2015_2016_Mpios_Proj_Correg.dbf` (dato medido de los 19 municipios).
- **Cartografía oficial de contexto (CORPOURABA):** Áreas protegidas (21 unidades), Resguardos indígenas (39), Consejos comunitarios (7), Cuencas (7), POMCAS, Reserva forestal Ley 2ª y Títulos mineros.
- **Control de calidad:** hojas "Cálculos" de los Excel originales (diferencias verificadas ≤ 0,29 %).

## 7. Stack tecnológico

| Componente | Tecnología |
| --- | --- |
| Framework web | Next.js 14.2.15 (App Router) |
| Lenguaje | TypeScript 5 |
| Estilos | Tailwind CSS 3.4 |
| Cartografía web | react-leaflet 4.2.1 / Leaflet 1.9.4 |
| Gráficas | Recharts 2.12.7 |
| Estado / utilidades | Zustand, framer-motion, lucide-react, jszip, xlsx |
| API | Rutas Next.js (`app/api/v1`) |
| ETL | Python (`run_etl.py`) y scripts de consolidación e informes |
| Despliegue | Vercel |

## 8. Estado y calidad del dato

- **Datos medidos:** 15 de los 18 periodos provienen de fuentes primarias (shapefiles, Excel, tabla .dbf o estadísticas zonales sobre ráster).
- **CRS:** origen EPSG:3115 (MAGNA-SIRGAS Bogotá, métrico); capas web reproyectadas a WGS84 (EPSG:4326).
- **Validación:** los periodos con hoja "Cálculos" muestran diferencias respecto a la referencia entre 0,00 % y 0,29 %.
- **Periodo 2015-2016:** es **dato medido** (`estimado=false`), calculado con la tabla municipal oficial .dbf. Su geometría (.shp) no se conservó, por lo que no aparece en el visor de polígonos, pero sus cifras en el dashboard y en la serie son reales.
- **Periodos estimados (3):**

| Periodo | Método de estimación |
| --- | --- |
| **2010-2012** | Interpolación/tendencia de la tasa anual, calibrada con el total departamental real (RAT del ráster) × participación histórica de la jurisdicción (~17,9 %). |
| **2018-2019** | Interpolación/tendencia de la tasa anual de deforestación. |
| **2023-2024** | Interpolación/tendencia de la tasa anual de deforestación. |

## 9. Limitaciones

- Los 3 periodos estimados (2010-2012, 2018-2019, 2023-2024) carecen de datos municipales en el paquete original; se marcan con `estimado=true` y deben usarse **solo como referencia**, no como cifra oficial.
- El periodo 2015-2016 no tiene geometría de polígonos, por lo que no se representa en el visor de deforestación aunque sus cifras sean reales.
- Algunas capas de contexto (resguardos, consejos comunitarios) incluyen territorios parcial o totalmente fuera de la jurisdicción; su deforestación solo se contabiliza dentro del área monitoreada por CORPOURABA.
- Las cifras corresponden al procesamiento del paquete cartográfico entregado y a su corte del 2026-07-04; no reflejan cambios posteriores en el terreno.
- La clase "Sin Información" varía entre periodos según la disponibilidad y calidad de la cobertura de origen, lo que puede afectar la comparabilidad directa entre algunos años.

## 10. Créditos

- **Entidad responsable:** CORPOURABA — Corporación para el Desarrollo Sostenible del Urabá.
- **Autores de la plataforma:** Alberto Vivas y Carlos Zuluaga.
- **Fuente de los datos:** CORPOURABA — monitoreo de bosque de la jurisdicción; datos procesados por el ETL del Observatorio.
- **Repositorio:** `sinetrasolutions-spec/deforestacion-corpouraba` (GitHub), desplegado en Vercel.
