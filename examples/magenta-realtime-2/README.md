# Magenta RealTime 2 — Live AI Music Instruments

Four interactive instruments built on Google DeepMind's [Magenta RealTime 2](https://magenta.withgoogle.com/magenta-realtime-2), unified in a single web UI.

## Prerequisites

- Apple Silicon Mac (M1+)
- Python 3.12

## Setup

```bash
uv sync
mrt models init
mrt models download
```

## Run

```bash
uv run python server.py
# Open http://localhost:8000
```

## Instruments

| Mode | Description |
|------|-------------|
| **Synth** | Prompt-driven neural synthesizer. Set a timbre prompt and play with pitch/velocity. |
| **Jam** | Interactive call-and-response with piano keyboard. Click keys, AI responds. |
| **Gesture** | Play music by moving your cursor on a 2D pad. X = pitch, Y = velocity. |
| **Looper** | Build layered loop arrangements layer by layer. |

## Options

```bash
uv run python server.py 8000  # Custom port
```
