import { datos, errorJson } from '@/server/datos';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export function GET() {
  try {
    return new Response(JSON.stringify(datos.municipiosFc()), {
      headers: {
        'content-type': 'application/geo+json',
        'content-disposition': 'attachment; filename="municipios_corpouraba.geojson"',
      },
    });
  } catch (e) {
    return errorJson(e);
  }
}
