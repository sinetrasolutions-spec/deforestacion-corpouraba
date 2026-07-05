# Índice del Soporte Documental

Este documento presenta el **soporte documental** de la plataforma web **Observatorio de Deforestación CORPOURABA**, que monitorea la deforestación en los 19 municipios de la jurisdicción de CORPOURABA (Urabá y occidente de Antioquia) durante el periodo **2000–2024**.

El soporte reúne, en una sola carpeta, la documentación necesaria para **usar, entender, mantener y auditar** la plataforma y sus datos. Está dirigido a la Corporación (gestión y decisión), al equipo técnico y a los usuarios finales (funcionarios, docentes y público).

## Documentos que lo componen

| Nº | Documento | Para quién | Qué contiene |
| --- | --- | --- | --- |
| 01 | **Ficha Técnica de la Plataforma** | Dirección / general | Identificación, alcance, cobertura, cifras clave, módulos, stack y estado del dato en 2–3 páginas. |
| 02 | **Manual de Usuario** | Usuarios no técnicos | Cómo usar cada módulo paso a paso y cómo interpretar las cifras. |
| 03 | **Documentación Técnica (Manual del Sistema)** | Ingeniero / desarrollador | Arquitectura, estructura, ejecución local, regeneración de datos y despliegue. |
| 04 | **Metodología y Fuentes de Datos** | Técnico / auditoría | Fuentes, pipeline ETL, calibraciones, control de calidad y limitaciones. |
| 05 | **Diccionario de Datos** | Técnico / analista | Cada dataset y campo, con tablas de códigos (clases, subregiones, municipios). |

Cada documento existe en dos formatos: **`.docx`** (Word, para lectura e impresión) y **`.md`** (Markdown, fuente editable y versionable).

## La plataforma de un vistazo

- **Entidad:** CORPOURABA — Corporación para el Desarrollo Sostenible del Urabá.
- **Cobertura:** 19 municipios · 2000–2024 · 18 periodos de monitoreo.
- **Cifra central:** ≈ 46.846 ha deforestadas (2000–2024); pico histórico en 2015-2016.
- **Módulos:** Inicio, Dashboard analítico, Mapa interactivo, Visor de deforestación, Aprende (PRAES) y Centro de descargas.
- **Tecnología:** Next.js 14 (TypeScript, Tailwind, react-leaflet, Recharts); datos procesados con un ETL en Python (GeoPandas). Desplegada en Vercel.
- **Autores de la plataforma:** Alberto Vivas y Carlos Zuluaga.

## Cómo se regenera esta documentación

Los documentos `.docx` se generan a partir de los archivos `.md` de esta carpeta con:

```
python etl/generar_soporte_docx.py
```

De modo que, al actualizar un `.md`, basta volver a ejecutar el generador para reconstruir el Word con la portada institucional y el mismo estilo.
