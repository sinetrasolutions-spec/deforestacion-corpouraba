import { json, errorJson } from '@/server/datos';
import { catalogoAnalisis } from '@/server/analisis';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export function GET() {
  try {
    return json(catalogoAnalisis());
  } catch (e) {
    return errorJson(e);
  }
}
