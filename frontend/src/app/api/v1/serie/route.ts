import { filtrarSerie, datos, json, errorJson, redondear, type FilaSerie } from '@/server/datos';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const NOTA_EXCLUIDOS =
  'Se excluyeron los periodos estimados (2010-2012, 2015-2016, 2018-2019 y 2023-2024) del resultado.';

function nota(df: FilaSerie[], incluir: boolean): string | null {
  if (!incluir) return NOTA_EXCLUIDOS;
  if (df.some((f) => f.estimado)) {
    return (datos.metadata().nota_estimados as string) ?? 'El resultado incluye periodos estimados (estimado=True).';
  }
  return null;
}

export function GET(request: Request) {
  try {
    const q = new URL(request.url).searchParams;
    const incluir = q.get('incluir_estimados') !== 'false';
    const df = filtrarSerie({
      municipios: q.getAll('municipio'),
      subregion: q.get('subregion'),
      clase: q.get('clase') ?? undefined,
      desde: q.get('desde') != null ? Number(q.get('desde')) : null,
      hasta: q.get('hasta') != null ? Number(q.get('hasta')) : null,
      incluirEstimados: incluir,
    });
    return json({
      data: df.map((f) => ({
        codigo_dane: f.codigo_dane, municipio: f.municipio, subregion: f.subregion,
        periodo: f.periodo, ano_inicio: f.ano_inicio, ano_fin: f.ano_fin, clase: f.clase,
        hectareas: redondear(f.hectareas), hectareas_anuales: redondear(f.hectareas_anuales),
        fuente: f.fuente, estimado: f.estimado,
      })),
      total_ha: df.length ? redondear(df.reduce((s, f) => s + f.hectareas, 0)) : 0,
      nota: nota(df, incluir),
    });
  } catch (e) {
    return errorJson(e);
  }
}
