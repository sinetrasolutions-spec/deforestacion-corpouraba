import { datos, json, errorJson, CLASE_DEFORESTACION } from '@/server/datos';
import { calcularRanking } from '@/server/analitica';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export function GET(request: Request) {
  try {
    const q = new URL(request.url).searchParams;
    const periodo = q.get('periodo');
    const n = q.get('n') != null ? Number(q.get('n')) : 10;
    const metrica = (q.get('metrica') === 'hectareas_anuales' ? 'hectareas_anuales' : 'hectareas') as
      'hectareas' | 'hectareas_anuales';
    const df = datos.serie().filter((f) => f.clase === CLASE_DEFORESTACION);
    return json({ data: calcularRanking(df, periodo, n, metrica) });
  } catch (e) {
    return errorJson(e);
  }
}
