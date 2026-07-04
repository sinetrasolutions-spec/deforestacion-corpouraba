import { serieRegional, json, errorJson, redondear } from '@/server/datos';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export function GET(request: Request) {
  try {
    const q = new URL(request.url).searchParams;
    const df = serieRegional(q.get('clase') ?? undefined, q.get('incluir_estimados') !== 'false');
    return json({
      data: df.map((f) => ({
        periodo: f.periodo, ano_inicio: f.ano_inicio, ano_fin: f.ano_fin,
        hectareas: redondear(f.hectareas), hectareas_anuales: redondear(f.hectareas_anuales),
        estimado: f.estimado,
      })),
    });
  } catch (e) {
    return errorJson(e);
  }
}
