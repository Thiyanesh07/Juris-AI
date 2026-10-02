"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";

/* ═══════════════════════════════════════════════════════════════════════════════
   PALETTE  (Slate Blue — locked, unchanged)
═══════════════════════════════════════════════════════════════════════════════ */
const P = {
  primary:    "#2563A8",
  accent:     "#3B82D0",
  deep:       "#183B5B",
  text:       "#17253A",
  edge:       "#B0C4D8",
  edgeActive: "#3B82D0",
  topFace:    "#EBF3FB",
  topCenter:  "#C8DDEF",
  topActive:  "#B8D4ED",
  topDest:    "#A6C8E8",
  leftFace:   "#BDD0E2",
  rightFace:  "#A5BBCC",
  bevelFace:  "#EFF7FD",   // outer bevel highlight — slightly lighter than topFace
  shadow:     "rgba(37,99,168,0.12)",
} as const;

/* ═══════════════════════════════════════════════════════════════════════════════
   NODE DATA  — positions LOCKED (unchanged from approved baseline)
═══════════════════════════════════════════════════════════════════════════════ */
interface INode {
  id: string; label: string;
  cx: number; cy: number;
  pw: number; ph: number; d: number;
  isCenter?: boolean;
  zOrder: number; layer: number;
}

const NODES: INode[] = [
  // Layer 1 — back
  { id:"amendment",  label:"Amendment",       cx:350, cy: 88, pw:48, ph:24, d:13, zOrder:1, layer:1 },
  { id:"court",      label:"Court",           cx:112, cy:268, pw:44, ph:22, d:12, zOrder:2, layer:1 },
  // Layer 2 — mid
  { id:"act",        label:"Act",             cx:540, cy:145, pw:48, ph:24, d:13, zOrder:3, layer:2 },
  { id:"judgment",   label:"Judgment",        cx:192, cy:158, pw:48, ph:24, d:13, zOrder:4, layer:2 },
  { id:"rule",       label:"Rule",            cx:618, cy:382, pw:44, ph:22, d:12, zOrder:5, layer:2 },
  { id:"principle",  label:"Legal Principle", cx:300, cy:385, pw:44, ph:22, d:12, zOrder:6, layer:2 },
  // Layer 3 — front
  { id:"section",    label:"Section",         cx:506, cy:308, pw:48, ph:24, d:13, zOrder:7, layer:3 },
  { id:"article",    label:"Article",         cx:362, cy:242, pw:68, ph:34, d:17, isCenter:true, zOrder:8, layer:3 },
];

const ALL_NODE_IDS = NODES.map(n => n.id);

/* ═══════════════════════════════════════════════════════════════════════════════
   EDGE DATA  — all semantic relationships (unchanged topology)
═══════════════════════════════════════════════════════════════════════════════ */
const EDGES = [
  { id:"e-aj", src:"article",  tgt:"judgment"  },
  { id:"e-aa", src:"article",  tgt:"amendment" },
  { id:"e-ac", src:"article",  tgt:"act"       },
  { id:"e-as", src:"article",  tgt:"section"   },
  { id:"e-ap", src:"article",  tgt:"principle" },
  { id:"e-jc", src:"judgment", tgt:"court"     },
  { id:"e-ca", src:"act",      tgt:"amendment" },
  { id:"e-sr", src:"section",  tgt:"rule"      },
  { id:"e-sj", src:"section",  tgt:"judgment"  },
  { id:"e-ja", src:"judgment", tgt:"amendment" },
];

/* ═══════════════════════════════════════════════════════════════════════════════
   PHASE STATE MACHINE — 21 phases, all 8 nodes visited
   Sequence:
     IDLE → SEED
     → Branch 1: ARTICLE→SECTION→RULE → return RULE→SECTION→ARTICLE
     → Branch 2: ARTICLE→ACT→AMENDMENT → return AMENDMENT→ACT→ARTICLE
     → Branch 3: ARTICLE→JUDGMENT→COURT → return COURT→JUDGMENT→ARTICLE
     → Branch 4: ARTICLE→LEGAL PRINCIPLE
     → GROUNDING (all 8 lit) → RESET → IDLE
   Total cycle: ~19 seconds
═══════════════════════════════════════════════════════════════════════════════ */

type Phase =
  | "IDLE" | "SEED"
  | "B1_H1" | "B1_H2" | "B1_PAUSE" | "B1_R1" | "B1_R2"
  | "B2_H1" | "B2_H2" | "B2_PAUSE" | "B2_R1" | "B2_R2"
  | "B3_H1" | "B3_H2" | "B3_PAUSE" | "B3_R1" | "B3_R2"
  | "B4_H1" | "B4_PAUSE"
  | "GROUNDING" | "RESET";

interface PhaseConfig {
  dur: number;            // phase duration in ms
  next: Phase;            // which phase follows
  activeNodes?: string[]; // replaces activeNodes set when transitioning in
  destNode?: string|null; // sets destNode when transitioning in
  activeEdgeId?: string|null;
  hop?: { src: string; tgt: string; isReturn?: boolean };
  triggerPulse?: boolean;
  showAllNodes?: boolean; // sets all 8 nodes active
  clearAll?: boolean;     // clears all state (for GROUNDING → RESET)
}

const HOP_MS  = 950; // forward particle travel duration
const RET_MS  = 620; // return particle travel duration

// Config is applied on TRANSITION OUT of each phase (into the next)
const PHASE_CFG: Record<Phase, PhaseConfig> = {
  // ── Phase ends → effects applied ──────────────────────────────────────────
  IDLE: {
    dur:1500, next:"SEED",
    activeNodes:["article"],
    triggerPulse:true,
  },
  SEED: {
    dur:850, next:"B1_H1",
    activeNodes:["article","section"], destNode:"section",
    activeEdgeId:"e-as",
    hop:{ src:"article", tgt:"section" },
  },

  // ── Branch 1: ARTICLE → SECTION → RULE ────────────────────────────────────
  B1_H1: {
    dur:1050, next:"B1_H2",
    activeNodes:["article","section","rule"], destNode:"rule",
    activeEdgeId:"e-sr",
    hop:{ src:"section", tgt:"rule" },
  },
  B1_H2: {
    dur:1050, next:"B1_PAUSE",
    destNode:null, activeEdgeId:null,
  },
  B1_PAUSE: {
    dur:400, next:"B1_R1",
    activeNodes:["article","section"],
    activeEdgeId:"e-sr",
    hop:{ src:"rule", tgt:"section", isReturn:true },
  },
  B1_R1: {
    dur:700, next:"B1_R2",
    activeNodes:["article"],
    activeEdgeId:"e-as",
    hop:{ src:"section", tgt:"article", isReturn:true },
  },
  // End of Branch 1; immediately begin Branch 2
  B1_R2: {
    dur:700, next:"B2_H1",
    activeNodes:["article","act"], destNode:"act",
    activeEdgeId:"e-ac",
    hop:{ src:"article", tgt:"act" },
  },

  // ── Branch 2: ARTICLE → ACT → AMENDMENT ───────────────────────────────────
  B2_H1: {
    dur:1050, next:"B2_H2",
    activeNodes:["article","act","amendment"], destNode:"amendment",
    activeEdgeId:"e-ca",
    hop:{ src:"act", tgt:"amendment" },
  },
  B2_H2: {
    dur:1050, next:"B2_PAUSE",
    destNode:null, activeEdgeId:null,
  },
  B2_PAUSE: {
    dur:400, next:"B2_R1",
    activeNodes:["article","act"],
    activeEdgeId:"e-ca",
    hop:{ src:"amendment", tgt:"act", isReturn:true },
  },
  B2_R1: {
    dur:700, next:"B2_R2",
    activeNodes:["article"],
    activeEdgeId:"e-ac",
    hop:{ src:"act", tgt:"article", isReturn:true },
  },
  B2_R2: {
    dur:700, next:"B3_H1",
    activeNodes:["article","judgment"], destNode:"judgment",
    activeEdgeId:"e-aj",
    hop:{ src:"article", tgt:"judgment" },
  },

  // ── Branch 3: ARTICLE → JUDGMENT → COURT ──────────────────────────────────
  B3_H1: {
    dur:1050, next:"B3_H2",
    activeNodes:["article","judgment","court"], destNode:"court",
    activeEdgeId:"e-jc",
    hop:{ src:"judgment", tgt:"court" },
  },
  B3_H2: {
    dur:1050, next:"B3_PAUSE",
    destNode:null, activeEdgeId:null,
  },
  B3_PAUSE: {
    dur:400, next:"B3_R1",
    activeNodes:["article","judgment"],
    activeEdgeId:"e-jc",
    hop:{ src:"court", tgt:"judgment", isReturn:true },
  },
  B3_R1: {
    dur:700, next:"B3_R2",
    activeNodes:["article"],
    activeEdgeId:"e-aj",
    hop:{ src:"judgment", tgt:"article", isReturn:true },
  },
  B3_R2: {
    dur:700, next:"B4_H1",
    activeNodes:["article","principle"], destNode:"principle",
    activeEdgeId:"e-ap",
    hop:{ src:"article", tgt:"principle" },
  },

  // ── Branch 4: ARTICLE → LEGAL PRINCIPLE ───────────────────────────────────
  B4_H1: {
    dur:1050, next:"B4_PAUSE",
    destNode:null, activeEdgeId:null,
  },
  B4_PAUSE: {
    dur:550, next:"GROUNDING",
    showAllNodes:true,   // all 8 nodes gently illuminate
  },

  // ── Grounding + Reset ──────────────────────────────────────────────────────
  GROUNDING: {
    dur:1500, next:"RESET",
    clearAll:true,
  },
  RESET: {
    dur:1800, next:"IDLE",
    // no effects — CSS transitions fade nodes back to idle naturally
  },
};

/* ═══════════════════════════════════════════════════════════════════════════════
   PER-NODE IDLE FLOAT  (organic, unsynchronised)
═══════════════════════════════════════════════════════════════════════════════ */
const FLOAT: Record<string, { delay:number; dur:number }> = {
  article:   { delay:0,    dur:5.5 },
  judgment:  { delay:-1.1, dur:6.2 },
  amendment: { delay:-2.3, dur:5.8 },
  act:       { delay:-0.8, dur:6.5 },
  court:     { delay:-1.7, dur:5.9 },
  section:   { delay:-3.1, dur:6.1 },
  rule:      { delay:-2.0, dur:5.7 },
  principle: { delay:-0.5, dur:6.3 },
};

/* ═══════════════════════════════════════════════════════════════════════════════
   DECORATIVE BACKGROUND CUBES
═══════════════════════════════════════════════════════════════════════════════ */
const DECOR = [
  { cx:50,  cy:148, s:14 },
  { cx:645, cy:192, s:12 },
  { cx:670, cy:298, s:15 },
  { cx:76,  cy:388, s:13 },
  { cx:425, cy:438, s:11 },
  { cx:148, cy:442, s:12 },
  { cx:658, cy:436, s:14 },
  { cx:212, cy:398, s:10 },
];

/* ═══════════════════════════════════════════════════════════════════════════════
   CSS KEYFRAMES  (injected once via <style>)
═══════════════════════════════════════════════════════════════════════════════ */
const KG_CSS = `
  @keyframes kg-float {
    0%, 100% { transform: translateY(0px); }
    50%       { transform: translateY(-3px); }
  }
  @keyframes kg-breathe {
    0%, 100% { opacity: 0.93; }
    50%       { opacity: 1.0; }
  }
  @keyframes kg-pulse {
    0%   { r: 22; opacity: 0.55; }
    100% { r: 82; opacity: 0; }
  }
  @media (prefers-reduced-motion: reduce) {
    .kg-wrap * { animation: none !important; }
  }
`;

/* ═══════════════════════════════════════════════════════════════════════════════
   HELPERS
═══════════════════════════════════════════════════════════════════════════════ */
function getNode(id: string) { return NODES.find(n => n.id === id); }

/** Rhombus boundary point in the direction of (tx,ty) from node centre */
function edgePt(n: INode, tx: number, ty: number): [number,number] {
  const dx = tx - n.cx, dy = ty - n.cy;
  const len = Math.hypot(dx, dy);
  if (len < 0.001) return [n.cx, n.cy];
  const nx = dx/len, ny = dy/len;
  const t  = 1 / (Math.abs(nx)/n.pw + Math.abs(ny)/n.ph);
  return [n.cx + t*nx, n.cy + t*ny];
}

/** Build SVG quadratic-bezier path string between two nodes */
function buildPath(srcId: string, tgtId: string): string {
  const s = getNode(srcId), t = getNode(tgtId);
  if (!s || !t) return "";
  const [sx,sy] = edgePt(s, t.cx, t.cy);
  const [tx,ty] = edgePt(t, s.cx, s.cy);
  const dist = Math.hypot(tx-sx, ty-sy);
  const mx = (sx+tx)/2, my = (sy+ty)/2 - dist*0.15;
  return `M${sx.toFixed(1)},${sy.toFixed(1)} Q${mx.toFixed(1)},${my.toFixed(1)} ${tx.toFixed(1)},${ty.toFixed(1)}`;
}

interface QBez { sx:number; sy:number; mx:number; my:number; ex:number; ey:number }

function parseQBez(d: string): QBez|null {
  const m = d.match(/M([\d.]+),([\d.]+)\s+Q([\d.]+),([\d.]+)\s+([\d.]+),([\d.]+)/);
  if (!m) return null;
  return { sx:+m[1], sy:+m[2], mx:+m[3], my:+m[4], ex:+m[5], ey:+m[6] };
}

function qbAt(b: QBez, t: number): [number,number] {
  const u = 1-t;
  return [u*u*b.sx + 2*u*t*b.mx + t*t*b.ex,
          u*u*b.sy + 2*u*t*b.my + t*t*b.ey];
}

/** Cubic ease-in-out */
function eio(t: number): number {
  return t < 0.5 ? 4*t*t*t : 1 - Math.pow(-2*t+2,3)/2;
}

/* ═══════════════════════════════════════════════════════════════════════════════
   SMALL DECORATIVE CUBE
═══════════════════════════════════════════════════════════════════════════════ */
function SmallCube({ cx, cy, s }: { cx:number; cy:number; s:number }) {
  const h = s*0.5;
  return (
    <g opacity="0.28">
      <polygon points={`${cx},${cy-h} ${cx+s},${cy} ${cx},${cy+h} ${cx-s},${cy}`}
        fill="#EBF3FB" stroke="rgba(255,255,255,0.55)" strokeWidth="0.5"/>
      <polygon points={`${cx},${cy+h} ${cx+s},${cy} ${cx+s},${cy+h} ${cx},${cy+h*2}`}
        fill={P.rightFace}/>
      <polygon points={`${cx-s},${cy} ${cx},${cy+h} ${cx},${cy+h*2} ${cx-s},${cy+h}`}
        fill={P.leftFace}/>
    </g>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════
   NODE ICON  — embedded in central icon-context area
═══════════════════════════════════════════════════════════════════════════════ */
function NodeIcon({ id, isCenter, isActive }: { id:string; isCenter:boolean; isActive:boolean }) {
  const col = isCenter ? "#F5F7FA" : isActive ? P.accent : P.primary;
  const sw  = isCenter ? 1.7 : 1.4;

  const icons: Record<string,React.ReactNode> = {
    article: (<>
      {/* Scales of justice motif */}
      <line x1="0" y1="-8" x2="0" y2="6"     stroke={col} strokeWidth={sw+0.2}/>
      <line x1="-8" y1="-1" x2="8" y2="-1"   stroke={col} strokeWidth={sw+0.2}/>
      <polygon points="-8,-1 -11.5,5.5 -4.5,5.5" fill={col}/>
      <polygon points="8,-1  11.5,5.5  4.5,5.5"  fill={col}/>
    </>),
    judgment: (<>
      {/* Gavel head + handle */}
      <rect x="-8" y="-5.5" width="16" height="7" rx="2.5" fill={col}/>
      <line x1="4" y1="1.5" x2="9.5" y2="9" stroke={col} strokeWidth="2.8" strokeLinecap="round"/>
      <line x1="-5" y1="-5.5" x2="-5" y2="-8.5" stroke={col} strokeWidth="1.8" strokeLinecap="round"/>
    </>),
    amendment: (<>
      {/* Document with edit mark */}
      <rect x="-7" y="-8" width="13" height="16" rx="2" stroke={col} strokeWidth={sw}/>
      <line x1="-4" y1="-3" x2="3"  y2="-3" stroke={col} strokeWidth="1.2"/>
      <line x1="-4" y1=" 1" x2="3"  y2=" 1" stroke={col} strokeWidth="1.2"/>
      <line x1="-4" y1=" 5" x2="0"  y2=" 5" stroke={col} strokeWidth="1.2"/>
      <line x1="5"  y1=" 3" x2="8"  y2=" 6" stroke={col} strokeWidth="1.5"/>
      <line x1="5"  y1=" 3" x2="6.5" y2="1.5" stroke={col} strokeWidth="1.5"/>
    </>),
    act: (<>
      {/* Open book / legislative tome */}
      <rect x="-8" y="-7" width="16" height="14" rx="1.5" stroke={col} strokeWidth={sw}/>
      <line x1="0" y1="-7" x2="0" y2="7"   stroke={col} strokeWidth={sw}/>
      <line x1="-5" y1="-3" x2="-1.5" y2="-3" stroke={col} strokeWidth="1.1"/>
      <line x1="-5" y1=" 0" x2="-1.5" y2=" 0" stroke={col} strokeWidth="1.1"/>
      <line x1="-5" y1=" 3" x2="-1.5" y2=" 3" stroke={col} strokeWidth="1.1"/>
      <line x1="1.5" y1="-3" x2="5" y2="-3" stroke={col} strokeWidth="1.1"/>
      <line x1="1.5" y1=" 0" x2="5" y2=" 0" stroke={col} strokeWidth="1.1"/>
    </>),
    court: (<>
      {/* Courthouse columns */}
      <rect x="-8" y="-8.5" width="16" height="3"   fill={col}/>
      <rect x="-7" y="5.5"  width="14" height="2.5" fill={col}/>
      <line x1="-5" y1="-5.5" x2="-5" y2="5.5" stroke={col} strokeWidth={sw}/>
      <line x1=" 0" y1="-5.5" x2=" 0" y2="5.5" stroke={col} strokeWidth={sw}/>
      <line x1=" 5" y1="-5.5" x2=" 5" y2="5.5" stroke={col} strokeWidth={sw}/>
    </>),
    section: (<>
      {/* Layered document / statute */}
      <rect x="-7" y="-8" width="14" height="16" rx="2" stroke={col} strokeWidth={sw}/>
      <line x1="-4" y1="-3" x2="4"  y2="-3" stroke={col} strokeWidth="1.2"/>
      <line x1="-4" y1=" 1" x2="4"  y2=" 1" stroke={col} strokeWidth="1.2"/>
      <line x1="-4" y1=" 5" x2="2"  y2=" 5" stroke={col} strokeWidth="1.2"/>
      <rect x="-4" y="-8" width="3" height="3" rx="0.5" fill={col} opacity="0.5"/>
    </>),
    rule: (<>
      {/* Rule / gear motif */}
      <circle cx="0" cy="0" r="5.5" stroke={col} strokeWidth={sw}/>
      <circle cx="0" cy="0" r="2.2" fill={col}/>
      {[0,45,90,135,180,225,270,315].map(a => (
        <rect key={a} x="-1" y="-9" width="2" height="3.5" rx="0.5"
          fill={col} transform={`rotate(${a})`}/>
      ))}
    </>),
    principle: (<>
      {/* Lightbulb / principle motif */}
      <path d="M0,-8.5 C-6,-8.5,-7,-2.5,-4,3.5 L4,3.5 C7,-2.5,6,-8.5,0,-8.5Z"
        stroke={col} strokeWidth={sw} fill="none"/>
      <line x1="-2.5" y1="4.5" x2="2.5" y2="4.5" stroke={col} strokeWidth="1.6"/>
      <line x1="-1.8" y1="6.5" x2="1.8" y2="6.5" stroke={col} strokeWidth="1.6"/>
      <line x1=" 0"   y1="-6"  x2=" 0"  y2="-2"  stroke={col} strokeWidth="1.3"/>
      <line x1="-2"   y1="-4"  x2=" 2"  y2="-4"  stroke={col} strokeWidth="1.3"/>
    </>),
  };

  return (
    <g fill="none" strokeLinecap="round" strokeLinejoin="round">
      {icons[id] ?? <circle cx="0" cy="0" r="5" fill={col}/>}
    </g>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════
   NODE PLATFORM  — enhanced multi-layer 3D geometry
   Layers (back-to-front within the node group):
     1. Drop shadow
     2. Right extrusion face
     3. Left extrusion face
     4. Bottom lip (thin darker strip at extrusion base — manufacturing detail)
     5. Outer bevel ring (full pw×ph, lighter — catches top light)
     6. Inner surface (inset, main visible surface — colour-transitions with status)
     7. Icon-context area (non-article: subtle recessed inset for icon)
        Article: glow ring + central blue platform
     8. Icon
     9. Label
═══════════════════════════════════════════════════════════════════════════════ */

type NodeStatus = "idle"|"path"|"destination"|"seed"|"grounding";

function NodePlatform({
  node, status, isHovered, floatDelay, floatDur, reducedMotion, onHover,
}: {
  node: INode;
  status: NodeStatus;
  isHovered: boolean;
  floatDelay: number;
  floatDur: number;
  reducedMotion: boolean;
  onHover: (id:string|null) => void;
}) {
  const { id, cx, cy, pw, ph, d, isCenter } = node;

  const isActive  = status === "path" || status === "destination" || status === "grounding";
  const isDest    = status === "destination";
  const isSeed    = status === "seed";
  const isGround  = status === "grounding";

  /* ── 3D GEOMETRY LAYER PARAMETERS ─────────────────────────────────────────── */
  // Bevel: gap between outer platform and inner surface (creates highlight rim)
  const BVL  = isCenter ? 4 : 3;       // bevel width on x-axis
  const BVLh = BVL * 0.5;              // bevel width on y-axis (half, maintains rhombus ratio)

  // Inner surface (main colour area)
  const INS  = isCenter ? 10 : 8;
  const INSh = INS * 0.5;

  // Icon context area (additional inset inside inner surface — non-article only)
  const ICO  = 20;
  const ICOh = ICO * 0.5;

  // Article central ring and platform
  const RING_DX = 18, RING_DY = 9;
  const CENT_DX = 24, CENT_DY = 12;

  // Derived inset sizes
  const bpw = pw - BVL,  bph = ph - BVLh;   // inner edge of bevel ring
  const ipw = pw - INS,  iph = ph - INSh;    // inner surface
  const apw = pw - INS - ICO;                // icon area
  const aph = ph - INSh - ICOh;
  const rpw = pw - RING_DX, rph = ph - RING_DY;   // article glow ring
  const cpw = pw - CENT_DX, cph = ph - CENT_DY;   // article central platform

  /* ── STATUS-DRIVEN COLOURS ─────────────────────────────────────────────────── */
  const topFill = isCenter
    ? isSeed   ? "#9ECBEF"
    : isActive ? P.topCenter
    :            "#C4D9EF"
    : isDest   ? P.topDest
    : isActive ? P.topActive
    : isGround ? "#CDDFF5"
    :            P.topFace;

  const iconAreaFill = (isActive || isSeed) ? "rgba(37,99,168,0.11)" : "rgba(37,99,168,0.055)";
  const accentStroke = (isActive || isSeed)  ? P.accent : "rgba(255,255,255,0.92)";
  const accentSW     = (isActive || isSeed)  ? 1.8 : 0.75;

  // Vertical lift on elevation events
  const liftY = isDest ? -5 : isSeed ? -4 : isHovered ? -6 : isActive ? -2 : 0;

  /* ── ANIMATION STYLES ───────────────────────────────────────────────────────── */
  const floatStyle: React.CSSProperties = reducedMotion ? {} : {
    animation: `kg-float ${floatDur}s ease-in-out ${floatDelay}s infinite`,
  };

  /* ─────────────────────────────────────────────────────────────────────────── */
  return (
    <g
      style={floatStyle}
      onPointerEnter={() => onHover(id)}
      onPointerLeave={() => onHover(null)}
    >
      {/* Lift group — spring-transitions on status changes */}
      <g style={{
        transform: `translateY(${liftY}px)`,
        transition: "transform 0.28s cubic-bezier(0.34,1.04,0.64,1)",
      }}>

        {/* ── 1. Drop shadow ───────────────────────────────────────────────── */}
        <ellipse
          cx={cx+3} cy={cy+ph+d+7}
          rx={pw*0.88} ry={ph*0.38}
          fill={P.shadow}
          style={{ opacity:isCenter?0.5:isDest?0.35:0.22, transition:"opacity 0.4s ease" }}
        />

        {/* ── 2. Right extrusion face ──────────────────────────────────────── */}
        <polygon
          points={`${cx},${cy+ph} ${cx+pw},${cy} ${cx+pw},${cy+d} ${cx},${cy+ph+d}`}
          fill={P.rightFace}
        />

        {/* ── 3. Left extrusion face ───────────────────────────────────────── */}
        <polygon
          points={`${cx-pw},${cy} ${cx},${cy+ph} ${cx},${cy+ph+d} ${cx-pw},${cy+d}`}
          fill={P.leftFace}
        />

        {/* ── 4. Bottom lip (thin darker strip at base of each face) ───────── */}
        {/* Right face lip */}
        <polygon
          points={`${cx+pw},${cy+d-2} ${cx},${cy+ph+d-2} ${cx},${cy+ph+d} ${cx+pw},${cy+d}`}
          fill="rgba(0,0,0,0.07)"
        />
        {/* Left face lip */}
        <polygon
          points={`${cx-pw},${cy+d-2} ${cx},${cy+ph+d-2} ${cx},${cy+ph+d} ${cx-pw},${cy+d}`}
          fill="rgba(0,0,0,0.04)"
        />

        {/* ── 5. Outer bevel ring ──────────────────────────────────────────── */}
        {/* Full pw×ph — slightly lighter than inner surface — "catches top light" */}
        <polygon
          points={`${cx},${cy-ph} ${cx+pw},${cy} ${cx},${cy+ph} ${cx-pw},${cy}`}
          fill={P.bevelFace}
          stroke="rgba(255,255,255,0.82)"
          strokeWidth="0.75"
        />
        {/* Thin top-left bevel highlight: lighter triangle on the upper-left half */}
        <polygon
          points={`${cx},${cy-ph} ${cx+pw},${cy} ${cx},${cy-ph+BVLh*2}`}
          fill="rgba(255,255,255,0.22)"
        />

        {/* ── 6. Inner surface (inset — main colour transitions here) ─────── */}
        <polygon
          points={`${cx},${cy-iph} ${cx+ipw},${cy} ${cx},${cy+iph} ${cx-ipw},${cy}`}
          style={{
            fill: topFill,
            stroke: accentStroke,
            strokeWidth: accentSW,
            transition: "fill 0.45s ease-out, stroke 0.3s ease",
          }}
        />

        {/* ── 7a. Icon context area — NON-ARTICLE (recessed inset plate) ──── */}
        {!isCenter && apw > 2 && (
          <polygon
            points={`${cx},${cy-aph} ${cx+apw},${cy} ${cx},${cy+aph} ${cx-apw},${cy}`}
            style={{ fill: iconAreaFill, transition: "fill 0.4s ease" }}
          />
        )}

        {/* ── 7b. ARTICLE: glow ring + central blue platform ───────────────── */}
        {isCenter && (
          <>
            {/* Perimeter accent ring (between inner surface and central platform) */}
            <polygon
              points={`${cx},${cy-rph} ${cx+rpw},${cy} ${cx},${cy+rph} ${cx-rpw},${cy}`}
              fill="none"
              stroke={P.accent}
              strokeWidth="1.8"
              style={{ opacity:(isActive||isSeed)?0.44:0.20, transition:"opacity 0.5s ease" }}
            />
            {/* Central blue platform (innermost layer — icon sits here) */}
            <polygon
              points={`${cx},${cy-cph} ${cx+cpw},${cy} ${cx},${cy+cph} ${cx-cpw},${cy}`}
              style={{
                fill: isSeed ? P.accent : isActive ? "#2A6DB8" : P.primary,
                opacity: 0.93,
                transition: "fill 0.45s ease-out",
                animation: reducedMotion ? undefined : "kg-breathe 5.5s ease-in-out 0s infinite",
              }}
            />
          </>
        )}

        {/* ── 8. Icon ──────────────────────────────────────────────────────── */}
        <g transform={`translate(${cx},${cy}) scale(${isCenter ? 1.38 : 1})`}>
          <NodeIcon id={id} isCenter={!!isCenter} isActive={isActive||isSeed}/>
        </g>

        {/* ── 9. Label ─────────────────────────────────────────────────────── */}
        <text
          x={cx} y={cy-ph-10}
          textAnchor="middle" dominantBaseline="auto"
          fontSize={isCenter ? 11.5 : 9.5}
          fontFamily="'Inter','Geist',system-ui,sans-serif"
          letterSpacing="0.08em"
          style={{
            fontWeight: isCenter ? 700 : (isActive||isSeed) ? 600 : 500,
            fill: isCenter ? P.primary : (isActive||isSeed) ? P.accent : P.text,
            transition: "fill 0.4s ease",
            userSelect: "none",
          }}
        >
          {node.label.toUpperCase()}
        </text>

      </g>
    </g>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════
   MAIN COMPONENT
═══════════════════════════════════════════════════════════════════════════════ */
export function LegalKnowledgeGraph() {

  /* ── Coarse React state (changes only on phase transitions, ~1-2 s) ─────── */
  const [phase,          setPhase]          = useState<Phase>("IDLE");
  const [activeNodes,    setActiveNodes]    = useState<Set<string>>(new Set());
  const [destNode,       setDestNode]       = useState<string|null>(null);
  const [activeEdgeId,   setActiveEdgeId]   = useState<string|null>(null);
  const [hoveredNode,    setHoveredNode]    = useState<string|null>(null);
  const [parallax,       setParallax]       = useState({ x:0, y:0 });
  const [reducedMotion,  setReducedMotion]  = useState(false);

  /* ── SVG element refs (updated per-frame in RAF — zero re-renders) ───────── */
  const svgRef           = useRef<SVGSVGElement>(null);
  const particleCoreRef  = useRef<SVGCircleElement>(null);
  const particleGlowRef  = useRef<SVGCircleElement>(null);
  const overlayEdgeRef   = useRef<SVGPathElement>(null);
  const pulseRingRef     = useRef<SVGCircleElement>(null);
  const trailEl          = useRef<(SVGCircleElement|null)[]>(Array(5).fill(null));

  /* ── RAF-internal state (no re-renders) ─────────────────────────────────── */
  const phaseRef         = useRef<Phase>("IDLE");
  const phaseStartRef    = useRef<number>(0);
  const rafRef           = useRef<number>(0);
  const hopAnim          = useRef<{
    active:   boolean;
    bz:       QBez|null;
    start:    number;
    edgeLen:  number;
    isReturn: boolean;
    duration: number;
  }>({ active:false, bz:null, start:0, edgeLen:0, isReturn:false, duration:HOP_MS });

  /* ── Reduced-motion detection ───────────────────────────────────────────── */
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReducedMotion(mq.matches);
    const h = () => setReducedMotion(mq.matches);
    mq.addEventListener("change", h);
    return () => mq.removeEventListener("change", h);
  }, []);

  /* ── Master RAF loop ────────────────────────────────────────────────────── */
  useEffect(() => {
    if (reducedMotion) return;

    /* Internal helpers — stable refs, no closure issues -------------------- */

    function hideParticle() {
      if (particleCoreRef.current) particleCoreRef.current.style.display = "none";
      if (particleGlowRef.current) particleGlowRef.current.style.display = "none";
      trailEl.current.forEach(el => { if (el) el.style.display = "none"; });
    }

    function hideOverlay() {
      if (overlayEdgeRef.current) overlayEdgeRef.current.style.display = "none";
    }

    function triggerPulse() {
      const el = pulseRingRef.current;
      if (!el) return;
      el.style.display = "";
      el.style.animation = "none";
      void el.getBoundingClientRect(); // force reflow to restart animation
      el.style.animation = "kg-pulse 0.9s cubic-bezier(0.2,0.8,0.4,1) forwards";
    }

    function startHop(src: string, tgt: string, ts: number, isReturn = false) {
      const d   = buildPath(src, tgt);
      const bz  = parseQBez(d);
      if (!bz || !overlayEdgeRef.current || !particleCoreRef.current) return;

      const duration = isReturn ? RET_MS : HOP_MS;

      if (!isReturn) {
        // Forward: progressive edge draw
        overlayEdgeRef.current.setAttribute("d", d);
        overlayEdgeRef.current.style.display = "";
        const len = overlayEdgeRef.current.getTotalLength();
        overlayEdgeRef.current.style.strokeDasharray  = String(len);
        overlayEdgeRef.current.style.strokeDashoffset = String(len); // fully hidden
        hopAnim.current = { active:true, bz, start:ts, edgeLen:len, isReturn:false, duration };
      } else {
        // Return: no edge draw, just the particle
        hideOverlay();
        hopAnim.current = { active:true, bz, start:ts, edgeLen:0, isReturn:true, duration };
      }

      const [sx,sy] = qbAt(bz, 0);
      const coreOpacity = isReturn ? "0.52" : "0.96";
      const glowOpacity = isReturn ? "0.14" : "0.22";

      if (particleCoreRef.current) {
        particleCoreRef.current.setAttribute("cx", sx.toFixed(2));
        particleCoreRef.current.setAttribute("cy", sy.toFixed(2));
        particleCoreRef.current.setAttribute("opacity", coreOpacity);
        particleCoreRef.current.style.display = "";
      }
      if (particleGlowRef.current) {
        particleGlowRef.current.setAttribute("cx", sx.toFixed(2));
        particleGlowRef.current.setAttribute("cy", sy.toFixed(2));
        particleGlowRef.current.setAttribute("opacity", glowOpacity);
        particleGlowRef.current.style.display = "";
      }
    }

    /* Phase transition — data-driven from PHASE_CFG ----------------------- */
    function transition(from: Phase, ts: number) {
      const cfg  = PHASE_CFG[from];
      const next = cfg.next;

      phaseRef.current      = next;
      phaseStartRef.current = ts;

      /* ── Special modes ────────────────────────────────────────────────── */
      if (cfg.clearAll) {
        setActiveNodes(new Set());
        setDestNode(null);
        setActiveEdgeId(null);
        setPhase(next);
        hideParticle();
        hideOverlay();
        if (pulseRingRef.current) pulseRingRef.current.style.display = "none";
        hopAnim.current.active = false;
        return;
      }

      if (cfg.showAllNodes) {
        setActiveNodes(new Set(ALL_NODE_IDS));
        setDestNode(null);
        setActiveEdgeId(null);
        setPhase(next);
        hideParticle();
        hideOverlay();
        return;
      }

      /* ── Standard state updates ───────────────────────────────────────── */
      if (cfg.activeNodes  !== undefined) setActiveNodes(new Set(cfg.activeNodes));
      if ("destNode"       in cfg)        setDestNode(cfg.destNode ?? null);
      if ("activeEdgeId"   in cfg)        setActiveEdgeId(cfg.activeEdgeId ?? null);
      setPhase(next);

      if (cfg.triggerPulse) triggerPulse();

      if (cfg.hop) {
        startHop(cfg.hop.src, cfg.hop.tgt, ts, cfg.hop.isReturn ?? false);
      } else {
        hopAnim.current.active = false;
      }
    }

    /* Per-frame tick ------------------------------------------------------- */
    function tick(ts: number) {
      const p       = phaseRef.current;
      const elapsed = ts - phaseStartRef.current;

      // Phase transition check
      if (elapsed >= PHASE_CFG[p].dur) {
        transition(p, ts);
      }

      // Particle + edge overlay per-frame update
      const h = hopAnim.current;
      if (h.active && h.bz) {
        const rawT = Math.min((ts - h.start) / h.duration, 1);
        const t    = eio(rawT);
        const [px,py] = qbAt(h.bz, t);

        // Particle positions
        if (particleCoreRef.current) {
          particleCoreRef.current.setAttribute("cx", px.toFixed(2));
          particleCoreRef.current.setAttribute("cy", py.toFixed(2));
        }
        if (particleGlowRef.current) {
          particleGlowRef.current.setAttribute("cx", px.toFixed(2));
          particleGlowRef.current.setAttribute("cy", py.toFixed(2));
        }

        // Progressive edge draw (forward hops only)
        if (!h.isReturn && overlayEdgeRef.current && h.edgeLen > 0) {
          overlayEdgeRef.current.style.strokeDashoffset = String(h.edgeLen * (1 - t));
        }

        // Trail (forward hops only — 5 ghost circles)
        if (!h.isReturn) {
          const GAPS = [0.055, 0.11, 0.165, 0.22, 0.275];
          const OPS  = [0.55,  0.35, 0.22,  0.13, 0.07];
          const RADII = [3.8,  3.2,  2.6,   2.1,  1.6];
          trailEl.current.forEach((el,i) => {
            if (!el) return;
            const tT = Math.max(0, t - GAPS[i]);
            if (tT <= 0 || rawT < GAPS[i]) { el.style.display = "none"; return; }
            const [tx2,ty2] = qbAt(h.bz!, tT);
            el.setAttribute("cx", tx2.toFixed(2));
            el.setAttribute("cy", ty2.toFixed(2));
            el.setAttribute("r",  String(RADII[i]));
            el.setAttribute("opacity", String(OPS[i]));
            el.style.display = "";
          });
        } else {
          // Return: no trail
          trailEl.current.forEach(el => { if (el) el.style.display = "none"; });
        }

        if (rawT >= 1) {
          h.active = false;
          hideParticle();
        }
      }

      rafRef.current = requestAnimationFrame(tick);
    }

    phaseStartRef.current = performance.now();
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [reducedMotion]);

  /* ── Parallax mouse handler ──────────────────────────────────────────────── */
  const handleMouseMove = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    if (reducedMotion || !svgRef.current) return;
    const r = svgRef.current.getBoundingClientRect();
    setParallax({
      x: ((e.clientX - r.left) / r.width  - 0.5) * 10,
      y: ((e.clientY - r.top)  / r.height - 0.5) *  7,
    });
  }, [reducedMotion]);

  /* ── Node visual status ──────────────────────────────────────────────────── */
  function nodeStatus(id: string): NodeStatus {
    if (phase === "GROUNDING")              return activeNodes.has(id) ? "grounding" : "idle";
    if (phase === "RESET")                  return "idle";
    if (id === "article" && phase === "SEED") return "seed";
    if (id === destNode)                    return "destination";
    if (activeNodes.has(id))               return "path";
    return "idle";
  }

  /* ── Edge active checks ──────────────────────────────────────────────────── */
  function isEdgePrimary(eid: string) { return eid === activeEdgeId; }
  function isEdgeActive(eid: string)  { return eid === activeEdgeId; }

  /* ── Sorted paint order (back-to-front) ─────────────────────────────────── */
  const sortedNodes = [...NODES].sort((a,b) => a.zOrder - b.zOrder);

  /* ═══════════════════════════════════════════════════════════════════════════
     RENDER
  ═══════════════════════════════════════════════════════════════════════════ */
  return (
    <div style={{ width:"100%", maxWidth:"780px", display:"flex", alignItems:"center", justifyContent:"center" }}>

      <style>{KG_CSS}</style>

      <svg
        ref={svgRef}
        viewBox="0 0 700 472"
        className="kg-wrap"
        style={{ width:"100%", height:"auto", display:"block", overflow:"visible" }}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setParallax({ x:0, y:0 })}
        aria-label="Legal knowledge graph: Article connects to Section, Judgment, Amendment, Act, Court, Rule, and Legal Principle"
      >
        <defs>
          {/* Particle glow */}
          <filter id="kg-glow-p" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="4.5" result="b"/>
            <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
          {/* Edge glow */}
          <filter id="kg-glow-e" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="2.5" result="b"/>
            <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
          {/* Background radial */}
          <radialGradient id="kg-bg" cx="54%" cy="56%" r="46%">
            <stop offset="0%"   stopColor="#D9E7F5" stopOpacity="0.55"/>
            <stop offset="100%" stopColor="#E7EDF4" stopOpacity="0"/>
          </radialGradient>
          {/* Article ambient */}
          <radialGradient id="kg-art-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%"   stopColor="#3B82D0" stopOpacity="0.28"/>
            <stop offset="100%" stopColor="#2563A8" stopOpacity="0"/>
          </radialGradient>
        </defs>

        {/* ── BACKGROUND GLOW ─────────────────────────────────────────────── */}
        <ellipse cx="390" cy="268" rx="308" ry="205" fill="url(#kg-bg)"/>

        {/* Article ambient halo */}
        <ellipse
          cx={362 + parallax.x * 0.8}
          cy={242 + parallax.y * 0.8}
          rx="100" ry="60"
          fill="url(#kg-art-glow)"
          style={{
            opacity: activeNodes.has("article") || phase === "SEED" || phase === "GROUNDING" ? 0.55 : 0,
            transition: "opacity 0.7s ease",
            pointerEvents: "none",
          }}
        />

        {/* ── DECORATIVE CUBES ─────────────────────────────────────────────── */}
        {DECOR.map((c,i) => <SmallCube key={i} cx={c.cx} cy={c.cy} s={c.s}/>)}

        {/* ── BASE EDGES (always rendered — colour-transitions with state) ─── */}
        <g transform={`translate(${parallax.x*0.35},${parallax.y*0.35})`}>
          {EDGES.map(edge => {
            const pathStr = buildPath(edge.src, edge.tgt);
            const active  = isEdgeActive(edge.id);
            const primary = isEdgePrimary(edge.id);
            const src     = getNode(edge.src), tgt = getNode(edge.tgt);
            if (!src || !tgt || !pathStr) return null;
            const [sx,sy] = edgePt(src, tgt.cx, tgt.cy);
            const [tx,ty] = edgePt(tgt, src.cx, src.cy);
            return (
              <g key={edge.id}>
                {/* Soft halo behind active edge */}
                {active && (
                  <path d={pathStr} fill="none"
                    stroke={P.edgeActive}
                    strokeWidth={primary ? 7 : 5}
                    opacity={primary ? 0.17 : 0.1}
                    filter="url(#kg-glow-e)"/>
                )}
                {/* Edge line */}
                <path
                  d={pathStr} fill="none"
                  stroke={active ? P.edgeActive : P.edge}
                  strokeWidth={active ? (primary ? 2.2 : 1.6) : 1.2}
                  strokeLinecap="round"
                  style={{
                    opacity: active ? (primary ? 0.94 : 0.62) : 0.56,
                    transition: "stroke 0.4s ease, opacity 0.4s ease, stroke-width 0.3s ease",
                  }}
                />
                {/* Endpoint dots */}
                {[{cx:sx,cy:sy},{cx:tx,cy:ty}].map((pt,i) => (
                  <circle key={i} cx={pt.cx} cy={pt.cy} r="2.6"
                    fill={active ? P.edgeActive : P.edge}
                    style={{ opacity:active?0.88:0.42, transition:"fill 0.4s ease, opacity 0.4s ease" }}
                  />
                ))}
              </g>
            );
          })}
        </g>

        {/* ── ACTIVE EDGE OVERLAY (progressive draw via stroke-dashoffset) ─── */}
        <g transform={`translate(${parallax.x*0.35},${parallax.y*0.35})`}>
          <path
            ref={overlayEdgeRef}
            d=""
            fill="none"
            stroke={P.edgeActive}
            strokeWidth="3"
            strokeLinecap="round"
            filter="url(#kg-glow-e)"
            opacity="0.78"
            style={{ display:"none", strokeDasharray:"0", strokeDashoffset:"0" }}
          />
        </g>

        {/* ── ARTICLE SEED PULSE RING ──────────────────────────────────────── */}
        <circle
          ref={pulseRingRef}
          cx={362 + parallax.x*0.8}
          cy={242 + parallax.y*0.8}
          r="22"
          fill="none"
          stroke={P.accent}
          strokeWidth="2"
          style={{ display:"none", pointerEvents:"none" }}
        />

        {/* ── TRAVERSAL PARTICLE TRAIL (5 ghost circles) ───────────────────── */}
        {Array.from({ length:5 }, (_,i) => (
          <circle
            key={`trail-${i}`}
            ref={el => { trailEl.current[i] = el; }}
            cx="0" cy="0" r="3"
            fill={P.accent}
            style={{ display:"none", pointerEvents:"none" }}
          />
        ))}

        {/* ── TRAVERSAL PARTICLE: glow halo ────────────────────────────────── */}
        <circle
          ref={particleGlowRef}
          cx="0" cy="0" r="9"
          fill={P.accent}
          opacity="0.22"
          filter="url(#kg-glow-p)"
          style={{ display:"none", pointerEvents:"none" }}
        />
        {/* ── TRAVERSAL PARTICLE: core ─────────────────────────────────────── */}
        <circle
          ref={particleCoreRef}
          cx="0" cy="0" r="4.5"
          fill={P.accent}
          opacity="0.96"
          style={{ display:"none", pointerEvents:"none" }}
        />

        {/* ── NODES (back-to-front by zOrder, layered parallax depth) ──────── */}
        {sortedNodes.map(node => {
          const pf = node.layer === 1 ? 0.3 : node.layer === 3 ? 0.8 : 0.55;
          return (
            <g key={node.id}
              transform={`translate(${parallax.x*pf},${parallax.y*pf})`}>
              <NodePlatform
                node={node}
                status={nodeStatus(node.id)}
                isHovered={hoveredNode === node.id}
                floatDelay={FLOAT[node.id]?.delay ?? 0}
                floatDur={FLOAT[node.id]?.dur ?? 6}
                reducedMotion={reducedMotion}
                onHover={setHoveredNode}
              />
            </g>
          );
        })}

      </svg>
    </div>
  );
}
