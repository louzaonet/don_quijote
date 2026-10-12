#!/usr/bin/env python3
"""Compila el fuente y genera index.html (español) y en/index.html (inglés):
el juego entero en una sola página por idioma."""
import subprocess, json, sys, os
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# parte2_proc va antes que parte1_proc: sus entradas tienen que ir delante en cada tabla
srcs = ['base.paw', 'parte1_mundo.paw', 'parte2_mundo.paw', 'parte2_proc.paw', 'parte1_proc.paw', 'comun.paw', 'pics.paw']
# dibujos retocados en Rocinante (tools/de_rocinante.py): van después y sustituyen a los de pics.paw
if os.path.exists(f'{R}/src/pics_editados.paw'):
    srcs.append('pics_editados.paw')
# textos de la página (lo demás sale de la base de datos de cada idioma)
UI = {
    'es': {'title': 'Don Quijote de la Mancha', 'screen': 'Pantalla de la aventura',
           'input': 'Escribe tu orden y pulsa Enter',
           'help': 'Escribe y pulsa <kbd>Enter</kbd>. En el móvil, toca la pantalla. Prueba <kbd>AYUDA</kbd>, '
                   '<kbd>SALIDAS</kbd>, <kbd>I</kbd>, <kbd>GRABAR</kbd>. <a href="en/">English</a>'},
    'en': {'title': 'Don Quixote of La Mancha', 'screen': 'Adventure screen',
           'input': 'Type your command and press Enter',
           'help': 'Type and press <kbd>Enter</kbd>. On a phone, tap the screen. Try <kbd>HELP</kbd>, '
                   '<kbd>EXITS</kbd>, <kbd>I</kbd>, <kbd>SAVE</kbd>. <a href="../">Español</a>'},
}
# idioma -> (base de datos, página)
OUT = {'es': ('build/quijote.json', 'index.html'), 'en': ('build/quijote_en.json', 'en/index.html')}

for lang, (dbf, page) in OUT.items():
    opts = [] if lang == 'es' else ['--lang', lang, '--tr', f'{R}/src/{lang}']
    subprocess.run([sys.executable, f'{R}/tools/pawc.py', *opts, f'{R}/{dbf}'] + [f'{R}/src/{s}' for s in srcs], check=True)
    t = open(f'{R}/tools/template.html', encoding='utf-8').read()
    db = open(f'{R}/{dbf}', encoding='utf-8').read()
    t = t.replace('/*__ENGINE__*/', open(f'{R}/src/engine.js', encoding='utf-8').read())
    t = t.replace('/*__SCREEN__*/', open(f'{R}/src/screen.js', encoding='utf-8').read())
    t = t.replace('/*__DB__*/null', db.replace('</', '<\\/'))
    t = t.replace('/*__FONT__*/null', open(f'{R}/src/font.json').read())
    for k, v in UI[lang].items():
        t = t.replace('{{' + k + '}}', v)
    # página completa, para abrir con doble clic o subir tal cual a la web
    full = (f'<!doctype html>\n<html lang="{lang}">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            '</head>\n<body style="margin:0">\n' + t + '\n</body>\n</html>\n')
    os.makedirs(os.path.dirname(f'{R}/{page}') or R, exist_ok=True)
    open(f'{R}/{page}', 'w', encoding='utf-8').write(full)
    print(page, len(full) // 1024, 'KB')
