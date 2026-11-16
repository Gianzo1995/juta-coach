/* Juta Coach — avatar dimostrativo 3D (sezione "Come si fa").
   Un manichino con scheletro esegue l'esercizio. Ogni esercizio = uno SCHEMA di movimento + parametri
   (esercizi/avatar.json). Tutto gira nel telefono: nessuna richiesta esterna oltre ai file dell'app.
   Dipende da three.js r128 (THREE, THREE.OrbitControls, THREE.GLTFLoader), caricati prima di questo file. */
(function () {
"use strict";
const rad = d => d * Math.PI / 180, lerp = (a, b, t) => a + (b - a) * t;
const ease = x => x < .5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2;
const V = (x, y, z) => new THREE.Vector3(x, y, z), X = V(1, 0, 0);
const COLORI = { corpo: 0xe9e6de, giunti: 0x2fbf71, guida: 0xf2b530, guida2: 0x8d9aa5, acciaio: 0xc9c9c4, gomma: 0x141414 };

// ---------------------------------------------------------------- modello (scaricato una volta sola)
let modelloBuf = null;
function caricaModello(url) {
  if (!modelloBuf) modelloBuf = fetch(url).then(r => { if (!r.ok) throw new Error("modello " + r.status); return r.arrayBuffer(); })
    .catch(e => { modelloBuf = null; throw e; });
  return modelloBuf.then(buf => new Promise((ok, ko) => new THREE.GLTFLoader().parse(buf, "", ok, ko)));
}

// ---------------------------------------------------------------- scheletro: posa per direzioni (non per angoli locali)
const OSSA = ["Hips", "Spine", "Spine1", "Spine2", "Neck", "Head",
  ...["Left", "Right"].flatMap(l => [l + "UpLeg", l + "Leg", l + "Foot", l + "ToeBase", l + "Toe_End",
    l + "Shoulder", l + "Arm", l + "ForeArm", l + "Hand",
    ...["Index", "Middle", "Ring", "Pinky", "Thumb"].flatMap(f => [1, 2, 3, 4].map(i => l + "Hand" + f + i))])];

function creaRig(gltf) {
  const m = gltf.scene, bn = {};
  const idle = gltf.animations.find(a => a.name === "idle");      // posa di riposo naturale (mani rilassate)
  if (idle) { const mx = new THREE.AnimationMixer(m); mx.clipAction(idle).play(); mx.update(0); }
  m.updateMatrixWorld(true);
  OSSA.forEach(n => { const o = m.getObjectByName("mixamorig" + n); if (o) bn[n] = o; });
  const riposo = {}, qRiposo = {}, pRiposo = {};
  for (const n in bn) {
    riposo[n] = { q: bn[n].quaternion.clone(), p: bn[n].position.clone() };
    qRiposo[n] = bn[n].getWorldQuaternion(new THREE.Quaternion());
    pRiposo[n] = bn[n].getWorldPosition(new THREE.Vector3());
  }
  const q1 = new THREE.Quaternion(), q2 = new THREE.Quaternion();
  const wp = n => bn[n].getWorldPosition(new THREE.Vector3());
  const wq = n => bn[n].getWorldQuaternion(new THREE.Quaternion());
  const R = {
    m, bn, pRiposo, qRiposo, wp, wq,
    lung: (a, b) => pRiposo[a].distanceTo(pRiposo[b]),
    azzera() { for (const n in bn) { bn[n].quaternion.copy(riposo[n].q); bn[n].position.copy(riposo[n].p); } },
    setQ(n, qw) { const p = bn[n].parent; p.updateMatrixWorld(true); p.getWorldQuaternion(q2);
      bn[n].quaternion.copy(q2.invert().multiply(qw)); bn[n].updateMatrixWorld(true); },
    ruotaRiposo(n, asse, ang) { R.setQ(n, new THREE.Quaternion().setFromAxisAngle(asse, ang).multiply(qRiposo[n])); },
    // orienta l'osso n in modo che il figlio stia nella direzione dir (rotazione minima)
    punta(n, figlio, dir) { bn[n].updateMatrixWorld(true);
      const cur = wp(figlio).sub(wp(n)).normalize(); q1.setFromUnitVectors(cur, dir.clone().normalize());
      R.setQ(n, q1.clone().multiply(wq(n))); },
    ruota(n, asse, ang) { R.setQ(n, new THREE.Quaternion().setFromAxisAngle(asse, ang).multiply(wq(n))); },
    sposta(n, posMondo) { const p = bn[n].parent; p.updateMatrixWorld(true); bn[n].position.copy(p.worldToLocal(posMondo.clone())); bn[n].updateMatrixWorld(true); },
  };
  // braccio a due segmenti (IK): spalla -> gomito -> polso sul bersaglio T, gomito verso "polo"
  const la = R.lung("LeftArm", "LeftForeArm"), lf = R.lung("LeftForeArm", "LeftHand");
  R.braccia = la + lf;
  R.ik = (l, T, polo) => {
    const S = wp(l + "Arm"), d = T.clone().sub(S), L = Math.min(d.length(), la + lf - 0.001), dir = d.normalize();
    const c = Math.max(-1, Math.min(1, (la * la + L * L - lf * lf) / (2 * la * L))), s = Math.sqrt(1 - c * c);
    const p = polo.clone().addScaledVector(dir, -polo.dot(dir)).normalize();
    const E = S.clone().addScaledVector(dir, la * c).addScaledVector(p, la * s);
    R.punta(l + "Arm", l + "ForeArm", E.clone().sub(S));
    R.punta(l + "ForeArm", l + "Hand", T.clone().sub(wp(l + "ForeArm")));
  };
  // palmo: verso calcolato una volta dalla posa di riposo (le dita a riposo sono un po' piegate verso il palmo)
  const verso = {};
  ["Left", "Right"].forEach(l => {
    const P = pRiposo, n0 = V().crossVectors(P[l + "HandIndex1"].clone().sub(P[l + "HandPinky1"]), P[l + "HandMiddle1"].clone().sub(P[l + "Hand"])).normalize();
    const al = P[l + "HandMiddle1"].clone().sub(P[l + "Hand"]).normalize(), tip = P[l + "HandMiddle4"].clone().sub(P[l + "HandMiddle1"]);
    verso[l] = tip.addScaledVector(al, -tip.dot(al)).dot(n0) >= 0 ? 1 : -1;
  });
  R.palmo = l => V().crossVectors(wp(l + "HandIndex1").sub(wp(l + "HandPinky1")), wp(l + "HandMiddle1").sub(wp(l + "Hand"))).normalize().multiplyScalar(verso[l]);
  // mano: dita verso fdir, palmo verso nrm; chiusa = dita avvolte (presa su un bilanciere)
  R.mano = (l, fdir, nrm, chiusa) => {
    R.punta(l + "Hand", l + "HandMiddle1", fdir);
    let pn = R.palmo(l); const f = fdir.clone().normalize();
    const p1 = pn.clone().addScaledVector(f, -pn.dot(f)).normalize(), p2 = nrm.clone().addScaledVector(f, -nrm.dot(f)).normalize();
    R.setQ(l + "Hand", new THREE.Quaternion().setFromUnitVectors(p1, p2).multiply(wq(l + "Hand")));
    if (!chiusa) return;
    pn = R.palmo(l);
    const piega = { Index: [1.25, 1.45, .9], Middle: [1.3, 1.5, .9], Ring: [1.3, 1.5, .9], Pinky: [1.3, 1.45, .9], Thumb: [.35, .5, .4] };
    for (const d in piega) for (let i = 1; i <= 3; i++) {
      const n = l + "Hand" + d + i, dd = wp(l + "Hand" + d + (i + 1)).sub(wp(n)).normalize();
      R.ruota(n, V().crossVectors(dd, pn).normalize(), piega[d][i - 1]);
    }
  };
  return R;
}

// ---------------------------------------------------------------- attrezzi
function bilanciere() {
  const g = new THREE.Group();
  const acciaio = new THREE.MeshStandardMaterial({ color: COLORI.acciaio, roughness: .28, metalness: .55 });
  const gomma = new THREE.MeshStandardMaterial({ color: COLORI.gomma, roughness: .8 });
  const filo = new THREE.MeshStandardMaterial({ color: COLORI.giunti, roughness: .5 });
  const cil = (r, l, mat, x) => { const c = new THREE.Mesh(new THREE.CylinderGeometry(r, r, l, 40), mat); c.rotation.z = Math.PI / 2; c.position.x = x; c.castShadow = true; g.add(c); };
  cil(.0145, 1.31, acciaio, 0);
  [1, -1].forEach(s => { cil(.025, .42, acciaio, s * .86); cil(.04, .03, acciaio, s * .67);
    cil(.225, .065, gomma, s * .725); cil(.226, .012, filo, s * .725); cil(.06, .067, acciaio, s * .725); cil(.032, .04, acciaio, s * .78); });
  return g;
}

// linee guida tratteggiate (aggiornabili)
function linea(scena, colore, a, b) {
  const geo = new THREE.BufferGeometry().setFromPoints([a, b]);
  const l = new THREE.Line(geo, new THREE.LineDashedMaterial({ color: colore, dashSize: .04, gapSize: .03 }));
  l.computeLineDistances(); scena.add(l);
  l.imposta = (p, q) => { const pos = geo.attributes.position; pos.setXYZ(0, p.x, p.y, p.z); pos.setXYZ(1, q.x, q.y, q.z); pos.needsUpdate = true; l.computeLineDistances(); };
  return l;
}

// ---------------------------------------------------------------- SCHEMI di movimento
// Ogni schema riceve (rig, parametri, scena) e restituisce { fasi, inAlto, posa(t), viste, bersaglio, guide(vis) }.
// t = 0 posizione di partenza, t = 1 punto più profondo.
const SCHEMI = {};

/* Accosciata: squat a corpo libero o con bilanciere sulla schiena.
   parametri: attrezzo ("bilanciere_schiena"), profondita (gradi coscia, 100 = sotto il parallelo),
   inclinazione_busto (gradi, solo senza bilanciere; col bilanciere si calcola per tenerlo sul metà piede) */
SCHEMI.accosciata = (R, par, scena) => {
  const P = R.pRiposo, conBil = par.attrezzo === "bilanciere_schiena";
  const L1 = R.lung("LeftLeg", "LeftFoot"), L2 = R.lung("LeftUpLeg", "LeftLeg");
  const FX = (Math.abs(P.LeftFoot.x) + Math.abs(P.RightFoot.x)) / 2 + .01, FY = (P.LeftFoot.y + P.RightFoot.y) / 2, FZ = (P.LeftFoot.z + P.RightFoot.z) / 2;
  const off = P.LeftUpLeg.clone().sub(P.Hips), MIDZ = FZ + .035;
  const prof = par.profondita ?? 100, busto = par.inclinazione_busto ?? 44;
  const su = a => V(0, Math.cos(a), Math.sin(a)), dietro = a => V(0, Math.sin(a), -Math.cos(a));
  const sulBil = (n, a) => n.clone().addScaledVector(su(a), -.075).addScaledVector(dietro(a), .075);
  const HjR = P.LeftUpLeg.clone().add(P.RightUpLeg).multiplyScalar(.5), bR = sulBil(P.Neck, 0);
  const Du = bR.y - HjR.y, Db = HjR.z - bR.z, RR = Math.hypot(Du, Db), PHI = Math.atan2(Db, Du);
  const bil = conBil ? bilanciere() : null; if (bil) scena.add(bil);
  const gPunte = linea(scena, COLORI.guida, V(FX + .05, .005, FZ + .2), V(FX + .05, .95, FZ + .2));
  const gCentro = linea(scena, COLORI.guida2, V(0, .005, MIDZ), V(0, 1.8, MIDZ));
  const gProf = linea(scena, COLORI.guida, V(-.35, 0, 0), V(.35, 0, 0));
  let mostra = true;
  return {
    viste: conBil ? { lato: [4.0, 1.35, 1.25], tq: [3.2, 1.6, 2.9], fronte: [.15, 1.3, 4.3] } : { lato: [3.7, 1.3, .2], tq: [2.8, 1.5, 2.5], fronte: [.15, 1.3, 3.7] },
    bersaglio: [0, .78, .05], ombra: [0, 0, 0],
    guide(v) { mostra = v; gPunte.visible = gCentro.visible = v; },
    posa(t) {
      R.azzera();
      const a1 = rad(lerp(conBil ? 4.5 : 0, 38, t)), a2 = rad(lerp(conBil ? -4.5 : 0, prof, t));
      const pos = {};
      ["Left", "Right"].forEach(l => { const s = l === "Left" ? 1 : -1, A = V(s * FX, FY, FZ);
        const K = V(A.x + s * .035 * t, A.y + L1 * Math.cos(a1), A.z + L1 * Math.sin(a1));
        pos[l] = { A, K, H: V(P[l + "UpLeg"].x, K.y + L2 * Math.cos(a2), K.z - L2 * Math.sin(a2)) }; });
      let a3;
      if (conBil) a3 = Math.max(rad(2), PHI + Math.asin(Math.max(-1, Math.min(1, (MIDZ - pos.Left.H.z) / RR))));
      else a3 = rad(lerp(2, busto, t));
      const pr = a3 * .8, qp = new THREE.Quaternion().setFromAxisAngle(X, pr);
      R.setQ("Hips", qp.clone().multiply(R.qRiposo.Hips));
      R.sposta("Hips", pos.Left.H.clone().sub(off.clone().applyQuaternion(qp)));
      ["Left", "Right"].forEach(l => { const p = pos[l];
        R.punta(l + "UpLeg", l + "Leg", p.K.clone().sub(R.wp(l + "UpLeg")));
        R.punta(l + "Leg", l + "Foot", p.A.clone().sub(R.wp(l + "Leg")));
        R.setQ(l + "Foot", R.qRiposo[l + "Foot"]); R.setQ(l + "ToeBase", R.qRiposo[l + "ToeBase"]); });
      R.punta("Spine", "Spine1", su(a3 * .9)); R.punta("Spine1", "Spine2", su(a3)); R.punta("Spine2", "Neck", su(a3));
      R.punta("Neck", "Head", su(a3 * .42)); R.ruotaRiposo("Head", X, a3 * .1);
      if (conBil) {
        const bc = sulBil(R.wp("Neck"), a3); bil.position.copy(bc);
        const fd = su(a3).addScaledVector(dietro(a3), .2).normalize(), nm = dietro(a3).negate().addScaledVector(su(a3), .2).normalize();
        ["Left", "Right"].forEach(l => { const s = l === "Left" ? 1 : -1;
          R.ik(l, bc.clone().add(V(s * .4, 0, 0)).addScaledVector(nm, -.034).addScaledVector(fd, -.07),
            su(a3).multiplyScalar(-.8).addScaledVector(dietro(a3), .6).add(V(s * .2, 0, 0)));
          R.mano(l, fd, nm, true); });
      } else {
        const b = rad(lerp(8, 90, Math.min(1, t * 1.2)));
        ["Left", "Right"].forEach(l => { const s = l === "Left" ? 1 : -1;
          R.punta(l + "Arm", l + "ForeArm", V(s * lerp(.22, .1, t), -Math.cos(b), Math.sin(b)));
          R.punta(l + "ForeArm", l + "Hand", V(s * lerp(.12, .04, t), -Math.cos(b + .12), Math.sin(b + .12))); });
      }
      gProf.visible = mostra && t > .8;
      gProf.imposta(V(-.35, pos.Left.K.y, (pos.Left.H.z + pos.Left.K.z) / 2), V(.35, pos.Left.K.y, (pos.Left.H.z + pos.Left.K.z) / 2));
    },
  };
};

/* Piegamenti: corpo rigido che ruota sulle punte dei piedi, mani ferme sotto le spalle.
   parametri: larghezza_mani (metri in più rispetto alle spalle, default .1), gomiti (gradi dal busto, default 45) */
SCHEMI.piegamenti = (R, par, scena) => {
  const larg = par.larghezza_mani ?? .1, gom = rad(par.gomiti ?? 45);
  function corpo(th) {
    R.azzera();
    const U = V(0, Math.sin(th), Math.cos(th));
    R.setQ("Hips", new THREE.Quaternion().setFromAxisAngle(X, Math.PI / 2 - th).multiply(R.qRiposo.Hips));
    R.punta("Spine", "Spine1", U); R.punta("Spine1", "Spine2", U); R.punta("Spine2", "Neck", U);
    R.punta("Neck", "Head", V(0, Math.sin(th) - .12, Math.cos(th)));
    R.ruotaRiposo("Head", X, Math.PI / 2 - th + .15);
    ["Left", "Right"].forEach(l => { const s = l === "Left" ? 1 : -1, D = U.clone().negate().add(V(-s * .012, 0, 0));
      R.punta(l + "UpLeg", l + "Leg", D); R.punta(l + "Leg", l + "Foot", D);
      R.punta(l + "Foot", l + "ToeBase", V(0, -1, .12)); R.punta(l + "ToeBase", l + "Toe_End", V(0, -.04, 1)); });
    const tb = R.wp("LeftToeBase").add(R.wp("RightToeBase")).multiplyScalar(.5);
    R.sposta("Hips", R.wp("Hips").add(V(0, .028 - tb.y, -tb.z)));
    return R.wp("LeftArm");
  }
  // tabella: inclinazione del corpo -> posizione della spalla (per trovare alto e basso)
  const tab = []; for (let d = 0; d <= 45; d += .5) { const s = corpo(rad(d)); tab.push({ th: rad(d), x: s.x, y: s.y, z: s.z }); }
  const cerca = (f, v) => { for (let i = 1; i < tab.length; i++) { const a = f(tab[i - 1]), b = f(tab[i]);
    if ((v - a) * (v - b) <= 0) return tab[i - 1].th + (tab[i].th - tab[i - 1].th) * ((v - a) / ((b - a) || 1)); }
    return tab.reduce((p, o) => Math.abs(f(o) - v) < Math.abs(f(p) - v) ? o : p).th; };   // nessun incrocio: il più vicino
  // in basso: spalle a ~15 cm da terra, ma mai meno di 3 cm sopra il corpo disteso (dipende dallo spessore del manichino)
  const WY = .035, thBasso = cerca(o => o.y, Math.max(.155, tab[0].y + .03));
  const basso = tab.reduce((p, o) => Math.abs(o.th - thBasso) < Math.abs(p.th - thBasso) ? o : p);
  const HZ = basso.z - .02, HX = Math.abs(basso.x) + larg;
  const thAlto = cerca(o => Math.hypot(HX - Math.abs(o.x), o.y - WY, o.z - HZ), .965 * R.braccia);
  const gCorpo = linea(scena, COLORI.guida, V(.33, 0, 0), V(.33, 0, 1));
  const gMano = linea(scena, COLORI.guida2, V(HX + .06, .005, HZ), V(HX + .06, .75, HZ));
  const polo = s => V(s * Math.sin(gom) * 1.1, .35, -Math.cos(gom) * .8);
  return {
    viste: { lato: [4.7, .9, .75], tq: [3.3, 1.8, 3.5], fronte: [.9, 1.5, 4.6] },
    bersaglio: [0, .28, .72], ombra: [0, 0, .7], lungo: true,
    guide(v) { gCorpo.visible = gMano.visible = v; },
    posa(t) {
      corpo(lerp(thAlto, thBasso, t));
      ["Left", "Right"].forEach(l => { const s = l === "Left" ? 1 : -1;
        R.ik(l, V(s * HX, WY, HZ), polo(s)); R.mano(l, V(s * .18, 0, 1), V(0, -1, 0), false); });
      const an = R.wp("LeftFoot"), hd = R.wp("Head");
      gCorpo.imposta(V(.33, an.y, an.z), V(.33, hd.y + (hd.y - an.y) * .06, hd.z + (hd.z - an.z) * .06));
    },
  };
};

const FASI = {   // nomi delle fasi e durate (secondi a velocità 1x)
  accosciata: [["In piedi", .8], ["Discesa", 1.9], ["Fondo", .45], ["Risalita", 1.4]],
  piegamenti: [["In alto", .7], ["Discesa", 1.5], ["In basso", .35], ["Spinta", 1.0]],
};

// ---------------------------------------------------------------- scena
/* JutaAvatar.mostra(contenitore, voce, opzioni) -> Promise<controllo>
   voce = { schema, parametri, fasi?: {nome fase: testo} } (da esercizi/avatar.json)
   opzioni = { modello?: url di un .glb con scheletro Mixamo (se manca: manichino di manichino.js), suFase(nome, testo) }
   controllo = { ferma(), pausa(bool), velocita(x), vista("lato"|"tq"|"fronte"), guide(bool) } */
async function mostra(cont, voce, opz = {}) {
  const schema = SCHEMI[voce.schema]; if (!schema) throw new Error("schema sconosciuto: " + voce.schema);
  const R0 = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  R0.setPixelRatio(Math.min(2, window.devicePixelRatio || 1)); R0.shadowMap.enabled = true; R0.shadowMap.type = THREE.PCFSoftShadowMap;
  R0.outputEncoding = THREE.sRGBEncoding; cont.appendChild(R0.domElement);
  const scena = new THREE.Scene(), cam = new THREE.PerspectiveCamera(32, 1, .1, 50);
  const ridimensiona = () => { const w = cont.clientWidth, h = cont.clientHeight; if (!w || !h) return; R0.setSize(w, h); cam.aspect = w / h; cam.updateProjectionMatrix(); };
  ridimensiona(); const ro = new ResizeObserver(ridimensiona); ro.observe(cont);
  scena.add(new THREE.HemisphereLight(0xffffff, 0x556070, .85));
  const sole = new THREE.DirectionalLight(0xffffff, 1); sole.castShadow = true; sole.shadow.mapSize.set(1024, 1024);
  Object.assign(sole.shadow.camera, { left: -1.7, right: 1.7, top: 2.5, bottom: -1.2 }); scena.add(sole, sole.target);
  const contro = new THREE.DirectionalLight(0xbfe8da, .55); contro.position.set(-3, 2.5, -2.5); scena.add(contro);
  const pavimento = new THREE.Mesh(new THREE.CircleGeometry(1.5, 64), new THREE.ShadowMaterial({ opacity: .35 }));
  pavimento.rotation.x = -Math.PI / 2; pavimento.receiveShadow = true; scena.add(pavimento);
  const anello = new THREE.Mesh(new THREE.RingGeometry(.62, .64, 96), new THREE.MeshBasicMaterial({ color: COLORI.giunti, transparent: true, opacity: .35 }));
  anello.rotation.x = -Math.PI / 2; scena.add(anello);

  // senza file indicato si usa il manichino costruito nel codice (web/avatar/manichino.js)
  const gltf = opz.modello ? await caricaModello(opz.modello) : window.JutaManichino.crea();
  gltf.scene.traverse(o => { if (o.isMesh) { o.castShadow = true; o.frustumCulled = false;
    const giunto = /joint|giunto/i.test(o.material.name || o.name);
    o.material = new THREE.MeshStandardMaterial({ skinning: !!o.isSkinnedMesh, color: giunto ? COLORI.giunti : COLORI.corpo, roughness: giunto ? .5 : .35, metalness: .05 }); } });
  scena.add(gltf.scene);
  const R = creaRig(gltf), S = schema(R, voce.parametri || {}, scena);
  const [ox, , oz] = S.ombra; pavimento.position.set(ox, 0, oz); anello.position.set(ox, .002, oz); if (S.lungo) anello.scale.setScalar(1.45);
  sole.position.set(ox + 2.5, 4, oz + 2.5); sole.target.position.set(ox, 0, oz);

  const ctl = new THREE.OrbitControls(cam, R0.domElement);
  ctl.target.set(...S.bersaglio); ctl.enableDamping = true; ctl.enablePan = false; ctl.minDistance = 2; ctl.maxDistance = 7; ctl.maxPolarAngle = Math.PI * .52;
  let verso = V(...S.viste.tq), inMoto = false; cam.position.copy(verso);
  ctl.addEventListener("start", () => { inMoto = false; });

  const fasi = FASI[voce.schema], tot = fasi.reduce((s, f) => s + f[1], 0);
  let orologio = 0, prima = null, va = true, vel = 1, faseVista = "", attivo = true;
  function giro(ts) {
    if (!attivo) return;
    if (prima == null) prima = ts; const dt = Math.min(.05, (ts - prima) / 1000); prima = ts;
    if (va) orologio = (orologio + dt * vel) % tot;
    let c = orologio, t = 0, fase = fasi[0][0];
    for (const [n, d] of fasi) { if (c < d) { fase = n; const f = c / d;
      t = n === fasi[0][0] ? 0 : n === fasi[2][0] ? 1 : n === fasi[1][0] ? ease(f) : 1 - ease(f); break; } c -= d; }
    S.posa(t);
    if (inMoto) { cam.position.lerp(verso, .08); if (cam.position.distanceTo(verso) < .01) inMoto = false; }
    ctl.update(); R0.render(scena, cam);
    if (fase !== faseVista) { faseVista = fase; opz.suFase?.(fase, voce.fasi?.[fase] || ""); }
    requestAnimationFrame(giro);
  }
  requestAnimationFrame(giro);
  return {
    pausa(p) { va = !p; }, velocita(x) { vel = x; }, guide(v) { S.guide(v); },
    vista(n) { verso = V(...S.viste[n]); inMoto = true; },
    _posa(c) { orologio = c; }, _cam: cam, _ctl: ctl, _rig: R,
    ferma() { attivo = false; ro.disconnect(); ctl.dispose(); R0.dispose(); R0.forceContextLoss?.(); R0.domElement.remove(); },
  };
}

window.JutaAvatar = { mostra, SCHEMI, FASI };
})();
