See https://google.github.io/adk-docs/streaming/custom-streaming

## Install

1. Build audio watermark package:

```bash
git clone https://github.com/swesterfeld/audiowmark.git
cd audiowmark
docker build -t audiowmark .
```

## Launch

Use venv. (Does not run with uv).

```bash
python -m venv .venv

# Activate (each new terminal)
source .venv/bin/activate
```

## Watermarks

Secret messages

- "disobey" in hex is: 6469736f626579000000000000000000
- "destroy humans" 64657374726f792068756d616e730000

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