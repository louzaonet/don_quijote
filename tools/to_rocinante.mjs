// Pasa el remake (build/quijote.json) a un proyecto de Rocinante con el mundo
// y los dibujos: vocabulario, localidades con sus salidas y sus dibujos,
// objetos, nombres de las banderas y la fuente de 1989. Los procesos del
// remake no van: el proyecto lleva los de la plantilla de Rocinante, así que
// se puede recorrer el mapa, coger y dejar cosas y ver los dibujos.
//
// Uso: node tools/to_rocinante.mjs [salida.json] [--en]
// Necesita Rocinante al lado (../rocinante) o en la variable ROCINANTE.

import fs from 'fs';
import path from 'path';
import vm from 'vm';

const HERE = path.dirname(new URL(import.meta.url).pathname);
const ROC = path.resolve(process.env.ROCINANTE || path.join(HERE, '../../rocinante'));
const { newProject } = await import(path.join(ROC, 'src/project/template.js'));
const { compileProject } = await import(path.join(ROC, 'src/project/compile.js'));
const { defaultCharset, fitFont42 } = await import(path.join(ROC, 'src/spectrum/zxexport.js'));
const { charToDaad } = await import(path.join(ROC, 'src/daad/charset.js'));
const { enc, paint } = await import(path.join(ROC, 'src/gfx/vector.js'));

// --en: la versión inglesa (build/quijote_en.json y plantilla de Rocinante en inglés)
const args = process.argv.slice(2);
const EN = args.includes('--en');
const db = JSON.parse(fs.readFileSync(path.join(HERE, EN ? '../build/quijote_en.json' : '../build/quijote.json'), 'utf8'));
const font = JSON.parse(fs.readFileSync(path.join(HERE, '../src/font.json'), 'utf8'));
const out = args.find((a) => !a.startsWith('--')) || path.join(HERE, EN ? '../don_quixote_2026.rocinante.json' : '../don_quijote_2026.rocinante.json');

const inv = (o) => Object.fromEntries(Object.entries(o).map(([k, v]) => [v, k]));
const locName = inv(db.names.locs), objName = inv(db.names.objs), picName = inv(db.names.pics);
const TYPES = ['verb', 'adverb', 'noun', 'adjective', 'preposition', 'conjunction', 'pronoun'];

// --------------------------------------------------------------- textos
// Los códigos de color del remake (\x10n tinta, \x11n papel, \x12n parpadeo,
// \x13n brillo) no existen en los textos de DAAD: se quitan
const clean = (s) => s.replace(/[\x10-\x13]./g, '');

// --------------------------------------------------------------- proyecto
const p = EN ? newProject('Don Quixote of La Mancha', 'en') : newProject('Don Quijote de la Mancha', 'es');
p.meta.author = 'Jorge Louzao Penalva (Aventuras Level 10)';
p.meta.description = 'Remake de 2026 de la aventura de 1989. De momento, el mundo y los dibujos del remake: localidades, salidas, objetos, vocabulario y los gráficos. Los procesos son los de la plantilla de Rocinante.';

// Vocabulario: el del remake (palabras de 5 letras, como en PAW y DAAD)
const vocab = [];
const seen = new Set();
for (const [w, n, t] of db.vocab) {
  const word = w.slice(0, 5);
  if (seen.has(word)) continue;
  seen.add(word);
  vocab.push({ word, value: n, type: TYPES[t] });
}
// Palabras que usan los procesos de la plantilla y el remake no tiene
const used = (type) => new Set(vocab.filter((v) => v.type === type).map((v) => v.value));
for (const v of p.vocab) {
  if (seen.has(v.word)) continue;
  if (!['verb', 'noun'].includes(v.type) || (v.type === 'noun' && v.value < 20)) continue;
  const taken = used(v.type);
  let n = 20; while (taken.has(n)) n++;
  // los sinónimos de la plantilla que ya estén añadidos comparten número
  const twin = p.vocab.find((x) => x.type === v.type && x.value === v.value && x.word !== v.word && vocab.some((y) => y.word === x.word && y.type === v.type));
  vocab.push({ word: v.word, value: twin ? vocab.find((y) => y.word === twin.word).value : n, type: v.type });
  seen.add(v.word);
}
p.vocab = vocab;
const firstWord = (value, type) => vocab.find((v) => v.value === value && v.type === type)?.word;

// Localidades: las del remake con su mismo número (las banderas del remake guardan números de
// localidad, así siguen valiendo)
// (la 0 se queda sin texto: es donde DAAD guarda lo que hay dentro del objeto
// 0, las alforjas; la presentación va en 'intro', como en el remake)
const ids = db.locs.map((_, i) => (i === 0 ? 'arranque' : locName[i] || `loc${i}`));
const titulo = clean(db.msgs[0]).split('\n').map((l) => l.trim()).join('\n');
p.locations = db.locs.map((l, i) => ({
  id: ids[i],
  text: i === 1 ? titulo + '\n' : clean(l.text),
  exits: (db.conns[i] || []).map(([d, to]) => ({ word: firstWord(d, 'noun'), to: ids[to] })),
}));

// Objetos. En DAAD el texto lleva el artículo indeterminado ("Una lanza."),
// que el motor cambia por el determinado cuando hace falta ("Cojo la lanza.")
const ARTICLE = { el: 'Un', la: 'Una', los: 'Unos', las: 'Unas' };
function objectText(t) {
  const m = t.match(/^(el|la|los|las) (.*)$/);
  const s = m ? `${ARTICLE[m[1]]} ${m[2]}` : t.charAt(0).toUpperCase() + t.slice(1);
  return s + '.';
}
const special = { 252: 'NOTCREATED', 253: 'WORN', 254: 'CARRIED' };
p.objects = db.objs.map((o, i) => ({
  id: objName[i] || `obj${i}`,
  text: objectText(o.text),
  noun: firstWord(o.noun, 'noun') ?? '_',
  adj: o.adj === 255 ? '_' : firstWord(o.adj, 'adjective') ?? '_',
  loc: special[o.loc] ?? ids[o.loc],
  weight: o.w, container: !!o.cont, wearable: !!o.wear, attrs: 0,
}));

// Banderas con nombre (las del sistema ya las conoce Rocinante)
p.flags = Object.entries(db.names.flags).filter(([, n]) => n >= 64).map(([name, num]) => ({ name, num }));

// Procesos de la plantilla, ajustados: presentación en la localidad 0, la
// partida empieza en la biblioteca, 4 objetos y 20 de peso como el remake
// (la plantilla inglesa llama main/init a los procesos, torch al objeto 0 y start a la entrada)
const light = p.processes.find((x) => x.id === 'principal' || x.id === 'main');
light.source = light.source.replace('AT intro ', 'AT arranque').replace(/ABSENT (linterna|torch)/, `ABSENT ${p.objects[0].id}`);
const ini = p.processes.find((x) => x.id === 'inicio' || x.id === 'init');
ini.source = ini.source.replace('DESC intro ', 'DESC intro ').replace(/GOTO (entrada|start)\b/, 'GOTO biblioteca')
  .replace('LET fStrength 10', `LET fStrength ${db.config.maxweight}`).replace('LET fMaxCarr 4', `LET fMaxCarr ${db.config.maxobj}`);
p.messages = [];
// Mensajes del sistema: los del remake (en segunda persona) donde significan lo
// mismo que en DAAD; los demás, los de la plantilla
for (const i of [0, 6, 7, 8, 9, 12, 15, 23, 24, 25, 26, 27, 28, 29, 36, 37, 38, 39, 40, 42, 43, 52]) {
  if (db.sys[i]) p.sysmsgs[i] = clean(db.sys[i]);
}
p.sysmsgs[10] = EN ? 'You are wearing:\n' : 'Llevas puesto:\n';
const resp = p.processes.find((x) => x.id === 'respuestas' || x.id === 'responses');
resp.source = resp.source.replace('No veo nada especial.', 'No ves nada especial.').replace('I see nothing special.', 'You see nothing special.');

// --------------------------------------------------------------- fuente
// La fuente de 1989: los símbolos que hacían de letras del castellano
// van a su sitio en DAAD, como al importar un juego de PAW
const cs = defaultCharset().slice();
cs.set(font, 32 * 8);
const ES = { '@': 'á', '#': 'é', '$': 'í', '%': 'ó', '&': 'ú', '[': '¡', '\\': 'Ñ', ']': '¿', '^': '«', '`': '»', '{': 'ü', '|': 'ñ', '~': 'ç' };
for (const [sym, ch] of Object.entries(ES)) {
  const g = (sym.charCodeAt(0) - 32) * 8;
  cs.set(font.slice(g, g + 8), charToDaad(ch) * 8);
}
// La fuente es de 32 columnas (letras de 7 puntos); DAAD escribe a 42 y solo
// enseña 6: se corre un punto a la izquierda para que la m no parezca una r
fitFont42(cs);

// --------------------------------------------------------------- dibujos
// Los dibujos del remake usan coordenadas absolutas desde arriba en una zona
// de 256x96; en DAAD van desde abajo (y = 175 arriba) y LINE y FILL son
// relativos a la pluma.
//  - PLOT del remake pinta la tinta y deja el papel: en DAAD se dibuja con
//    PAPER 8 (transparente) y el papel solo se pone para BLOCK y CLS
//  - CLS: BLOCK de toda la zona con los colores actuales
//  - SHADE n: trama del remake (el byte, girado un bit por fila) como carácter
//  - los rellenos del remake no pasan de la zona del dibujo; en DAAD sí, así
//    que los dibujos con rellenos ponen una raya justo debajo (fila 96, con
//    tinta y brillo transparentes para no tocar los colores) y la borran al final
const Y = (y) => 175 - y;
const shadeSlots = new Map();
let nextSlot = 164;
const popcount = (b) => { let n = 0; while (b) { n += b & 1; b >>= 1; } return n; };
function shadeChar(pat) {
  if (Array.isArray(pat)) {                // trama de 8 bytes: ya es un carácter
    const key = pat.join(',');
    if (!shadeSlots.has(key)) { cs.set(pat, nextSlot * 8); shadeSlots.set(key, nextSlot++); }
    return shadeSlots.get(key);
  }
  if (!shadeSlots.has(pat)) {
    const g = [];
    for (let k = 0; k < 8; k++) {
      const r = k & 3;
      let b = ((pat >> r) | (pat << (8 - r))) & 0xff;
      if (r & 1 && popcount(pat) <= 2) b = 0;
      g.push(b);
    }
    cs.set(g, nextSlot * 8);
    shadeSlots.set(pat, nextSlot++);
  }
  return shadeSlots.get(pat);
}
// El rellenado de DAAD (el del intérprete) se queda corto en zonas con muchos
// entrantes, porque solo guarda 30 puntos pendientes. Para que el dibujo
// salga como en el remake, tras cada FILL o SHADE se pintan los dos (el remake
// con su propio screen.js y DAAD con el de Rocinante) y, si queda algo sin
// rellenar, se añade otro FILL o SHADE ahí.
const ctx = { window: {}, requestAnimationFrame() {} };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(HERE, '../src/screen.js'), 'utf8'), ctx);
const RemakeScreen = ctx.window.SpectrumScreen;
function remakePixels(cmds) {
  const s = Object.create(RemakeScreen.prototype);
  Object.assign(s, { px: new Uint8Array(256 * 192), ink: new Uint8Array(768), paper: new Uint8Array(768),
    bright: new Uint8Array(768), flash: new Uint8Array(768), db: { pics: [...db.pics, cmds] } });
  s.picture(db.pics.length);
  return s.px;
}
const lib = [];                           // dibujos ya convertidos, por número
const rowAddr = (y) => ((y & 0xc0) << 5) | ((y & 7) << 8) | ((y & 0x38) << 2);
function daadPixels(d) {
  const l = lib.slice();
  l[255] = { data: [...d, 7] };
  const { mem } = paint(l, 255, { line: 0, height: 12, paper: 7, ink: 0 }, { charset: cs });
  const px = new Uint8Array(256 * 96);
  for (let y = 0; y < 96; y++) for (let x = 0; x < 256; x++) px[y * 256 + x] = (mem[rowAddr(y) + (x >> 3)] >> (7 - (x & 7))) & 1;
  return px;
}
function region(px, x, y) {               // zona sin pintar que tocaría el relleno
  if (px[y * 256 + x]) return [];
  const seen = new Uint8Array(256 * 96), out = [], stack = [y * 256 + x];
  seen[y * 256 + x] = 1;
  while (stack.length) {
    const q = stack.pop(); out.push(q);
    const qx = q & 255, qy = q >> 8;
    for (const [nx, ny] of [[qx - 1, qy], [qx + 1, qy], [qx, qy - 1], [qx, qy + 1]]) {
      if (nx < 0 || nx > 255 || ny < 0 || ny > 95) continue;
      const r = ny * 256 + nx;
      if (!seen[r] && !px[r]) { seen[r] = 1; stack.push(r); }
    }
  }
  return out;
}
let extraFills = 0;

// Números fijos para los dibujos que se usan dentro de otros (GOSUB)
const gosubTargets = new Set(db.pics.flatMap((cmds) => cmds.filter((c) => c[0] === 'GOSUB').map((c) => c[1])));
const fixedNumber = new Map([...gosubTargets].sort((a, b) => a - b).map((k, i) => [k, db.locs.length + i]));

// Estado al terminar cada dibujo (plumas y colores), para los que lo llaman
const endState = new Map(), converted = new Map();
// Recorta un segmento a la zona del dibujo (el remake no pinta fuera; DAAD daría
// el error B de la ROM si una línea se sale de la pantalla): el primer y el
// último punto visibles de la línea tal como la traza el remake
function clip(x0, y0, x1, y1) {
  const dx = Math.abs(x1 - x0), dy = -Math.abs(y1 - y0), sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
  let err = dx + dy, first = null, last = null;
  for (;;) {
    if (inside(x0, y0)) { first ??= [x0, y0]; last = [x0, y0]; }
    if (x0 === x1 && y0 === y1) break;
    const e2 = 2 * err;
    if (e2 >= dy) { err += dy; x0 += sx; }
    if (e2 <= dx) { err += dx; y0 += sy; }
  }
  return first && [...first, ...last];
}
const inside = (x, y) => x >= 0 && x <= 255 && y >= 0 && y <= 95;

function convert(k) {
  if (converted.has(k)) return converted.get(k);
  // st: pluma del remake y colores; dp: pluma de DAAD (difiere si algo se recortó)
  const st = { x: 0, y: 0, ink: 0, paper: 7, bright: 0 };
  const dp = { x: 0, y: 0 };
  const d = [];
  d.push(...enc.ink(st.ink), ...enc.bright(st.bright), ...enc.paper(8));
  const cmds = db.pics[k];
  const plot = (x, y, mode = 0) => { d.push(...enc.plot(x, Y(y), mode)); dp.x = x; dp.y = y; };
  const lineTo = (x, y, mode = 0) => { d.push(...enc.line(x - dp.x, -(y - dp.y), mode)); dp.x = x; dp.y = y; };
  const fills = cmds.some((c) => c[0] === 'FILL' || c[0] === 'SHADE');
  const rule = (mode) => {
    d.push(...enc.ink(8), ...enc.bright(8));
    plot(0, 96, mode); lineTo(255, 96, mode);
    d.push(...enc.ink(st.ink), ...enc.bright(st.bright));
  };
  const fill = (op, x, y, c) => d.push(...(op === 'FILL' ? enc.fill(x - dp.x, -(y - dp.y)) : enc.shade(x - dp.x, -(y - dp.y), shadeChar(c))));
  if (fills) rule(0);
  for (let i = 0; i < cmds.length; i++) {
    const [op, a, b, c, e] = cmds[i];
    switch (op) {
      case 'INK': st.ink = a; d.push(...enc.ink(a)); break;
      case 'PAPER': st.paper = a; break;                    // se usa en BLOCK y CLS
      case 'BRIGHT': st.bright = a; d.push(...enc.bright(a)); break;
      case 'CLS': d.push(...enc.paper(st.paper), ...enc.block(11, 31, 0, 0), ...enc.paper(8)); break;
      case 'BLOCK': d.push(...enc.paper(st.paper), ...enc.block(Math.min(12, b + e) - b - 1, Math.min(32, a + c) - a - 1, a, b), ...enc.paper(8)); break;
      case 'PLOT': if (inside(a, b)) plot(a, b); st.x = a; st.y = b; break;
      case 'MOVE': st.x = a; st.y = b; break;
      case 'UNPLOT': if (inside(a, b)) plot(a, b, 2); st.x = a; st.y = b; break;
      case 'LINE': {
        const s2 = clip(st.x, st.y, a, b);
        if (s2) {
          const [x0, y0, x1, y1] = s2;
          if (x0 !== dp.x || y0 !== dp.y) plot(x0, y0);
          lineTo(x1, y1);
        }
        st.x = a; st.y = b;
        break;
      }
      case 'FILL': case 'SHADE': {
        const zone = region(remakePixels(cmds.slice(0, i)), a, b);
        fill(op, a, b, c);
        if (!zone.length) break;
        const want = remakePixels(cmds.slice(0, i + 1));
        for (let tries = 0; tries < 40; tries++) {
          const got = daadPixels(d);
          const miss = zone.find((q) => want[q] && !got[q]);
          if (miss === undefined) break;
          fill(op, miss & 255, miss >> 8, c);
          extraFills++;
        }
        break;
      }
      case 'GOSUB': {
        d.push(...enc.gosub(fixedNumber.get(a)));
        convert(a);
        const s2 = endState.get(a);
        Object.assign(st, s2.st); Object.assign(dp, s2.dp);
        break;
      }
      default: throw new Error('Orden de dibujo desconocida: ' + op);
    }
  }
  if (fills) rule(2);
  d.push(7);
  endState.set(k, { st: { ...st }, dp: { ...dp } });
  converted.set(k, d);
  if (fixedNumber.has(k)) lib[fixedNumber.get(k)] = { data: d };
  return d;
}
const drawings = db.pics.map((_, k) => convert(k));
p.pictures = db.pics.map((_, k) => ({
  id: (picName[k] || `dibujo${k}`).toLowerCase(),
  drawstring: drawings[k], location: true,
  ...(fixedNumber.has(k) ? { number: fixedNumber.get(k) } : {}),
  line: 0, col: 0, height: 12, width: 42, paper: 7, ink: 0,
}));
db.locs.forEach((l, i) => { if (l.pic >= 0) p.locations[i].picture = p.pictures[l.pic].id; });

p.settings = { ...p.settings, textTop: 12, charset: Buffer.from(cs).toString('base64') };

const { errors, warnings } = compileProject(p);
if (errors.length) { console.error(errors.slice(0, 20)); process.exit(1); }
fs.writeFileSync(out, JSON.stringify(p, null, 1));
console.log(`${out}: ${p.locations.length} localidades, ${p.objects.length} objetos, ${p.vocab.length} palabras, ` +
  `${p.flags.length} banderas, ${p.pictures.length} dibujos (${drawings.reduce((a, x) => a + x.length, 0)} bytes, ${extraFills} rellenos añadidos)` +
  (warnings.length ? `, ${warnings.length} avisos` : ''));
