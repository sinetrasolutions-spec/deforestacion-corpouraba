import { datos, serieMunicipio, serieRegional, json, errorJson, CLASE_DEFORESTACION } from '@/server/datos';
import { calcularPrediccion } from '@/server/analitica';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export function GET(request: Request) {
  try {
    const q = new URL(request.url).searchParams;
    const municipio = q.get('municipio');
    const horizonte = q.get('horizonte') != null ? Number(q.get('horizonte')) : 3;

    let porPeriodo;
    if (municipio) {
      const codigo = datos.resolverMunicipio(municipio);
      porPeriodo = serieMunicipio(codigo, CLASE_DEFORESTACION).map((f) => ({
        periodo: f.periodo, ano_inicio: f.ano_inicio, ano_fin: f.ano_fin,
        hectareas_anuales: f.hectareas_anuales, estimado: f.estimado,
      }));
    } else {
      porPeriodo = serieRegional(CLASE_DEFORESTACION, true).map((f) => ({
        periodo: f.periodo, ano_inicio: f.ano_inicio, ano_fin: f.ano_fin,
        hectareas_anuales: f.hectareas_anuales, estimado: f.estimado,
      }));
    }
    return json(calcularPrediccion(porPeriodo, horizonte, false));
  } catch (e) {
    return errorJson(e);
  }
}
