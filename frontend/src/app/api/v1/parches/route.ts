import { json, errorJson } from '@/server/datos';
import { parches } from '@/server/analisis';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export function GET(request: Request) {
  try {
    const q = new URL(request.url).searchParams;
    const minHa = q.get('min_ha') != null ? Number(q.get('min_ha')) : 0;
    return json(parches(q.get('periodo'), minHa, q.get('municipio')));
  } catch (e) {
    return errorJson(e);
  }
}
