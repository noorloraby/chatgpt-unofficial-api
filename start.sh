#!/usr/bin/env bash
set -euo pipefail

DISPLAY_NUM="${DISPLAY_NUM:-:99}"
VNC_PORT="${VNC_PORT:-5900}"
NOVNC_PORT="${NOVNC_PORT:-6080}"
VNC_GEOMETRY="${VNC_GEOMETRY:-1920x1080}"
VNC_DEPTH="${VNC_DEPTH:-24}"
APP_PORT="${APP_PORT:-8000}"
export DISPLAY="$DISPLAY_NUM"

if command -v Xvnc >/dev/null 2>&1; then
  XVNC_BIN="Xvnc"
elif command -v Xtigervnc >/dev/null 2>&1; then
  XVNC_BIN="Xtigervnc"
else
  echo "ERROR: Xvnc executable not found (expected Xvnc or Xtigervnc)." >&2
  exit 1
fi

DISPLAY_ID="${DISPLAY#:}"
echo "Starting TigerVNC display server ($XVNC_BIN on $DISPLAY)..."
rm -f "/tmp/.X${DISPLAY_ID}-lock" "/tmp/.X11-unix/X${DISPLAY_ID}" 2>/dev/null || true

XVNC_ARGS=(
  "$DISPLAY"
  -geometry "$VNC_GEOMETRY"
  -depth "$VNC_DEPTH"
  -rfbport "$VNC_PORT"
  -localhost yes
)

if [[ -n "${VNC_PASSWORD:-}" ]]; then
  if command -v tigervncpasswd >/dev/null 2>&1; then
    VNC_PASSWD_CMD="tigervncpasswd"
  elif command -v vncpasswd >/dev/null 2>&1; then
    VNC_PASSWD_CMD="vncpasswd"
  else
    echo "ERROR: VNC_PASSWORD is set but no vncpasswd utility is available." >&2
    exit 1
  fi

  VNC_PASSWD_FILE="/tmp/.vnc/passwd"
  mkdir -p /tmp/.vnc
  OLD_UMASK="$(umask)"
  umask 077
  printf '%s\n' "$VNC_PASSWORD" | "$VNC_PASSWD_CMD" -f > "$VNC_PASSWD_FILE"
  umask "$OLD_UMASK"
  XVNC_ARGS+=(-SecurityTypes VncAuth -PasswordFile "$VNC_PASSWD_FILE")
else
  XVNC_ARGS+=(-SecurityTypes None)
fi

"$XVNC_BIN" "${XVNC_ARGS[@]}" &
XVNC_PID=$!
sleep 1

ENABLE_VNC_VALUE="${ENABLE_VNC:-true}"
ENABLE_VNC_VALUE="$(echo "$ENABLE_VNC_VALUE" | tr '[:upper:]' '[:lower:]')"

if [[ "$ENABLE_VNC_VALUE" == "1" || "$ENABLE_VNC_VALUE" == "true" || "$ENABLE_VNC_VALUE" == "yes" ]]; then
  if command -v novnc_proxy >/dev/null 2>&1; then
    NOVNC_PROXY_BIN="novnc_proxy"
  elif [[ -x "/usr/share/novnc/utils/novnc_proxy" ]]; then
    NOVNC_PROXY_BIN="/usr/share/novnc/utils/novnc_proxy"
  else
    echo "ERROR: novnc_proxy is not installed or not in PATH." >&2
    exit 1
  fi

  echo "Starting noVNC on port ${NOVNC_PORT}..."
  "$NOVNC_PROXY_BIN" --listen "$NOVNC_PORT" --vnc "127.0.0.1:${VNC_PORT}" &
  NOVNC_PID=$!
else
  echo "VNC disabled (ENABLE_VNC=${ENABLE_VNC:-})"
  NOVNC_PID=""
fi

echo "Starting FastAPI on port ${APP_PORT}..."
python -m uvicorn app:app --host 0.0.0.0 --port "$APP_PORT" &
UVICORN_PID=$!

cleanup() {
  set +e
  for pid in "$UVICORN_PID" "$NOVNC_PID" "$XVNC_PID"; do
    if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
}

trap cleanup EXIT INT TERM
WAIT_PIDS=("$UVICORN_PID" "$XVNC_PID")
if [[ -n "${NOVNC_PID:-}" ]]; then
  WAIT_PIDS+=("$NOVNC_PID")
fi

wait -n "${WAIT_PIDS[@]}"
