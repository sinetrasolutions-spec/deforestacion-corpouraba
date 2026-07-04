/**
 * Cálculos analíticos del lado servidor (réplica de analytics.py):
 * breaks del choropleth, choropleth, ranking, KPIs y predicción lineal.
 */
import { type FilaSerie, redondear } from './datos';

export const METODO_PREDICCION = 'regresión lineal sobre tasa anual';
export const ADVERTENCIA_PREDICCION =
  'Proyección estadística de referencia (regresión lineal sobre la tasa anual histórica). ' +
  'No constituye una cifra oficial: la incertidumbre crece con el horizonte y la ' +
  'deforestación depende de factores no modelados.';
export const ADVERTENCIA_SERIE_CORTA =
  'Serie histórica insuficiente para ajustar una tendencia confiable; no se genera proyección.';

/** Cuantil por interpolación lineal (equivalente a numpy.quantile por defecto). */
function cuantil(ordenados: number[], q: number): number {
  if (ordenados.length === 1) return ordenados[0];
  const pos = (ordenados.length - 1) * q;
  const base = Math.floor(pos);
  const resto = pos - base;
  const siguiente = ordenados[base + 1] ?? ordenados[base];
  return ordenados[base] + resto * (siguiente - ordenados[base]);
}

/** Cortes de la escala choropleth (quantiles p20..p100 de los positivos). */
export function calcularBreaks(valores: (number | null | undefined)[]): number[] {
  const positivos = valores.filter((v): v is number => v != null && v > 0).sort((a, b) => a - b);
  if (positivos.length >= 5) {
    return [0.2, 0.4, 0.6, 0.8, 1.0].map((q) => redondear(cuantil(positivos, q)));
  }
  if (positivos.length) {
    const max = positivos[positivos.length - 1];
    return [0.2, 0.4, 0.6, 0.8, 1.0].map((f) => redondear(max * f));
  }
  return [1, 2, 3, 4, 5];
}

export function construirChoropleth(filas: FilaSerie[], periodo: string, metrica: 'hectareas' | 'hectareas_anuales') {
  const valores: Record<string, { hectareas: number; hectareas_anuales: number; estimado: boolean; municipio: string }> = {};
  for (const f of filas) {
    valores[f.codigo_dane] = {
      hectareas: redondear(f.hectareas),
      hectareas_anuales: redondear(f.hectareas_anuales),
      estimado: f.estimado,
      municipio: f.municipio,
    };
  }
  const medidas = Object.values(valores).map((v) => v[metrica]);
  return {
    periodo, metrica, valores,
    breaks: calcularBreaks(medidas),
    max: medidas.length ? redondear(Math.max(...medidas)) : 0,
  };
}

export function calcularRanking(
  df: FilaSerie[], periodo: string | null, n: number, metrica: 'hectareas' | 'hectareas_anuales',
) {
  let tabla: { codigo_dane: string; municipio: string; subregion: string; hectareas: number; hectareas_anuales: number; estimado: boolean }[];
  if (periodo != null) {
    tabla = df.filter((f) => f.periodo === periodo).map((f) => ({
      codigo_dane: f.codigo_dane, municipio: f.municipio, subregion: f.subregion,
      hectareas: f.hectareas, hectareas_anuales: f.hectareas_anuales, estimado: f.estimado,
    }));
  } else {
    const periodosVistos = new Map<string, [number, number]>();
    df.forEach((f) => periodosVistos.set(f.periodo, [f.ano_inicio, f.ano_fin]));
    let totalAnos = 0;
    periodosVistos.forEach(([i, fi]) => { totalAnos += fi - i; });
    totalAnos = totalAnos || 1;
    const map = new Map<string, { codigo_dane: string; municipio: string; subregion: string; hectareas: number; estimado: boolean }>();
    for (const f of df) {
      const e = map.get(f.codigo_dane) ?? { codigo_dane: f.codigo_dane, municipio: f.municipio, subregion: f.subregion, hectareas: 0, estimado: false };
      e.hectareas += f.hectareas;
      e.estimado = e.estimado || f.estimado;
      map.set(f.codigo_dane, e);
    }
    tabla = [...map.values()].map((e) => ({ ...e, hectareas_anuales: e.hectareas / totalAnos }));
  }
  return tabla
    .sort((a, b) => b[metrica] - a[metrica])
    .slice(0, n)
    .map((f, i) => ({
      codigo_dane: f.codigo_dane, municipio: f.municipio, subregion: f.subregion,
      hectareas: redondear(f.hectareas), hectareas_anuales: redondear(f.hectareas_anuales),
      estimado: f.estimado, posicion: i + 1,
    }));
}

export function calcularKpis(df: FilaSerie[], incluirEstimados: boolean) {
  const base = incluirEstimados ? df : df.filter((f) => !f.estimado);

  const porPeriodo = new Map<string, { periodo: string; ano_inicio: number; ano_fin: number; hectareas: number; estimado: boolean }>();
  for (const f of base) {
    const e = porPeriodo.get(f.periodo) ?? { periodo: f.periodo, ano_inicio: f.ano_inicio, ano_fin: f.ano_fin, hectareas: 0, estimado: false };
    e.hectareas += f.hectareas;
    e.estimado = e.estimado || f.estimado;
    porPeriodo.set(f.periodo, e);
  }
  const periodos = [...porPeriodo.values()];
  const total = base.reduce((s, f) => s + f.hectareas, 0);
  let anos = 0;
  periodos.forEach((p) => { anos += p.ano_fin - p.ano_inicio; });
  anos = anos || 1;

  const critico = periodos.reduce((a, b) => (b.hectareas > a.hectareas ? b : a), periodos[0]);
  const menor = periodos.reduce((a, b) => (b.hectareas < a.hectareas ? b : a), periodos[0]);

  const porMun = new Map<string, { codigo_dane: string; municipio: string; hectareas: number }>();
  for (const f of base) {
    const e = porMun.get(f.codigo_dane) ?? { codigo_dane: f.codigo_dane, municipio: f.municipio, hectareas: 0 };
    e.hectareas += f.hectareas;
    porMun.set(f.codigo_dane, e);
  }
  const municipios = [...porMun.values()];
  const afectado = municipios.reduce((a, b) => (b.hectareas > a.hectareas ? b : a), municipios[0]);

  const pctEst = df.length ? (100 * df.filter((f) => f.estimado).length) / df.length : 0;
  const nMun = new Set(df.map((f) => f.codigo_dane)).size;

  return {
    total_deforestado_ha: redondear(total),
    promedio_anual_ha: redondear(total / anos),
    periodo_mas_critico: { periodo: critico.periodo, hectareas: redondear(critico.hectareas), estimado: critico.estimado },
    municipio_mas_afectado: { municipio: afectado.municipio, codigo_dane: afectado.codigo_dane, hectareas: redondear(afectado.hectareas) },
    periodo_menor: { periodo: menor.periodo, hectareas: redondear(menor.hectareas), estimado: menor.estimado },
    n_periodos: periodos.length,
    n_municipios: nMun,
    pct_datos_estimados: redondear(pctEst, 1),
  };
}

/** Regresión lineal grado 1 (mínimos cuadrados) → [pendiente, intercepto]. */
function ajusteLineal(x: number[], y: number[]): [number, number] {
  const n = x.length;
  const sx = x.reduce((a, b) => a + b, 0);
  const sy = y.reduce((a, b) => a + b, 0);
  const sxx = x.reduce((a, b) => a + b * b, 0);
  const sxy = x.reduce((a, b, i) => a + b * y[i], 0);
  const m = (n * sxy - sx * sy) / (n * sxx - sx * sx);
  const b = (sy - m * sx) / n;
  return [m, b];
}

export function calcularPrediccion(
  porPeriodo: { periodo: string; ano_inicio: number; ano_fin: number; hectareas_anuales: number; estimado: boolean }[],
  horizonte: number, incluirEstimados: boolean,
) {
  const base = (incluirEstimados ? porPeriodo : porPeriodo.filter((p) => !p.estimado))
    .slice().sort((a, b) => a.ano_inicio - b.ano_inicio);
  const historico = base.map((p) => ({ periodo: p.periodo, hectareas_anuales: redondear(p.hectareas_anuales) }));

  if (base.length < 3) {
    return { historico, prediccion: [], metodo: METODO_PREDICCION, advertencia: ADVERTENCIA_SERIE_CORTA };
  }
  const x = base.map((p) => (p.ano_inicio + p.ano_fin) / 2);
  const y = base.map((p) => p.hectareas_anuales);
  const [m, b] = ajusteLineal(x, y);
  const residuales = y.map((yi, i) => yi - (m * x[i] + b));
  const media = residuales.reduce((a, c) => a + c, 0) / residuales.length;
  const sigma = Math.sqrt(residuales.reduce((a, c) => a + (c - media) ** 2, 0) / residuales.length);

  const ultimoAno = Math.max(...base.map((p) => p.ano_fin));
  const prediccion = [];
  for (let paso = 1; paso <= horizonte; paso += 1) {
    const ano = ultimoAno + paso;
    const valor = Math.max(m * ano + b, 0);
    prediccion.push({
      ano,
      hectareas_anuales_estimadas: redondear(valor),
      intervalo: [redondear(Math.max(valor - 1.96 * sigma, 0)), redondear(valor + 1.96 * sigma)],
    });
  }
  return { historico, prediccion, metodo: METODO_PREDICCION, advertencia: ADVERTENCIA_PREDICCION };
}
