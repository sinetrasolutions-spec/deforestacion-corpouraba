import { datos, json, errorJson } from '@/server/datos';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export function GET() {
  try {
    return json(datos.subregionesFc());
  } catch (e) {
    return errorJson(e);
  }
}
