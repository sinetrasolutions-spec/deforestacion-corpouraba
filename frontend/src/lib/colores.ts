/**
 * Escala de color del choropleth de deforestación y tokens asociados.
 * Contrato EXACTO del SPEC §7.2 — el mapa y el heatmap dependen de esto.
 */

/** Rampa de 5 clases (amarillo pálido → rojo profundo), una por break. */
export const RAMPA_DEFORESTACION = ['#FEF3C7', '#FDBA74', '#F97316', '#DC2626', '#7F1D1D']; // 5 clases por breaks

/** Gris neutro para municipios sin dato en el periodo. */
export const COLOR_SIN_DATOS = '#E5E7EB';

/**
 * Devuelve el color de la rampa para un valor dado los breaks (p20..p100
 * del endpoint /choropleth). `undefined` o NaN → gris sin datos.
 */
export function colorPara(valor: number | undefined, breaks: number[]): string {
  if (valor === undefined || Number.isNaN(valor)) return COLOR_SIN_DATOS;
  const ultimo = RAMPA_DEFORESTACION[RAMPA_DEFORESTACION.length - 1];
  const n = Math.min(breaks.length, RAMPA_DEFORESTACION.length);
  for (let i = 0; i < n; i += 1) {
    if (valor <= breaks[i]) return RAMPA_DEFORESTACION[i];
  }
  return ultimo;
}

/**
 * Estilo distintivo para polígonos con dato ESTIMADO: borde discontinuo
 * y relleno más tenue (se combina con badge «estimado» en tooltips/leyenda).
 */
export const PATRON_ESTIMADO = { dashArray: '4 3', fillOpacity: 0.55 }; // polígonos estimados
