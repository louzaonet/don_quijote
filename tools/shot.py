#!/usr/bin/env python3
"""Capturas con Playwright.
  shot.py galeria            -> build/pics/<NOMBRE>.png con cada imagen
  shot.py juego cmd1 cmd2... -> build/juego.png tras teclear las órdenes"""
import sys, os, asyncio
from playwright.async_api import async_playwright
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

async def main():
    mode = sys.argv[1]
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': 900, 'height': 800})
        msgs = []
        pg.on('console', lambda m: msgs.append(m.text))
        pg.on('pageerror', lambda e: msgs.append('ERROR ' + str(e)))
        url = 'file://' + f'{R}/index.html'
        if mode == 'galeria':
            await pg.goto(url + '#galeria')
            await pg.wait_for_timeout(300)
            os.makedirs(f'{R}/build/pics', exist_ok=True)
            names = await pg.evaluate('Object.keys(window.__db.names.pics)')
            only = sys.argv[2:]
            for i, n in enumerate(names):
                if only and n not in only: continue
                await pg.evaluate(f'window.__screen.picture({i}); window.__screen.render()')
                await pg.locator('#screen').screenshot(path=f'{R}/build/pics/{n}.png')
        else:
            await pg.goto(url)
            await pg.wait_for_timeout(400)
            for c in sys.argv[2:]:
                if c == '_':
                    await pg.keyboard.press('Space')
                else:
                    await pg.keyboard.type(c, delay=5)
                    await pg.keyboard.press('Enter')
                await pg.wait_for_timeout(250)
            await pg.wait_for_timeout(300)
            await pg.screenshot(path=f'{R}/build/juego.png')
        if msgs: print('\n'.join(msgs))
        await b.close()
asyncio.run(main())
