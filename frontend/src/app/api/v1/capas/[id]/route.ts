import { datos, json, errorJson, ErrorDatos } from '@/server/datos';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export function GET(_request: Request, { params }: { params: { id: string } }) {
  try {
    const fc = datos.capas()[params.id];
    if (!fc) {
      throw new ErrorDatos(`Capa desconocida: '${params.id}'. Disponibles: ${Object.keys(datos.capas()).join(', ')}.`, 404);
    }
    return json(fc);
  } catch (e) {
    return errorJson(e);
  }
}
