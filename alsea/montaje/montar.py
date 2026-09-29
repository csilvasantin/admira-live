#!/usr/bin/env python3
"""Monta el vídeo lineal Alsea a partir de GUION-VIDEO-LINEAL.md (encargo #4732, fase 2).

Cada fila de la escaleta es un minuto. Para cada minuto:
  - imagen: el plano grabado (planos/P<nº>-*.mp4) si existe; si no, una lámina
    1920x1080 con la captura de respaldo, rotulada «captura · plano pendiente»;
  - locución: la columna LOC con Piper (voz libre local, sin coste);
  - música: «Tu pausa» del Stock de Pixeria, con ducking bajo la voz.

Uso:
  montar.py --planos DIR --assets DIR --salida alsea-lineal.mp4 [--seg 60] [--solo 00:00,10:00]
"""
import argparse, json, os, re, shutil, subprocess, sys, html, tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
GUION = os.path.join(AQUI, '..', 'GUION-VIDEO-LINEAL.md')
W, H = 1920, 1080

# Consejero que graba cada plano (tabla 4 del guion).
DUENO = {**{f'P{n:02d}': 'Woz' for n in range(4, 8)},
         **{f'P{n:02d}': 'Lucas' for n in range(8, 12)},
         **{f'P{n:02d}': 'Walt' for n in range(12, 16)}}

def parse(md):
    filas, tramo, sub = [], '', ''
    for ln in open(md, encoding='utf-8'):
        if ln.startswith('### '):
            tramo, sub = re.sub(r'\s*\(.*', '', ln[4:]).strip(), ''
        elif ln.startswith('#### '):
            sub = re.sub(r'\s*\(.*', '', ln[5:]).strip()
        m = re.match(r'^\| (\d\d):(\d\d) \|(.*)\|\s*$', ln)
        if m:
            c = [x.strip() for x in m.group(3).split(' | ')]
            if len(c) != 4:
                sys.exit(f'fila mal formada en {m.group(1)}:{m.group(2)}: {len(c)} columnas')
            planos = re.findall(r'P\d\d', c[3])
            filas.append(dict(min=f'{m.group(1)}:{m.group(2)}', n=int(m.group(1)), tramo=tramo, sub=sub,
                              izq=c[0], der=c[1], loc=c[2], plano_txt=c[3], plano=planos[0] if planos else ''))
    if len(filas) != 60:
        sys.exit(f'la escaleta tiene {len(filas)} minutos, no 60')
    return filas

def respaldo(f, A):
    """Captura de respaldo para la mitad izquierda (o pantalla entera) y para la Cafebrería."""
    n, P = f['n'], f['plano']
    deck = os.path.join(A, 'deck')
    izq = {
        0: f'{deck}/01-portada-alsea-circuito.png', 1: f'{deck}/02-portada-tres-actos.png',
        2: f'{deck}/03-acto-studio.png', 3: f'{deck}/04-acto-store.png', 4: f'{deck}/05-acto-app.png',
        7: f'{A}/live-app.png', 59: f'{deck}/01-portada-alsea-circuito.png',
        56: f'{A}/live-app.png', 57: f'{A}/niveles/comparativa-4-niveles.png',
    }.get(n)
    if not izq:
        if P in ('P04', 'P05', 'P06', 'P07'): izq = f'{A}/live-store.png'
        elif P in ('P08', 'P09', 'P10', 'P11'): izq = f'{A}/stock-xpaces-alsea.png'
        elif P in ('P12', 'P13'):
            izq = f'{A}/niveles/' + {40: '01-good', 41: '02-better'}.get(n, '03-best') + '-opciones-avanzado-experto.png'
        elif P == 'P14': izq = f'{A}/niveles/03-avanzado-32bits-best.png'
        elif P == 'P15': izq = f'{A}/' + ('visor-iot-wifi-altavoces.png' if n >= 54 else 'live-yokup.png' if n == 52 else 'visor-pizarras.png')
    if n < 9:
        der = None                                            # A y B: pantalla entera
    elif n in (9, 40) or n < 25:
        der = f'{A}/niveles/01-good-vista.png'
    elif n < 40 or n == 41:
        der = f'{A}/niveles/02-better-vista.png'
    else:
        der = f'{A}/niveles/03-best-vista.png'
    return izq, der

CSS = '''*{box-sizing:border-box;margin:0}body{width:1920px;height:1080px;background:%s;color:#eef2f0;
font:28px/1.3 "DejaVu Sans",Arial,sans-serif;overflow:hidden;position:relative}
.top{position:absolute;top:0;left:0;right:0;height:72px;display:flex;align-items:center;gap:22px;padding:0 36px;
background:rgba(8,14,12,.88);border-bottom:2px solid #00704a;font-size:24px}
.top b{color:#9fd8bd;letter-spacing:.08em}.top .tc{margin-left:auto;font-family:"DejaVu Sans Mono",monospace;color:#9fd8bd}
.sub{position:absolute;left:0;right:0;bottom:0;min-height:150px;padding:22px 60px;background:rgba(8,14,12,.9);
border-top:2px solid #00704a;font-size:34px;line-height:1.35;display:flex;align-items:center}
.cols{position:absolute;top:72px;bottom:150px;left:0;right:0;display:flex}
.col{flex:1;display:flex;flex-direction:column;padding:18px 26px;gap:12px;min-width:0}
.col+.col{border-left:2px solid #00704a}
.lab{font-size:20px;letter-spacing:.14em;color:#9fd8bd}
.img{flex:1;min-height:0;background:#050807 center/contain no-repeat;border-radius:10px}
.txt{font-size:25px;color:#d5e3dc}
.big{flex:1;display:flex;align-items:center;justify-content:center;text-align:center;padding:0 140px;
font-size:54px;line-height:1.3;font-weight:bold;color:#eef2f0;background:radial-gradient(circle at 50%% 40%%,#12342a,#050807 70%%);border-radius:10px}
.tag{position:absolute;top:92px;padding:6px 16px;border-radius:6px;font-size:22px;font-weight:bold}
.pend{right:36px;background:#b8860b;color:#111}.ej{left:36px;background:#c62828;color:#fff}'''

def md_txt(s):
    s = html.escape(s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    s = re.sub(r'\*(.+?)\*', r'<i>\1</i>', s)
    return re.sub(r'`(.+?)`', r'\1', s)

def cabecera(f):
    return (f'<div class="top"><b>ADMIRA × ALSEA</b><span>{md_txt(f["tramo"])}</span>'
            f'<span style="color:#9fd8bd">{md_txt(f["sub"])}</span><span class="tc">{f["min"]} / 60:00</span></div>'
            f'<div class="sub"><span>{md_txt(re.sub(r"\*\([^)]*\)\*\s*", "", f["loc"]))}</span></div>')

def etiquetas(f, pendiente):
    t = ''
    if re.search(r'EJEMPLO|simulad', f['izq'] + f['der'] + f['loc'], re.I):
        t += '<div class="tag ej">EJEMPLO · datos simulados</div>'
    if pendiente:
        t += f'<div class="tag pend">captura · plano {f["plano"]} pendiente ({DUENO[f["plano"]]})</div>'
    return t

def lamina(f, A, pendiente):
    izq, der = respaldo(f, A)
    url = lambda p: f"url('file://{p}')" if p and os.path.exists(p) else 'none'
    if der is None and url(izq) == 'none':
        cuerpo = f'<div class="cols"><div class="col"><div class="big">{md_txt(re.sub(r"^Entera:\s*", "", f["izq"]))}</div></div></div>'
    elif der is None:
        cuerpo = (f'<div class="cols"><div class="col"><div class="img" style="background-image:{url(izq)}"></div>'
                  f'<div class="txt">{md_txt(f["izq"])}</div></div></div>')
    else:
        cuerpo = (f'<div class="cols"><div class="col"><div class="lab">CONTROL</div>'
                  f'<div class="img" style="background-image:{url(izq)}"></div><div class="txt">{md_txt(f["izq"])}</div></div>'
                  f'<div class="col"><div class="lab">LA CAFEBRERÍA</div>'
                  f'<div class="img" style="background-image:{url(der)}"></div><div class="txt">{md_txt(f["der"])}</div></div></div>')
    return f'<!doctype html><meta charset="utf-8"><style>{CSS % "#0b1210"}</style>{cuerpo}{cabecera(f)}{etiquetas(f, pendiente)}'

def superpuesto(f):
    return f'<!doctype html><meta charset="utf-8"><style>{CSS % "transparent"}</style>{cabecera(f)}{etiquetas(f, False)}'

def foto(html_txt, png, tmp, transparente=False):
    h = os.path.join(tmp, os.path.basename(png) + '.html')
    open(h, 'w', encoding='utf-8').write(html_txt)
    cmd = ['google-chrome', '--headless=new', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
           '--no-first-run', f'--user-data-dir={tmp}/ud', '--hide-scrollbars', '--allow-file-access-from-files',
           f'--window-size={W},{H}', f'--screenshot={png}', 'file://' + h]
    if transparente: cmd.insert(3, '--default-background-color=00000000')
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90)
    if not os.path.exists(png): sys.exit(f'no se pudo renderizar {png}')

def dur(p):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]))

def ff(*a):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *a], check=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--planos', required=True); ap.add_argument('--assets', required=True)
    ap.add_argument('--salida', required=True); ap.add_argument('--seg', type=float, default=60)
    ap.add_argument('--solo', default=''); ap.add_argument('--piper', default='piper')
    ap.add_argument('--voz', required=True); ap.add_argument('--tmp', default='')
    a = ap.parse_args()
    filas = parse(GUION)
    if a.solo: filas = [f for f in filas if f['min'] in a.solo.split(',')]
    tmp = a.tmp or tempfile.mkdtemp(prefix='alsea-lineal-'); os.makedirs(tmp, exist_ok=True)
    planos = {os.path.basename(p)[:3]: os.path.join(a.planos, p)
              for p in sorted(os.listdir(a.planos)) if re.match(r'P\d\d-.*\.(mp4|mov|webm)$', p)} if os.path.isdir(a.planos) else {}
    usos = {}
    for f in filas: usos.setdefault(f['plano'], []).append(f['n'])
    informe, segs, voces = [], [], []
    for f in filas:
        tag = f['min'].replace(':', '')
        seg, voz = f'{tmp}/seg-{tag}.mp4', f'{tmp}/voz-{tag}.wav'
        # Locución: Piper → 1,5 s de entrada → relleno hasta la duración del minuto.
        crudo = f'{tmp}/tts-{tag}.wav'
        txt = re.sub(r'\*\([^)]*\)\*', '', f['loc']).replace('*', '').replace('`', '')
        txt = re.sub(r'\[[^\]]*\]', 'pendiente de confirmar', txt).strip()
        subprocess.run([a.piper, '-m', a.voz, '-f', crudo], input=txt.encode(), check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        ff('-i', crudo, '-af', f'adelay=1500:all=1,apad,atrim=0:{a.seg},aformat=sample_rates=48000:channel_layouts=stereo', voz)
        voces.append(voz)
        P = f['plano']
        if P in planos:
            over = f'{tmp}/over-{tag}.png'; foto(superpuesto(f), over, tmp, transparente=True)
            d, idx = dur(planos[P]), usos[P].index(f['n'])
            off = (d / len(usos[P])) * idx
            ff('-ss', f'{off:.2f}', '-stream_loop', '-1', '-i', planos[P], '-loop', '1', '-i', over,
               '-filter_complex', f'[0:v]scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v];[v][1:v]overlay=0:0',
               '-t', str(a.seg), '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', seg)
            informe.append((f['min'], P, 'plano', os.path.basename(planos[P])))
        else:
            pend = P in DUENO
            png = f'{tmp}/lam-{tag}.png'; foto(lamina(f, a.assets, pend), png, tmp)
            ff('-loop', '1', '-framerate', '30', '-i', png, '-t', str(a.seg), '-c:v', 'libx264', '-preset', 'veryfast',
               '-tune', 'stillimage', '-pix_fmt', 'yuv420p', seg)
            informe.append((f['min'], P, 'captura-pendiente' if pend else 'lamina', ''))
        segs.append(seg)
        print(f'  {f["min"]} {P or "--"} {informe[-1][2]}', flush=True)
    open(f'{tmp}/segs.txt', 'w').write(''.join(f"file '{s}'\n" for s in segs))
    open(f'{tmp}/voces.txt', 'w').write(''.join(f"file '{v}'\n" for v in voces))
    ff('-f', 'concat', '-safe', '0', '-i', f'{tmp}/segs.txt', '-c', 'copy', f'{tmp}/video.mp4')
    ff('-f', 'concat', '-safe', '0', '-i', f'{tmp}/voces.txt', '-c', 'pcm_s16le', f'{tmp}/voz.wav')
    total = a.seg * len(filas)
    musica = os.path.join(a.assets, 'tu-pausa.mp3')
    ff('-i', f'{tmp}/video.mp4', '-i', f'{tmp}/voz.wav', '-stream_loop', '-1', '-i', musica, '-filter_complex',
       '[1:a]asplit=2[v1][v2];'
       '[2:a]aformat=sample_rates=48000:channel_layouts=stereo,volume=0.30[m];'
       '[m][v1]sidechaincompress=threshold=0.02:ratio=8:attack=20:release=400[md];'
       '[md][v2]amix=inputs=2:duration=first:normalize=0,afade=t=out:st=%.1f:d=4[a]' % max(total - 4, 0),
       '-map', '0:v', '-map', '[a]', '-t', str(total), '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k',
       '-movflags', '+faststart', a.salida)
    json.dump([dict(min=m, plano=p, fuente=s, fichero=x) for m, p, s, x in informe],
              open(os.path.splitext(a.salida)[0] + '.planos.json', 'w'), ensure_ascii=False, indent=1)
    print('✓', a.salida, f'{total/60:.1f} min', flush=True)

if __name__ == '__main__':
    main()
