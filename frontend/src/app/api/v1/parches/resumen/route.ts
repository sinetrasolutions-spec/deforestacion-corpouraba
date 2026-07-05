import { json, errorJson } from '@/server/datos';
import { parchesResumen } from '@/server/analisis';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export function GET(request: Request) {
  try {
    const q = new URL(request.url).searchParams;
    return json(parchesResumen(q.get('municipio')));
  } catch (e) {
    return errorJson(e);
  }
}
