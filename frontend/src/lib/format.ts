/**
 * Formateo de números con convención colombiana (es-CO): punto de miles,
 * coma decimal. Firmas exactas según SPEC §6.3.
 */

/** Formatea un número en es-CO con `dec` decimales (0 por defecto). */
export function fmtNum(n: number, dec?: number): string {
  const decimales = dec ?? 0;
  return new Intl.NumberFormat('es-CO', {
    minimumFractionDigits: decimales,
    maximumFractionDigits: decimales,
  }).format(n);
}

/** Hectáreas sin decimales con unidad, p. ej. 3938.2 → '3.938 ha'. */
export function fmtHa(n: number): string {
  return `${fmtNum(Math.round(n))} ha`;
}

/** Porcentaje con un decimal, p. ej. 22.22 → '22,2 %'. */
export function fmtPct(n: number): string {
  return `${fmtNum(n, 1)} %`;
}
