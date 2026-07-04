import { filtrarSerie, errorJson, redondear, CLASE_DEFORESTACION, type FilaSerie } from '@/server/datos';
import { csvSerie } from '@/server/descargas';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const COLS: (keyof FilaSerie)[] = [
  'codigo_dane', 'municipio', 'subregion', 'periodo', 'ano_inicio', 'ano_fin',
  'clase', 'hectareas', 'hectareas_anuales', 'fuente', 'estimado',
];

function agregarRegional(df: FilaSerie[]) {
  const map = new Map<string, Record<string, unknown>>();
  for (const f of df) {
    const e = (map.get(f.periodo) as { hectareas: number; hectareas_anuales: number; estimado: boolean } | undefined)
      ?? { periodo: f.periodo, ano_inicio: f.ano_inicio, ano_fin: f.ano_fin, clase: f.clase, hectareas: 0, hectareas_anuales: 0, estimado: false };
    e.hectareas += f.hectareas;
    e.hectareas_anuales += f.hectareas_anuales;
    e.estimado = e.estimado || f.estimado;
    map.set(f.periodo, e);
  }
  return [...map.values()]
    .sort((a, b) => Number(a.ano_inicio) - Number(b.ano_inicio))
    .map((e) => ({ ...e, hectareas: redondear(Number(e.hectareas)), hectareas_anuales: redondear(Number(e.hectareas_anuales)) }));
}

export function GET(request: Request) {
  try {
    const q = new URL(request.url).searchParams;
    const df = filtrarSerie({
      municipios: q.getAll('municipio'), subregion: q.get('subregion'),
      clase: q.get('clase') ?? CLASE_DEFORESTACION,
      desde: q.get('desde') != null ? Number(q.get('desde')) : null,
      hasta: q.get('hasta') != null ? Number(q.get('hasta')) : null,
      incluirEstimados: q.get('incluir_estimados') !== 'false',
    });
    const filtros: Record<string, unknown> = {
      municipio: q.getAll('municipio').join(', ') || null, subregion: q.get('subregion'),
      clase: q.get('clase') ?? CLASE_DEFORESTACION, desde: q.get('desde'), hasta: q.get('hasta'),
      incluir_estimados: q.get('incluir_estimados') !== 'false',
    };
    let filas: Record<string, unknown>[];
    let nombre = 'serie_deforestacion_corpouraba.csv';
    if (q.get('agregado') === 'regional') {
      filas = agregarRegional(df);
      filtros.agregado = 'regional';
      nombre = 'serie_regional_deforestacion_corpouraba.csv';
    } else {
      filas = df.map((f) => Object.fromEntries(COLS.map((c) => [c, f[c]])));
    }
    return new Response(csvSerie(filas, filtros), {
      headers: { 'content-type': 'text/csv; charset=utf-8', 'content-disposition': `attachment; filename="${nombre}"` },
    });
  } catch (e) {
    return errorJson(e);
  }
}
