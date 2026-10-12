// Arnés de pruebas: ejecuta una lista de órdenes contra el motor y vuelca la transcripción.
// Uso: node test/run.mjs build/quijote.json test/solucion1.txt[,test/solucion2.txt] [--quiet] [--state]
import { createRequire } from 'module';
import fs from 'fs';
const require = createRequire(import.meta.url);
const { Engine } = require('../src/engine.js');

const [dbPath, solPath, ...opts] = process.argv.slice(2);
const db = JSON.parse(fs.readFileSync(dbPath, 'utf8'));
// varias soluciones seguidas: a.txt,b.txt
const cmds = solPath.split(',').map((p) => fs.readFileSync(p, 'utf8')).join('\n').split('\n')
  .map(l => l.replace(/#.*/, '').trim()).filter(Boolean);
const quiet = opts.includes('--quiet');
const strip = s => s.replace(/[\x10-\x13]./g, '');

let out = '';
let i = 0;
const problems = [];
let ended = null;
class Stop extends Error {}

const io = {
  print: s => { out += strip(s); },
  cls: () => { out += '\n[CLS]\n'; },
  picture: n => { out += n >= 0 ? `[IMG ${Object.keys(db.names.pics)[n]}]\n` : ''; },
  input: (yesno) => {
    if (yesno) { ended = out.slice(-600); throw new Stop(); }
    if (i >= cmds.length) throw new Stop();
    const c = cmds[i++];
    // detecta respuestas de error del turno anterior
    out += `\n> ${c.toUpperCase()}\n`;
    return c;
  },
  anykey: p => { out += '[TECLA]\n'; },
  pause: () => {},
  border: () => {},
  store: () => null,
};

const eng = new Engine(db, io);
try { await eng.run(); } catch (e) { if (!(e instanceof Stop)) throw e; }

// busca órdenes que dieron error
const blocks = out.split('\n> ');
for (const b of blocks.slice(1)) {
  const [cmd, ...rest] = b.split('\n');
  const body = rest.join('\n');
  if (/No puedes hacer eso|No entiendo|No puedes ir|No tienes eso|No hay de eso|No puedes llevar|pesa demasiado|muert/i.test(body))
    problems.push(`${cmd} -> ${body.trim().split('\n').slice(0, 3).join(' / ')}`);
}
if (!quiet) console.log(out);
console.log('\n==== RESUMEN ====');
console.log(`Órdenes ejecutadas: ${i}/${cmds.length}`);
console.log(`Localidad final: ${Object.entries(db.names.locs).find(([, v]) => v === eng.flags[38])?.[0]}`);
console.log(`Puntuación: ${eng.percent()}% (${eng.flags[30]} puntos)  Turnos: ${eng.flags[31] + 256 * eng.flags[32]}`);
if (ended) console.log('FIN DE PARTIDA:\n' + ended);
if (problems.length) console.log('Respuestas de error:\n  ' + problems.join('\n  '));
if (opts.includes('--state')) {
  const nf = Object.entries(db.names.flags).filter(([, v]) => v >= 64 && eng.flags[v]).map(([k, v]) => `${k}=${eng.flags[v]}`);
  console.log('Flags:', nf.join(' '));
  console.log('Objetos llevados:', eng.objloc.map((l, k) => [l, k]).filter(([l]) => l >= 253).map(([, k]) => Object.keys(db.names.objs)[k]).join(', '));
}
