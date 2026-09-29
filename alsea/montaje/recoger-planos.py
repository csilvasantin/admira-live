#!/usr/bin/env python3
"""Baja del Stock de Pixeria los planos del vídeo lineal Alsea (encargo #4761, relevo de #4732).

Un plano es un vídeo del Stock con `alsea-lineal` en etiquetas, título o comentario y un código
P04–P15 en el título o el comentario (p. ej. «P07-woz-alta-excel»). Se guarda como
planos/P<nº>-<id>.mp4, que es lo que busca montar.py. Si hay varios del mismo plano, gana el más nuevo.

Uso: recoger-planos.py DIR_PLANOS   → imprime cuántos ha bajado
"""
import json, os, re, sys, urllib.request

INDICE = 'https://stock.admira.store/stock/index.json'
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) Chrome/140.0 Safari/537.36'}

def main(dest):
    os.makedirs(dest, exist_ok=True)
    items = json.load(urllib.request.urlopen(urllib.request.Request(INDICE, headers=UA), timeout=60))['items']
    elegidos = {}
    for it in items:
        texto = ' '.join([it.get('title') or '', it.get('comment') or '', ' '.join(it.get('tags') or [])])
        if it.get('type') != 'video' or 'alsea-lineal' not in texto.lower():
            continue
        m = re.search(r'\bP(0[4-9]|1[0-5])\b', (it.get('title') or '') + ' ' + (it.get('comment') or ''))
        if not m:
            continue                                  # p. ej. el propio vídeo montado
        P = 'P' + m.group(1)
        if P not in elegidos or it.get('createdAt', 0) > elegidos[P].get('createdAt', 0):
            elegidos[P] = it
    for P, it in sorted(elegidos.items()):
        ruta = os.path.join(dest, f'{P}-{it["id"]}.mp4')
        if not os.path.exists(ruta):
            with urllib.request.urlopen(urllib.request.Request(it['url'], headers=UA), timeout=600) as r, open(ruta, 'wb') as f:
                f.write(r.read())
        print(f'  {P} ← {it["id"]} · {it.get("title")}')
    print(f'{len(elegidos)} planos de 12')

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'planos')
