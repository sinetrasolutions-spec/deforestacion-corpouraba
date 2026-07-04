import { json, errorJson } from '@/server/datos';
import { geoAnalisis } from '@/server/analisis';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export function GET(_request: Request, { params }: { params: { dataset: string[] } }) {
  try {
    return json(geoAnalisis(params.dataset.join('/')));
  } catch (e) {
    return errorJson(e);
  }
}
