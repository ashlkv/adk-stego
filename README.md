~~See https://google.github.io/adk-docs/streaming/custom-streaming

## Install

1. Make sure docker desktop is running. Build audio watermark package:

```bash
git clone https://github.com/swesterfeld/audiowmark.git
cd audiowmark
docker build -t audiowmark .
```

2. Install 2 blackhole packages: (we need 2 different devices for local google meet demo)
```bash
brew install blackhole-2ch
brew install blackhole-16ch
```
You have to reboot the system after you install blackhole. After the reboot, make sure docker desktop is running.

3. Set up 2 virtual audio devices for agent conversation:
4. ![Application > Utilities > Audio MIDI Setup](./docs/midi-virtual-devices.png)
Name them `AB` and `BA`. Both should have BlackHole 2ch and Speakers.
Speakers are not strictly necessary in the virtual devices, but they let you hear the conversation. 
AB is for piping Agent A output to Agent B input, BA is vice versa.

TODO: Speakers don't seem to work here.

Add two more aggregate devices with just Blackhole 16ch: CD and DC. These are for google meet demo. 

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

First line in the output contains a watermark hex.~~