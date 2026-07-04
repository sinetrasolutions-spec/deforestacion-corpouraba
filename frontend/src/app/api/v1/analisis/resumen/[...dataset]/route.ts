import { json, errorJson } from '@/server/datos';
import { resumenAnalisis } from '@/server/analisis';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export function GET(_request: Request, { params }: { params: { dataset: string[] } }) {
  try {
    return json(resumenAnalisis(params.dataset.join('/')));
  } catch (e) {
    return errorJson(e);
  }
}
