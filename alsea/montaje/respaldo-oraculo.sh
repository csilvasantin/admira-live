#!/usr/bin/env bash
# Respaldo de P08–P11 (Lucas) para el vídeo lineal Alsea (seguimiento #4768 de #4761).
# Si a las 20:45 no están en DIR_PLANOS, captura la biblioteca de Oráculo como P08…P11-oraculo.png.
# Ojo: esa página NO lleva la interfaz de siempre (☰ Opciones / Avanzado / Experto); es solo respaldo.
# Uso: respaldo-oraculo.sh DIR_PLANOS
set -euo pipefail
D=${1:?DIR_PLANOS}; mkdir -p "$D"
URL=https://oraculo-demo-distribucion-bi.pixeria.pages.dev/demo/biblioteca/
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
for P in P08 P09 P10 P11; do
  if ls "$D"/$P-* >/dev/null 2>&1; then echo "$P: ya está"; continue; fi
  [ -f "$T/bib.png" ] || timeout 90 google-chrome --headless=new --no-sandbox --disable-gpu --disable-dev-shm-usage \
    --hide-scrollbars --user-data-dir="$T/ud" --window-size=1440,860 --virtual-time-budget=8000 \
    --screenshot="$T/bib.png" "$URL" >/dev/null 2>&1
  cp "$T/bib.png" "$D/$P-oraculo.png"; echo "$P: respaldo Oráculo"
done
