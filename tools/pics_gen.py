#!/usr/bin/env python3
"""
Genera src/pics.paw: gráficos vectoriales al estilo PAW.
Zona gráfica: 256x96 píxeles (32x12 celdas de atributos). Origen arriba a la izquierda.
Solo se emiten órdenes portables: INK PAPER BRIGHT CLS PLOT LINE FILL SHADE BLOCK GOSUB
(más RECT/POLY/CIRCLE/ELLIPSE, que el compilador expande a PLOT+LINE).
Colores Spectrum: 0 negro 1 azul 2 rojo 3 magenta 4 verde 5 cian 6 amarillo 7 blanco
"""
import random, math, os

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pics = {}


class P:
    def __init__(self, name):
        self.name, self.c = name, []
        pics[name] = self

    def __call__(self, *a):
        self.c.append(' '.join(str(x) for x in a)); return self

    # atributos de un rectángulo de celdas
    def block(self, col, row, w, h, ink, paper, bright=0):
        self('INK', ink); self('PAPER', paper); self('BRIGHT', bright); self('BLOCK', col, row, w, h)

    def ink(self, i, b=None):
        self('INK', i)
        if b is not None: self('BRIGHT', b)

    def line(self, x0, y0, x1, y1):
        self('PLOT', x0, y0); self('LINE', x1, y1)

    def poly(self, *pts, close=False):
        pts = list(pts)
        if close: pts += pts[:2]
        self('POLY', *pts)

    def rect(self, x, y, w, h): self('RECT', x, y, w, h)
    def fill(self, x, y): self('FILL', x, y)
    def shade(self, x, y, pat): self('SHADE', x, y, f'{pat:02X}')
    def circle(self, cx, cy, r, seg=16): self('CIRCLE', cx, cy, r, seg)
    def ellipse(self, cx, cy, rx, ry, seg=16): self('ELLIPSE', cx, cy, rx, ry, seg)
    def gosub(self, n): self('GOSUB', n)

    def bar(self, x0, y0, x1, y1):
        """rectángulo relleno a base de líneas horizontales (útil para lomos de libros)"""
        for y in range(y0, y1 + 1): self.line(x0, y, x1, y)

    def encina(self, x, y, r):
        """encina: tronco y copa redondeada rellena"""
        self.circle(x, y, r, 14); self.fill(x, y)
        self.circle(x, y - r + 2, r // 2, 10); self.fill(x, y - r - 1)
        self.line(x, y + r, x, y + r + 8); self.line(x + 1, y + r, x + 1, y + r + 8)


# ---------------------------------------------------------------- CAMINO
# Llanura manchega: cielo cian, tierra amarilla, camino que se pierde en el horizonte.
p = P('CAMINO')
p('INK 0'); p('PAPER 7'); p('BRIGHT 0'); p('CLS')
p.block(0, 0, 32, 5, 7, 5, 1)          # cielo
p.block(0, 5, 32, 7, 2, 6, 0)          # tierra
# nubes (blanco sobre cian)
p.ink(7, 1)
p.ellipse(52, 12, 14, 4); p.fill(52, 12); p.ellipse(66, 10, 9, 4); p.fill(66, 10)
p.ellipse(150, 20, 12, 3); p.fill(150, 20)
# sol
p.ink(6, 1); p.circle(222, 16, 7, 14); p.fill(222, 16)
# lomas lejanas (verde) en la última fila de cielo
p.ink(4, 1)
p.poly(0, 39, 18, 35, 40, 37, 66, 33, 90, 36, 112, 34, 128, 37, 150, 33, 178, 36, 204, 32, 232, 35, 255, 34, 255, 39, 0, 39)
p.fill(30, 37); p.fill(200, 36)
# horizonte y camino (rojo tierra sobre amarillo)
p.ink(2, 0)
p.line(0, 40, 255, 40)
p.line(124, 41, 52, 95); p.line(132, 41, 204, 95)
p.shade(128, 80, 0x22)
# matas y piedras
for x, y in [(20, 60), (36, 78), (90, 52), (210, 58), (230, 82), (186, 50), (12, 90), (244, 66)]:
    p.line(x - 3, y, x + 3, y); p.line(x - 2, y - 1, x + 2, y - 1)
for x, y in [(70, 47), (176, 46), (100, 46), (156, 48)]:
    p('PLOT', x, y)

# ---------------------------------------------------------------- NOCHE
p = P('NOCHE')
p.gosub('CAMINO')
p.block(0, 0, 32, 4, 7, 1, 0)          # cielo nocturno: el sol pasa a ser luna
p.block(0, 4, 32, 1, 0, 1, 0)          # lomas en silueta
p.block(0, 5, 32, 7, 1, 0, 0)          # tierra oscura
p.ink(7, 1)
for x, y in [(12, 6), (30, 20), (84, 4), (100, 24), (120, 10), (176, 6), (190, 26), (248, 22), (140, 30), (64, 28)]:
    p('PLOT', x, y)

# ---------------------------------------------------------------- BOSQUE
p = P('BOSQUE')
p.gosub('CAMINO')
p.ink(4, 0)
p.encina(22, 62, 14); p.encina(70, 54, 9); p.encina(192, 57, 11); p.encina(234, 66, 16)

p = P('BOSQUE_NOCHE')
p.gosub('BOSQUE')
p.block(0, 0, 32, 4, 7, 1, 0)
p.block(0, 4, 32, 1, 0, 1, 0)
p.block(0, 5, 32, 7, 1, 0, 0)

# ---------------------------------------------------------------- SIERRA
p = P('SIERRA')
p('INK 0'); p('PAPER 7'); p('BRIGHT 0'); p('CLS')
p.block(0, 0, 32, 12, 7, 5, 1)
p.block(0, 8, 32, 4, 2, 6, 0)
p.ink(2, 1)
# cordillera de fondo
p.poly(0, 60, 20, 38, 34, 46, 58, 18, 76, 34, 96, 22, 120, 44, 140, 26, 160, 14, 182, 36, 204, 24, 228, 40, 255, 30, 255, 63, 0, 63, close=False)
p.line(0, 60, 0, 63)
p.shade(150, 40, 0x55)
# riscos en primer plano
p.ink(0, 0)
p.poly(0, 95, 10, 72, 26, 66, 40, 80, 52, 74, 64, 95)
p.shade(30, 85, 0x55)
p.poly(176, 95, 190, 70, 204, 62, 222, 74, 240, 66, 255, 74, 255, 95)
p.shade(220, 85, 0x55)
# jaras (verde)
p.ink(4, 0)
for x, y in [(90, 80), (110, 88), (140, 76), (160, 90), (80, 70)]:
    p.circle(x, y, 4, 8); p.fill(x, y)

# ---------------------------------------------------------------- INTERIOR
# Casa manchega: paredes encaladas, vigas, suelo de barro cocido, puerta y ventana.
p = P('INTERIOR')
p('INK 0'); p('PAPER 7'); p('BRIGHT 0'); p('CLS')
p.block(0, 0, 32, 12, 0, 7, 1)
p.block(0, 9, 32, 3, 0, 2, 0)          # suelo
# vigas
p.ink(0, 1)
p.line(0, 4, 255, 4); p.line(0, 7, 255, 7)
for x in range(8, 256, 32): p.rect(x, 0, 6, 4)
# rincones y zócalo
p.line(0, 71, 255, 71); p.line(0, 66, 255, 66)
# baldosas
p.ink(0, 0)
for x in range(-60, 300, 26): p.line(128 + (x - 128) // 3, 72, x, 95)
p.line(0, 80, 255, 80); p.line(0, 88, 255, 88)
# puerta con arco
p.ink(0, 1)
p.poly(40, 71, 40, 30, 46, 22, 56, 19, 66, 22, 72, 30, 72, 71)
p.line(56, 19, 56, 71)
p.block(5, 3, 4, 6, 2, 7, 1)
p.ink(2, 1); p.shade(48, 50, 0x88); p.shade(64, 50, 0x88)
p.ink(0, 1)
p('PLOT', 52, 46); p('PLOT', 60, 46)
# ventana con reja (cielo detrás)
p.block(22, 3, 4, 3, 0, 5, 1)
p.rect(176, 24, 32, 24)
for x in range(182, 208, 6): p.line(x, 24, x, 47)
p.line(176, 36, 207, 36)
# banco
p.ink(0, 1)
p.rect(110, 56, 44, 4); p.line(114, 60, 114, 70); p.line(150, 60, 150, 70)

# ---------------------------------------------------------------- CORRAL
p = P('CORRAL')
p('INK 0'); p('PAPER 7'); p('BRIGHT 0'); p('CLS')
p.block(0, 0, 32, 3, 7, 5, 1)
p.block(0, 3, 32, 6, 0, 7, 1)
p.block(0, 9, 32, 3, 2, 6, 0)
p.ink(0, 1)
p.line(0, 24, 255, 24); p.line(0, 71, 255, 71)
# piedras de la tapia
random.seed(3)
for y in range(30, 70, 8):
    off = 0 if (y // 8) % 2 else 6
    for x in range(off, 256, 14):
        p.line(x, y, x + 9, y)
# puerta falsa
p.block(25, 4, 4, 5, 0, 2, 0)
p.rect(200, 34, 32, 37); p.line(216, 34, 216, 70)
p.ink(2); p.shade(205, 50, 0xCC); p.shade(225, 50, 0xCC)
# pesebre con paja
p.ink(0, 1)
p.rect(40, 58, 60, 12); p.line(44, 70, 44, 78); p.line(96, 70, 96, 78)
p.ink(6, 1)
for x in range(42, 98, 3): p.line(x, 57, x + 2, 52)
p.ink(2, 0)
for x, y in [(130, 84), (150, 90), (170, 82), (20, 88), (230, 90)]:
    p.line(x, y, x + 6, y - 2)

# ---------------------------------------------------------------- TOLEDO
p = P('TOLEDO')
p('INK 0'); p('PAPER 7'); p('BRIGHT 0'); p('CLS')
p.block(0, 0, 32, 12, 0, 5, 1)
p.block(0, 10, 32, 2, 2, 6, 0)
p.ink(6, 0)
# Alcázar
p.rect(150, 30, 70, 40)
for x in (146, 214):
    p.rect(x, 18, 10, 52); p.poly(x, 18, x + 5, 8, x + 10, 18)
p.fill(185, 50); p.fill(151, 40); p.fill(219, 40)
# catedral
p.ink(7, 1)
p.rect(70, 40, 40, 30); p.rect(84, 10, 12, 30); p.poly(84, 10, 90, 0, 96, 10)
p.fill(90, 55); p.fill(90, 25)
# casas
for x, w, h in [(0, 30, 24), (30, 26, 18), (56, 14, 26), (112, 36, 20), (228, 28, 22)]:
    p.ink(7, 1); p.rect(x, 80 - h, w, h); p.fill(x + 2, 79)
    p.ink(2, 1); p.poly(x, 80 - h, x + w // 2, 74 - h, x + w - 1, 80 - h, x, 80 - h); p.fill(x + w // 2, 78 - h)
p.ink(0, 0)
p.line(0, 80, 255, 80)
for x in range(4, 256, 20): p.rect(x, 64, 4, 6)

# ---------------------------------------------------------------- BIBLIOTECA
# Estanterías de lomos de colores, una mesa con el libro abierto y el candil.
p = P('BIBLIOTECA')
p('INK 0'); p('PAPER 7'); p('BRIGHT 0'); p('CLS')
p.block(0, 0, 32, 12, 2, 0, 0)
# baldas
p.ink(2, 0)
for y in (0, 15, 31, 47, 63):
    p.line(6, y, 249, y)
p.line(6, 0, 6, 63); p.line(249, 0, 249, 63)
# lomos: barras verticales de altura variable dentro de cada balda
for top in (1, 16, 32, 48):
    x = 9
    while x < 246:
        w = random.choice([3, 3, 4, 5])
        h = random.choice([10, 11, 12, 13, 14])
        if random.random() < 0.06:
            # libro tumbado
            x += 2; continue
        for xx in range(x, min(x + w - 1, 246)):
            p.line(xx, top + 14 - h, xx, top + 13)
        x += w
# columnas de color para los lomos (cada celda su tinta: lomos multicolores)
colores = [2, 6, 4, 5, 3, 7, 2, 4, 6, 3, 5, 7]
random.seed(11)
for row in range(0, 8):
    for col in range(1, 31):
        p.block(col, row, 1, 1, colores[(col * 5 + row * 3) % len(colores)], 0, random.choice([0, 1]))
# mesa y libro abierto
p.block(0, 8, 32, 4, 2, 0, 0)
p.ink(2, 0)
p.bar(60, 76, 196, 79)
p.line(66, 80, 66, 95); p.line(190, 80, 190, 95); p.line(67, 80, 67, 95); p.line(189, 80, 189, 95)
p.block(12, 8, 8, 2, 7, 0, 1)
p.ink(7, 1)
p.poly(96, 74, 104, 68, 126, 70, 128, 74, 130, 70, 152, 68, 160, 74, 96, 74)
for y in (70, 72): p.line(106, y, 124, y); p.line(132, y, 150, y)
# candil con llama
p.block(23, 7, 2, 2, 6, 0, 1)
p.ink(6, 1)
p.rect(186, 68, 8, 6)
p.poly(190, 67, 188, 62, 190, 56, 192, 62, 190, 67)
p.fill(190, 62)
p.ink(2, 0)
p.line(184, 74, 196, 74)

# ---------------------------------------------------------------- VENTA
# La venta (o castillo): casa larga encalada, tejado rojo, palomar-torre y el pozo con su pila.
p = P('VENTA')
p('INK 0'); p('PAPER 7'); p('BRIGHT 0'); p('CLS')
p.block(0, 0, 32, 5, 7, 5, 1)          # cielo
p.block(0, 5, 32, 7, 2, 6, 0)          # tierra
p.block(2, 4, 22, 5, 0, 7, 1)          # muros encalados
p.block(16, 1, 4, 3, 0, 7, 1)          # torre-palomar
# tejado
p.ink(2, 0)
p.poly(12, 34, 30, 26, 190, 26, 196, 34, 12, 34)
p.shade(100, 30, 0x55)
p.ink(2, 1)
p.poly(128, 26, 128, 12, 136, 6, 152, 6, 160, 12, 160, 26)
p.ink(0, 1)
p.rect(128, 12, 32, 22)
p.rect(140, 16, 8, 8)
for x in (130, 136, 152, 158): p.line(x, 12, x, 10)
# muros, puerta y ventanucos
p.line(16, 34, 16, 71); p.line(191, 34, 191, 71); p.line(16, 71, 191, 71)
p.poly(70, 71, 70, 46, 76, 40, 90, 40, 96, 46, 96, 71)
p.ink(0); p.shade(83, 60, 0xAA)
p.rect(30, 44, 12, 10); p.rect(120, 44, 12, 10); p.rect(160, 44, 12, 10)
p.line(36, 44, 36, 53); p.line(126, 44, 126, 53); p.line(166, 44, 166, 53)
# pozo
p.ink(0, 0)
p.ellipse(224, 70, 18, 5)
p.line(206, 70, 206, 84); p.line(242, 70, 242, 84)
p('PLOT', 206, 84); p('LINE', 224, 89); p('LINE', 242, 84)
p.line(210, 70, 210, 48); p.line(238, 70, 238, 48); p.line(206, 48, 242, 48)
p.circle(224, 52, 3, 8)
p.line(224, 55, 224, 66)
p.ink(0, 0); p.shade(224, 80, 0x22)
# pila
p.ink(0, 0)
p.rect(200, 88, 26, 6)
p.ink(5, 1); p.fill(212, 91)
# piedras del camino
p.ink(2, 0)
for x, y in [(40, 84), (60, 90), (120, 82), (150, 92), (180, 86)]:
    p.line(x, y, x + 5, y)

# ---------------------------------------------------------------- MOLINOS
# Tres molinos (o gigantes) sobre una loma, aspas en aspa.
p = P('MOLINOS')
p('INK 0'); p('PAPER 7'); p('BRIGHT 0'); p('CLS')
p.block(0, 0, 32, 8, 0, 5, 1)          # cielo
p.block(0, 8, 32, 4, 2, 6, 0)          # loma
p.ink(7, 1)
p.ellipse(30, 14, 16, 4); p.fill(30, 14)
p.ellipse(120, 8, 10, 3); p.fill(120, 8)
# loma
p.ink(2, 0)
p.line(0, 64, 255, 64)
p.shade(128, 84, 0x22)


def molino(px, cx, base_y, h, w, sail):
    """cuerpo blanco (atributos de papel blanco), caperuza negra, cuatro aspas"""
    top = base_y - h
    c0, c1 = (cx - w // 2) // 8, (cx + w // 2) // 8
    r0, r1 = top // 8, (base_y - 1) // 8
    px.block(c0, r0, c1 - c0 + 1, r1 - r0 + 1, 0, 7, 1)
    px.ink(0, 1)
    px.poly(cx - w // 2, base_y, cx - w // 2 + 2, top, cx + w // 2 - 2, top, cx + w // 2, base_y)
    # caperuza
    px.poly(cx - w // 2, top, cx, top - w // 2, cx + w // 2, top, cx - w // 2, top)
    px.fill(cx, top - 2)
    # puerta y ventana
    px.rect(cx - 2, base_y - 8, 5, 8)
    px('PLOT', cx, top + h // 3)
    # aspas
    hx, hy = cx, top + 2
    for ang in (35, 125, 215, 305):
        a = math.radians(ang)
        ex, ey = round(hx + sail * math.cos(a)), round(hy + sail * math.sin(a))
        px.line(hx, hy, ex, ey)
        # bastidor del aspa: rectángulo estrecho a un lado del palo
        nx, ny = -math.sin(a), math.cos(a)
        bw = max(2, sail // 6)
        sx, sy = round(hx + sail * 0.35 * math.cos(a)), round(hy + sail * 0.35 * math.sin(a))
        p1 = (sx + round(nx * bw), sy + round(ny * bw))
        p2 = (ex + round(nx * bw), ey + round(ny * bw))
        px.line(sx, sy, *p1); px.line(*p1, *p2); px.line(*p2, ex, ey)
        for k in (0.55, 0.75):
            qx, qy = round(hx + sail * k * math.cos(a)), round(hy + sail * k * math.sin(a))
            px.line(qx, qy, qx + round(nx * bw), qy + round(ny * bw))


molino(p, 44, 70, 24, 12, 18)
molino(p, 120, 68, 30, 14, 23)
molino(p, 200, 76, 44, 18, 32)

# =========================================================================
#  SEGUNDA PARTE
# =========================================================================

def casa(px, x, y, w, h, roof=2):
    """casa baja encalada: muro, tejado a dos aguas y un ventanuco"""
    px.ink(0, 1); px.rect(x, y, w, h)
    px.ink(roof, 0); px.poly(x - 2, y, x + w // 2, y - h // 3, x + w + 1, y, x - 2, y)
    px.fill(x + w // 2, y - 2)
    px.ink(0, 1); px.rect(x + w // 2 - 2, y + h // 3, 4, 4)


# ---------------------------------------------------------------- TOBOSO
# El Toboso de noche: luna, torre de la iglesia y casas bajas.
p = P('TOBOSO')
p('INK 0'); p('PAPER 7'); p('BRIGHT 0'); p('CLS')
p.block(0, 0, 32, 12, 7, 1, 0)
p.block(0, 9, 32, 3, 6, 0, 0)          # tierra en sombra
p.ink(6, 1); p.circle(36, 18, 8, 14); p.fill(36, 18)
p.ink(7, 1)
for x, y in [(80, 6), (100, 22), (120, 8), (200, 12), (230, 26), (240, 6), (66, 30), (180, 4)]:
    p('PLOT', x, y)
# torre de la iglesia (silueta blanca a la luz de la luna)
p.block(19, 1, 3, 8, 0, 7, 0)
p.ink(0, 0)
p.rect(152, 16, 24, 56); p.poly(152, 16, 164, 4, 175, 16)
p.rect(160, 24, 8, 10); p.line(164, 24, 164, 33)
p('PLOT', 164, 2); p.line(164, 0, 164, 4); p.line(162, 2, 166, 2)
# casas
p.block(1, 7, 7, 2, 0, 7, 0); p.block(9, 7, 6, 2, 0, 7, 0); p.block(23, 7, 8, 2, 0, 7, 0)
for x, w in [(10, 46), (74, 42), (186, 58)]:
    p.ink(0, 0); p.rect(x, 58, w, 14)
    p.poly(x - 2, 58, x + w // 2, 52, x + w + 1, 58)
    p.rect(x + w // 2 - 3, 63, 6, 9)
# perros que ladran (unas manchas en la calle)
p.ink(6, 0)
p.line(0, 72, 255, 72)
for x in (60, 120, 140, 230):
    p.line(x, 84, x + 8, 84); p.line(x, 85, x + 8, 85); p.line(x + 8, 82, x + 10, 81)

# ---------------------------------------------------------------- LEONES
# El carro de los leones con sus banderas reales, en el camino.
p = P('LEONES')
p.gosub('CAMINO')
p.block(10, 5, 12, 5, 0, 6, 1)         # el carro
p.ink(2, 0)
p.rect(80, 44, 96, 30)                  # caja del carro
p.line(80, 74, 176, 74); p.line(80, 75, 176, 75)
for x in range(88, 176, 8): p.line(x, 44, x, 73)    # barrotes
# el león detrás de los barrotes
p.ink(2, 0); p.circle(128, 58, 9, 14); p.fill(128, 58)
p.ink(0, 1); p('PLOT', 125, 56); p('PLOT', 131, 56); p.line(126, 61, 130, 61)
# ruedas
p.ink(0, 0)
for cx in (96, 160):
    p.circle(cx, 80, 8, 12)
    p.line(cx - 8, 80, cx + 8, 80); p.line(cx, 72, cx, 88)
# banderas reales
p.block(10, 2, 2, 3, 2, 5, 1); p.block(20, 2, 2, 3, 2, 5, 1)
p.ink(2, 1)
for x in (82, 162):
    p.line(x, 44, x, 18); p.poly(x, 18, x + 12, 22, x, 26); p.fill(x + 3, 22)

# ---------------------------------------------------------------- BODAS
# La enramada de las bodas: árboles, el novillo en el asador y las ollas.
p = P('BODAS')
p('INK 0'); p('PAPER 7'); p('BRIGHT 0'); p('CLS')
p.block(0, 0, 32, 4, 7, 5, 1)
p.block(0, 4, 32, 8, 2, 6, 0)
p.ink(4, 0)
p.encina(20, 30, 16); p.encina(236, 30, 16)
# arco de ramas
p.block(4, 0, 24, 2, 4, 5, 1)
p.ink(4, 1)
for x in range(34, 222, 10):
    p.circle(x, 8, 5, 8); p.fill(x, 8)
p.line(40, 12, 40, 70); p.line(216, 12, 216, 70)
# asador con el novillo
p.ink(2, 0)
p.line(70, 40, 70, 62); p.line(130, 40, 130, 62); p.line(64, 44, 136, 44)
p.ellipse(100, 44, 20, 7); p.fill(100, 47); p.fill(100, 41)
# fuego
p.block(10, 7, 6, 2, 2, 6, 1)
p.ink(2, 1)
for x in range(82, 120, 6): p.poly(x, 70, x + 3, 60, x + 6, 70)
# ollas como tinajas
p.ink(0, 0)
for cx in (160, 186, 212):
    p.ellipse(cx, 76, 11, 10); p.fill(cx, 76); p.line(cx - 9, 66, cx + 9, 66)
p.ink(7, 1)
for cx in (160, 186, 212):
    p.line(cx - 2, 64, cx - 4, 58); p.line(cx + 2, 64, cx + 4, 57)

# ---------------------------------------------------------------- CUEVA
# La boca de la cueva de Montesinos, ciega de zarzas, y los cuervos.
p = P('CUEVA')
p('INK 0'); p('PAPER 7'); p('BRIGHT 0'); p('CLS')
p.block(0, 0, 32, 4, 7, 5, 1)
p.block(0, 4, 32, 8, 0, 6, 0)
p.ink(0, 0)
p.poly(0, 60, 30, 34, 60, 30, 90, 20, 140, 18, 180, 26, 214, 32, 255, 50)
# la boca, negra (antes del sombreado, para que este no se cuele dentro)
p.ellipse(128, 62, 34, 20, 20); p.fill(128, 62)
p.shade(40, 50, 0x55); p.shade(220, 54, 0x55)
# zarzas
p.block(11, 8, 10, 3, 4, 6, 0)
p.ink(4, 0)
for x in range(92, 166, 6):
    p.line(x, 86, x + 4, 70); p.line(x + 4, 70, x + 8, 84); p('PLOT', x + 2, 78)
# cuervos
p.ink(0, 1)
for x, y in [(60, 10), (76, 18), (180, 8), (196, 16), (150, 6), (110, 12)]:
    p.line(x - 4, y - 2, x, y); p.line(x, y, x + 4, y - 2)

# ---------------------------------------------------------------- PALACIO
# El palacio de cristal de Montesinos en un prado de ensueño.
p = P('PALACIO')
p('INK 0'); p('PAPER 7'); p('BRIGHT 0'); p('CLS')
p.block(0, 0, 32, 8, 7, 3, 0)
p.block(0, 8, 32, 4, 6, 4, 0)
p.block(8, 1, 16, 7, 7, 5, 1)          # muros de cristal
p.ink(7, 1)
p.rect(70, 26, 116, 38)
for x in (64, 120, 180):
    p.rect(x, 10, 12, 54); p.poly(x, 10, x + 6, 2, x + 12, 10)
p.poly(108, 64, 108, 44, 128, 34, 148, 44, 148, 64)
for x in range(80, 180, 12): p.line(x, 30, x + 6, 60)
# sepulcro de mármol y flores
p.ink(7, 1)
p.rect(20, 74, 40, 10); p.fill(30, 78)
p.ink(6, 1)
for x, y in [(90, 80), (110, 88), (150, 82), (200, 90), (230, 78), (10, 90)]:
    p.circle(x, y, 2, 6); p('PLOT', x, y)

# ---------------------------------------------------------------- RIO
# El Ebro, el barco sin remos y las aceñas.
p = P('RIO')
p('INK 0'); p('PAPER 7'); p('BRIGHT 0'); p('CLS')
p.block(0, 0, 32, 4, 7, 5, 1)
p.block(0, 4, 32, 2, 0, 4, 0)          # ribera de enfrente
p.block(0, 6, 32, 6, 7, 1, 0)          # el río
p.ink(4, 1)
for x in range(6, 170, 26): p.encina(x, 30, 6)
# ondas
p.ink(5, 1)
for y in (56, 68, 80, 90):
    for x in range(4 + (y % 3) * 8, 256, 30): p.line(x, y, x + 8, y)
# el barco
p.block(5, 8, 7, 2, 6, 1, 0)
p.ink(6, 0)
p.poly(40, 66, 50, 76, 86, 76, 96, 66, 40, 66); p.fill(68, 72)
# las aceñas: casa sobre el agua y la rueda
p.block(23, 4, 7, 4, 0, 7, 1)
p.ink(0, 1)
p.rect(186, 34, 50, 28); p.poly(184, 34, 211, 22, 238, 34)
p.ink(7, 1)
p.circle(176, 62, 16, 16)
for k in range(8):
    a = math.pi * k / 4
    p.line(176, 62, 176 + round(16 * math.cos(a)), 62 + round(16 * math.sin(a)))

# ---------------------------------------------------------------- CASTILLO
# El castillo de los duques, con sus torres, almenas y estandartes.
p = P('CASTILLO')
p('INK 0'); p('PAPER 7'); p('BRIGHT 0'); p('CLS')
p.block(0, 0, 32, 8, 7, 5, 1)
p.block(0, 8, 32, 4, 4, 6, 0)
p.block(5, 2, 22, 7, 0, 7, 1)
p.ink(0, 1)
p.rect(56, 30, 144, 40)
for x in range(56, 200, 12): p.rect(x, 24, 6, 6)       # almenas
for x in (40, 196):
    p.rect(x, 16, 22, 54)
    for k in range(0, 22, 8): p.rect(x + k, 10, 5, 6)
# puerta y rastrillo
p.poly(112, 70, 112, 48, 128, 40, 144, 48, 144, 70)
for x in range(116, 144, 6): p.line(x, 46, x, 69)
p.rect(70, 40, 6, 10); p.rect(180, 40, 6, 10); p.rect(48, 30, 6, 10); p.rect(204, 30, 6, 10)
# estandartes
p.block(6, 0, 2, 2, 2, 5, 1); p.block(25, 0, 2, 2, 2, 5, 1)
p.ink(2, 1)
for x in (50, 206):
    p.line(x, 10, x, 0); p.poly(x, 1, x + 12, 4, x, 7); p.fill(x + 3, 4)

# ---------------------------------------------------------------- BARATARIA
# La ínsula Barataria: una plaza con el palacio del gobernador.
p = P('BARATARIA')
p('INK 0'); p('PAPER 7'); p('BRIGHT 0'); p('CLS')
p.block(0, 0, 32, 4, 7, 5, 1)
p.block(0, 4, 32, 5, 0, 7, 1)
p.block(0, 9, 32, 3, 2, 6, 0)
# el palacio, con balcón y campana
p.ink(0, 1)
p.rect(90, 26, 76, 46)
p.poly(88, 26, 128, 12, 168, 26)
p.rect(122, 14, 12, 10); p.circle(128, 19, 2, 6)
for x in (100, 120, 140): p.rect(x, 34, 10, 12)
p.line(96, 50, 160, 50); p.line(96, 52, 160, 52)
for x in range(98, 160, 6): p.line(x, 46, x, 50)
p.rect(120, 56, 16, 16)
p.ink(2, 0); p.shade(128, 64, 0x88)
# casas a los lados
for x, w in [(4, 36), (44, 38), (176, 36), (216, 36)]:
    casa(p, x, 44, w, 28)
# el gentío
p.ink(0, 0)
for x in range(20, 240, 14):
    p.circle(x, 82, 2, 6); p.line(x, 84, x, 90)

# ---------------------------------------------------------------- PLAYA
# La playa de Barcelona: el mar, las galeras y la muralla de la ciudad.
p = P('PLAYA')
p('INK 0'); p('PAPER 7'); p('BRIGHT 0'); p('CLS')
p.block(0, 0, 32, 4, 7, 5, 1)
p.block(0, 4, 32, 5, 7, 1, 0)          # el mar
p.block(0, 9, 32, 3, 2, 6, 1)          # la arena
p.ink(7, 1)
for y in (40, 52, 64):
    for x in range(10 + y % 16, 256, 34): p.line(x, y, x + 10, y)
# muralla de la ciudad a la izquierda
p.block(0, 1, 7, 5, 0, 7, 1)
p.ink(0, 1)
p.rect(0, 14, 54, 30)
for x in range(0, 54, 9): p.rect(x, 9, 5, 5)
p.rect(30, 2, 14, 42); p.poly(30, 2, 37, -0, 44, 2)
# galeras: casco, remos y vela latina
for gx, gw in [(96, 60), (176, 52)]:
    p.ink(0, 0)
    p.poly(gx, 50, gx + 6, 58, gx + gw - 6, 58, gx + gw, 50, gx, 50); p.fill(gx + gw // 2, 54)
    for k in range(gx + 6, gx + gw - 4, 6): p.line(k, 58, k - 3, 64)
    p.ink(7, 1)
    p.line(gx + gw // 2, 50, gx + gw // 2, 24)
    p.poly(gx + gw // 2 - 14, 46, gx + gw // 2 + 16, 22, gx + gw // 2, 46)
    p.ink(2, 1); p.poly(gx + gw // 2, 24, gx + gw // 2 + 8, 26, gx + gw // 2, 28)
# huellas de caballo en la arena
p.ink(2, 0)
for x in range(70, 240, 18): p('PLOT', x, 84); p('PLOT', x + 4, 88)

# --------------------------------------------------------------------------- salida
with open(f'{R}/src/pics.paw', 'w', encoding='utf-8') as f:
    f.write('# Generado por tools/pics_gen.py - no editar a mano\n\n')
    # GOSUB necesita que la imagen llamada exista: el orden de definición no importa al compilar
    for name, pic in pics.items():
        f.write(f'/PIC {name}\n' + '\n'.join(pic.c) + '\n\n')
print('imágenes:', ', '.join(pics), '| órdenes:', sum(len(p.c) for p in pics.values()))
