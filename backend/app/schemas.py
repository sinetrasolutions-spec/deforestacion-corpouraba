"""Modelos Pydantic del contrato API (SPEC §5 y §6)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Metrica = Literal["hectareas", "hectareas_anuales"]


class Salud(BaseModel):
    """Respuesta de GET /salud."""

    estado: str
    version: str
    modo_datos: Literal["archivos", "postgis"]


class Periodo(BaseModel):
    """Un periodo de monitoreo (GET /periodos)."""

    id: str
    ano_inicio: int
    ano_fin: int
    anos: int
    fuente: str
    tiene_hotspots: bool


class FilaSerie(BaseModel):
    """Fila de la serie municipal (GET /serie)."""

    codigo_dane: str
    municipio: str
    subregion: str
    periodo: str
    ano_inicio: int
    ano_fin: int
    clase: str
    hectareas: float
    hectareas_anuales: float
    fuente: str
    estimado: bool


class RespuestaSerie(BaseModel):
    """Respuesta de GET /serie."""

    data: list[FilaSerie]
    total_ha: float
    nota: str | None = None


class FilaSerieRegional(BaseModel):
    """Fila de la serie regional (GET /serie/regional)."""

    periodo: str
    ano_inicio: int
    ano_fin: int
    hectareas: float
    hectareas_anuales: float
    estimado: bool


class RespuestaSerieRegional(BaseModel):
    """Respuesta de GET /serie/regional."""

    data: list[FilaSerieRegional]


class ValorChoropleth(BaseModel):
    """Valor por municipio en el choropleth."""

    hectareas: float
    hectareas_anuales: float
    estimado: bool
    municipio: str


class RespuestaChoropleth(BaseModel):
    """Respuesta de GET /choropleth."""

    periodo: str
    metrica: Metrica
    valores: dict[str, ValorChoropleth]
    breaks: list[float] = Field(..., min_length=5, max_length=5)
    max: float


class ItemRanking(BaseModel):
    """Posición del ranking de municipios (GET /ranking)."""

    codigo_dane: str
    municipio: str
    subregion: str
    hectareas: float
    hectareas_anuales: float
    estimado: bool
    posicion: int


class RespuestaRanking(BaseModel):
    """Respuesta de GET /ranking."""

    data: list[ItemRanking]


class PeriodoExtremo(BaseModel):
    """Periodo crítico o de menor deforestación en los KPIs."""

    periodo: str
    hectareas: float
    estimado: bool


class MunicipioAfectado(BaseModel):
    """Municipio más afectado en los KPIs."""

    municipio: str
    codigo_dane: str
    hectareas: float


class Kpis(BaseModel):
    """Respuesta de GET /kpis."""

    total_deforestado_ha: float
    promedio_anual_ha: float
    periodo_mas_critico: PeriodoExtremo
    municipio_mas_afectado: MunicipioAfectado
    periodo_menor: PeriodoExtremo
    n_periodos: int
    n_municipios: int
    pct_datos_estimados: float


class PuntoComparacion(BaseModel):
    """Punto de la serie en la comparación de municipios."""

    periodo: str
    hectareas_anuales: float
    estimado: bool


class MunicipioComparacion(BaseModel):
    """Serie de un municipio en GET /comparacion."""

    municipio: str
    codigo_dane: str
    serie: list[PuntoComparacion]


class RespuestaComparacion(BaseModel):
    """Respuesta de GET /comparacion."""

    data: list[MunicipioComparacion]


class CapaInfo(BaseModel):
    """Resumen de una capa de contexto (GET /capas)."""

    id: str
    nombre: str
    unidades: int


class RespuestaCapas(BaseModel):
    """Respuesta de GET /capas."""

    capas: list[CapaInfo]


class PuntoHistorico(BaseModel):
    """Punto histórico de la predicción."""

    periodo: str
    hectareas_anuales: float


class PuntoPrediccion(BaseModel):
    """Punto proyectado de la predicción."""

    ano: int
    hectareas_anuales_estimadas: float
    intervalo: tuple[float, float]


class RespuestaPrediccion(BaseModel):
    """Respuesta de GET /prediccion."""

    historico: list[PuntoHistorico]
    prediccion: list[PuntoPrediccion]
    metodo: str
    advertencia: str
