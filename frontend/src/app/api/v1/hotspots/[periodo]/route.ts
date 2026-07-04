import { datos, json } from '@/server/datos';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export function GET(_request: Request, { params }: { params: { periodo: string } }) {
  const fc = datos.hotspots(params.periodo);
  if (fc === null) {
    return json(
      { detail: `No hay hotspots para el periodo '${params.periodo}'.`, disponibles: datos.hotspotsDisponibles() },
      404,
    );
  }
  return json(fc);
}
