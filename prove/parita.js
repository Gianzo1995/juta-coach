// Parte JavaScript della prova di parità: vedi prove/parita.py
const path = require("path");
const { Analizzatore, costruisciCatalogo, applicaImpostazioni } = require(path.join(__dirname, "..", "web", "motore.js"));
const d = require(path.resolve(process.argv[2]));
let ok = true;

const { esercizi } = costruisciCatalogo(d.voci);
const ordinato = v => JSON.parse(JSON.stringify(v, (k, x) =>
  (x && typeof x === "object" && !Array.isArray(x)) ? Object.fromEntries(Object.entries(x).sort()) : x));

for (const [id, c] of Object.entries(d.cfg)) {
  const e = esercizi[id] || {};
  const js = ordinato({ misure: e.misure, ripetizione: e.ripetizione, errori: e.errori, lato: e.lato });
  if (JSON.stringify(js) !== JSON.stringify(ordinato(c))) { ok = false; console.log("CONFIG DIVERSA:", id); }
}
console.log("Configurazioni confrontate:", Object.keys(d.cfg).join(", "));

for (const [k, v] of Object.entries(d.impostazioni || {})) {
  const id = k.split("|")[0], r = applicaImpostazioni(esercizi[id], v.imposta);
  const js = ordinato({ misure: r.misure, ripetizione: r.ripetizione, errori: r.errori, lato: r.lato });
  if (JSON.stringify(js) !== JSON.stringify(ordinato(v.cfg))) { ok = false; console.log("IMPOSTAZIONE DIVERSA:", k); }
}
console.log("Impostazioni confrontate:", Object.keys(d.impostazioni || {}).length);

const chiave = e => JSON.stringify([e.tipo, e.numero ?? e.ripetizione ?? null, e.errori ?? e.id ?? null,
  e.durata_s ?? null, e.anticipato ?? null, e.t ?? e.fine_t ?? null, e.fasi ? ordinato(e.fasi) : null]);
for (const [k, frames] of Object.entries(d.cases)) {
  const a = new Analizzatore(esercizi[k]);
  let ev = [], t = 0;
  for (const p of frames) { ev.push(...a.aggiorna(p, t).eventi); t += 1 / 30; }
  for (let i = 0; i < 240; i++) { ev.push(...a.aggiorna(null, t).eventi); t += 1 / 30; }
  const uguale = JSON.stringify(ev.map(chiave)) === JSON.stringify(d.py[k].map(chiave));
  ok &&= uguale;
  console.log(uguale ? "OK     " : "DIVERSO", k, `${ev.length} eventi`);
}
console.log(ok ? "Parità Python/JavaScript confermata" : "ERRORE: i due motori non danno gli stessi risultati");
process.exit(ok ? 0 : 1);
