#!/usr/bin/env bash
# One-command live observation: the observer UI + a cognition run with the
# zero-authority ledger stream, started and stopped together.
#
#   ./scripts/live.sh start                  # 20 agents, full day, metis
#   ./scripts/live.sh start --fake --tick-seconds 0.05   # offline demo pace
#   ./scripts/live.sh start --seed 9 --ticks 25920 --agents maren_alder,piet_alder
#   ./scripts/live.sh status
#   ./scripts/live.sh stop                   # stops runner + UI (run artifacts stay)
#
# The run writes to runs/live_<timestamp>/ (ledger, completions, memories on
# completion). Stopping mid-run keeps everything written so far; --pg-dsn
# streams to Postgres too if you pass it.
set -euo pipefail
cd "$(dirname "$0")/.."

LIVE_DIR=.live
WS_PORT="${WS_PORT:-8010}"
UI_PORT="${UI_PORT:-5173}"

alive() { [ -f "$LIVE_DIR/$1.pid" ] && kill -0 "$(cat "$LIVE_DIR/$1.pid")" 2>/dev/null; }

cmd_start() {
    local ticks=8640 seed=7 agents="" profile="metis" pg_dsn="" tick_seconds="" fake=0
    while [ $# -gt 0 ]; do
        case "$1" in
            --fake) fake=1; shift ;;
            --seed) seed="$2"; shift 2 ;;
            --ticks) ticks="$2"; shift 2 ;;
            --agents) agents="$2"; shift 2 ;;
            --profile) profile="$2"; shift 2 ;;
            --pg-dsn) pg_dsn="$2"; shift 2 ;;
            --tick-seconds) tick_seconds="$2"; shift 2 ;;
            *) echo "unknown flag: $1" >&2; exit 2 ;;
        esac
    done

    if alive runner || alive ui; then
        echo "already running — ./scripts/live.sh status (or stop first)" >&2
        exit 1
    fi
    mkdir -p "$LIVE_DIR"

    # observer UI (exec so the pidfile pid IS vite, not a wrapper)
    ( cd observer && exec ./node_modules/.bin/vite --port "$UI_PORT" \
        > "../$LIVE_DIR/ui.log" 2>&1 ) &
    echo $! > "$LIVE_DIR/ui.pid"

    # live run
    local out="runs/live_$(date +%Y%m%d_%H%M%S)"
    local cmd=(uv run python -m cognition.runner
               --ticks "$ticks" --seed "$seed" --out-dir "$out"
               --serve-ws "$WS_PORT")
    [ "$fake" -eq 0 ] && cmd+=(--profile "$profile")
    [ -n "$agents" ] && cmd+=(--agents "$agents")
    [ -n "$pg_dsn" ] && cmd+=(--pg-dsn "$pg_dsn")
    [ -n "$tick_seconds" ] && cmd+=(--tick-seconds "$tick_seconds")
    "${cmd[@]}" > "$LIVE_DIR/runner.log" 2>&1 &
    echo $! > "$LIVE_DIR/runner.pid"
    echo "$out" > "$LIVE_DIR/out_dir"

    local url="http://localhost:$UI_PORT/?ws=ws://localhost:$WS_PORT/ws/ledger"
    echo "runner  -> $out  (seed $seed, $ticks ticks$( [ "$fake" -eq 1 ] && echo ', FAKE MODEL — non-conforming' || echo ", profile $profile" ))"
    echo "observe -> $url"
    if command -v open >/dev/null; then
        sleep 2 && open "$url"
    fi
}

cmd_status() {
    for name in runner ui; do
        if alive "$name"; then
            echo "$name: running (pid $(cat "$LIVE_DIR/$name.pid"))"
        else
            echo "$name: not running"
        fi
    done
    [ -f "$LIVE_DIR/out_dir" ] && echo "run dir: $(cat "$LIVE_DIR/out_dir")"
    [ -f "$LIVE_DIR/runner.log" ] && { echo "--- runner.log tail ---"; tail -3 "$LIVE_DIR/runner.log"; }
}

cmd_stop() {
    for name in runner ui; do
        if alive "$name"; then
            kill "$(cat "$LIVE_DIR/$name.pid")" 2>/dev/null || true
            echo "stopped $name"
        fi
        rm -f "$LIVE_DIR/$name.pid"
    done
    echo "run artifacts kept$( [ -f "$LIVE_DIR/out_dir" ] && echo " in $(cat "$LIVE_DIR/out_dir")" )"
}

case "${1:-}" in
    start) shift; cmd_start "$@" ;;
    status) cmd_status ;;
    stop) cmd_stop ;;
    *) echo "usage: $0 start [--fake] [--seed N] [--ticks N] [--agents a,b] [--profile P] [--pg-dsn DSN] [--tick-seconds S] | status | stop" >&2
       exit 2 ;;
esac
