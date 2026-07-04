/**
 * Tipos compartidos del frontend — contrato EXACTO del SPEC §6.
 * Todos los módulos (mapa, dashboard, aprende, datos) importan de aquí.
 */

export type Clase = 'Bosque Estable'|'Deforestación'|'No Bosque Estable'|'Regeneración'|'Sin Información';

export interface Periodo { id: string; ano_inicio: number; ano_fin: number; anos: number; fuente: string; tiene_hotspots: boolean; }

export interface FilaSerie { codigo_dane: string; municipio: string; subregion: string; periodo: string; ano_inicio: number; ano_fin: number; clase: Clase; hectareas: number; hectareas_anuales: number; fuente: string; estimado: boolean; }

export interface ValorChoropleth { hectareas: number; hectareas_anuales: number; estimado: boolean; municipio: string; }

export interface Choropleth { periodo: string; metrica: 'hectareas'|'hectareas_anuales'; valores: Record<string, ValorChoropleth>; breaks: number[]; max: number; }

export interface Kpis { total_deforestado_ha: number; promedio_anual_ha: number; periodo_mas_critico: { periodo: string; hectareas: number; estimado: boolean }; municipio_mas_afectado: { municipio: string; codigo_dane: string; hectareas: number }; periodo_menor: { periodo: string; hectareas: number; estimado: boolean }; n_periodos: number; n_municipios: number; pct_datos_estimados: number; }

export interface ItemRanking { codigo_dane: string; municipio: string; subregion: string; hectareas: number; hectareas_anuales: number; estimado: boolean; posicion: number; }

export interface Prediccion { historico: { periodo: string; hectareas_anuales: number }[]; prediccion: { ano: number; hectareas_anuales_estimadas: number; intervalo: [number, number] }[]; metodo: string; advertencia: string; }

export type Subregion = 'Caribe'|'Centro'|'Atrato'|'Nutibara'|'Urrao';
