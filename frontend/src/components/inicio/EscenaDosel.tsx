'use client';

/**
 * Escena 3D "El dosel vivo de Urabá" (React Three Fiber).
 * Terreno low-poly procedural + bosque de árboles low-poly (InstancedMesh) que,
 * al avanzar el scroll (progresoRef 0→1), se hunden y desvanecen revelando el
 * suelo desnudo mientras la cámara desciende e inclina. Idle: viento senoidal,
 * barrido satelital lento y puntos de alerta ámbar sobre el dosel.
 *
 * Se monta SIEMPRE con dynamic import ssr:false (usa WebGL/Math.random en runtime).
 * Solo anima transform/opacidad; dpr [1,2].
 */
import { MutableRefObject, useEffect, useMemo, useRef } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Html } from '@react-three/drei';
import * as THREE from 'three';

// ── Paleta (tomada del tema Tailwind del proyecto) ──────────────────────────
const VERDES = ['#2E8B57', '#257A49', '#1B5E3A', '#175E3A', '#3AA06A'];
const COLOR_FONDO = '#062818'; // bosque-950
const COLOR_TRONCO = '#3B2A1B';
const COLOR_SUELO = '#123024'; // suelo bajo el dosel (verde muy profundo)
const AMBAR = '#F97316'; // alerta-500

// Municipios reales con su deforestación 2000–2024 (para los puntos de alerta).
const ALERTAS: { nombre: string; ha: string; pos: [number, number, number] }[] = [
  { nombre: 'Turbo', ha: '13.309 ha', pos: [-6.5, 3.4, 1.5] },
  { nombre: 'Dabeiba', ha: '5.003 ha', pos: [5.8, 3.0, -3.5] },
  { nombre: 'Mutatá', ha: '4.720 ha', pos: [1.2, 3.2, 4.2] },
  { nombre: 'Necoclí', ha: '2.351 ha', pos: [-3.0, 2.9, -5.5] },
  { nombre: 'Chigorodó', ha: '2.111 ha', pos: [8.0, 3.1, 2.0] },
];

// Ruido de valor barato y determinista (suma de senos): colinas suaves y
// distribución del bosque sin dependencias externas.
function alturaTerreno(x: number, z: number): number {
  return (
    Math.sin(x * 0.28 + 0.6) * 1.15 +
    Math.cos(z * 0.24 - 0.3) * 1.05 +
    Math.sin((x + z) * 0.16) * 0.7 +
    Math.cos(x * 0.5 - z * 0.35) * 0.35
  );
}

const ANCHO = 34; // extensión del terreno en X
const FONDO = 30; // extensión en Z

// ── Terreno low-poly ────────────────────────────────────────────────────────
function Terreno() {
  const geom = useMemo(() => {
    const g = new THREE.PlaneGeometry(ANCHO, FONDO, 40, 36);
    g.rotateX(-Math.PI / 2);
    const pos = g.attributes.position as THREE.BufferAttribute;
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      const z = pos.getZ(i);
      pos.setY(i, alturaTerreno(x, z) - 0.2);
    }
    g.computeVertexNormals();
    return g;
  }, []);
  return (
    <mesh geometry={geom} position={[0, -1.6, 0]} receiveShadow>
      <meshStandardMaterial color={COLOR_SUELO} flatShading roughness={1} metalness={0} />
    </mesh>
  );
}

// ── Bosque (dos InstancedMesh: follaje cónico + tronco cilíndrico) ──────────
type DatoArbol = {
  x: number;
  z: number;
  base: number; // altura del suelo
  escala: number;
  giro: number;
  fase: number; // desfase del viento
  umbral: number; // progreso de scroll al que este árbol cae (0.15–0.95)
  cae: boolean; // pertenece al sector que se deforesta (frente)
};

function Bosque({
  progresoRef,
  reduced,
  treeCount,
}: {
  progresoRef: MutableRefObject<number>;
  reduced: boolean;
  treeCount: number;
}) {
  const refCono = useRef<THREE.InstancedMesh>(null);
  const refTronco = useRef<THREE.InstancedMesh>(null);

  const arboles = useMemo<DatoArbol[]>(() => {
    const out: DatoArbol[] = [];
    let intentos = 0;
    while (out.length < treeCount && intentos < treeCount * 6) {
      intentos++;
      const x = (Math.random() - 0.5) * (ANCHO - 4);
      const z = (Math.random() - 0.5) * (FONDO - 4);
      // densidad natural: menos árboles en las cimas más altas
      const base = alturaTerreno(x, z);
      if (Math.random() > 0.5 + base * 0.12) continue;
      // el "frente de deforestación" es el sector delantero (z alto, hacia cámara)
      const cae = z > -2 && x < 9;
      out.push({
        x,
        z,
        base: base - 1.6,
        escala: 0.7 + Math.random() * 0.9,
        giro: Math.random() * Math.PI,
        fase: Math.random() * Math.PI * 2,
        umbral: 0.15 + Math.random() * 0.7,
        cae,
      });
    }
    return out;
  }, [treeCount]);

  const dummy = useMemo(() => new THREE.Object3D(), []);

  // Color por árbol (variación de verdes) — se fija tras montar (ref ya existe).
  useEffect(() => {
    const cono = refCono.current;
    if (!cono) return;
    const c = new THREE.Color();
    for (let i = 0; i < arboles.length; i++) {
      c.set(VERDES[i % VERDES.length]).offsetHSL(0, (Math.random() - 0.5) * 0.05, (Math.random() - 0.5) * 0.08);
      cono.setColorAt(i, c);
    }
    if (cono.instanceColor) cono.instanceColor.needsUpdate = true;
  }, [arboles]);

  useFrame((state) => {
    const cono = refCono.current;
    const tronco = refTronco.current;
    if (!cono || !tronco) return;
    const t = state.clock.elapsedTime;
    const p = progresoRef.current;
    for (let i = 0; i < arboles.length; i++) {
      const a = arboles[i];
      // Deforestación: al pasar su umbral, el árbol se hunde y encoge a 0.
      let caida = 0;
      let esc = a.escala;
      if (a.cae && p > a.umbral) {
        const k = Math.min((p - a.umbral) / 0.18, 1); // 0→1 al desaparecer
        const e = k * k * (3 - 2 * k); // smoothstep
        caida = e * 3.2;
        esc = a.escala * (1 - e);
      }
      const viento = reduced ? 0 : Math.sin(t * 0.9 + a.fase) * 0.05 * a.escala;
      // Cono (follaje)
      dummy.position.set(a.x, a.base + 1.15 * a.escala - caida, a.z);
      dummy.rotation.set(viento, a.giro, viento * 0.6);
      dummy.scale.set(esc, esc, esc);
      dummy.updateMatrix();
      cono.setMatrixAt(i, dummy.matrix);
      // Tronco
      dummy.position.set(a.x, a.base + 0.35 * a.escala - caida, a.z);
      dummy.rotation.set(viento * 0.5, a.giro, viento * 0.3);
      dummy.scale.set(esc, esc, esc);
      dummy.updateMatrix();
      tronco.setMatrixAt(i, dummy.matrix);
    }
    cono.instanceMatrix.needsUpdate = true;
    tronco.instanceMatrix.needsUpdate = true;
  });

  return (
    <group>
      <instancedMesh ref={refCono} args={[undefined, undefined, arboles.length] as any}>
        <coneGeometry args={[0.42, 1.5, 6]} />
        <meshStandardMaterial vertexColors flatShading roughness={0.9} metalness={0} />
      </instancedMesh>
      <instancedMesh ref={refTronco} args={[undefined, undefined, arboles.length] as any}>
        <cylinderGeometry args={[0.07, 0.1, 0.8, 5]} />
        <meshStandardMaterial color={COLOR_TRONCO} flatShading roughness={1} />
      </instancedMesh>
    </group>
  );
}

// ── Barrido satelital: línea tenue que rota lento sobre el dosel ─────────────
function BarridoSatelital({ reduced }: { reduced: boolean }) {
  const ref = useRef<THREE.Mesh>(null);
  useFrame((state) => {
    if (ref.current && !reduced) ref.current.rotation.z = state.clock.elapsedTime * 0.09;
  });
  const tex = useMemo(() => {
    const c = document.createElement('canvas');
    c.width = 512;
    c.height = 512;
    const ctx = c.getContext('2d')!;
    const ctxAny = ctx as CanvasRenderingContext2D & {
      createConicGradient?: (a: number, x: number, y: number) => CanvasGradient;
    };
    const g = ctxAny.createConicGradient
      ? ctxAny.createConicGradient(0, 256, 256)
      : ctx.createLinearGradient(0, 0, 512, 0);
    g.addColorStop(0, 'rgba(123,199,150,0.0)');
    g.addColorStop(0.03, 'rgba(123,199,150,0.28)');
    g.addColorStop(0.08, 'rgba(123,199,150,0.0)');
    g.addColorStop(1, 'rgba(123,199,150,0.0)');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, 512, 512);
    const t = new THREE.CanvasTexture(c);
    return t;
  }, []);
  return (
    <mesh ref={ref} position={[0, 4.2, -2]} rotation={[-Math.PI / 2, 0, 0]}>
      <circleGeometry args={[20, 48]} />
      <meshBasicMaterial map={tex} transparent opacity={0.5} depthWrite={false} blending={THREE.AdditiveBlending} />
    </mesh>
  );
}

// ── Puntos de alerta (drei Html: pulsan y muestran tooltip al pasar) ─────────
function PuntosAlerta({ interactivo }: { interactivo: boolean }) {
  return (
    <>
      {ALERTAS.map((a) => (
        <Html
          key={a.nombre}
          position={a.pos}
          center
          distanceFactor={16}
          zIndexRange={[20, 0]}
          style={{ pointerEvents: interactivo ? 'auto' : 'none' }}
        >
          <div className="grupo-alerta">
            <span className="punto-alerta" aria-hidden="true" />
            {interactivo && (
              <span className="tooltip-alerta" role="tooltip">
                <strong>{a.nombre}</strong>
                {a.ha}
              </span>
            )}
          </div>
        </Html>
      ))}
    </>
  );
}

// ── Cámara: desciende e inclina con el scroll + parallax de cursor ──────────
function Camara({
  progresoRef,
  punteroRef,
  reduced,
}: {
  progresoRef: MutableRefObject<number>;
  punteroRef: MutableRefObject<{ x: number; y: number }>;
  reduced: boolean;
}) {
  const { camera } = useThree();
  const objetivo = useRef(new THREE.Vector3(0, 1.2, 0));
  useFrame(() => {
    const p = progresoRef.current;
    // posición base: arranca alta y alejada; desciende y avanza hacia el frente
    const bx = 0;
    const by = 7.5 - p * 4.2;
    const bz = 15 - p * 3.5;
    // parallax de cursor: máx ~3° (pequeño desplazamiento lateral)
    const px = reduced ? 0 : punteroRef.current.x * 0.9;
    const py = reduced ? 0 : punteroRef.current.y * 0.5;
    camera.position.x += (bx + px - camera.position.x) * 0.05;
    camera.position.y += (by + py - camera.position.y) * 0.05;
    camera.position.z += (bz - camera.position.z) * 0.05;
    // mira: al inicio al horizonte del dosel; con el scroll baja al suelo talado
    objetivo.current.y += (1.8 - p * 3.2 - objetivo.current.y) * 0.05;
    objetivo.current.z += (-2 + p * 4 - objetivo.current.z) * 0.05;
    camera.lookAt(objetivo.current);
  });
  return null;
}

export default function EscenaDosel({
  progresoRef,
  punteroRef,
  reduced,
  treeCount,
  interactivo,
}: {
  progresoRef: MutableRefObject<number>;
  punteroRef: MutableRefObject<{ x: number; y: number }>;
  reduced: boolean;
  treeCount: number;
  interactivo: boolean;
}) {
  return (
    <Canvas
      dpr={[1, 2]}
      shadows={false}
      gl={{ antialias: true, alpha: true }}
      camera={{ position: [0, 7.5, 15], fov: 42, near: 0.1, far: 120 }}
      onCreated={({ gl }) => gl.setClearColor(new THREE.Color(COLOR_FONDO), 0)}
    >
      <fog attach="fog" args={[COLOR_FONDO, 16, 44]} />
      <ambientLight intensity={0.55} color="#8Fe0b0" />
      <hemisphereLight intensity={0.4} color="#bff3d0" groundColor="#0a2018" />
      <directionalLight position={[-8, 12, 6]} intensity={1.15} color="#ffd9a0" />
      <Terreno />
      <Bosque progresoRef={progresoRef} reduced={reduced} treeCount={treeCount} />
      <BarridoSatelital reduced={reduced} />
      <PuntosAlerta interactivo={interactivo} />
      <Camara progresoRef={progresoRef} punteroRef={punteroRef} reduced={reduced} />
    </Canvas>
  );
}
