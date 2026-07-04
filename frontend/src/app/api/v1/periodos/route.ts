import { periodos, json, errorJson } from '@/server/datos';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export function GET() {
  try {
    return json(periodos());
  } catch (e) {
    return errorJson(e);
  }
}
