import { datos, json, errorJson, ErrorDatos, CLASE_DEFORESTACION } from '@/server/datos';
import { construirChoropleth } from '@/server/analitica';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export function GET(request: Request) {
  try {
    const q = new URL(request.url).searchParams;
    const periodo = q.get('periodo');
    if (!periodo) throw new ErrorDatos('Falta el parámetro periodo.', 422);
    datos.validarPeriodo(periodo);
    const metrica = (q.get('metrica') === 'hectareas_anuales' ? 'hectareas_anuales' : 'hectareas') as
      'hectareas' | 'hectareas_anuales';
    const filas = datos.serie().filter((f) => f.clase === CLASE_DEFORESTACION && f.periodo === periodo);
    return json(construirChoropleth(filas, periodo, metrica));
  } catch (e) {
    return errorJson(e);
  }
}
