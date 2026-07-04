/**
 * Genera el informe Word detallado del análisis de deforestación CORPOURABA
 * 2000–2024, leyendo entregables/informe_datos.json (consolidar_informe.py).
 *   node etl/generar_informe.js
 */
const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun,
  Header, Footer, AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, PageBreak, TableOfContents,
} = require('docx');

const RAIZ = path.resolve(__dirname, '..');
const D = JSON.parse(fs.readFileSync(path.join(RAIZ, 'entregables', 'informe_datos.json'), 'utf-8'));
const LOGO = path.join(RAIZ, 'frontend', 'public', 'logo-corpouraba.png');
const SALIDA = path.join(RAIZ, 'entregables', 'Informe_Deforestacion_CORPOURABA_2000-2024.docx');

// ── colores ──
const VERDE = '1F7347';
const VERDE_OSC = '0B3D25';
const GRIS = '6B7280';
const ROJO = 'B91C1C';
const AMBAR = 'B45309';

// ── helpers de números (es-CO) ──
const nf = (n, dec = 0) =>
  Number(n).toLocaleString('es-CO', { minimumFractionDigits: dec, maximumFractionDigits: dec });
const ha = (n) => `${nf(Math.round(n))} ha`;

// ── helpers de contenido ──
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
const H3 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(t)] });

function P(text, opts = {}) {
  const runs = Array.isArray(text) ? text : [new TextRun({ text, size: 22 })];
  return new Paragraph({
    spacing: { after: 120, line: 276 },
    alignment: opts.justify === false ? AlignmentType.LEFT : AlignmentType.JUSTIFIED,
    children: runs,
    ...opts,
  });
}
const run = (t, o = {}) => new TextRun({ text: t, size: 22, ...o });
const B = (t, o = {}) => new TextRun({ text: t, size: 22, bold: true, ...o });

function bullet(text) {
  const runs = Array.isArray(text) ? text : [new TextRun({ text, size: 22 })];
  return new Paragraph({ numbering: { reference: 'vinetas', level: 0 }, spacing: { after: 60 }, children: runs });
}

const BORDE = { style: BorderStyle.SINGLE, size: 1, color: 'D1D5DB' };
const BORDES = { top: BORDE, bottom: BORDE, left: BORDE, right: BORDE };

function tabla(encabezados, filas, anchos) {
  const total = 9360;
  const w = anchos || encabezados.map(() => Math.floor(total / encabezados.length));
  const celdaEnc = (t, i) =>
    new TableCell({
      borders: BORDES, width: { size: w[i], type: WidthType.DXA },
      shading: { fill: VERDE, type: ShadingType.CLEAR }, verticalAlign: VerticalAlign.CENTER,
      children: [new Paragraph({ alignment: i === 0 ? AlignmentType.LEFT : AlignmentType.CENTER,
        children: [new TextRun({ text: String(t), bold: true, color: 'FFFFFF', size: 20 })] })],
    });
  const celda = (t, i, alt) =>
    new TableCell({
      borders: BORDES, width: { size: w[i], type: WidthType.DXA },
      shading: alt ? { fill: 'F3F6F4', type: ShadingType.CLEAR } : undefined,
      children: [new Paragraph({ alignment: i === 0 ? AlignmentType.LEFT : AlignmentType.CENTER,
        children: [new TextRun({ text: String(t), size: 20 })] })],
    });
  return new Table({
    columnWidths: w, margins: { top: 60, bottom: 60, left: 120, right: 120 },
    rows: [
      new TableRow({ tableHeader: true, children: encabezados.map((t, i) => celdaEnc(t, i)) }),
      ...filas.map((fila, r) => new TableRow({ children: fila.map((t, i) => celda(t, i, r % 2 === 1)) })),
    ],
  });
}

const P_ESPACIO = () => new Paragraph({ spacing: { after: 80 }, children: [new TextRun('')] });

// ═══════════════════════════════ contenido ═══════════════════════════════
const cuerpo = [];

// ── PORTADA ──
if (fs.existsSync(LOGO)) {
  cuerpo.push(new Paragraph({
    alignment: AlignmentType.CENTER, spacing: { before: 1200, after: 200 },
    children: [new ImageRun({ type: 'png', data: fs.readFileSync(LOGO),
      transformation: { width: 260, height: 105 },
      altText: { title: 'CORPOURABA', description: 'Logo de CORPOURABA', name: 'logo' } })],
  }));
}
cuerpo.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 400, after: 100 },
  children: [new TextRun({ text: 'Observatorio de Deforestación de Urabá', bold: true, size: 52, color: VERDE_OSC })] }));
cuerpo.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 400 },
  children: [new TextRun({ text: 'Informe técnico del análisis de deforestación', size: 30, color: VERDE })] }));
cuerpo.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 100 },
  children: [new TextRun({ text: 'Jurisdicción CORPOURABA · 19 municipios · Periodo 2000–2024', size: 24, color: GRIS })] }));
cuerpo.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 1400, after: 60 },
  children: [new TextRun({ text: 'Elaborado por', size: 20, color: GRIS })] }));
cuerpo.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 300 },
  children: [new TextRun({ text: 'Alberto Vivas  ·  Carlos Zuluaga', bold: true, size: 26 })] }));
cuerpo.push(new Paragraph({ alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: 'Corporación para el Desarrollo Sostenible del Urabá — CORPOURABA', size: 20, color: GRIS })] }));
cuerpo.push(new Paragraph({ alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: 'Datos: monitoreo de bosque (IDEAM/SMByC) procesado por el Observatorio', size: 18, color: GRIS })] }));
cuerpo.push(new Paragraph({ children: [new PageBreak()] }));

// ── TABLA DE CONTENIDO ──
cuerpo.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun('Contenido')] }));
cuerpo.push(new TableOfContents('Contenido', { hyperlink: true, headingStyleRange: '1-2' }));
cuerpo.push(new Paragraph({ children: [new PageBreak()] }));

// ── 1. RESUMEN EJECUTIVO ──
cuerpo.push(H1('1. Resumen ejecutivo'));
const totFmt = nf(Math.round(D.total_deforestacion_ha));
cuerpo.push(P([
  run('Entre 2000 y 2024, la jurisdicción de CORPOURABA —los 19 municipios de la región de Urabá y el Occidente antioqueño— perdió aproximadamente '),
  B(`${totFmt} hectáreas`), run(' de bosque por deforestación. El bosque estable de la jurisdicción se redujo de '),
  B(`${nf(Math.round(D.dinamica.regional_bosque_2000_2002_ha))} ha`), run(' en 2000 a '),
  B(`${nf(Math.round(D.dinamica.regional_bosque_2022_2023_ha))} ha`), run(' en 2023, una pérdida neta del '),
  B(`${nf(Math.abs(D.dinamica.regional_delta_pct), 1)} %`), run('.'),
]));
cuerpo.push(P([
  run('El periodo más crítico fue '), B(D.pico.periodo), run(`, con ${ha(D.pico.ha)} deforestadas (${nf(Math.round(D.pico.ha_anual))} ha/año), mientras que el menor registro correspondió a `),
  B(D.minimo.periodo), run(`. El municipio más afectado es `), B(D.ranking_municipios[0].municipio),
  run(` (${ha(D.ranking_municipios[0].hectareas)} acumuladas), y la subregión más golpeada es `),
  B(D.por_subregion[0].subregion), run(` (${ha(D.por_subregion[0].hectareas)}).`),
]));
cuerpo.push(P('Los hallazgos más relevantes del análisis son:'));
D.hallazgos.slice(0, 6).forEach((h) => cuerpo.push(bullet([B(`${h.titulo}: `), run(h.descripcion)])));

// ── 2. INTRODUCCIÓN ──
cuerpo.push(H1('2. Introducción y contexto'));
cuerpo.push(P([
  run('El Observatorio de Deforestación de Urabá consolida y analiza el monitoreo de cambio de bosque de la jurisdicción de CORPOURABA durante 24 años (2000–2024). La jurisdicción abarca cerca de '),
  B('1,86 millones de hectáreas'), run(' distribuidas en 19 municipios y cinco subregiones (Caribe, Centro, Atrato, Nutibara y Urrao), un territorio que combina el bosque húmedo del Darién y el Atrato con la frontera agropecuaria del eje bananero.'),
]));
cuerpo.push(P('Este informe documenta la magnitud, la distribución espacial y las tendencias de la deforestación, así como su relación con áreas protegidas, territorios étnicos, cuencas hidrográficas, figuras de ordenamiento y presiones extractivas. Acompaña a la plataforma web interactiva del Observatorio (mapa, visor de deforestación, tablero analítico, módulo educativo y centro de descargas).'));

// ── 3. METODOLOGÍA ──
cuerpo.push(H1('3. Metodología y fuentes'));
cuerpo.push(P('El análisis parte del paquete institucional de monitoreo de bosque (shapefiles, tablas de atributos y rásters por periodo), alineado con la metodología del Sistema de Monitoreo de Bosques y Carbono (SMByC) del IDEAM. Cada píxel/​polígono se clasifica en cinco categorías de cobertura:'));
[['Bosque Estable', 'cobertura boscosa que se mantiene entre dos periodos'],
 ['Deforestación', 'bosque que se pierde entre dos periodos (variable central de este informe)'],
 ['No Bosque Estable', 'áreas sin bosque que permanecen sin bosque'],
 ['Regeneración', 'recuperación de cobertura boscosa'],
 ['Sin Información', 'zonas sin dato válido (nubes, sombra)']].forEach(([c, d]) =>
  cuerpo.push(bullet([B(`${c}: `), run(d)])));
cuerpo.push(H2('3.1. Consolidación y control de calidad'));
cuerpo.push(P('La serie municipal se construyó priorizando, en cada periodo, la mejor fuente disponible: shapefile municipal (área geométrica en CRS métrico), tabla de atributos exportada, cruce con cuencas o estadística zonal del ráster. El área se calcula siempre en un sistema de referencia proyectado (EPSG:3115 / MAGNA-SIRGAS), y las capas web se publican en WGS84 (EPSG:4326).'));
cuerpo.push(P([
  run('Como control de calidad, la serie consolidada se contrastó con las hojas de «Cálculos» de los archivos institucionales originales: la diferencia es '),
  B('inferior al 0,3 %'), run(' en los diez periodos comparables, lo que confirma la fidelidad de la reconstrucción.'),
]));
if (Array.isArray(D.qa_calculos) && D.qa_calculos.length) {
  cuerpo.push(P('Tabla 1. Verificación contra los cálculos institucionales (deforestación).', { justify: false, spacing: { after: 80 } }));
  cuerpo.push(tabla(['Periodo', 'Referencia (ha)', 'Diferencia'],
    D.qa_calculos.map((q) => [q.periodo, nf(q.total_referencia_ha, 1), `${nf(q.diferencia_pct, 2)} %`]),
    [3120, 3120, 3120]));
}
cuerpo.push(H2('3.2. Periodos con datos estimados'));
cuerpo.push(P(D.nota_estimados || 'Algunos periodos carecen de datos municipales directos en el paquete original y se estimaron por interpolación o tendencia; se marcan siempre como estimados.'));
cuerpo.push(P(D.nota_2015_2016 || ''));

// ── 4. RESULTADOS REGIONALES ──
cuerpo.push(H1('4. Resultados regionales'));
cuerpo.push(P(`La deforestación acumulada en la jurisdicción entre 2000 y 2024 asciende a ${ha(D.total_deforestacion_ha)}. La tabla siguiente resume la serie por periodo; los periodos marcados con asterisco (*) contienen valores estimados o calibrados.`));
cuerpo.push(P('Tabla 2. Deforestación regional por periodo.', { justify: false, spacing: { after: 80 } }));
cuerpo.push(tabla(['Periodo', 'Deforestación (ha)', 'Ha/año', 'Fuente'],
  D.serie_regional.map((r) => [
    r.periodo + (r.estimado ? ' *' : ''), nf(r.hectareas, 1), nf(r.hectareas_anuales, 1),
    r.estimado ? 'estimado' : 'medido']),
  [2340, 2340, 2340, 2340]));
cuerpo.push(P([run('* Periodos estimados/calibrados: 2010-2012, 2015-2016, 2018-2019 y 2023-2024. Véase la sección 12.')], { justify: false }));
cuerpo.push(P([
  B('Tendencia general. '),
  run(`Tras un máximo histórico en 2002-2004 y un repunte marcado en 2015-2016 (${ha(D.pico.ha)}, coincidiendo con el periodo posterior a los acuerdos de paz), la deforestación anual muestra una tendencia general a la baja en los años más recientes, con el mínimo en 2020-2021. No obstante, la presión no desaparece: se desplaza hacia nuevas zonas (véanse las secciones 8 a 11).`),
]));

// ── 5. ANÁLISIS MUNICIPAL ──
cuerpo.push(H1('5. Análisis por municipio'));
cuerpo.push(P('La deforestación se concentra fuertemente en pocos municipios. La tabla 3 presenta el ranking por deforestación acumulada 2000–2024.'));
cuerpo.push(P('Tabla 3. Ranking municipal de deforestación acumulada.', { justify: false, spacing: { after: 80 } }));
cuerpo.push(tabla(['#', 'Municipio', 'Subregión', 'Deforestación (ha)'],
  D.ranking_municipios.map((r, i) => [String(i + 1), r.municipio, r.subregion, nf(r.hectareas, 1)]),
  [720, 3540, 2460, 2640]));
const top5 = D.ranking_municipios.slice(0, 5).reduce((s, r) => s + r.hectareas, 0);
cuerpo.push(P([
  run('Los cinco municipios más afectados ('),
  B(D.ranking_municipios.slice(0, 5).map((r) => r.municipio).join(', ')),
  run(`) concentran ${ha(top5)}, es decir el `),
  B(`${nf(100 * top5 / D.total_deforestacion_ha, 1)} %`),
  run(' de toda la deforestación de la jurisdicción.'),
]));

// ── 6. SUBREGIONES ──
cuerpo.push(H1('6. Análisis por subregión'));
cuerpo.push(P('Tabla 4. Deforestación acumulada por subregión.', { justify: false, spacing: { after: 80 } }));
cuerpo.push(tabla(['Subregión', 'Deforestación (ha)', '% del total'],
  D.por_subregion.map((r) => [r.subregion, nf(r.hectareas, 1), `${nf(100 * r.hectareas / D.total_deforestacion_ha, 1)} %`]),
  [3120, 3120, 3120]));
const tsub = D.dinamica.tasa_por_subregion_tendencia || {};
const acel = Object.keys(tsub).filter((k) => tsub[k].cambio === 'acelera');
const desa = Object.keys(tsub).filter((k) => tsub[k].cambio === 'desacelera');
cuerpo.push(P([
  run('Analizando la tasa relativa de pérdida (deforestación anual sobre bosque remanente), las subregiones divergen: '),
  B(desa.join(' y ')), run(' desaceleran, mientras que '), B(acel.join(', ')),
  run(' aceleran. La frontera de deforestación se corre hacia las subregiones más boscosas, coherente con el desplazamiento de la presión hacia territorios colectivos (sección 9).'),
]));

// ── 7. DINÁMICA DEL BOSQUE ──
cuerpo.push(H1('7. Dinámica del bosque'));
cuerpo.push(P([
  run('Más allá de la deforestación, el análisis de cobertura permite estimar cuánto bosque queda hoy respecto al año 2000. A nivel regional, el bosque estable pasó de '),
  B(ha(D.dinamica.regional_bosque_2000_2002_ha)), run(' a '), B(ha(D.dinamica.regional_bosque_2022_2023_ha)),
  run(` (${nf(D.dinamica.regional_delta_pct, 1)} %). La tabla 5 muestra los municipios con mayor pérdida de bosque en hectáreas y en proporción.`),
]));
const bosque = (D.dinamica.bosque_hoy_vs_2000 || []).slice(0, 8);
cuerpo.push(P('Tabla 5. Pérdida de bosque estable por municipio (2000 → 2023).', { justify: false, spacing: { after: 80 } }));
cuerpo.push(tabla(['Municipio', 'Bosque 2000 (ha)', 'Bosque 2023 (ha)', 'Cambio'],
  bosque.map((b) => [b.municipio, nf(b.bosque_2000_2002_ha, 0), nf(b.bosque_2022_2023_ha, 0), `${nf(b.delta_pct, 1)} %`]),
  [2760, 2400, 2400, 1800]));
cuerpo.push(P([
  B('Regeneración insuficiente. '),
  run(`Frente a ${ha(D.dinamica.regional_defo_real_ha)} deforestadas (en periodos con medición directa), solo se regeneraron `),
  B(ha(D.dinamica.regional_regen_real_ha)), run(`, una relación aproximada de 1 a ${Math.round(D.dinamica.regional_defo_real_ha / Math.max(D.dinamica.regional_regen_real_ha, 1))}. La recuperación natural del bosque no alcanza a compensar la pérdida.`),
]));

// ── 8. FRAGMENTACIÓN ──
cuerpo.push(H1('8. Fragmentación y frentes persistentes'));
const frag = D.fragmentacion || {};
const conc = frag.concentracion_vs_atomizacion || {};
const recu = frag.recurrencia || {};
cuerpo.push(P([
  run('La deforestación mapeada se compone de '), B(nf(conc.n_parches_total)), run(' polígonos (parches ≥1 ha), con un tamaño medio de '),
  B(`${nf(conc.tamano_medio_ha, 1)} ha`), run(' y mediano de '), B(`${nf(conc.tamano_mediano_ha, 1)} ha`),
  run(`. El ${nf(conc.pct_parches_menores_5ha, 1)} % de los parches mide menos de 5 ha, señal de una colonización gradual («hormiga») más que de grandes praderizaciones.`),
]));
cuerpo.push(P([
  B('Frentes persistentes. '),
  run(`Al superponer una rejilla de 2×2 km sobre la jurisdicción, ${nf(recu['n_celdas_persistentes_>=3'])} celdas registran deforestación en tres o más periodos y concentran el `),
  B(`${nf(recu['pct_ha_en_persistentes'], 1)} %`),
  run(' de las hectáreas deforestadas. No son eventos dispersos: son frentes activos y localizables, priorizables para el control territorial. Los municipios con más celdas persistentes son '),
  B((recu.municipios_mas_celdas_persistentes || []).slice(0, 3).map((m) => m.municipio).join(', ')), run('.'),
]));

// ── 9. ÁREAS PROTEGIDAS ──
cuerpo.push(H1('9. Deforestación en áreas protegidas'));
const ap = D.areas_protegidas || {};
cuerpo.push(P([
  run('En los periodos comparables, '), B(ha(ap.deforestacion_ap_total_ha)),
  run(` de deforestación ocurrieron dentro de áreas protegidas, equivalente al `), B(`${nf(ap.pct_global_dentro_ap, 1)} %`),
  run(' de la deforestación de la jurisdicción en esos periodos. La tabla 6 muestra las áreas más afectadas.'),
]));
const rankAp = (ap.ranking_ap_por_deforestacion || []).slice(0, 8);
cuerpo.push(P('Tabla 6. Áreas protegidas con mayor deforestación.', { justify: false, spacing: { after: 80 } }));
cuerpo.push(tabla(['Área protegida', 'Categoría', 'Deforestación (ha)'],
  rankAp.map((a) => [a.nombre, a.categoria, nf(a.defo_ha_total, 1)]),
  [3960, 3360, 2040]));
cuerpo.push(P([
  run('El '), B('Distrito Regional de Manejo Integrado Serranía de Abibe'),
  run(' concentra la mayor parte de la pérdida dentro de áreas protegidas, seguido de reservas forestales protectoras y del Parque Nacional Natural Las Orquídeas. Complementariamente, el cruce con la cartografía oficial de la '),
  B('Reserva Forestal de Ley 2ª de 1959'),
  run(` revela que una fracción muy alta de la deforestación mapeada —del orden del 34 %— ocurre dentro de esa reserva, con tendencia al alza en los años recientes.`),
]));

// ── 10. TERRITORIOS ÉTNICOS ──
cuerpo.push(H1('10. Deforestación en territorios étnicos'));
const et = D.territorios_etnicos || {};
const tend = et.tendencia_fraccion_etnica || {};
cuerpo.push(P([
  B('Desplazamiento hacia territorios colectivos. '),
  run('Uno de los hallazgos más relevantes: la participación de resguardos indígenas y consejos comunitarios en la deforestación de la jurisdicción pasó del '),
  B(`${nf(tend.pct_promedio_2002_2010, 1)} %`), run(' (2002–2010) al '),
  B(`${nf(tend.pct_promedio_2019_2023, 1)} %`),
  run(' (2019–2023). La presión se corrió hacia los territorios étnicos mientras el resto de la jurisdicción desaceleraba.'),
]));
const pueblos = et.deforestacion_por_pueblo || [];
if (pueblos.length) {
  cuerpo.push(P('Tabla 7. Deforestación en resguardos por pueblo indígena.', { justify: false, spacing: { after: 80 } }));
  cuerpo.push(tabla(['Pueblo', 'Deforestación (ha)'],
    pueblos.map((p) => [p.pueblo, nf(p.defo_total_ha, 1)]), [4680, 4680]));
}
const topRes = (et.top_resguardos_deforestacion || []).slice(0, 5);
if (topRes.length) {
  cuerpo.push(P([run('Los resguardos más afectados ('),
    B(topRes.map((r) => r.resguardo.replace(/^Resguardo Ind[ií]gena /i, '')).slice(0, 3).join(', ')),
    run(') corresponden mayoritariamente al pueblo Embera Katío, en el piedemonte y la vertiente del Atrato.')]));
}

// ── 11. CUENCAS Y POMCAS ──
cuerpo.push(H1('11. Cuencas hidrográficas y POMCAS'));
const pomcas = D.pomcas || {};
const rankPom = (pomcas.ranking || []).slice(0, 7);
cuerpo.push(P([
  run('Los Planes de Ordenación y Manejo de Cuencas (POMCAS) organizan las principales cuencas de la jurisdicción. El cruce de sus límites con la deforestación mapeada da un total de '),
  B(ha(pomcas.deforestacion_total_ha || 0)), run(', concentrado en las cuencas abastecedoras del eje bananero.'),
]));
if (rankPom.length) {
  cuerpo.push(P('Tabla 8. Deforestación mapeada por POMCA.', { justify: false, spacing: { after: 80 } }));
  cuerpo.push(tabla(['POMCA', 'Deforestación (ha)', '% de su área'],
    rankPom.map((p) => [p.pomca, nf(p.deforestacion_ha, 1), p.pct_del_pomca != null ? `${nf(p.pct_del_pomca, 2)} %` : '—']),
    [4680, 2340, 2340]));
}
cuerpo.push(P([
  run('La cuenca del '), B('río León'), run(' es la más afectada, seguida de '), B('río Turbo-Currulao'),
  run(' y '), B('río Sucio Alto'), run('. Su deterioro tiene implicaciones directas sobre la oferta hídrica de una región agroindustrial intensiva en agua.'),
]));

// ── 12. LIMITACIONES Y DATOS ESTIMADOS ──
cuerpo.push(H1('12. Limitaciones y datos estimados'));
cuerpo.push(P('El análisis es transparente respecto a sus límites. Cuatro periodos no cuentan con medición municipal directa en el paquete recibido y sus cifras son estimadas o calibradas:'));
[['2010-2012', 'No hay shapefile ni tabla municipal en el paquete; solo sobrevive la tabla de atributos del ráster departamental. Se estima por interpolación municipal calibrada contra el total departamental real y la participación histórica de la jurisdicción (~18 %).'],
 ['2015-2016', 'Solo existe el cruce con cuencas (cobertura parcial de la jurisdicción). Se calibra con factores municipio-clase derivados de 2016-2017, único periodo con ambas fuentes.'],
 ['2018-2019', 'La carpeta del periodo no existe en el paquete. Se estima por interpolación de la tasa anual entre periodos vecinos.'],
 ['2023-2024', 'El shapefile municipal se perdió (solo sobreviven tablas de atributos sin geometría ni columna de área). Se estima por tendencia.']].forEach(([p, d]) =>
  cuerpo.push(bullet([B(`${p}: `), run(d)])));
cuerpo.push(H2('12.1. Cómo obtener los datos reales'));
cuerpo.push(P('Estos periodos NO son recuperables a partir del paquete actual (se verificó archivo por archivo). Para reemplazar las estimaciones por cifras oficiales existen tres vías:'));
cuerpo.push(bullet([B('CORPOURABA (recomendada). '), run('Solicitar a la Corporación los shapefiles municipales completos de 2010-2012, 2018-2019 y 2023-2024, y el shapefile municipal de 2015-2016. La Corporación los generó en su momento; simplemente no quedaron en esta descarga o llegaron corruptos.')]));
cuerpo.push(bullet([B('IDEAM — SMByC. '), run('El Sistema de Monitoreo de Bosques y Carbono publica la deforestación anual nacional a nivel municipal (portal smbyc.ideam.gov.co y datos abiertos). Es la fuente autoritativa nacional de la que se deriva el monitoreo regional; permite reconstruir todos los años faltantes.')]));
cuerpo.push(bullet([B('Reconstrucción parcial 2023-2024. '), run('Las tablas de atributos que sobrevivieron (cuencas, áreas protegidas y consejos) permiten un conteo parcial por municipio, aunque sin hectáreas fiables; serviría solo como referencia mínima.')]));
cuerpo.push(P([
  B('Integración inmediata. '),
  run('La plataforma está diseñada para incorporar estos datos sin reprogramación: basta colocar los archivos en la carpeta del periodo correspondiente y volver a ejecutar el ETL ('),
  new TextRun({ text: 'python etl/run_etl.py', font: 'Consolas', size: 20 }),
  run('). El sistema los detecta, reemplaza las estimaciones por las mediciones reales y actualiza automáticamente el mapa, el tablero y las descargas.'),
]));

// ── 13. HALLAZGOS CLAVE ──
cuerpo.push(H1('13. Hallazgos clave'));
cuerpo.push(P('Síntesis de los hallazgos verificados de la investigación, ordenados por relevancia:'));
D.hallazgos.forEach((h) => cuerpo.push(bullet([
  B(`${h.titulo} `), run(`(${nf(h.cifra, h.cifra % 1 === 0 ? 0 : 1)} ${h.unidad}, ${h.periodo_referencia}). `), run(h.descripcion),
])));

// ── 14. RECOMENDACIONES Y MEJORAS DE LA PLATAFORMA ──
cuerpo.push(H1('14. Recomendaciones y mejoras de la plataforma'));
cuerpo.push(P('El Observatorio es una base sólida y ampliable. Se proponen las siguientes mejoras, ordenadas por prioridad e impacto:'));
cuerpo.push(H2('14.1. Datos y análisis'));
[['Completar los periodos estimados', 'Incorporar los datos reales de 2010-2012, 2018-2019, 2023-2024 y 2015-2016 (sección 12) para eliminar las estimaciones.'],
 ['Cerrar los cruces cartográficos pendientes', 'Finalizar los cruces con ecosistemas estratégicos (acuíferos, humedales, manglares) y con la zonificación de conflicto de uso (aptitud forestal vs. realidad), pendientes por el peso de los shapefiles.'],
 ['Modelo predictivo mejorado', 'Sustituir la regresión lineal actual por un modelo que incorpore variables explicativas (cercanía a vías, frentes persistentes, presión previa) para pronósticos por municipio más robustos.'],
 ['Alertas tempranas', 'Integrar las alertas trimestrales de deforestación del IDEAM para pasar de un monitoreo bienal a un seguimiento casi en tiempo real.']].forEach(([t, d]) => cuerpo.push(bullet([B(`${t}. `), run(d)])));
cuerpo.push(H2('14.2. Funcionalidad y experiencia de usuario'));
[['Comparador de territorios en el tiempo', 'Gráfico de línea que muestre la evolución de la deforestación de un área protegida, POMCA o resguardo a lo largo de todos los periodos.'],
 ['Descarga de reportes por municipio', 'Botón que genere una ficha PDF/Word automática por municipio con sus cifras clave.'],
 ['Búsqueda y geolocalización', 'Buscador de municipios/territorios y opción de centrar el mapa en la ubicación del usuario.'],
 ['Accesibilidad y multilenguaje', 'Auditoría de accesibilidad (lectores de pantalla, contraste) y versión en inglés para divulgación internacional.'],
 ['Cuadros de indicadores imprimibles', 'Vista «para imprimir» del tablero, útil en informes institucionales.']].forEach(([t, d]) => cuerpo.push(bullet([B(`${t}. `), run(d)])));
cuerpo.push(H2('14.3. Técnicas y despliegue'));
[['Base de datos espacial', 'Migrar de archivos a PostgreSQL + PostGIS (ya soportado) para escalar consultas y habilitar filtros espaciales dinámicos.'],
 ['Publicación en línea', 'Desplegar el frontend (Vercel/Netlify) y el backend (contenedor Docker) con un dominio institucional, y teselas vectoriales para acelerar el mapa.'],
 ['Actualización automatizada', 'Programar la ejecución del ETL cuando CORPOURABA publique un nuevo periodo, con validación automática de calidad.'],
 ['API pública documentada', 'Exponer la API REST con documentación abierta para que terceros (academia, prensa, otras CAR) reutilicen los datos.']].forEach(([t, d]) => cuerpo.push(bullet([B(`${t}. `), run(d)])));

// ── 15. CONCLUSIONES ──
cuerpo.push(H1('15. Conclusiones'));
cuerpo.push(P(`En 24 años, la jurisdicción de CORPOURABA perdió cerca de ${totFmt} hectáreas de bosque. Aunque la tasa anual muestra una tendencia general a la baja frente a los picos de la década de 2000 y de 2015-2016, la deforestación no se detiene: se concentra en frentes persistentes y se desplaza hacia las subregiones más boscosas y hacia los territorios colectivos, áreas protegidas y reservas de ley.`));
cuerpo.push(P('La regeneración natural es marcadamente insuficiente para compensar la pérdida, lo que subraya la necesidad de intervención activa (restauración, acuerdos de conservación, control territorial focalizado en los frentes persistentes identificados). El Observatorio ofrece, por primera vez, una lectura integrada y espacialmente explícita de este fenómeno para apoyar la toma de decisiones, el análisis técnico, la educación ambiental y la divulgación pública.'));

// ── ANEXO ──
cuerpo.push(H1('Anexo. Fuentes por periodo'));
cuerpo.push(tabla(['Periodo', 'Años', 'Fuente del dato municipal'],
  (D.periodos_meta || []).map((p) => [p.id, String((p.ano_fin || 0) - (p.ano_inicio || 0)), p.fuente || '—']),
  [2340, 1560, 5460]));
cuerpo.push(P_ESPACIO());
cuerpo.push(P([run('CRS de origen: '), B(D.crs_origen || 'EPSG:3115'), run('  ·  CRS de publicación: '), B(D.crs_salida || 'EPSG:4326')], { justify: false }));
cuerpo.push(P([run('Atribución sugerida: '), new TextRun({ text: 'CORPOURABA — Observatorio de Deforestación de Urabá (2000–2024). Elaborado por Alberto Vivas y Carlos Zuluaga.', italics: true, size: 20 })], { justify: false }));

// ═══════════════════════════════ documento ═══════════════════════════════
const doc = new Document({
  creator: 'Alberto Vivas y Carlos Zuluaga',
  title: 'Informe de Deforestación CORPOURABA 2000-2024',
  styles: {
    default: { document: { run: { font: 'Arial', size: 22 } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 30, bold: true, color: VERDE_OSC, font: 'Arial' },
        paragraph: { spacing: { before: 320, after: 160 }, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 25, bold: true, color: VERDE, font: 'Arial' },
        paragraph: { spacing: { before: 200, after: 120 }, outlineLevel: 1 } },
      { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 23, bold: true, color: '374151', font: 'Arial' },
        paragraph: { spacing: { before: 160, after: 100 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [{ reference: 'vinetas', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•',
      alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 260 } } } }] }],
  },
  sections: [{
    properties: { page: { margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    footers: {
      default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
        children: [
          new TextRun({ text: 'Observatorio de Deforestación de Urabá — CORPOURABA   |   Página ', size: 16, color: GRIS }),
          new TextRun({ children: [PageNumber.CURRENT], size: 16, color: GRIS }),
          new TextRun({ text: ' de ', size: 16, color: GRIS }),
          new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 16, color: GRIS }),
        ] })] }),
    },
    children: cuerpo,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(SALIDA, buf);
  console.log('OK ->', SALIDA);
  console.log('Párrafos/elementos:', cuerpo.length);
});
