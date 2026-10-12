# Don Quijote de la Mancha (remake 2026)

Aventura conversacional basada en la novela de Cervantes. Es el remake de
la que publicamos en 1989 como Aventuras Level 10 para ZX Spectrum.

Se puede jugar en <https://louzao.network/quijote/>, o abriendo
`index.html` en cualquier navegador. No necesita servidor ni conexión.
Hay versión en inglés, *Don Quixote of La Mancha*, en `en/index.html`.

## El original de 1989

La aventura original se escribió para el ZX Spectrum con PAW (Professional
Adventure Writer). Programa y gráficos de Jorge Louzao Penalva, con la
colaboración de Angel Louzao Penalva y Luis Gabaldón Alvarez.

Algunos de sus puzles tenían soluciones que Cervantes no
habría firmado, como el león que se duerme si le cantas o el final con las
dos muchachas que dicen ser Dulcinea.

## El remake

El remake vuelve a contar la historia con mucho más texto, más localidades
y gráficos nuevos. Sigue la novela de cerca: la Primera Parte llega hasta
la jaula y la Segunda continúa en la misma partida hasta Barcelona y la
vuelta a casa. Los puzles de 1989 se han respetado, y su final se mantiene
como final alternativo junto al del libro.

Se ve como en un Spectrum: pantalla de 256x192, colores por atributos y la
misma fuente de 1989, sacada de la imagen original del juego. Por dentro
funciona con un motor propio en JavaScript que imita la forma de trabajar
de PAW: localidades, objetos, banderas, mensajes y tablas de proceso con
condactos. Las fuentes de la aventura se escriben en un formato de texto
parecido al de PAW y un pequeño compilador las convierte en lo que lee el
motor.

## Idiomas

La aventura se escribe en español y la lógica es una sola para todos los
idiomas. Una traducción solo lleva textos, en `src/<idioma>/`: los mensajes,
localidades y objetos van por su nombre, y las frases que hay dentro de los
procesos van por una clave sacada del texto español. El vocabulario de cada
idioma se cuelga de los mismos grupos de palabras del español, así que los
procesos no cambian.

Al compilar, lo que falte por traducir se queda en español y se lista en
`build/faltan_<idioma>.txt`, con el texto original, listo para traducir. Si
cambia un texto en español, su traducción deja de valer y vuelve a salir en
esa lista.

La traducción al inglés es propia; algunas frases muy conocidas de la novela
siguen de cerca la traducción clásica de John Ormsby (1885).

## De aquí nació Rocinante

La primera idea era que el remake pudiera volver al Spectrum de verdad. Para
eso hacía falta llevarlo a DAAD, el sucesor de PAW, y de ese trabajo salió
Rocinante, un editor de aventuras para DAAD que funciona en el navegador.

https://github.com/louzaonet/rocinante

Rocinante sigue su propio camino y sirve para cualquier aventura. El remake,
en cambio, se quedó en la web: tiene más texto del que cabe en un Spectrum
y más mensajes de los que admite DAAD, y recortarlo era perder justo lo que
lo hace distinto del original.

Como los dos usan formatos distintos, hay dos herramientas para pasar cosas
de uno a otro:

- `tools/to_rocinante.mjs` convierte el mundo y los dibujos del remake en un
  proyecto de Rocinante (`don_quijote_2026.rocinante.json`). Así el mapa, el
  vocabulario y los gráficos se pueden abrir y editar allí. Los procesos no
  van, porque son del motor del remake.
- `tools/de_rocinante.py` hace el camino contrario con los dibujos: lee un
  proyecto de Rocinante y pasa sus dibujos vectoriales al formato del remake.
  Así el editor de dibujos de Rocinante sirve también para el remake.

## Estructura

| Ruta | Contenido |
|---|---|
| `index.html` | El juego completo en una sola página |
| `en/index.html` | El juego en inglés |
| `don_quijote_2026.rocinante.json` | El mundo y los dibujos como proyecto de Rocinante |
| `don_quixote_2026.rocinante.json` | Lo mismo, en inglés |
| `src/base.paw` | Configuración, vocabulario, mensajes del sistema y banderas |
| `src/parte1_*.paw` | Primera Parte: localidades, objetos, mensajes y procesos |
| `src/parte2_*.paw` | Segunda Parte |
| `src/comun.paw` | Respuestas comunes a toda la aventura |
| `src/pics.paw` | Dibujos (los genera `tools/pics_gen.py`) |
| `src/en/` | Textos y vocabulario en inglés |
| `src/engine.js` | Motor de la aventura |
| `src/screen.js` | Pantalla de Spectrum: atributos, fuente y dibujos |
| `src/font.json` | La fuente de 1989 |
| `tools/pawc.py` | Compilador de los `.paw` |
| `tools/pics_gen.py` | Generador de los dibujos |
| `tools/build.py` | Compila todo y genera `index.html` y `en/index.html` |
| `tools/to_rocinante.mjs` | Del remake a Rocinante |
| `tools/de_rocinante.py` | Dibujos de Rocinante al remake |
| `tools/shot.py`, `tools/e2e.py` | Capturas y partida completa en un navegador (Playwright) |
| `test/solucion1.txt` | Solución de la Primera Parte |
| `test/solucion2.txt` | Solución de la Segunda Parte, con el final del libro |
| `test/solucion2_1989.txt` | Solución de la Segunda Parte, con el final de 1989 |
| `test/run.mjs` | Juega una lista de órdenes y resume la partida |
| `test/t_varios.txt` | Órdenes sueltas para probar respuestas |
| `test/lineas.mjs` | Comprueba que ningún texto se pierde por arriba sin pausa para leerlo |
| `test/en/` | Las soluciones y las órdenes de prueba en inglés |

Las soluciones destripan el juego entero.

`build/` se genera al compilar.

## Compilar y probar

Hace falta Python 3 y Node.js. No hay que instalar paquetes, salvo
Playwright para `shot.py` y `e2e.py`.

```
python3 tools/pics_gen.py        # solo si cambian los dibujos
python3 tools/build.py
node test/run.mjs build/quijote.json test/solucion1.txt,test/solucion2.txt --quiet
node test/lineas.mjs test/solucion1.txt,test/solucion2.txt
node test/run.mjs build/quijote_en.json test/en/solucion1.txt,test/en/solucion2.txt --quiet
node test/lineas.mjs test/en/solucion1.txt,test/en/solucion2.txt build/quijote_en.json
python3 tools/e2e.py en/index.html           # partida entera en un navegador
```

## Editar en Rocinante

Para abrir el mundo en Rocinante, usa Proyecto > Abrir proyecto con
`don_quijote_2026.rocinante.json`. Si cambian los fuentes, se regenera con:

```
node tools/to_rocinante.mjs        # en español
node tools/to_rocinante.mjs --en   # en inglés
```

Necesita el código de Rocinante en una carpeta `rocinante` junto a esta, o
la ruta en la variable `ROCINANTE`.

Para traer dibujos hechos o retocados en Rocinante:

```
python3 tools/de_rocinante.py proyecto.json                 # todos los vectoriales
python3 tools/de_rocinante.py proyecto.json camino toboso   # solo esos
python3 tools/build.py
```

Los dibujos van a `src/pics_editados.paw`, que se compila después de
`pics.paw`. Un dibujo con el mismo nombre sustituye al generado; el nombre
es el identificador de Rocinante en mayúsculas. Cada exportación cambia solo
los dibujos exportados.

El remake no tiene texto dentro de los dibujos, ni parpadeo, ni líneas en
modo OVER o INVERSE: si un dibujo los usa, se quitan.