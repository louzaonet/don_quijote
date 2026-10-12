#!/usr/bin/env python3
"""Partida completa en Chromium: teclea la solución respondiendo a los 'pulsa una tecla'.
Uso: e2e.py [en/index.html] [test/solucion1.txt test/solucion2.txt]"""
import asyncio, os, sys
from playwright.async_api import async_playwright
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
args = sys.argv[1:]
page = args.pop(0) if args and args[0].endswith('.html') else 'index.html'
sols = args or (['test/en/solucion1.txt', 'test/en/solucion2.txt'] if page.startswith('en/')
                else ['test/solucion1.txt', 'test/solucion2.txt'])
cmds = [l.split('#')[0].strip() for f in sols for l in open(f'{R}/{f}', encoding='utf-8')]
cmds = [c for c in cmds if c]
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': 420, 'height': 800})   # ancho de móvil
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('file://' + f'{R}/{page}')
        await pg.evaluate('window.__screen.pause = () => Promise.resolve()')
        i, keys = 0, 0
        for _ in range(20000):
            await pg.wait_for_timeout(15)
            mode = await pg.evaluate('window.__screen.mode')
            if mode == 'key':
                await pg.keyboard.press('Space'); keys += 1
            elif mode == 'input':
                if i >= len(cmds): break
                await pg.locator('#cmd').fill(cmds[i]); i += 1
                await pg.keyboard.press('Enter')
        await pg.wait_for_timeout(200)
        await pg.screenshot(path=f'{R}/build/e2e_final.png')
        print(f'órdenes {i}/{len(cmds)}, teclas {keys}, errores JS: {errs}')
        await b.close()
asyncio.run(main())
