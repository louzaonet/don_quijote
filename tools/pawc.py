#!/usr/bin/env python3
"""
pawc.py - Compilador del fuente tipo PAW (*.paw) a la base de datos JSON del motor.

Uso: pawc.py salida.json fuente1.paw [fuente2.paw ...]
     pawc.py --lang en --tr src/en salida.json fuentes...   versión en otro idioma
     pawc.py --dump textos.txt salida.json fuentes...       vuelca los textos a traducir

Idiomas: los fuentes se escriben en español y la lógica es la misma en todos
los idiomas. Una traducción es un directorio con ficheros .paw que solo llevan
textos:
  /VOC                 líneas "V COGER: GET TAKE" (tipo, palabra española que
                       da nombre al grupo, y las palabras del otro idioma)
  /SYS n, /MSG nombre, /LOC nombre, /OBJ nombre   el texto traducido
  /STR clave           el texto de un MESSAGE "..." de los procesos; la clave
                       son 8 cifras del SHA-1 del texto español entre comillas
                       ("/STR clave raw" y el texto entre comillas: respeta
                       los espacios del principio y del final)
Lo que falte se queda en español y se lista en build/faltan_<idioma>.txt.

El fuente usa nombres simbólicos para localidades, objetos, flags y mensajes;
el compilador asigna los números (respetando las reglas de PAW: contenedores
con el mismo número que su localidad interna, palabras de movimiento < 20...)
para que la conversión posterior a una base de datos PAW real sea directa.

Secciones:
  /CONFIG                     clave = valor
  /VOC                        DIR n pal...  |  V|N|A|P|ADV|CONJ|PRON pal...
  /FLAGS                      nombres (se asignan desde el 64) o nombre = n
  /SYS n                      mensaje de sistema
  /MSG nombre                 mensaje
  /LOC nombre [pic=NOMBRE]    texto de la localidad; líneas "=> DIR:dest ..." = conexiones
  /OBJ nombre @loc [noun=X] [adj=Y] [w=n] [wear] [cont]   descripción en la línea siguiente
  /PRO n                      entradas "> VERBO NOMBRE" seguidas de condactos
  /PIC nombre                 órdenes gráficas
"""
import json, re, sys, math, unicodedata, hashlib, os, glob

NONE = 255
SPECIAL_LOCS = {'CARRIED': 254, 'WORN': 253, 'NOTCREATED': 252, 'HERE': 255}
SYS_FLAGS = {'carried': 1, 'score': 30, 'turns_lo': 31, 'turns_hi': 32, 'verb': 33, 'noun1': 34,
             'adj1': 35, 'adverb': 36, 'maxobj': 37, 'loc': 38, 'prep': 43, 'noun2': 44,
             'adj2': 45, 'objref': 51, 'maxweight': 52}
TYPES = {'V': 0, 'ADV': 1, 'N': 2, 'A': 3, 'P': 4, 'CONJ': 5, 'PRON': 6}

# Firma de cada condacto: L=localidad O=objeto F=flag N=número M=mensaje
# X=localidad/contenedor/especial  WN/WA/WP/WV=palabra (nombre/adjetivo/prep/adverbio)  P=proceso  I=imagen
SIG = {
    'AT': 'L', 'NOTAT': 'L', 'ATGT': 'L', 'ATLT': 'L', 'PRESENT': 'O', 'ABSENT': 'O', 'WORN': 'O',
    'NOTWORN': 'O', 'CARRIED': 'O', 'NOTCARR': 'O', 'CHANCE': 'N', 'ZERO': 'F', 'NOTZERO': 'F',
    'EQ': 'FN', 'NOTEQ': 'FN', 'GT': 'FN', 'LT': 'FN', 'SAME': 'FF', 'NOTSAME': 'FF',
    'ADJECT1': 'A', 'ADJECT2': 'A', 'ADVERB': 'D', 'PREP': 'R', 'NOUN2': 'W', 'ISAT': 'OX',
    'ISNOTAT': 'OX', 'INVEN': '', 'DESC': '', 'QUIT': '', 'END': '', 'DONE': '', 'NOTDONE': '',
    'OK': '', 'ANYKEY': '', 'SAVE': '', 'LOAD': '', 'RAMSAVE': '', 'RAMLOAD': '', 'TURNS': '',
    'SCORE': '', 'CLS': '', 'DROPALL': '', 'AUTOG': '', 'AUTOD': '', 'AUTOW': '', 'AUTOR': '',
    'AUTOP': 'O', 'AUTOT': 'O', 'GET': 'O', 'DROP': 'O', 'WEAR': 'O', 'REMOVE': 'O', 'PUTIN': 'OO',
    'TAKEOUT': 'OO', 'DESTROY': 'O', 'CREATE': 'O', 'SWAP': 'OO', 'PLACE': 'OX', 'PAUSE': 'N',
    'GOTO': 'L', 'MESSAGE': 'M', 'MES': 'M', 'SYSMESS': 'N', 'NEWLINE': '', 'PRINT': 'F',
    'SET': 'F', 'CLEAR': 'F', 'LET': 'FN', 'PLUS': 'FN', 'MINUS': 'FN', 'ADD': 'FF', 'SUB': 'FF',
    'COPYFF': 'FF', 'COPYOF': 'OF', 'COPYFO': 'FO', 'LISTOBJ': '', 'LISTAT': 'X', 'PROCESS': 'P',
    'PARSE': '', 'PICTURE': 'I', 'BORDER': 'N', 'BEEP': 'NN', 'DOALL': 'X', 'MOVE': 'F',
}
# Órdenes gráficas primitivas (las que se portarán a PAW) y sus argumentos
# SHADE x y trama: la trama es un byte (2 cifras hex, se gira un bit por fila)
# o un carácter de 8 bytes (16 cifras hex, una fila por byte, como en DAAD).
# MOVE x y mueve la pluma sin pintar.
PIC_PRIM = {'INK': 1, 'PAPER': 1, 'BRIGHT': 1, 'CLS': 0, 'PLOT': 2, 'LINE': 2, 'DRAW': 2,
            'FILL': 2, 'SHADE': 3, 'BLOCK': 4, 'GOSUB': 1, 'UNPLOT': 2, 'MOVE': 2}


def norm_word(w):
    """Palabra de vocabulario: mayúsculas, sin acentos (salvo Ñ), 5 letras"""
    w = w.upper().replace('Ñ', '\0')
    w = ''.join(c for c in unicodedata.normalize('NFD', w) if unicodedata.category(c) != 'Mn')
    return w.replace('\0', 'Ñ')[:5]


CODES = {'i': '\x10', 'p': '\x11', 'f': '\x12', 'b': '\x13'}


def enc_text(lines):
    """Une líneas de texto: salto de línea simple = espacio, línea vacía = salto real.
    {i3} ink 3, {p0} paper 0, {b1} brillo, {n} salto de línea forzado."""
    paras, cur = [], []
    for l in lines:
        if l.strip() == '':
            paras.append(' '.join(cur)); cur = []
        else:
            cur.append(l.strip())
    if cur:
        paras.append(' '.join(cur))
    while paras and paras[-1] == '':
        paras.pop()
    s = '\n'.join(paras).replace('{n} ', '{n}')
    s = re.sub(r'\{([ipfb])(\d)\}', lambda m: CODES[m.group(1)] + m.group(2), s)
    return s.replace('{n}', '\n')


def str_key(raw):
    """Clave de una cadena de los procesos: 8 cifras del SHA-1 del texto entre comillas"""
    return hashlib.sha1(raw.encode('utf-8')).hexdigest()[:8]


class Compiler:
    def __init__(self, lang=None):
        self.lang = lang                       # None = español (los fuentes)
        self.tr = {k: {} for k in ('MSG', 'LOC', 'OBJ', 'SYS', 'STR')}
        self.voc_tr = []                       # (tipo, palabra española, [palabras], dónde)
        self.canon = {}                        # (tipo, palabra5) -> número de grupo
        self.units = []                        # textos traducibles: (tipo, clave, líneas, fichero)
        self.missing = set()
        self.used = set()
        self.src = ""
        self.config = {'start': 'intro', 'maxobj': 4, 'maxweight': 10}
        self.vocab = []            # (palabra5, num, tipo)
        self.words = {}            # (palabra5, tipo) -> num
        self.next_num = {t: 20 for t in TYPES.values()}
        self.flags = dict(SYS_FLAGS)
        self.next_flag = 64
        self.sys = {}
        self.msgs, self.msg_index = [], {}
        self.locs = []             # dict(name, pic, text, conns)
        self.objs = []             # dict(name, loc, noun, adj, w, wear, cont, text)
        self.procs = {}            # n -> lista de (verbo, nombre, [condactos crudos], línea)
        self.pics = {}             # nombre -> lista de órdenes crudas
        self.errors = []

    # ------------------------------------------------------------ lectura
    def load(self, path):
        self.src = path
        sect, buf, head = None, [], None
        for ln, raw in enumerate(open(path, encoding='utf-8'), 1):
            line = raw.rstrip('\n')
            if line.startswith('#'):
                continue
            if line.startswith('/'):
                if sect:
                    self.section(sect, head, buf, path)
                parts = line[1:].split(None, 1)
                sect, head, buf = parts[0].upper(), (parts[1] if len(parts) > 1 else ''), []
                continue
            buf.append((ln, line))
        if sect:
            self.section(sect, head, buf, path)

    def section(self, sect, head, buf, path):
        lines = [l for _, l in buf]
        if sect == 'CONFIG':
            for l in lines:
                if '=' in l:
                    k, v = [x.strip() for x in l.split('=', 1)]
                    self.config[k] = int(v) if v.isdigit() else v
        elif sect == 'VOC':
            for l in lines:
                t = l.split('#')[0].split()
                if not t:
                    continue
                if t[0] == 'DIR':
                    num, words, typ = int(t[1]), t[2:], 2
                else:
                    typ, words, num = TYPES[t[0]], t[1:], None
                    num = self.next_num[typ]; self.next_num[typ] += 1
                self.canon.setdefault((typ, norm_word(words[0])), num)
                self.units.append(('VOC', f"{t[0] if t[0] != 'DIR' else 'DIR'} {words[0]}", [' '.join(words)], self.src))
                for w in words:
                    w5 = norm_word(w)
                    if (w5, typ) in self.words and self.words[(w5, typ)] != num:
                        self.errors.append(f'Palabra duplicada {w} ({w5}) tipo {typ}')
                    self.words[(w5, typ)] = num
                    self.vocab.append((w5, num, typ))
        elif sect == 'FLAGS':
            for l in lines:
                for tok in l.split('#')[0].split():
                    if '=' in tok:
                        k, v = tok.split('='); self.flags[k] = int(v)
                    else:
                        self.flags[tok] = self.next_flag; self.next_flag += 1
        elif sect == 'SYS':
            raw = '\n'.join(lines).strip()
            if raw.startswith('"') and raw.endswith('"'):
                txt = raw[1:-1].replace('\\n', '\n')
                txt = re.sub(r'\{([ipfb])(\d)\}', lambda m: CODES[m.group(1)] + m.group(2), txt)
            else:
                txt = enc_text(lines).replace('\\n', '\n')
            self.units.append(('SYS', head.strip(), lines, self.src))
            self.sys[int(head)] = self.translated('SYS', head.strip(), txt)
        elif sect == 'MSG':
            self.units.append(('MSG', head.strip(), lines, self.src))
            self.add_msg(self.translated('MSG', head.strip(), enc_text(lines)), head.strip())
        elif sect == 'LOC':
            parts = head.split()
            name, opts = parts[0], dict(p.split('=') for p in parts[1:])
            text = [l for l in lines if not l.startswith('=>')]
            conns = []
            for l in lines:
                if l.startswith('=>'):
                    for c in l[2:].split():
                        d, dest = c.split(':')
                        conns.append((d, dest))
            if any(l.strip() for l in text): self.units.append(('LOC', name, text, self.src))
            txt = enc_text(text)
            self.locs.append(dict(name=name, pic=opts.get('pic'), text=self.translated('LOC', name, txt) if txt else txt, conns=conns))
        elif sect == 'OBJ':
            parts = head.split()
            self.units.append(('OBJ', parts[0], lines, self.src))
            d = dict(name=parts[0], loc=parts[1].lstrip('@'), noun=None, adj=None, w=1,
                     wear=False, cont=False, text=self.translated('OBJ', parts[0], enc_text(lines)))
            for p in parts[2:]:
                if p == 'wear': d['wear'] = True
                elif p == 'cont': d['cont'] = True
                else:
                    k, v = p.split('='); d[k] = int(v) if k == 'w' else v
            self.objs.append(d)
        elif sect == 'PRO':
            n = int(head)
            entries = self.procs.setdefault(n, [])
            cur = None
            for ln, l in buf:
                s = l.strip()
                if not s or s.startswith('#'):
                    continue
                if s.startswith('>'):
                    t = s[1:].split()
                    cur = [t[0], t[1] if len(t) > 1 else '_', [], f'{path}:{ln}', path]
                    entries.append(cur)
                else:
                    cur[2].extend(split_condacts(s))
        elif sect == 'PIC':
            self.pics[head.strip()] = [l.split('#')[0].split() for l in lines if l.split('#')[0].strip()]

    def translated(self, kind, key, text):
        """El texto en el idioma de la compilación (o el español si falta)"""
        if not self.lang: return text
        if key in self.tr[kind]:
            self.used.add((kind, key)); return self.tr[kind][key]
        self.missing.add((kind, key))
        return text

    def load_tr(self, path):
        """Fichero de traducción: solo textos y vocabulario"""
        sect, head, buf = None, None, []

        def flush():
            if not sect: return
            if sect == 'VOC':
                for l in buf:
                    l = l.split('#')[0].strip()
                    if not l: continue
                    left, _, right = l.partition(':')
                    typ, canon = left.split()
                    self.voc_tr.append((typ, canon, right.split(), path))
            elif sect == 'SYS':
                raw = '\n'.join(buf).strip()
                if raw.startswith('"') and raw.endswith('"'):
                    txt = raw[1:-1].replace('\\n', '\n')
                    txt = re.sub(r'\{([ipfb])(\d)\}', lambda m: CODES[m.group(1)] + m.group(2), txt)
                else:
                    txt = enc_text(buf).replace('\\n', '\n')
                self.tr['SYS'][head] = txt
            elif sect in self.tr:
                key, *flags = head.split()
                if key in self.tr[sect]:
                    self.errors.append(f'{path}: /{sect} {key} está dos veces')
                if 'raw' in flags:
                    # "/STR clave raw": el texto va entre comillas y se respetan sus espacios
                    raw = '\n'.join(buf).strip()[1:-1].replace('\\n', '\n')
                    raw = re.sub(r'\{([ipfb])(\d)\}', lambda m: CODES[m.group(1)] + m.group(2), raw)
                    self.tr[sect][key] = raw.replace('{n}', '\n')
                else:
                    self.tr[sect][key] = enc_text(buf)
        for raw in open(path, encoding='utf-8'):
            line = raw.rstrip('\n')
            if line.startswith('#'): continue
            if line.startswith('/'):
                flush()
                parts = line[1:].split(None, 1)
                sect, head, buf = parts[0].upper(), (parts[1].strip() if len(parts) > 1 else ''), []
                continue
            buf.append(line)
        flush()

    def lang_vocab(self):
        """Vocabulario del otro idioma, colgado de los mismos grupos"""
        out, seen = [], {}
        tmap = dict(TYPES, DIR=2)
        for typ, canon, words, where in self.voc_tr:
            t = tmap[typ]
            num = self.canon.get((t, norm_word(canon)))
            if num is None:
                self.errors.append(f'{where}: no hay grupo {typ} {canon}'); continue
            self.used.add(('VOC', f'{typ} {canon}'))
            for w in words:
                w5 = norm_word(w)
                if seen.get((w5, t), num) != num:
                    self.errors.append(f'{where}: la palabra {w} ({w5}) ya es de otro grupo')
                seen[(w5, t)] = num
                out.append((w5, num, t))
        for u in self.units:
            if u[0] == 'VOC' and ('VOC', u[1]) not in self.used: self.missing.add(('VOC', u[1]))
        return out

    def dump(self, path, only=None):
        """Vuelca los textos (todos, o los que faltan) en formato de traducción"""
        with open(path, 'w', encoding='utf-8') as f:
            last = None
            order = {}
            for u in self.units: order.setdefault(u[3], len(order))
            for kind, key, lines, src in sorted(self.units, key=lambda u: order[u[3]]):
                if only is not None and (kind, key) not in only: continue
                if src != last:
                    f.write(f'\n# ===== {os.path.basename(src)}\n'); last = src
                if kind == 'VOC':
                    f.write(f'/VOC\n{key}: # {lines[0]}\n')
                else:
                    f.write(f'/{kind} {key}\n' + '\n'.join(lines).strip('\n') + '\n\n')

    def add_msg(self, text, name=None):
        if name and name in self.msg_index:
            self.errors.append(f'Mensaje duplicado {name}')
        self.msgs.append(text)
        idx = len(self.msgs) - 1
        if name:
            self.msg_index[name] = idx
        return idx

    # ------------------------------------------------------------ resolución
    def build(self):
        # Objetos: número = orden. Las localidades se saltan los números de contenedores.
        self.obj_index = {o['name']: i for i, o in enumerate(self.objs)}
        cont_nums = {i for i, o in enumerate(self.objs) if o['cont']}
        self.loc_index, n = {}, 0
        start = self.config['start']
        # la localidad inicial va la primera (número 0)
        order = sorted(self.locs, key=lambda l: l['name'] != start)
        for l in order:
            while n in cont_nums:
                n += 1
            self.loc_index[l['name']] = n
            n += 1
        nlocs = n
        locs = [dict(text='', pic=-1) for _ in range(nlocs)]
        conns = [[] for _ in range(nlocs)]
        self.pic_index = {name: i for i, name in enumerate(self.pics)}
        for l in self.locs:
            i = self.loc_index[l['name']]
            if l['pic'] and l['pic'] not in self.pic_index:
                self.errors.append(f"Imagen {l['pic']} no existe ({l['name']})")
            locs[i] = dict(text=l['text'], pic=self.pic_index.get(l['pic'], -1) if l['pic'] else -1)
            for d, dest in l['conns']:
                conns[i].append([self.dirnum(d), self.loc(dest)])
        objs = []
        for o in self.objs:
            objs.append(dict(text=o['text'], loc=self.xloc(o['loc']),
                             noun=self.word(o['noun'], 2) if o['noun'] else NONE,
                             adj=self.word(o['adj'], 3) if o['adj'] else NONE,
                             w=o['w'], wear=o['wear'], cont=o['cont']))
        procs = []
        for pn in range(max(self.procs) + 1 if self.procs else 0):
            table = []
            for v, nn, cds, where, src in self.procs.get(pn, []):
                self.src = src
                try:
                    table.append(dict(v=self.headword(v, True), n=self.headword(nn, False),
                                      c=[self.condact(c) for c in cds]))
                except Exception as e:
                    self.errors.append(f'{where}: {e}')
            procs.append(table)
        pics = []
        for name, cmds in self.pics.items():
            try:
                pics.append(self.picture(cmds))
            except Exception as e:
                self.errors.append(f'PIC {name}: {e}')
        sysm = [self.sys.get(i, '') for i in range(max(self.sys) + 1)] if self.sys else []
        vocab = self.lang_vocab() if self.lang else self.vocab
        return dict(config=dict(start=self.loc_index[start], maxobj=self.config['maxobj'], lang=self.lang or 'es',
                                maxweight=self.config['maxweight'],
                                maxscore=self.config.get('maxscore', 100)),
                    vocab=vocab, locs=locs, conns=conns, objs=objs, msgs=self.msgs,
                    sys=sysm, procs=procs, pics=pics,
                    names=dict(locs=self.loc_index, objs=self.obj_index, flags=self.flags,
                               pics=self.pic_index))

    def dirnum(self, d):
        w = norm_word(d)
        if (w, 2) in self.words and self.words[(w, 2)] < 20:
            return self.words[(w, 2)]
        raise ValueError(f'Dirección desconocida {d}')

    def loc(self, name):
        if name not in self.loc_index:
            raise ValueError(f'Localidad desconocida {name}')
        return self.loc_index[name]

    def xloc(self, name):
        if name.upper() in SPECIAL_LOCS:
            return SPECIAL_LOCS[name.upper()]
        if name in self.loc_index:
            return self.loc_index[name]
        if name in self.obj_index and self.objs[self.obj_index[name]]['cont']:
            return self.obj_index[name]
        if name.isdigit():
            return int(name)
        raise ValueError(f'Localidad/contenedor desconocido {name}')

    def word(self, w, typ):
        k = (norm_word(w), typ)
        if k not in self.words:
            raise ValueError(f'Palabra {w} (tipo {typ}) no está en el vocabulario')
        return self.words[k]

    def headword(self, w, is_verb):
        if w in ('_', '*'):
            return NONE
        w5 = norm_word(w)
        if is_verb:
            if (w5, 0) in self.words:
                return self.words[(w5, 0)]
            if (w5, 2) in self.words and self.words[(w5, 2)] < 20:
                return self.words[(w5, 2)]
            raise ValueError(f'Verbo desconocido {w}')
        return self.word(w, 2)

    def flag(self, name):
        if name.isdigit():
            return int(name)
        if name not in self.flags:
            raise ValueError(f'Flag no declarado {name}')
        return self.flags[name]

    def condact(self, c):
        op, args = c[0].upper(), c[1:]
        if op not in SIG:
            raise ValueError(f'Condacto desconocido {op}')
        sig = SIG[op]
        if len(args) != len(sig):
            raise ValueError(f'{op} espera {len(sig)} argumentos, recibe {args}')
        out = [op]
        for t, a in zip(sig, args):
            if t == 'L': out.append(self.loc(a))
            elif t == 'O':
                if a not in self.obj_index: raise ValueError(f'Objeto desconocido {a}')
                out.append(self.obj_index[a])
            elif t == 'F': out.append(self.flag(a))
            elif t == 'N':
                # número literal, o nombre de localidad/objeto (p.ej. LET rocinante_loc corral)
                if a.lstrip('-').isdigit(): out.append(int(a))
                elif a in self.loc_index: out.append(self.loc_index[a])
                elif a in self.obj_index: out.append(self.obj_index[a])
                else: raise ValueError(f'Valor desconocido {a}')
            elif t == 'X': out.append(self.xloc(a))
            elif t == 'W': out.append(self.word(a, 2))
            elif t == 'A': out.append(self.word(a, 3))
            elif t == 'R': out.append(self.word(a, 4))
            elif t == 'D': out.append(self.word(a, 1))
            elif t == 'P': out.append(int(a))
            elif t == 'I':
                if a not in self.pic_index: raise ValueError(f'Imagen desconocida {a}')
                out.append(self.pic_index[a])
            elif t == 'M':
                if a.startswith('"'):
                    key = str_key(a[1:-1])
                    if not any(u[0] == 'STR' and u[1] == key for u in self.units):
                        self.units.append(('STR', key, [a[1:-1]], self.src))
                    if self.lang and key in self.tr['STR']:
                        self.used.add(('STR', key))
                        out.append(self.add_msg(self.tr['STR'][key])); continue
                    if self.lang: self.missing.add(('STR', key))
                    raw = a[1:-1].replace('\\n', '\n').replace('\\"', '"')
                    raw = re.sub(r'\{([ipfb])(\d)\}', lambda m: CODES[m.group(1)] + m.group(2), raw).replace('{n}', '\n')
                    out.append(self.add_msg(raw))
                else:
                    if a not in self.msg_index: raise ValueError(f'Mensaje desconocido {a}')
                    out.append(self.msg_index[a])
        return out

    def picture(self, cmds):
        """Expande las órdenes de ayuda (RECT, POLY, CIRCLE...) a primitivas"""
        out = []
        for c in cmds:
            op, a = c[0].upper(), c[1:]
            if op in PIC_PRIM:
                if op == 'GOSUB':
                    out.append([op, self.pic_index[a[0]]])
                elif op == 'SHADE':
                    pat = (int(a[2], 16) if len(a[2]) <= 2 else
                           [int(a[2][k:k + 2], 16) for k in range(0, 16, 2)])
                    if isinstance(pat, list) and len(a[2]) != 16:
                        raise ValueError(f'Trama de SHADE con {len(a[2])} cifras (2 o 16)')
                    out.append([op, int(a[0]), int(a[1]), pat])
                else:
                    out.append([op] + [int(x) for x in a])
            elif op == 'RECT':
                x, y, w, h = map(int, a)
                out += [['PLOT', x, y], ['LINE', x + w - 1, y], ['LINE', x + w - 1, y + h - 1],
                        ['LINE', x, y + h - 1], ['LINE', x, y]]
            elif op == 'POLY':     # POLY x y x y ... (abierta)
                pts = list(map(int, a))
                out.append(['PLOT', pts[0], pts[1]])
                for i in range(2, len(pts), 2):
                    out.append(['LINE', pts[i], pts[i + 1]])
            elif op == 'CIRCLE':   # CIRCLE cx cy r [segmentos]
                cx, cy, r = map(int, a[:3]); seg = int(a[3]) if len(a) > 3 else 16
                pts = [(round(cx + r * math.cos(2 * math.pi * k / seg)),
                        round(cy + r * math.sin(2 * math.pi * k / seg))) for k in range(seg + 1)]
                out.append(['PLOT', *pts[0]])
                out += [['LINE', *p] for p in pts[1:]]
            elif op == 'ELLIPSE':  # ELLIPSE cx cy rx ry [segmentos]
                cx, cy, rx, ry = map(int, a[:4]); seg = int(a[4]) if len(a) > 4 else 16
                pts = [(round(cx + rx * math.cos(2 * math.pi * k / seg)),
                        round(cy + ry * math.sin(2 * math.pi * k / seg))) for k in range(seg + 1)]
                out.append(['PLOT', *pts[0]])
                out += [['LINE', *p] for p in pts[1:]]
            else:
                raise ValueError(f'Orden gráfica desconocida {op}')
        return out


def split_condacts(s):
    """Separa 'AT sala; MESSAGE "hola; adiós"; DONE' respetando comillas"""
    res, cur, inq = [], '', False
    for ch in s:
        if ch == '"':
            inq = not inq
        if ch == ';' and not inq:
            if cur.strip(): res.append(tokenize(cur))
            cur = ''
        else:
            cur += ch
    if cur.strip():
        res.append(tokenize(cur))
    return res


def tokenize(s):
    s = s.strip()
    m = re.match(r'(\w+)\s+(".*")\s*$', s)
    if m:
        return [m.group(1), m.group(2)]
    return s.split()


def main():
    args = sys.argv[1:]
    lang = tr = dump = None
    while args and args[0].startswith('--'):
        opt = args.pop(0)
        if opt == '--lang': lang = args.pop(0)
        elif opt == '--tr': tr = args.pop(0)
        elif opt == '--dump': dump = args.pop(0)
    out, srcs = args[0], args[1:]
    c = Compiler(lang)
    if lang:
        for f in sorted(glob.glob(os.path.join(tr, '*.paw'))):
            c.load_tr(f)
    for s in srcs:
        c.load(s)
    db = c.build()
    if c.errors:
        print('\n'.join('ERROR: ' + e for e in c.errors))
        sys.exit(1)
    if dump:
        c.dump(dump)
    json.dump(db, open(out, 'w', encoding='utf-8'), ensure_ascii=False)
    print(f"OK{' (' + lang + ')' if lang else ''}: {len(db['locs'])} localidades, {len(db['objs'])} objetos, {len(db['msgs'])} mensajes, "
          f"{len(db['vocab'])} palabras, {sum(len(p) for p in db['procs'])} entradas, {len(db['pics'])} imágenes, "
          f"{len([f for f in c.flags if c.flags[f] >= 64])} flags")
    if lang:
        rep = os.path.join(os.path.dirname(os.path.abspath(out)), f'faltan_{lang}.txt')
        c.dump(rep, only=c.missing)
        unused = [f'{k} {n}' for k in c.tr for n in c.tr[k] if (k, n) not in c.used]
        print(f'{lang}: faltan {len(c.missing)} textos por traducir'
              + (f' (lista en {os.path.relpath(rep)})' if c.missing else '')
              + (f'; {len(unused)} traducciones que ya no se usan: {", ".join(unused[:8])}' if unused else ''))


if __name__ == '__main__':
    main()
