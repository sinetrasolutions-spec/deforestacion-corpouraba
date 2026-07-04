import { datos, serieMunicipio, json, errorJson, ErrorDatos, redondear } from '@/server/datos';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export function GET(request: Request) {
  try {
    const q = new URL(request.url).searchParams;
    const valores = (q.get('municipios') ?? '').split(',').map((v) => v.trim()).filter(Boolean);
    if (valores.length < 2 || valores.length > 6) {
      throw new ErrorDatos('Debe indicar entre 2 y 6 municipios separados por coma.', 422);
    }
    const data = valores.map((valor) => {
      const codigo = datos.resolverMunicipio(valor);
      return {
        municipio: datos.nombreMunicipio(codigo),
        codigo_dane: codigo,
        serie: serieMunicipio(codigo).map((f) => ({
          periodo: f.periodo, hectareas_anuales: redondear(f.hectareas_anuales), estimado: f.estimado,
        })),
      };
    });
    return json({ data });
  } catch (e) {
    return errorJson(e);
  }
}
