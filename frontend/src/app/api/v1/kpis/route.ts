import { datos, json, errorJson, CLASE_DEFORESTACION } from '@/server/datos';
import { calcularKpis } from '@/server/analitica';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export function GET(request: Request) {
  try {
    const q = new URL(request.url).searchParams;
    const df = datos.serie().filter((f) => f.clase === CLASE_DEFORESTACION);
    return json(calcularKpis(df, q.get('incluir_estimados') !== 'false'));
  } catch (e) {
    return errorJson(e);
  }
}
