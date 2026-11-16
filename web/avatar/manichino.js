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
function segmento(len, profilo, { scalaX = 1, scalaZ = 1, calotte = true } = {}) {
  const pts = [], r0 = profilo[0][1], r1 = profilo[profilo.length - 1][1];
  if (calotte) for (let i = 0; i <= 8; i++) { const a = (i / 8) * Math.PI / 2; pts.push(new THREE.Vector2(Math.max(1e-4, r0 * Math.sin(a)), -r0 * Math.cos(a) * .9)); }
  const N = 28;
  for (let i = 1; i < N; i++) {
    const t = i / N; let k = 1; while (k < profilo.length - 1 && profilo[k][0] < t) k++;
    const [ta, ra] = profilo[k - 1], [tb, rb] = profilo[k], u = (t - ta) / ((tb - ta) || 1), w = (1 - Math.cos(u * Math.PI)) / 2;
    pts.push(new THREE.Vector2(ra + (rb - ra) * w, t * len));
  }
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
  // --- tronco
  tra("Hips", V(0, .875, -.005), V(0, 1.03, -.01), segmento(.155, [[0, .1], [.45, .148], [1, .128]], { scalaX: 1.12, scalaZ: .78 }));
  palla("Spine1", V(0, 1.11, -.012), .1, [1.12, .62, .74]);
  tra("Spine1", V(0, 1.12, -.012), V(0, 1.23, -.015), segmento(.11, [[0, .108], [1, .118]], { scalaX: 1.12, scalaZ: .72, calotte: false }));
  tra("Spine2", V(0, 1.2, -.018), V(0, 1.44, -.025), segmento(.24, [[0, .118], [.55, .148], [1, .1]], { scalaX: 1.22, scalaZ: .74 }));
  palla("Neck", V(0, 1.51, -.02), .052, [1, .9, 1]);
  tra("Neck", V(0, 1.49, -.02), V(0, 1.575, -.008), segmento(.085, [[0, .045], [1, .04]], { calotte: false }));
  // --- testa: ovale, un po' più profonda davanti (mento)
  palla("Head", V(0, 1.672, .008), .1, [.88, 1.08, .98], corpo);                     // cranio
  palla("Head", V(0, 1.625, .03), .07, [.95, .9, 1], corpo);                         // mascella e mento
  ["Left", "Right"].forEach(l => {
    const s = l === "Left" ? 1 : -1;
    // --- braccio
    palla(l + "Shoulder", P(l + "Arm").clone().add(V(-.01 * s, .012, 0)), .068, [1, .95, 1]);
    tra(l + "Shoulder", V(.07 * s, 1.445, -.022), P(l + "Arm").clone().add(V(-.02 * s, .01, 0)), segmento(.11, [[0, .05], [1, .06]], { scalaZ: .8 }));
    tra(l + "Arm", P(l + "Arm"), P(l + "ForeArm"), segmento(.28, [[0, .052], [.12, .055], [.45, .052], [1, .04]], { scalaZ: .92 }));
    palla(l + "ForeArm", P(l + "ForeArm"), .041);
    tra(l + "ForeArm", P(l + "ForeArm"), P(l + "Hand"), segmento(.255, [[0, .04], [.25, .045], [1, .028]], { scalaX: .92 }));
    palla(l + "Hand", P(l + "Hand"), .028);
    // --- mano: palmo + falangi
    const H = P(l + "Hand");
    tra(l + "Hand", H.clone().add(V(-.004 * s, -.012, .002)), H.clone().add(V(-.006 * s, -.08, .002)),
      segmento(.068, [[0, .03], [.6, .042], [1, .038]], { scalaX: .5, scalaZ: 1.15 }));
    for (const d of ["Index", "Middle", "Ring", "Pinky", "Thumb"]) for (let i = 1; i <= 3; i++) {
      const a = l + "Hand" + d + i, b = l + "Hand" + d + (i + 1), r = (d === "Thumb" ? .0115 : d === "Pinky" ? .0085 : .0098) * (1 - (i - 1) * .1);
      tra(a, P(a), P(b), segmento(P(a).distanceTo(P(b)), [[0, r], [1, r * .93]]));
    }
    // --- gamba
    palla(l + "UpLeg", P(l + "UpLeg").clone().add(V(.01 * s, -.02, 0)), .085, [1, 1, 1]);
    tra(l + "UpLeg", P(l + "UpLeg"), P(l + "Leg"), segmento(.425, [[0, .085], [.25, .084], [.7, .066], [1, .052]], { scalaZ: .96 }));
    palla(l + "Leg", P(l + "Leg"), .056);
    tra(l + "Leg", P(l + "Leg"), P(l + "Foot"), segmento(.425, [[0, .052], [.28, .058], [.75, .038], [1, .032]], { scalaX: .95 }));
    palla(l + "Foot", P(l + "Foot"), .036);
    // --- piede: tallone-pianta sull'osso Foot, punta sull'osso ToeBase
    tra(l + "Foot", P(l + "Foot").clone().add(V(0, -.05, -.06)), P(l + "ToeBase").clone().add(V(0, .01, 0)),
      segmento(.2, [[0, .036], [.5, .044], [1, .04]], { scalaX: 1.05, scalaZ: .7 }));
    tra(l + "ToeBase", P(l + "ToeBase").clone().add(V(0, .004, 0)), P(l + "Toe_End").clone().add(V(0, .002, 0)),
      segmento(.07, [[0, .038], [1, .03]], { scalaX: 1.1, scalaZ: .55 }));
  });
  radice.traverse(o => { if (o.isMesh) o.castShadow = true; });
  return { scene: radice, animations: [] };
}

window.JutaManichino = { crea: creaManichino };
})();
