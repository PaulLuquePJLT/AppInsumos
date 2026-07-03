from __future__ import annotations

import html
import time
from typing import Any

import streamlit as st
import streamlit.components.v1 as components


def _qp_get(name: str) -> str | None:
    try:
        value = st.query_params.get(name)
        if isinstance(value, list):
            return value[0] if value else None
        return value
    except Exception:
        return None


def consume_scanned_value() -> None:
    """Consume valores enviados por el scanner HTML y los coloca en session_state.

    El componente JS actualiza la URL con rf_scan_target/rf_scan_value cuando
    detecta un código. En el siguiente rerun se aplica al input correspondiente.
    """
    target = _qp_get("rf_scan_target")
    value = _qp_get("rf_scan_value")
    if not target or not value:
        return

    st.session_state[str(target)] = str(value).strip()
    st.session_state[f"{target}_scanner_open"] = False
    st.session_state["rf_last_scanned_value"] = str(value).strip()
    st.session_state["rf_last_scanned_target"] = str(target)
    st.session_state["rf_last_scanned_ts"] = time.time()

    try:
        # Mantener otros query params de Streamlit limpios evita rescans al refrescar.
        st.query_params.clear()
    except Exception:
        pass


def scan_text_input(
    label: str,
    key: str,
    placeholder: str = "",
    *,
    button_label: str = "Escanear",
    help: str | None = None,
    max_chars: int | None = None,
    uppercase: bool = False,
) -> str:
    """Input con botón lateral para abrir scanner de cámara."""
    col_input, col_scan = st.columns([0.76, 0.24], gap="small")
    with col_input:
        value = st.text_input(label, key=key, placeholder=placeholder, help=help, max_chars=max_chars)
    with col_scan:
        st.markdown('<div style="height:1.45rem"></div>', unsafe_allow_html=True)
        if st.button("▣", key=f"{key}_scanner_btn", help=button_label, use_container_width=True):
            st.session_state[f"{key}_scanner_open"] = True

    if st.session_state.get(f"{key}_scanner_open"):
        _render_scanner_panel(target_key=key, title=button_label)

    return str(value or "").upper() if uppercase else str(value or "")


def _render_scanner_panel(target_key: str, title: str = "Escanear código") -> None:
    with st.container(border=True):
        c1, c2 = st.columns([0.74, 0.26])
        with c1:
            st.markdown(f"**{title}**")
            st.caption("Apunta al código. Se usará la cámara posterior si el navegador la permite.")
        with c2:
            if st.button("Cerrar", key=f"{target_key}_scanner_close", use_container_width=True):
                st.session_state[f"{target_key}_scanner_open"] = False
                st.rerun()
        _barcode_scanner_component(target_key)


def _barcode_scanner_component(target_key: str) -> None:
    safe_target = html.escape(target_key, quote=True)
    component_key = f"rf_live_scanner_{target_key}"
    html_code = f"""
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no" />
<style>
  html, body {{ margin:0; padding:0; background:#071f27; font-family: Arial, sans-serif; }}
  .wrap {{ position:relative; width:100%; height:260px; overflow:hidden; border-radius:14px; background:#071f27; }}
  video {{ width:100%; height:100%; object-fit:cover; transform: translateZ(0); }}
  canvas {{ position:absolute; inset:0; width:100%; height:100%; pointer-events:none; }}
  .scanline {{ position:absolute; left:9%; right:9%; top:50%; height:2px; background:#22c55e; box-shadow:0 0 16px #22c55e; animation: scan 1.25s linear infinite; }}
  .corners:before, .corners:after {{ content:""; position:absolute; width:44px; height:44px; border-color:#22c55e; border-style:solid; }}
  .corners:before {{ left:10%; top:21%; border-width:3px 0 0 3px; }}
  .corners:after {{ right:10%; bottom:21%; border-width:0 3px 3px 0; }}
  .status {{ position:absolute; left:8px; right:8px; bottom:8px; padding:5px 7px; border-radius:10px; background:rgba(0,0,0,.48); color:#d1fae5; font-size:12px; text-align:center; }}
  .ok {{ color:#22c55e; font-weight:700; }}
  .err {{ color:#fbbf24; }}
  @keyframes scan {{ 0% {{ top:24%; }} 50% {{ top:76%; }} 100% {{ top:24%; }} }}
</style>
</head>
<body>
<div class="wrap">
  <video id="video" autoplay muted playsinline></video>
  <canvas id="overlay"></canvas>
  <div class="corners"></div>
  <div class="scanline"></div>
  <div id="status" class="status">Iniciando cámara posterior...</div>
</div>
<script src="https://unpkg.com/@zxing/browser@latest"></script>
<script>
const TARGET = "{safe_target}";
const video = document.getElementById('video');
const canvas = document.getElementById('overlay');
const ctx = canvas.getContext('2d');
const statusEl = document.getElementById('status');
let emitted = false;
let stream = null;

function setStatus(msg, cls='') {{ statusEl.innerHTML = msg; statusEl.className = 'status ' + cls; }}
function fitCanvas() {{ canvas.width = video.clientWidth || 640; canvas.height = video.clientHeight || 360; }}
function drawGreenBox(box) {{
  fitCanvas(); ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (!box) return;
  ctx.strokeStyle = '#22c55e'; ctx.lineWidth = 4; ctx.shadowColor = '#22c55e'; ctx.shadowBlur = 10;
  const sx = canvas.width / (video.videoWidth || canvas.width);
  const sy = canvas.height / (video.videoHeight || canvas.height);
  ctx.strokeRect(box.x * sx, box.y * sy, box.width * sx, box.height * sy);
}}
function emit(code) {{
  if (emitted || !code) return;
  emitted = true;
  setStatus('Código detectado: <span class="ok">' + code + '</span>', 'ok');
  try {{ if (stream) stream.getTracks().forEach(t => t.stop()); }} catch(e) {{}}
  setTimeout(() => {{
    const url = new URL(window.parent.location.href);
    url.searchParams.set('rf_scan_target', TARGET);
    url.searchParams.set('rf_scan_value', code);
    url.searchParams.set('rf_scan_ts', String(Date.now()));
    window.parent.location.href = url.toString();
  }}, 260);
}}
async function getBackCameraStream() {{
  const constraints = {{
    audio: false,
    video: {{
      facingMode: {{ ideal: 'environment' }},
      width: {{ ideal: 1920 }},
      height: {{ ideal: 1080 }},
      frameRate: {{ ideal: 30 }},
      advanced: [{{ focusMode: 'continuous' }}]
    }}
  }};
  try {{ return await navigator.mediaDevices.getUserMedia(constraints); }}
  catch (e) {{
    return await navigator.mediaDevices.getUserMedia({{ audio:false, video: {{ facingMode: 'environment' }} }});
  }}
}}
async function runNativeDetector() {{
  const formats = ['ean_13','ean_8','code_128','code_39','code_93','itf','codabar','upc_a','upc_e','qr_code','data_matrix'];
  const detector = new BarcodeDetector({{ formats }});
  async function loop() {{
    if (emitted) return;
    try {{
      const codes = await detector.detect(video);
      if (codes && codes.length) {{
        const c = codes[0];
        drawGreenBox(c.boundingBox || null);
        emit(c.rawValue);
        return;
      }}
      ctx.clearRect(0,0,canvas.width,canvas.height);
    }} catch(e) {{}}
    requestAnimationFrame(loop);
  }}
  loop();
}}
async function runZXingFallback() {{
  if (!window.ZXingBrowser) {{ throw new Error('ZXing no disponible'); }}
  const reader = new ZXingBrowser.BrowserMultiFormatReader();
  setStatus('Escaneando con motor compatible...');
  await reader.decodeFromVideoElement(video, (result, err, controls) => {{
    if (result && !emitted) {{
      drawGreenBox({{x: canvas.width*.12, y: canvas.height*.25, width: canvas.width*.76, height: canvas.height*.50}});
      emit(result.getText());
      try {{ controls.stop(); }} catch(e) {{}}
    }}
  }});
}}
async function start() {{
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {{
    setStatus('La cámara no está disponible en este navegador.', 'err'); return;
  }}
  try {{
    stream = await getBackCameraStream();
    video.srcObject = stream;
    await video.play();
    fitCanvas();
    setStatus('Apunta el código dentro de las guías verdes.');
    if ('BarcodeDetector' in window) await runNativeDetector();
    else await runZXingFallback();
  }} catch(e) {{
    console.error(e);
    setStatus('No se pudo iniciar la cámara. Verifica permisos HTTPS/cámara.', 'err');
  }}
}}
window.addEventListener('resize', fitCanvas);
start();
</script>
</body>
</html>
"""
    components.html(html_code, height=278, scrolling=False)
