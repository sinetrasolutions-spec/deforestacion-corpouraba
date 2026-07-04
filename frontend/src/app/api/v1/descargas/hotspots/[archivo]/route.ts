import { datos, json, errorJson } from '@/server/datos';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export function GET(_request: Request, { params }: { params: { archivo: string } }) {
  try {
    const periodo = params.archivo.replace(/\.geojson$/i, '');
    const fc = datos.hotspots(periodo);
    if (fc === null) {
      return json({ detail: `No hay hotspots para '${periodo}'.`, disponibles: datos.hotspotsDisponibles() }, 404);
    }
    return new Response(JSON.stringify(fc), {
      headers: {
        'content-type': 'application/geo+json',
        'content-disposition': `attachment; filename="hotspots_${periodo}.geojson"`,
      },
    });
  } catch (e) {
    return errorJson(e);
  }
}
