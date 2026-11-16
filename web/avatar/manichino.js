/* Juta Coach — manichino 3D costruito interamente nel codice (nessun file di terzi, nessuna licenza esterna).
   Stile "manichino articolato": segmenti lisci bianchi + giunti sferici verdi, ognuno attaccato a un osso.
   Lo scheletro usa gli stessi nomi di Mixamo ("mixamorig..."), così il motore di avatar.js funziona uguale.
   Misure in metri, persona di circa 1,78 m, rivolta verso +z, sinistra del manichino = +x. */
(function () {
"use strict";
const V = (x, y, z) => new THREE.Vector3(x, y, z);

// ---------------------------------------------------------------- scheletro (posizioni nel mondo, a riposo)
const S = {
  Hips: [0, .98, 0], Spine: [0, 1.06, -.005], Spine1: [0, 1.17, -.01], Spine2: [0, 1.29, -.012],
  Neck: [0, 1.5, -.02], Head: [0, 1.575, -.005], HeadTop_End: [0, 1.78, 0],
};
const LATO = {
  Shoulder: [.045, 1.445, -.02], Arm: [.185, 1.43, -.025], ForeArm: [.205, 1.15, -.035], Hand: [.215, .895, -.01],
  UpLeg: [.092, .935, 0], Leg: [.1, .51, .012], Foot: [.105, .085, -.012], ToeBase: [.11, .018, .125], Toe_End: [.112, .018, .2],
};
// dita: attacco sulla mano (dx = verso il palmo per il sinistro: -x) e tre falangi che scendono, un po' piegate verso il palmo
const DITA = {
  Index: { base: [-.006, -.088, .032], l: [.042, .026, .021] },
  Middle: { base: [-.006, -.092, .011], l: [.046, .029, .022] },
  Ring: { base: [-.006, -.088, -.009], l: [.043, .027, .021] },
  Pinky: { base: [-.004, -.08, -.027], l: [.034, .021, .019] },
};
const PADRE = { Spine: "Hips", Spine1: "Spine", Spine2: "Spine1", Neck: "Spine2", Head: "Neck", HeadTop_End: "Head" };

function creaScheletro() {
  const pos = {}, padre = { ...PADRE };
  for (const k in S) pos[k] = V(...S[k]);
  ["Left", "Right"].forEach(l => {
    const s = l === "Left" ? 1 : -1, m = a => V(a[0] * s, a[1], a[2]);
    for (const k in LATO) pos[l + k] = m(LATO[k]);
    Object.assign(padre, { [l + "Shoulder"]: "Spine2", [l + "Arm"]: l + "Shoulder", [l + "ForeArm"]: l + "Arm", [l + "Hand"]: l + "ForeArm",
      [l + "UpLeg"]: "Hips", [l + "Leg"]: l + "UpLeg", [l + "Foot"]: l + "Leg", [l + "ToeBase"]: l + "Foot", [l + "Toe_End"]: l + "ToeBase" });
    const H = pos[l + "Hand"];
    for (const d in DITA) {
      const f = DITA[d]; let p = H.clone().add(m(f.base)), prec = l + "Hand";
      for (let i = 1; i <= 4; i++) {
        const n = l + "Hand" + d + i; pos[n] = p.clone(); padre[n] = prec; prec = n;
        if (i < 4) p = p.clone().add(V(-.006 * s * i, -f.l[i - 1], .002));
      }
    }
    // pollice: davanti al palmo, verso il basso e in avanti
    let p = H.clone().add(m([-.018, -.025, .03])), prec = l + "Hand";
    const lp = [.035, .03, .024], dir = [V(-.012 * s, -.6, .55), V(-.01 * s, -.75, .35), V(-.008 * s, -.85, .2)];
    for (let i = 1; i <= 4; i++) {
      const n = l + "HandThumb" + i; pos[n] = p.clone(); padre[n] = prec; prec = n;
      if (i < 4) p = p.clone().addScaledVector(dir[i - 1].normalize(), lp[i - 1]);
    }
  });
  const ossa = {};
  for (const n in pos) { const b = new THREE.Bone(); b.name = "mixamorig" + n; ossa[n] = b; }
  for (const n in pos) {
    const b = ossa[n];
    if (padre[n]) { ossa[padre[n]].add(b); b.position.copy(pos[n]).sub(pos[padre[n]]); } else b.position.copy(pos[n]);
  }
  return { ossa, pos };
}

// ---------------------------------------------------------------- forme lisce (tornio) con estremi arrotondati
// profilo: [[t, r], ...] con t da 0 (osso A) a 1 (osso B); calotte sferiche ai due capi
function segmento(len, profilo, { scalaX = 1, scalaZ = 1, calotte = true, fondo = .9 } = {}) {
  const pts = [], r0 = profilo[0][1], r1 = profilo[profilo.length - 1][1];
  if (calotte) for (let i = 0; i <= 8; i++) { const a = (i / 8) * Math.PI / 2; pts.push(new THREE.Vector2(Math.max(1e-4, r0 * Math.sin(a)), -r0 * Math.cos(a) * fondo)); }
  // raggio lungo il pezzo: curva morbida (Catmull-Rom) che passa per i punti del profilo, senza "gradini"
  const curva = new THREE.SplineCurve(profilo.map(([tt, r]) => new THREE.Vector2(tt, r)));
  const N = 40;
  for (let i = 1; i < N; i++) { const q = curva.getPointAt(i / N); pts.push(new THREE.Vector2(Math.max(.002, q.y), q.x * len)); }
  if (calotte) for (let i = 0; i <= 8; i++) { const a = (i / 8) * Math.PI / 2; pts.push(new THREE.Vector2(Math.max(1e-4, r1 * Math.cos(a)), len + r1 * Math.sin(a) * .9)); }
  const g = new THREE.LatheGeometry(pts, 40);
  g.scale(scalaX, 1, scalaZ); g.computeVertexNormals();
  return g;
}

// ---------------------------------------------------------------- manichino
function creaManichino() {
  const { ossa, pos } = creaScheletro();
  const radice = new THREE.Group(); radice.name = "Manichino"; radice.add(ossa.Hips);
  const corpo = new THREE.MeshStandardMaterial({ name: "corpo", color: 0xe9e6de, roughness: .35 });
  const giunto = new THREE.MeshStandardMaterial({ name: "giunto", color: 0x2fbf71, roughness: .5 });
  const su = V(0, 1, 0);
  // mesh rigida attaccata all'osso "osso", disegnata dalla posizione A verso la posizione B (nel mondo, a riposo)
  function tra(osso, A, B, geo, mat = corpo, nome = "corpo") {
    const m = new THREE.Mesh(geo, mat); m.name = nome;
    const d = B.clone().sub(A); m.quaternion.setFromUnitVectors(su, d.normalize());
    m.position.copy(A).sub(pos[osso]); ossa[osso].add(m); return m;
  }
  function palla(osso, P, r, sc = [1, 1, 1], mat = giunto) {
    const m = new THREE.Mesh(new THREE.SphereGeometry(r, 32, 20), mat); m.name = mat === giunto ? "giunto" : "corpo";
    m.scale.set(...sc); m.position.copy(P).sub(pos[osso]); ossa[osso].add(m); return m;
  }
  const P = n => pos[n];
  // pezzo bianco tra due punti, accorciato ai capi (ga, gb) per lasciare a vista la sfera verde del giunto
  function pezzo(osso, A, B, profilo, opz = {}, ga = 0, gb = 0) {
    const d = B.clone().sub(A).normalize(), A2 = A.clone().addScaledVector(d, ga), B2 = B.clone().addScaledVector(d, -gb);
    return tra(osso, A2, B2, segmento(A2.distanceTo(B2), profilo, opz));
  }
  // --- tronco: guscio del petto, addome verde a vista, guscio del bacino
  tra("Hips", V(0, .925, -.006), V(0, 1.035, -.012), segmento(.11, [[0, .112], [.5, .13], [1, .118]], { scalaX: 1.12, scalaZ: .78, fondo: .3 }));
  palla("Spine1", V(0, 1.125, -.008), .102, [1.02, .95, .8]);                           // addome (verde)
  tra("Spine2", V(0, 1.215, -.014), V(0, 1.45, -.026), segmento(.235, [[0, .1], [.22, .118], [.55, .146], [.85, .14], [1, .095]], { scalaX: 1.24, scalaZ: .72 }));
  palla("Spine2", V(0, 1.34, .03), .1, [1.2, .7, .42], corpo);                         // pettorali
  palla("Neck", V(0, 1.488, -.024), .046);                                              // collo (verde)
  tra("Neck", V(0, 1.5, -.022), V(0, 1.565, -.01), segmento(.065, [[0, .047], [1, .041]], { calotte: false }));
  // --- testa: ovale liscio, leggermente inclinato in avanti
  const testa = palla("Head", V(0, 1.668, .012), .105, [.86, 1.12, .98], corpo); testa.rotation.x = -.18;
  ["Left", "Right"].forEach(l => {
    const s = l === "Left" ? 1 : -1;
    // --- braccio: spalla, braccio, gomito, avambraccio, polso
    palla(l + "Arm", P(l + "Arm").clone().add(V(-.006 * s, .006, 0)), .053);
    tra(l + "Shoulder", V(.06 * s, 1.448, -.024), P(l + "Arm").clone().add(V(-.035 * s, .012, 0)), segmento(.09, [[0, .045], [1, .05]], { scalaZ: .8 }));
    pezzo(l + "Arm", P(l + "Arm"), P(l + "ForeArm"), [[0, .046], [.35, .05], [1, .038]], { scalaZ: .92 }, .05, .036);
    palla(l + "ForeArm", P(l + "ForeArm"), .036);
    pezzo(l + "ForeArm", P(l + "ForeArm"), P(l + "Hand"), [[0, .039], [.3, .042], [1, .027]], { scalaX: .9 }, .036, .024);
    palla(l + "Hand", P(l + "Hand"), .025);
    const H = P(l + "Hand");
    tra(l + "Hand", H.clone().add(V(-.004 * s, -.024, .002)), H.clone().add(V(-.006 * s, -.08, .002)),
      segmento(.056, [[0, .032], [.6, .041], [1, .037]], { scalaX: .5, scalaZ: 1.15 }));
    for (const d of ["Index", "Middle", "Ring", "Pinky", "Thumb"]) for (let i = 1; i <= 3; i++) {
      const a = l + "Hand" + d + i, b = l + "Hand" + d + (i + 1), r = (d === "Thumb" ? .0112 : d === "Pinky" ? .0085 : .0097) * (1 - (i - 1) * .1);
      tra(a, P(a), P(b), segmento(P(a).distanceTo(P(b)), [[0, r], [1, r * .93]]));
    }
    // --- gamba: anca, coscia, ginocchio, gamba, caviglia
    palla(l + "UpLeg", P(l + "UpLeg").clone().add(V(0, -.03, 0)), .062);
    pezzo(l + "UpLeg", P(l + "UpLeg"), P(l + "Leg"), [[0, .07], [.3, .08], [.75, .062], [1, .05]], { scalaZ: .95 }, .125, .048);
    palla(l + "Leg", P(l + "Leg"), .049);
    pezzo(l + "Leg", P(l + "Leg"), P(l + "Foot"), [[0, .05], [.25, .057], [.75, .036], [1, .03]], { scalaX: .95 }, .046, .034);
    palla(l + "Foot", P(l + "Foot"), .034);
    // --- piede: scarpa bianca (tallone-pianta sull'osso Foot, punta su ToeBase)
    tra(l + "Foot", P(l + "Foot").clone().add(V(0, -.052, -.062)), P(l + "ToeBase").clone().add(V(0, .008, 0)),
      segmento(.2, [[0, .034], [.5, .044], [1, .04]], { scalaX: 1.05, scalaZ: .68 }));
    tra(l + "ToeBase", P(l + "ToeBase").clone().add(V(0, .004, .006)), P(l + "Toe_End").clone().add(V(0, .002, 0)),
      segmento(.065, [[0, .038], [1, .03]], { scalaX: 1.1, scalaZ: .55 }));
  });
  radice.traverse(o => { if (o.isMesh) o.castShadow = true; });
  return { scene: radice, animations: [] };
}

window.JutaManichino = { crea: creaManichino };
})();
