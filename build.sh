#!/usr/bin/env bash
# Render every scene and stitch them into explainer.mp4.
#   ./build.sh            full quality (1080p30)
#   ./build.sh preview    low quality, fast
# Needs: manim (Community), ffmpeg, LaTeX; audio/ from make_audio.py.
set -euo pipefail
cd "$(dirname "$0")"
PY=${PYTHON:-python}
MEDIA=${MEDIA_DIR:-media}
if [[ "${1:-}" == "preview" ]]; then
  QUAL=(-ql); OUT=explainer_preview.mp4; QDIR=480p15
else
  QUAL=(--resolution 1920,1080 --frame_rate 30); OUT=explainer.mp4; QDIR=1080p30
fi
SCENES=$($PY -c "import scenes; print(' '.join(scenes.SCENES))" 2>/dev/null | tail -1)
JOBS=${JOBS:-4}
printf '%s\n' $SCENES | xargs -P "$JOBS" -I{} $PY -m manim render "${QUAL[@]}" --media_dir "$MEDIA" \
  --disable_caching -v WARNING scenes.py {}
LIST=$(mktemp)
for s in $SCENES; do
  f="$MEDIA/videos/scenes/$QDIR/$s.mp4"
  echo "file '$(realpath "$f")'" >> "$LIST"
done
ffmpeg -y -loglevel error -f concat -safe 0 -i "$LIST" -c:v libx264 -crf 18 -pix_fmt yuv420p \
  -c:a aac -b:a 192k -movflags +faststart "$OUT"
echo "wrote $OUT"
