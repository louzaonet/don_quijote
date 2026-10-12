#!/usr/bin/env python3
"""
de_rocinante.py - Pasa los dibujos vectoriales de un proyecto de Rocinante
(.json) al formato de dibujos del remake (/PIC de los fuentes .paw).

Uso:
  python3 tools/de_rocinante.py proyecto.json                 todos los vectoriales
  python3 tools/de_rocinante.py proyecto.json camino toboso   solo esos
  python3 tools/de_rocinante.py proyecto.json -o otro.paw     a otro fichero

Escribe (o actualiza) src/pics_editados.paw, que build.py compila después de
pics.paw: un dibujo con el mismo nombre que uno de pics.paw lo sustituye, y
uno nuevo se añade. Si el fichero ya existe, solo se cambian los dibujos que
se exportan ahora; los demás se quedan como estaban.

El nombre de cada dibujo en el remake es su identificador en Rocinante en
mayúsculas (camino -> CAMINO).

Cómo se traduce (DAAD -> remake):
  - coordenadas: DAAD va de abajo arriba (y = 175 arriba) y LINE/FILL son
    relativos a la pluma; el remake va de arriba abajo, en absolutas, y solo
    pinta la zona de 256x96 de arriba (filas de texto 0-11)
  - SHADE: la trama es el carácter del juego de caracteres del proyecto (o el
    de DAAD si el proyecto no lleva uno), en 8 bytes
  - GOSUB: por nombre si el subdibujo no tiene escala ni espejo y se coloca
    solo (empieza con un PLOT o un mover absoluto); si no, se copia dentro,
    ya escalado y en su sitio, porque el GOSUB del remake no es relativo
  - TEXT, FLASH y líneas en modo OVER o INVERSE no existen en el remake: se
    quitan y se avisa
Solo usa la biblioteca estándar de Python.
"""
import argparse, base64, json, os, re, sys

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = os.path.join(R, 'src', 'pics_editados.paw')
PIC_H = 96                          # alto de la zona de dibujo del remake


# ------------------------------------------------------------ órdenes de DAAD
def op_len(d, i):
    """Longitud en bytes de la orden que empieza en d[i] (como opLen de Rocinante)"""
    c = d[i]; op = c & 7
    if op == 0: return 3
    if op == 1: return 2 if c & 0x20 else 3
    if op == 2: return 5 if c == 0x12 else (4 if c & 0x20 else 3)
    if op == 3: return 2
    if op == 4: return 4
    return 1


def as_bytes(v):
    """drawstring del proyecto: lista de números o base64"""
    if v is None: return []
    if isinstance(v, str): return list(base64.b64decode(v))
    return list(v)


def number_pictures(p):
    """Número de cada dibujo, igual que numberPictures de Rocinante:
    primero los que tienen número fijo, luego el de su localidad, luego al final"""
    pics = p.get('pictures') or []
    slots, num = {}, {}
    for pic in pics:
        n = pic.get('number')
        if isinstance(n, int) and 0 <= n <= 255:
            slots[n] = pic; num[pic['id']] = n
    locs = p.get('locations') or []
    for i, l in enumerate(locs):
        pic = next((x for x in pics if x['id'] == l.get('picture')), None)
        if not pic or (i in slots and slots[i]['id'] != pic['id']): continue
        slots[i] = pic
        num.setdefault(pic['id'], i)
    for pic in pics:
        if pic['id'] in num: continue
        n = max(max(slots) + 1 if slots else 0, len(locs))
        slots[n] = pic; num[pic['id']] = n
    return slots, num


def positions_itself(d):
    """¿Pone la pluma en un sitio fijo antes de pintar nada que dependa de ella?
    Solo esos se pueden llamar por nombre: el GOSUB del remake usa absolutas"""
    i = 0
    while i < len(d):
        c = d[i]; op = c & 7
        if op == 7: return True
        if op == 0: return True                       # PLOT o mover a un punto fijo
        if op in (1, 3): return False                 # LINE, mover relativo, GOSUB
        if op == 2 and c != 0x12: return False        # FILL, SHADE
        i += op_len(d, i)
    return True


def remake_name(pic_id):
    return re.sub(r'[^A-Z0-9_]', '_', pic_id.upper())


# ------------------------------------------------------------ traducción
class Exporter:
    def __init__(self, project, charset):
        self.p = project
        self.cs = charset
        self.slots, self.num = number_pictures(project)
        self.names = {}
        used = set()
        for pic in project.get('pictures') or []:
            n = remake_name(pic['id'])
            while n in used: n += '_'
            used.add(n); self.names[pic['id']] = n
        # dibujos llamados con GOSUB: no se les pone cabecera (borraría lo de debajo)
        self.targets = set()
        for pic in project.get('pictures') or []:
            d = as_bytes(pic.get('drawstring'))
            i = 0
            while i < len(d) and d[i] & 7 != 7:
                c = d[i]
                if c & 7 == 3 and i + 1 < len(d) and d[i + 1] in self.slots:
                    self.targets.add(self.slots[d[i + 1]]['id'])
                i += op_len(d, i)

    def export(self, pic):
        """Órdenes del remake (lista de cadenas) y avisos para un dibujo"""
        self.out, self.warn = [], set()
        self.outside = 0
        # estado de DAAD: pluma y colores (8 = transparente)
        ink, paper = pic.get('ink', 7), pic.get('paper', 0)
        self.st = {'x': 0, 'y': 0, 'ink': ink, 'paper': paper, 'bright': 0, 'flash': 0}
        self.unknown()
        if (pic.get('line') or 0) != 0 or (pic.get('height') or 12) > 12:
            self.warn.add('la ventana del dibujo no es la de arriba (filas 0-11): '
                          'lo que caiga fuera no se ve en el remake')
        # el remake empieza cada dibujo con tinta 0 y papel 7, borrado; DAAD lo
        # borra con los colores de la ventana del dibujo
        if pic['id'] not in self.targets and (paper, ink) != (7, 0):
            self.emit('INK', ink & 7); self.emit('PAPER', paper & 7); self.emit('BRIGHT', 0); self.emit('CLS')
            self.em.update(ink=ink & 7, paper=paper & 7, bright=0)
        self.run(as_bytes(pic.get('drawstring')), 0, 0, True, 0)
        if self.outside:
            self.warn.add(f'{self.outside} órdenes caen fuera de la zona de 256x96 y no se ven')
        return self.out, sorted(self.warn)

    # --- salida
    def emit(self, *a):
        if self.emitting: self.out.append(' '.join(str(x) for x in a))

    def unknown(self):
        """No se sabe qué colores y pluma tiene el remake (al empezar, tras un GOSUB)"""
        self.em = {'ink': None, 'paper': None, 'bright': None}
        self.pen = None
        self.emitting = True

    def colours(self, with_paper=False):
        """Pone en el remake los colores de DAAD antes de pintar (los transparentes no)"""
        keys = ('ink', 'bright', 'paper') if with_paper else ('ink', 'bright')
        for k in keys:
            v = self.st[k]
            if v == 8 or self.em[k] == v: continue
            self.emit(k.upper(), v & 7); self.em[k] = v
        if not with_paper and self.st['paper'] not in (8, None) and self.st['paper'] != self.window_paper:
            self.warn.add('en DAAD el papel fijo también cambia el papel de cada punto pintado; '
                          'en el remake el papel solo lo cambia BLOCK')

    # --- coordenadas: DAAD (y hacia arriba) -> remake (y hacia abajo)
    @staticmethod
    def ry(y): return 175 - y

    def inside(self, x, y):
        return 0 <= x <= 255 and 0 <= self.ry(y) < PIC_H

    def run(self, d, scale, flip, top, depth):
        """Recorre las órdenes como Painter.run de Rocinante"""
        if depth > 10: return
        if top: self.window_paper = self.st['paper']
        sc = (lambda v: (v * scale) >> 3) if scale else (lambda v: v)
        st = self.st
        i = 0
        while i < len(d):
            c = d[i]; op = c & 7
            if op == 7: break
            n = op_len(d, i)
            fl = c ^ flip
            neg = lambda v, bit: -v if fl & bit else v
            if op == 0:                                   # PLOT / mover
                x, y, mode = d[i + 1], d[i + 2], (c >> 3) & 3
                if mode == 3:
                    st['x'], st['y'] = x, y
                elif self.ry(y) >= PIC_H:
                    st['x'], st['y'] = x, y               # bajo la zona del dibujo: no se ve
                else:
                    if mode == 1: self.warn.add('PLOT en modo OVER: se pinta como un punto normal')
                    self.colours()
                    if not self.inside(x, y): self.outside += 1
                    self.emit('UNPLOT' if mode == 2 else 'PLOT', x, self.ry(y))
                    st['x'], st['y'] = x, y; self.pen = (x, y)
            elif op == 1:                                 # LINE / mover relativo
                if c & 0x20: dx, dy = d[i + 1] >> 4, d[i + 1] & 15
                else: dx, dy = d[i + 1], d[i + 2]
                dx, dy = neg(sc(dx), 0x40), neg(sc(dy), 0x80)
                mode = (c >> 3) & 3
                x0, y0 = st['x'], st['y']
                below = self.ry(y0) >= PIC_H and self.ry(y0 + dy) >= PIC_H
                if mode == 3:
                    st['x'], st['y'] = (x0 + dx) & 255, (y0 + dy) % 176
                elif below:                               # bajo la zona del dibujo: no se ve
                    st['x'], st['y'] = x0 + dx, y0 + dy
                elif mode:
                    self.warn.add('líneas en modo OVER o INVERSE: no existen en el remake y se quitan')
                    st['x'], st['y'] = x0 + dx, y0 + dy
                elif dx or dy:
                    x1, y1 = x0 + dx, y0 + dy
                    if not self.inside(x0, y0) and not self.inside(x1, y1): self.outside += 1
                    self.colours()
                    if self.pen != (x0, y0):
                        # DAAD no pinta el punto de partida de la línea: se empieza en
                        # el primer paso, como DRAW-LINE de la ROM
                        sx, sy = (1 if dx > 0 else -1 if dx < 0 else 0), (1 if dy > 0 else -1 if dy < 0 else 0)
                        big, small = max(abs(dx), abs(dy)), min(abs(dx), abs(dy))
                        diag = (big >> 1) + small >= big
                        fx, fy = (sx, sy) if diag else ((sx, 0) if abs(dx) >= abs(dy) else (0, sy))
                        self.emit('MOVE', x0 + fx, self.ry(y0 + fy))
                    self.emit('LINE', x1, self.ry(y1))
                    self.pen = (x1, y1)
                    st['x'], st['y'] = x1, y1
            elif op == 2:
                if c == 0x12:                             # BLOCK alto-1 ancho-1 col fila
                    h, w, col, row = d[i + 1:i + 5]
                    self.colours(with_paper=True)
                    if row >= 12: self.outside += 1
                    self.emit('BLOCK', col, row, w + 1, h + 1)
                else:                                     # FILL / SHADE
                    x, y = (st['x'] + neg(sc(d[i + 1]), 0x40)) & 255, (st['y'] + neg(sc(d[i + 2]), 0x80)) % 176
                    self.colours()
                    if not self.inside(x, y): self.outside += 1
                    if c & 0x20:
                        ch = d[i + 3]
                        pat = list(self.cs[ch * 8:ch * 8 + 8])
                        if c & 0x10: pat = [255 - v for v in pat]
                        if pat == [255] * 8: self.emit('FILL', x, self.ry(y))
                        else: self.emit('SHADE', x, self.ry(y), ''.join(f'{v:02X}' for v in pat))
                    else:
                        self.emit('FILL', x, self.ry(y))
            elif op == 3:                                 # GOSUB
                sub, s = d[i + 1], (c >> 3) & 7
                f = (c & 0xc0) ^ flip
                pic = self.slots.get(sub)
                data = as_bytes(pic.get('drawstring')) if pic else []
                if not pic or not data:
                    self.warn.add(f'GOSUB {sub}: no hay un dibujo vectorial con ese número; se quita')
                elif s == 0 and f == 0 and positions_itself(data):
                    self.emit('GOSUB', self.names[pic['id']])
                    was = self.emitting
                    self.emitting = False                 # solo para seguir la pluma y los colores
                    self.run(data, 0, 0, False, depth + 1)
                    self.unknown()
                    self.emitting = was
                else:
                    self.run(data, s, f, False, depth + 1)   # copiado, con escala y espejo
            elif op == 4:
                self.warn.add('TEXT dentro del dibujo: el remake no lo tiene y se quita')
            elif op == 5:
                st['bright' if c & 0x80 else 'paper'] = (c >> 3) & 15
            elif op == 6:
                v = (c >> 3) & 15
                if c & 0x80:
                    if v not in (0, 8): self.warn.add('FLASH: el remake no lo tiene y se quita')
                    st['flash'] = v
                else:
                    st['ink'] = v
            i += n


# ------------------------------------------------------------ fichero .paw
def read_pics(path):
    """Dibujos ya escritos en un .paw: {nombre: [líneas]} en orden"""
    out = {}
    if not os.path.exists(path): return out
    cur = None
    for line in open(path, encoding='utf-8'):
        line = line.rstrip('\n')
        if line.startswith('/PIC '):
            cur = line[5:].strip(); out[cur] = []
        elif cur and line.strip() and not line.startswith('#'):
            out[cur].append(line)
    return out


def main():
    ap = argparse.ArgumentParser(description='Dibujos vectoriales de un proyecto de Rocinante al remake (.paw)')
    ap.add_argument('proyecto', help='proyecto de Rocinante (.json)')
    ap.add_argument('dibujos', nargs='*', help='identificadores de los dibujos (por defecto, todos los vectoriales)')
    ap.add_argument('-o', '--salida', default=DEFAULT_OUT, help='fichero .paw (por defecto src/pics_editados.paw)')
    a = ap.parse_args()

    p = json.load(open(a.proyecto, encoding='utf-8'))
    cs = p.get('settings', {}).get('charset')
    charset = base64.b64decode(cs) if cs else base64.b64decode(''.join(DAAD_CHARSET))
    ex = Exporter(p, charset)
    pics = p.get('pictures') or []

    want = {w.lower() for w in a.dibujos}
    chosen = []
    for pic in pics:
        if want and pic['id'].lower() not in want and ex.names[pic['id']].lower() not in want: continue
        if not as_bytes(pic.get('drawstring')):
            if want: print(f'{pic["id"]}: es un dibujo de mapa de bits, no vectorial; no se exporta')
            continue
        chosen.append(pic)
    missing = want - {x['id'].lower() for x in pics} - {ex.names[x['id']].lower() for x in pics}
    for m in sorted(missing): print(f'{m}: no hay ningún dibujo con ese nombre en el proyecto')
    if not chosen:
        print('No hay dibujos vectoriales que exportar.'); return 1

    old = read_pics(a.salida)
    for pic in chosen:
        cmds, warns = ex.export(pic)
        name = ex.names[pic['id']]
        old[name] = cmds
        print(f'{name}: {len(cmds)} órdenes' + ''.join(f'\n  aviso: {w}' for w in warns))

    with open(a.salida, 'w', encoding='utf-8') as f:
        f.write(f'# Dibujos exportados desde Rocinante con tools/de_rocinante.py\n'
                f'# (último: {os.path.basename(a.proyecto)}). Se compilan después de pics.paw:\n'
                f'# un dibujo con el mismo nombre sustituye al de pics.paw.\n\n')
        for name, cmds in old.items():
            f.write(f'/PIC {name}\n' + '\n'.join(cmds) + '\n\n')
    print(f'{os.path.relpath(a.salida)}: {len(old)} dibujos')
    return 0


# Juego de caracteres de DAAD (el que usa Rocinante si el proyecto no lleva uno)
DAAD_CHARSET = (
    'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
    'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
    'AAAAAAAAAAAAAAAAAAAAIFAwAHAAACAAICAgICAAIAAgQIiIcAAAAChQoFAoAAAAoFAoUKAAIEAA'
    'aJiYaAAQIHCI+IB4ABAgAGAgIHAAECAAcIiIcAAQIACIiIhwAChQALDIiIgAKFCIyKiYiAAAcIiA'
    'iHAgQHCIgICIcCBAAFAAiIiIcABQAIiIiIhwAAAAAAAAAAAAICAgICAAIABQUAAAAAAAAFD4UFBQ'
    '+FAAIPig+Cj4IADIyBAgQJiYACBQIGCYkGgAIEAAAAAAAAAIEBAQEBAIAEAgICAgIEAAqKhw+HCo'
    'qAAAICD4ICAAAAAAAAAAEBAgAAAAeAAAAAAAAAAAADAwAAgIECBAgIAAcJiYqMjIcAAgYCAgICBw'
    'AHCICHCAgPgAcIgIMAiIcAAQMFCQ+BAQAPiAgPAIiHAAcIiA8IiIcAD4CAgQECAgAHCIiHCIiHAA'
    'cIiIeAiIcAAAACAAACAAAAAAIAAAICBAAAgQICAQCAAAAAB4AHgAAABAIBAQIEAAcIiIECAAIAAA'
    'cIiouIBwAHCIiPiIiIgA8IiI8IiI8ABwiICAgIhwAPCIiIiIiPAA+ICA8ICA+AD4gIDwgICAAHCI'
    'gICYiHAAiIiI+IiIiABwICAgICBwAAgICAgIiHAAiJCgwKCQiACAgICAgID4AIjYqIiIiIgAiIjI'
    'qJiIiABwiIiIiIhwAPCIiPCAgIAAcIiIiKiYeADwiIjwkIiIAHCIgHAIiHAA+CAgICAgIACIiIiI'
    'iIhwAIiIiIiIUCAAiIiIiKioUACIiFAgUIiIAIiIUCAgICAA+AgQIECA+AA4ICAgICA4AICAQCAQ'
    'CAgAcBAQEBAQcAAgcKggICAgAAAAAAAAAAAAMEhA8EBA+AAAAGiYiJhoAICAsMiIyLAAAABwiICI'
    'cAAICGiYiJhoAAAAcIjwgHgAMEhAYEBAQAAAAHCIiHgIcICAsMiIiIgAIABgICAgcAAQABAQEJBg'
    'AICAgKDAoJAAQEBAQEBAMAAAANCoqKioAAAAsMiIiIgAAABwiIiIcAAAALDIiPCAgAAAaJiIeAgM'
    'AACwQEBAQAAAAHCAcAjwAABA4EBAQDAAAACIiIiIcAAAAIiIUFAgAAAAiKioqFAAAACIUCBQiAAA'
    'AIiImGgIcAAA+BAgQPgAGCAgQCAgGAAQEBAQEBAQAGAQEAgQEGAAAChQAAAAAAAAAAAAAAAAAMSq'
    'rsomVXVWAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
    'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
    'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
    'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
    'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
    'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
    'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
    'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
    'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
    'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
    'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
    'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
    'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
    'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
    'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
    'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
    'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
    'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA='
)


if __name__ == '__main__':
    sys.exit(main())
