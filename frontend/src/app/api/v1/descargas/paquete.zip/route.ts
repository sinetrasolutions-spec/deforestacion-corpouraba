import { errorJson } from '@/server/datos';
import { zipPaquete } from '@/server/descargas';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const buf = await zipPaquete();
    return new Response(buf as unknown as BodyInit, {
      headers: {
        'content-type': 'application/zip',
        'content-disposition': 'attachment; filename="datos_deforestacion_corpouraba.zip"',
      },
    });
  } catch (e) {
    return errorJson(e);
  }
}
