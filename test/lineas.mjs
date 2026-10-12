// Comprueba con la pantalla real del remake que ninguna línea se va por
// arriba sin que el jugador haya tenido una pausa para leerla.
// Uso: node test/lineas.mjs [test/solucion1.txt]
import fs from 'fs';
import vm from 'vm';
import path from 'path';
import { fileURLToPath } from 'url';
const R = path.dirname(path.dirname(fileURLToPath(import.meta.url))) + '/';
const db = JSON.parse(fs.readFileSync(R + (process.argv[3] || 'build/quijote.json'), 'utf8'));
const font = JSON.parse(fs.readFileSync(R + 'src/font.json', 'utf8'));
const ctx = { window: {}, requestAnimationFrame() {}, document: { addEventListener() {} }, globalThis: null, console };
ctx.globalThis = ctx; vm.createContext(ctx);
vm.runInContext(fs.readFileSync(R + 'src/screen.js', 'utf8'), ctx);
vm.runInContext(fs.readFileSync(R + 'src/engine.js', 'utf8'), ctx);
const S = ctx.window.SpectrumScreen, PAW = ctx.window.PAW || ctx.PAW;
const cmds = (process.argv[2] || R + 'test/solucion1.txt').split(',').map((p) => fs.readFileSync(p, 'utf8')).join('\n').split('\n').map((l) => l.replace(/#.*/, '').trim()).filter(Boolean);
const s = Object.create(S.prototype);
Object.assign(s, { px: new Uint8Array(256 * 192), ink: new Uint8Array(768), paper: new Uint8Array(768), bright: new Uint8Array(768), flash: new Uint8Array(768), db, font, dirty: false });
s.resetText();
// identificador de línea por fila; "visto" al parar
const rowId = new Array(24).fill(0); let next = 1; const seen = new Set(); let bad = 0, pauses = 0;
const put = s.putChar.bind(s);
s.putChar = (ch, row, col, ...r) => { if (ch !== ' ' && !rowId[row]) rowId[row] = next++; return put(ch, row, col, ...r); };
const clr = s.clearRows.bind(s);
s.clearRows = (a, b) => { for (let r = a; r <= b; r++) rowId[r] = 0; return clr(a, b); };
const scr = s.scrollText.bind(s);
s.scrollText = () => { const top = s.top ?? 12; const id = rowId[top]; if (id && !seen.has(id)) bad++; rowId.copyWithin(top, top + 1); rowId[23] = 0; return scr(); };
const look = () => { pauses++; for (const id of rowId) if (id) seen.add(id); };
s.waitKey = async () => { look(); };
s.redrawEcho = () => {}; s.render = () => {};
let k = 0;
s.input = async function () { look(); if (this.col > 0) await this.newline(); this.scrolled = 0; if (k >= cmds.length) throw new Error('fin'); return cmds[k++]; };
s.anykey = async function (p) { if (this.col > 0) await this.newline(); await this.print(p); look(); await this.newline(); this.scrolled = 0; };
s.pause = async () => {}; s.store = () => null; s.border = () => {};
const eng = new PAW.Engine(db, s);
try { await eng.run(); } catch (e) { if (e.message !== 'fin') throw e; }
console.log('órdenes', k, 'pausas', pauses, 'líneas perdidas sin leer', bad);
process.exit(bad ? 1 : 0);
