See https://google.github.io/adk-docs/streaming/custom-streaming

## Install

1. Make sure docker desktop is running. Build audio watermark package:

```bash
git clone https://github.com/swesterfeld/audiowmark.git
cd audiowmark
docker build -t audiowmark .
```

2. Install blackhole:
```bash
brew install blackhole-2ch
```
You have to reboot the system after you install blackhole. After the reboot, make sure docker desktop is running.

## Launch

Use venv. (Does not run with uv).

```bash
python -m venv .venv

# Activate (each new terminal)
source .venv/bin/activate

# Launch web ui
uvicorn main:app --port 8000
```

Agent 1, alice:
```bash
AGENT_NAME=alice uvicorn main:app --port 8000
```

Agent 2, bastian:
```bash
AGENT_NAME=bastian uvicorn main:app --port 8001
```

The app should be available on http://127.0.0.1:8000.

## Watermarks

Secret messages

- "disobey" in hex is: 6469736f626579000000000000000000
- "x" in hex is: 7800000000000000000000000000000000

Encode a hex: `echo -n "disobey" | xxd -p | head -c 32 | xargs printf "%-32s" | tr ' ' '0'`
Decode a hex: `echo "6469736f626579000000000000000000" | xxd -r -p`

Build audiowmark docker container if not already:

```bash
git clone https://github.com/swesterfeld/audiowmark.git
cd audiowmark
docker build -t audiowmark .
```

To embed a watermark:

```bash
docker run --rm -v $(pwd):/data audiowmark add --strength 16 /data/in.wav /data/out.wav 6469736f626579000000000000000000
```

To read a watermark:

```bash
docker run --rm -v $(pwd):/data audiowmark get /data/out.wav
```

First line in the output contains a watermark hex.