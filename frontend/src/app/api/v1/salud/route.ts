import { json, VERSION } from '@/server/datos';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export function GET() {
  return json({ estado: 'ok', version: VERSION, modo_datos: 'archivos' });
}
