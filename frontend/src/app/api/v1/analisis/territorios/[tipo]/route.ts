import { json, errorJson } from '@/server/datos';
import { territorios } from '@/server/analisis';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export function GET(request: Request, { params }: { params: { tipo: string } }) {
  try {
    const q = new URL(request.url).searchParams;
    return json(territorios(params.tipo, q.get('periodo')));
  } catch (e) {
    return errorJson(e);
  }
}
