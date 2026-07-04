import { datos, json, errorJson, NOMBRES_CAPAS } from '@/server/datos';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export function GET() {
  try {
    const capas = datos.capas();
    return json({
      capas: Object.entries(capas).map(([id, fc]) => ({
        id, nombre: NOMBRES_CAPAS[id] ?? id, unidades: (fc.features ?? []).length,
      })),
    });
  } catch (e) {
    return errorJson(e);
  }
}
