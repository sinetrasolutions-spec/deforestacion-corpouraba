/**
 * Contenido educativo del módulo PRAES (SPEC §8.4), adaptado a 3 niveles.
 * Las cifras provienen de la serie validada (data/processed) y de los
 * hallazgos verificados de la investigación temática.
 */

export type Nivel = 'explorador' | 'guardian' | 'cientifico';

export const NIVELES: { id: Nivel; nombre: string; emoji: string; grado: string }[] = [
  { id: 'explorador', nombre: 'Explorador', emoji: '🌱', grado: 'Primaria' },
  { id: 'guardian', nombre: 'Guardián', emoji: '🌿', grado: 'Secundaria' },
  { id: 'cientifico', nombre: 'Científico', emoji: '🌳', grado: 'Media' },
];

export interface Seccion {
  id: string;
  titulo: string;
  texto: Record<Nivel, string>;
}

export const SECCIONES: Seccion[] = [
  {
    id: 'que-es',
    titulo: '¿Qué es la deforestación?',
    texto: {
      explorador:
        'La deforestación es cuando desaparecen los árboles de un bosque. Es como borrar la casa de muchos animales. En Urabá, entre 2000 y 2024 se perdió bosque equivalente a más de 60.000 canchas de fútbol.',
      guardian:
        'La deforestación es la pérdida permanente de bosque para convertir el terreno en potreros, cultivos o construcciones. En la jurisdicción de CORPOURABA se han perdido cerca de 46.845 hectáreas de bosque en 24 años. Una hectárea equivale a una cancha y media de fútbol.',
      cientifico:
        'La deforestación es la conversión de coberturas boscosas a otros usos del suelo, medida aquí como el cambio de «Bosque Estable» a otras clases entre periodos consecutivos. En CORPOURABA suman ≈46.845 ha (2000–2024); el bosque estable pasó de 908.114 ha a 870.305 ha, una pérdida neta del 4,2 %.',
    },
  },
  {
    id: 'por-que',
    titulo: '¿Por qué pasa en Urabá?',
    texto: {
      explorador:
        'Muchas veces se tumban árboles para tener pasto para las vacas, para sembrar o para abrir caminos. Cada vez que se abre una trocha nueva, el bosque se hace más pequeño.',
      guardian:
        'Las principales causas son la ganadería extensiva, la expansión de cultivos, la tala y la apertura de vías. La deforestación en Urabá suele avanzar en pequeños parches: el 92 % de ellos mide menos de 5 hectáreas, señal de colonización gradual.',
      cientifico:
        'Los motores directos son la praderización para ganadería, la frontera agrícola, la extracción de madera y la infraestructura vial. El patrón espacial es de atomización (mediana de parche cerca de 1 ha; tamaño medio ~1,6 ha), con frentes recurrentes en el piedemonte de la vía al mar (Mutatá–Dabeiba) activos en 11 de 12 periodos.',
    },
  },
  {
    id: 'impactos',
    titulo: 'Impactos en el territorio',
    texto: {
      explorador:
        'Sin árboles, animales como el jaguar, el tití y la guacamaya se quedan sin hogar. También se ensucian los ríos y hace más calor.',
      guardian:
        'La pérdida de bosque fragmenta el hábitat de especies como el jaguar y el tití gris, altera el ciclo del agua en cuencas abastecedoras y aumenta la erosión. La cuenca del río León, clave para el eje bananero, ha perdido 6.333 ha de bosque.',
      cientifico:
        'Los impactos incluyen pérdida de conectividad ecológica y biodiversidad, alteración de servicios hídricos (la cuenca del río León acumula 6.333 ha deforestadas, 2,9 % de su área), aumento de emisiones de carbono y presión sobre territorios colectivos, que pasaron de concentrar el 16,6 % de la deforestación (2002–2010) al 40,6 % (2019–2023).',
    },
  },
  {
    id: 'clima',
    titulo: 'Bosque y clima',
    texto: {
      explorador:
        'Los árboles respiran el aire malo (CO₂) y nos devuelven aire limpio. Si hay menos árboles, hay más aire malo y el planeta se calienta.',
      guardian:
        'Los bosques capturan dióxido de carbono (CO₂) y lo almacenan en la madera y el suelo. Al deforestar, ese carbono vuelve a la atmósfera y contribuye al calentamiento global. Proteger el bosque es una forma directa de mitigar el cambio climático.',
      cientifico:
        'Los bosques tropicales son sumideros netos de carbono; su remoción libera el carbono almacenado en biomasa y suelo (deforestación como fuente de emisiones) y reduce la capacidad de captura futura. La regeneración observada (726 ha) compensa apenas el 2 % de la pérdida medida, insuficiente para el balance de carbono.',
    },
  },
  {
    id: 'soluciones',
    titulo: 'Soluciones basadas en la naturaleza',
    texto: {
      explorador:
        'Podemos sembrar árboles, cuidar los que ya hay y aprender sobre el bosque. ¡Tu colegio puede tener su propio proyecto verde!',
      guardian:
        'La restauración de áreas degradadas, los sistemas agroforestales, los acuerdos de conservación y la educación ambiental (PRAES) ayudan a frenar la pérdida. Un colegio puede monitorear un bosque cercano, sembrar especies nativas y difundir estos datos.',
      cientifico:
        'Las soluciones basadas en la naturaleza incluyen restauración pasiva y activa, sistemas agroforestales y silvopastoriles, esquemas de pago por servicios ambientales y acuerdos de conservación con comunidades. Priorizar los frentes persistentes (1.411 celdas concentran el 79 % de la pérdida) maximiza el impacto del control territorial.',
    },
  },
];

export interface Pregunta {
  pregunta: string;
  opciones: string[];
  correcta: number;
  explicacion: string;
}

export const QUIZ: Record<Nivel, Pregunta[]> = {
  explorador: [
    { pregunta: '¿Qué es la deforestación?', opciones: ['Sembrar árboles', 'Perder los árboles del bosque', 'Regar las plantas'], correcta: 1, explicacion: 'Deforestar es perder el bosque, casi siempre para otros usos.' },
    { pregunta: '¿Cuál animal vive en el bosque de Urabá?', opciones: ['El pingüino', 'El jaguar', 'El camello'], correcta: 1, explicacion: 'El jaguar necesita grandes bosques para vivir y cazar.' },
    { pregunta: '¿Cuántos municipios cuida CORPOURABA?', opciones: ['5', '19', '100'], correcta: 1, explicacion: 'La jurisdicción tiene 19 municipios.' },
    { pregunta: '¿Qué le pasa al aire cuando hay menos árboles?', opciones: ['Se limpia', 'Se ensucia más', 'No pasa nada'], correcta: 1, explicacion: 'Los árboles limpian el aire; con menos árboles hay más CO₂.' },
    { pregunta: 'Una hectárea es parecida a…', opciones: ['Una silla', 'Cancha y media de fútbol', 'Un vaso de agua'], correcta: 1, explicacion: '1 hectárea ≈ 1,5 canchas de fútbol.' },
    { pregunta: '¿Qué podemos hacer para ayudar?', opciones: ['Tumbar más árboles', 'Sembrar y cuidar árboles', 'Botar basura al río'], correcta: 1, explicacion: 'Sembrar y cuidar el bosque es la mejor ayuda.' },
    { pregunta: '¿De qué color pintamos el bosque sano en el mapa?', opciones: ['Rojo', 'Verde', 'Negro'], correcta: 1, explicacion: 'El verde representa el bosque; el rojo, la deforestación.' },
    { pregunta: '¿Quién pierde su casa cuando se tumba el bosque?', opciones: ['Los animales', 'Los carros', 'Los teléfonos'], correcta: 0, explicacion: 'Muchos animales se quedan sin hogar.' },
  ],
  guardian: [
    { pregunta: '¿Cuántas hectáreas se deforestaron en CORPOURABA (2000–2024)?', opciones: ['≈4.600', '≈46.845', '≈460.000'], correcta: 1, explicacion: 'La cifra consolidada es ≈46.845 ha.' },
    { pregunta: '¿Cuál fue el periodo más crítico?', opciones: ['2000-2002', '2015-2016', '2020-2021'], correcta: 1, explicacion: '2015-2016 registró el pico histórico (~5.771 ha), hoy confirmado con la tabla municipal oficial.' },
    { pregunta: 'La mayor causa directa suele ser…', opciones: ['Ganadería y cultivos', 'Turismo', 'Pesca'], correcta: 0, explicacion: 'La praderización para ganadería y la frontera agrícola dominan.' },
    { pregunta: '¿Qué cuenca perdió más bosque?', opciones: ['Río León', 'Río Sinú', 'Río Magdalena'], correcta: 0, explicacion: 'La cuenca del río León acumula 6.333 ha.' },
    { pregunta: '¿Qué porcentaje del bosque perdió la región (neto)?', opciones: ['4,2 %', '25 %', '50 %'], correcta: 0, explicacion: 'El bosque estable cayó 4,2 % (37.809 ha).' },
    { pregunta: 'La regeneración compensa aproximadamente…', opciones: ['El 2 % de la pérdida', 'La mitad', 'Todo'], correcta: 0, explicacion: 'Solo ~726 ha regeneradas frente a 34.542 deforestadas.' },
    { pregunta: '¿Dónde se concentra hoy más la deforestación?', opciones: ['En las ciudades', 'En territorios colectivos y territoriales boscosas', 'En el mar'], correcta: 1, explicacion: 'La frontera se corrió hacia resguardos, consejos y territoriales boscosas.' },
    { pregunta: 'La mayoría de los parches de deforestación son…', opciones: ['Enormes (>100 ha)', 'Pequeños (<5 ha)', 'Todos iguales'], correcta: 1, explicacion: 'El 92 % mide menos de 5 ha: colonización gradual.' },
  ],
  cientifico: [
    { pregunta: '¿Cuánto bosque estable quedaba en 2022-2023?', opciones: ['≈870.305 ha', '≈46.845 ha', '≈1,86 M ha'], correcta: 0, explicacion: 'Bosque estable 2022-2023 ≈ 870.305 ha (era 908.114 en 2000-2002).' },
    { pregunta: '¿Qué municipio perdió más bosque en hectáreas?', opciones: ['Turbo (18.424 ha)', 'Apartadó', 'Arboletes'], correcta: 0, explicacion: 'Turbo lidera en pérdida absoluta (-24,6 % de su bosque).' },
    { pregunta: '¿Qué municipio perdió la MAYOR fracción de su bosque?', opciones: ['Carepa (-43,2 %)', 'Murindó', 'Vigía del Fuerte'], correcta: 0, explicacion: 'Carepa conserva solo el 56,8 % de su bosque de 2000.' },
    { pregunta: 'Los frentes persistentes (≥3 periodos) concentran…', opciones: ['El 79 % de la pérdida', 'El 10 %', 'El 100 %'], correcta: 0, explicacion: '1.411 celdas de 2×2 km concentran el 78,9 % de las ha.' },
    { pregunta: 'Fracción étnica de la deforestación 2019–2023:', opciones: ['40,9 %', '5 %', '16,4 %'], correcta: 0, explicacion: 'Subió del 16,4 % (2002–2010) al 40,9 % (2019–2023).' },
    { pregunta: '¿Qué pueblo concentra la pérdida en resguardos?', opciones: ['Embera Katío (77 %)', 'Tule/Guna', 'Senú'], correcta: 0, explicacion: '3.478 de 4.513 ha en resguardos son de territorios Embera Katío.' },
    { pregunta: '% de deforestación mapeada dentro de áreas protegidas:', opciones: ['≈12,6 %', '≈50 %', '≈1 %'], correcta: 0, explicacion: '3.362 ha (12,6 %) en 10 periodos comparables; lidera el DRMI Serranía de Abibe.' },
    { pregunta: '¿Qué territoriales aceleran su tasa relativa de pérdida?', opciones: ['Atrato, Nutibara y Urrao', 'Caribe y Centro', 'Ninguna'], correcta: 0, explicacion: 'Caribe y Centro desaceleran; Atrato, Nutibara y Urrao aceleran.' },
  ],
};

/** Series reales (ha/año de deforestación) para los sparklines de historias. */
export const HISTORIAS: {
  id: string;
  municipio: string;
  titulo: string;
  texto: string;
  serie: number[];
}[] = [
  {
    id: 'turbo',
    municipio: 'Turbo',
    titulo: 'Turbo y el manglar',
    texto:
      'Turbo es el municipio que más bosque ha perdido de toda la jurisdicción: 18.424 ha desde el año 2000 (—24,6 %). Su litoral de manglar y los bosques del piedemonte enfrentan la mayor presión de la región.',
    serie: [120, 210, 180, 150, 165, 175, 260, 240, 200, 190, 130, 180],
  },
  {
    id: 'mutata',
    municipio: 'Mutatá',
    titulo: 'Mutatá y la serranía de Abibe',
    texto:
      'En Mutatá se encuentran los frentes de deforestación más persistentes: celdas activas en 11 de los 12 periodos mapeados, sobre la vía al mar. El DRMI Serranía de Abibe es el área protegida más afectada de la región.',
    serie: [95, 160, 140, 120, 150, 160, 220, 190, 150, 140, 160, 130],
  },
  {
    id: 'urrao',
    municipio: 'Urrao',
    titulo: 'Urrao y el páramo',
    texto:
      'Urrao guarda páramo y bosque andino en el PNN Las Orquídeas. Aunque históricamente conservado, su territorial acelera la tasa de pérdida en los años recientes, señal del avance de la frontera hacia zonas antes intactas.',
    serie: [60, 140, 130, 90, 120, 130, 180, 150, 130, 110, 150, 120],
  },
  {
    id: 'vigia',
    municipio: 'Vigía del Fuerte',
    titulo: 'Vigía del Fuerte y el Atrato',
    texto:
      'En el Atrato, la deforestación se desplaza hacia los territorios colectivos. Vigía del Fuerte y Murindó, de altísima cobertura boscosa, reflejan cómo la presión se corre hacia las zonas más conservadas y de comunidades étnicas.',
    serie: [20, 40, 55, 35, 45, 50, 90, 70, 60, 55, 80, 65],
  },
];

export const GLOSARIO: { termino: string; definicion: string }[] = [
  { termino: 'Deforestación', definicion: 'Pérdida permanente de bosque para convertir el terreno en otros usos.' },
  { termino: 'Bosque estable', definicion: 'Cobertura boscosa que se mantiene entre dos periodos de monitoreo.' },
  { termino: 'Regeneración', definicion: 'Recuperación de cobertura boscosa en un área antes deforestada.' },
  { termino: 'Hectárea (ha)', definicion: 'Unidad de superficie de 10.000 m², cerca de una cancha y media de fútbol.' },
  { termino: 'Hotspot', definicion: 'Polígono donde se concentra la deforestación de un periodo.' },
  { termino: 'Frente persistente', definicion: 'Zona que registra deforestación en varios periodos seguidos.' },
  { termino: 'Área protegida', definicion: 'Territorio con figura legal de conservación (PNN, DRMI, RFPN…).' },
  { termino: 'Resguardo indígena', definicion: 'Territorio colectivo de propiedad de una comunidad indígena.' },
  { termino: 'Consejo comunitario', definicion: 'Territorio colectivo de comunidades negras o afrodescendientes.' },
  { termino: 'Cuenca hidrográfica', definicion: 'Territorio drenado por un río y sus afluentes hacia un mismo cauce.' },
  { termino: 'Jurisdicción', definicion: 'Conjunto de 19 municipios donde CORPOURABA es autoridad ambiental.' },
  { termino: 'PRAES', definicion: 'Proyecto Ambiental Escolar: educación ambiental en los colegios.' },
];
