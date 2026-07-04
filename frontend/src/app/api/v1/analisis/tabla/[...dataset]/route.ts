import { json, errorJson } from '@/server/datos';
import { tablaAnalisis } from '@/server/analisis';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export function GET(request: Request, { params }: { params: { dataset: string[] } }) {
  try {
    const q = new URL(request.url).searchParams;
    const dataset = params.dataset.join('/');
    return json(tablaAnalisis(dataset, {
      municipio: q.get('municipio'),
      periodo: q.get('periodo'),
      limite: q.get('limite') != null ? Number(q.get('limite')) : undefined,
    }));
  } catch (e) {
    return errorJson(e);
  }
}
