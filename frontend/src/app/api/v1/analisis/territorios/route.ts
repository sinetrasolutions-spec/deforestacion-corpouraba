import { json, errorJson } from '@/server/datos';
import { catalogoTerritorios } from '@/server/analisis';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export function GET() {
  try {
    return json(catalogoTerritorios());
  } catch (e) {
    return errorJson(e);
  }
}
