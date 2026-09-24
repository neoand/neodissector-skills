---
name: protocol-reverse-engineering
description: Network protocol reverse engineering for security research, interoperability, and debugging. Covers Wireshark 4.6.8 (ago 2026), mitmproxy 12.2.3 (mai 2026), Scapy 2.6.x, CyberChef (GCHQ), binary protocol analysis, encryption identification, TLS fingerprinting (JA3/JA3S/JA4), and WA ecosystem tooling (wa-fetcher, wa-export, biscuit). 2025-2026 toolchain.
disable-model-invocation: true
risk: unknown
source: community
date_added: '2026-09-22'
---

# Protocol Reverse Engineering — Modern Toolchain (2025-2026)

Capturing, analyzing, and documenting network protocols for authorized security research, interoperability, debugging, and vulnerability investigation. Stack: Wireshark 4.6.8, mitmproxy 12.2.3, Scapy 2.6.x, CyberChef, tshark, mitmdump, Boofuzz, plus WA ecosystem tooling (`wa-fetcher`/`wa-export`/`biscuit`).

## Use this skill when

- Capturing traffic from a desktop, IoT, mobile, or web client and decoding the wire protocol
- Reverse engineering closed/proprietary binary protocols (game servers, IoT devices, custom RPC, WA Web bundles)
- Identifying TLS fingerprinting (JA3/JA3S/JA4) or comparing client implementations against expected behavior
- Decrypting TLS with `SSLKEYLOGFILE` from a browser under test
- Decoding Protobuf, gRPC, HTTP/2, HTTP/3 (QUIC), WebSocket frames
- Building custom Wireshark Lua dissectors or mitmproxy addons for a proprietary protocol
- Fuzzing a custom TCP/UDP service with Boofuzz, AFL++, or radamsa
- Extracting and deobfuscating JavaScript bundles from web apps (WA, Discord, Telegram Web, custom SaaS)
- Bypassing anti-bot detection (Cloudflare, PerimeterX, DataDome, Fingerprint Pro) for authorized testing

## Do not use this skill when

- The task is purely static binary analysis of a single executable (use `reverse-engineer` or `binary-analysis-patterns` skills)
- The target is mobile-only and you need app instrumentation (use `mobile-re`)
- You are intercepting your own infrastructure in production without change-control / authorization
- The task is about decrypting user traffic without explicit authorization (illegal in most jurisdictions — Lei Carolina Dieckmann, GDPR, CFAA, etc.)
- You need firmware RE specifically (use `firmware-analyst`)

## Modern toolchain overview (Sep 2026)

| Tool | Version | Best for | Notes |
|---|---|---|---|
| Wireshark | 4.6.8 (ago 2026) | GUI inspection, Lua dissectors | 4.4.18 LTS in parallel; AI-assisted vulnerability report trend mentioned in 4.6.7+ release notes |
| tshark | bundled with Wireshark | CLI capture, field extraction, JSON export | `-G fields`, `-T fields`, `-T json`, `-T ek` |
| tcpdump | 4.99.x | Lightweight capture, BPF syntax | Works on macOS/Linux, no GUI dependency |
| mitmproxy | 12.2.3 (mai 2026) | Interactive HTTP/HTTPS MITM | `--mode transparent`, addons in Python, web socket API |
| mitmdump | bundled with mitmproxy | Non-interactive capture (`-w file.flow`) | Same addon API as mitmproxy |
| Scapy | 2.6.x | Packet crafting, pcap manipulation, fuzzing primitives | `rdpcap`, `sr()`, `Ether()/TCP()/Raw` |
| CyberChef | 10.x (GCHQ) | Encoding/encoding/decoding recipes | Web app + CLI; 400+ operations including protobuf, JSONPath, regex |
| Boofuzz | 0.4.x | Network protocol fuzzing | Successor to Sulley; session-based, structured fuzzing |
| AFL++ | 4.x | Coverage-guided fuzzing with QEMU mode | Best for binary targets with minimal harness |
| radamsa | 0.7.x | Generative mutator for inputs | Pairs with AFL++/Boofuzz for corpus generation |
| `wa-fetcher` | npm `@vinikjkkj/wa-fetcher` | Discover WhatsApp Web bundle URLs | `discoverBundleUrls()`; URL-only mode supported |
| `wa-export` | npm | Export WA bundles to disk | `wa-export urls.json files --workers 50 --flat` |
| `biscuit` | npm | WA Web crypto token reverse | Used by WA-Extractor / wa-crypto-tools community |
| `webcrack` | GitHub | Webpack chunk extraction | Pulls modules from a bundle; pairs with `synchrony` |
| `synchrony` | npm | WA Web (legacy) deobfuscation | Useful for older WA Web `<= 2.2412` builds |
| `restringer` | npm | JS deobfuscation (string + control flow) | Handles Webpack-obfuscated code |
| `unminify` | npm + `webcrack` pipeline | JS unminification + beautify | Use `--config` for source map rewriting |
| `puppeteer-extra` + `stealth` | npm | Anti-detect browser automation | Plug-and-play stealth plugins for puppeteer/playwright |

## Capture workflows

### Wireshark GUI

```bash
# Open capture directly
wireshark -i en0 -k -f "port 443"

# Load pcap + filter on open
wireshark capture.pcap -Y "http2 && ip.addr==1.2.3.4"

# Set TLS keylog file (Preferences > Protocols > TLS)
# Or via menu: Edit > Preferences > Protocols > TLS
# (Pre)-Master-Secret log filename: /tmp/keys.log
```

### tshark (CLI Wireshark)

```bash
# Capture to file with ring buffer (rotate every 100MB, keep 10 files)
tshark -i eth0 -b filesize:100000 -b files:10 -w capture.pcap

# Live capture with display filter
tshark -i eth0 -Y "tcp.port==443" -w https.pcap

# Read pcap and extract specific fields as JSON
tshark -r capture.pcap -Y "http.request" \
    -T json \
    -e frame.time_epoch \
    -e ip.src -e ip.dst \
    -e http.request.method -e http.request.uri \
    -e http.host \
    > requests.json

# Export HTTP objects (from GUI: File > Export Objects > HTTP)
# tshark has no direct export-objects; use the GUI for that.

# Protocol hierarchy stats
tshark -r capture.pcap -q -z io,phs

# TCP conversations
tshark -r capture.pcap -q -z conv,tcp

# Endpoints
tshark -r capture.pcap -q -z endpoints,ip

# Follow TCP stream (stdout)
tshark -r capture.pcap -q -z follow,tcp,ascii,0
```

### tcpdump

```bash
# Basic pcap capture
tcpdump -i eth0 -w capture.pcap

# BPF filter
tcpdump -i eth0 'tcp port 443 and host 1.2.3.4' -w capture.pcap

# Full packet capture (no truncation)
tcpdump -i eth0 -s 0 -w capture.pcap

# Verbose + hex dump to stdout
tcpdump -i eth0 -X 'port 80'

# Read pcap + filter
tcpdump -r capture.pcap 'tcp[13] & 0x17 == 2'  # SYN packets only
```

### mitmproxy / mitmdump

```bash
# Interactive MITM (HTTP/HTTPS via proxy at 8080)
mitmproxy --mode regular --listen-port 8080

# Transparent mode (Linux only — iptables redirect 80/443 to 8080)
mitmproxy --mode transparent -p 8080

# SSL insecure (skip cert verification on upstream)
mitmproxy --mode transparent --ssl-insecure

# Non-interactive dump (production-friendly)
mitmdump -w traffic.flow
mitmdump -nr traffic.flow  # replay

# Pipe through addon
mitmdump -s ./my_addon.py --set option1=value1

# WebSocket / HTTP/2 by default in 12.x (no extra flag needed)
```

### mitmproxy addon skeleton

```python
# my_addon.py — drop into mitmdump with `-s my_addon.py`
from mitmproxy import http, ctx
from mitmproxy.addonmanager import Loader

class WAInterceptor:
    def __init__(self):
        self.count = 0

    def load(self, loader: Loader):
        loader.add_option("myoption", str, "default", "doc")

    def request(self, flow: http.HTTPFlow) -> None:
        self.count += 1
        if b"web.whatsapp.com" in flow.request.host.encode():
            ctx.log.info(f"[WA] {flow.request.method} {flow.request.pretty_url}")

    def response(self, flow: http.HTTPFlow) -> None:
        if flow.response and b"application/json" in flow.response.headers.get("content-type", ""):
            ctx.log.info(f"[JSON] {flow.response.status_code} {len(flow.response.raw_content)} bytes")

addons = [WAInterceptor()]
```

## Protocol identification

### Magic-byte signatures (heuristic detection)

```
HTTP/1.x     - "HTTP/1." or "GET " / "POST " at start
HTTP/2       - "PRI * HTTP/2.0" preface (cleartext h2c) or ALPN h2 in TLS
HTTP/3       - QUIC long header (1st byte MSB=1), version 0x00000003
TLS 1.2/1.3  - 0x16 0x03 (record layer) + version 0x0303 / 0x0304
DNS          - UDP/53 with header format
SSH          - "SSH-2.0" banner
FTP          - "220 " response, "USER " command
SMTP         - "220 " banner, "EHLO"
MySQL        - 0x00 length prefix, protocol version 0x0a
PostgreSQL   - 0x00 0x00 0x00 startup length (8-byte header)
Redis        - "*" RESP array prefix
MongoDB      - BSON documents with 4-byte little-endian length prefix
MQTT         - fixed header: 0x10/0x20/0x30/0x40 etc.
gRPC         - HTTP/2 with `content-type: application/grpc(+proto)`
WebSocket    - HTTP/1.1 Upgrade + "Sec-WebSocket-Key" header
WA WebSocket - WA-specific path `wss://wss.web.whatsapp.com/ws/...`
Protobuf     - varint-delimited; first byte often 0x08 (field 1, varint) or 0x12 (field 2, length-delimited)
QUIC         - long header flags form; connection ID encoded
```

### Header pattern template

```
+--------+--------+--------+--------+
| Magic / signature (4 bytes)       |
+--------+--------+--------+--------+
| Version       | Type / Opcode     |
+--------+--------+--------+--------+
| Length        | Flags             |
+--------+--------+--------+--------+
| Sequence / Session ID (8 bytes)   |
+--------+--------+--------+--------+
| Payload...                        |
+--------+--------+--------+--------+
```

## Binary protocol analysis

### Common patterns

```c
// Length-prefixed message
struct Message {
    uint32_t length;      // Total message length (big-endian or little-endian)
    uint16_t msg_type;    // Message type identifier
    uint8_t  flags;       // Optional flags
    uint8_t  reserved;    // Padding/alignment
    uint8_t  payload[length - 8];
};

// Type-Length-Value (TLV)
struct TLV {
    uint8_t  type;        // Field type discriminator
    uint16_t length;      // Field length (big-endian)
    uint8_t  value[];     // Field data
};

// Fixed header + variable payload
struct Packet {
    uint8_t  magic[4];    // "ABCD" / "PROT"
    uint32_t version;
    uint32_t payload_len;
    uint32_t checksum;    // CRC32 or similar
    uint8_t  payload[payload_len];
};

// WA Web noise protocol variant (simplified):
// - "WA[..]" 6-byte header (4 magic + 2 version/flags)
// - 3-byte length prefix (big-endian) for inner frame
// - varint-delimited Protobuf frames inside
```

### Python parser for length-prefixed framing

```python
import struct
from dataclasses import dataclass

@dataclass
class MessageHeader:
    magic: bytes
    version: int
    msg_type: int
    length: int

    @classmethod
    def from_bytes(cls, data: bytes):
        # Adjust unpack codes to match observed byte order.
        magic, version, msg_type, length = struct.unpack(">4sHHI", data[:12])
        return cls(magic, version, msg_type, length)

def parse_messages(data: bytes):
    offset = 0
    messages = []
    while offset + 12 <= len(data):
        header = MessageHeader.from_bytes(data[offset:])
        payload = data[offset+12:offset+12+header.length]
        messages.append((header, payload))
        offset += 12 + header.length
    return messages

def parse_tlv(data: bytes):
    fields, offset = [], 0
    while offset + 3 <= len(data):
        field_type = data[offset]
        length = struct.unpack(">H", data[offset+1:offset+3])[0]
        value = data[offset+3:offset+3+length]
        fields.append((field_type, value))
        offset += 3 + length
    return fields
```

### Hexdump utility

```python
def hexdump(data: bytes, width: int = 16) -> str:
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i:i+width]
        hex_part = ' '.join(f'{b:02x}' for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        lines.append(f'{i:08x}  {hex_part:<{width*3}}  {ascii_part}')
    return '\n'.join(lines)

# Example output:
# 00000000  48 54 54 50 2f 31 2e 31  20 32 30 30 20 4f 4b 0d  HTTP/1.1 200 OK.
```

## Encryption analysis

### Shannon entropy per buffer

```python
import math
from collections import Counter

def shannon_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counter = Counter(data)
    n = len(data)
    return -sum((c / n) * math.log2(c / n) for c in counter.values())

# Thresholds (per-byte, on bytes [0..255]):
# < 6.0   -> plaintext / structured data
# 6.0-7.5 -> possibly compressed (gzip, zstd, brotli)
# > 7.5   -> likely encrypted or random (AES, ChaCha20)
```

### Indicators of encryption / compression

- **Uniform high entropy** across the payload.
- **No obvious structure** (no printable ASCII runs, no magic bytes inside).
- **Length multiple of block size**: 16 for AES-CBC, 8 for DES, 16/32 for ChaCha20 (rare to be exactly aligned except by chance).
- **Possible IV at start**: 16 bytes for AES-CBC, 12 bytes for AES-GCM (often marked as `IV:` in captures).
- **No compression dictionary** — pure random bytes are visually indistinguishable from compressed data; check entropy per byte, not per message.
- **High-bit bytes dominant** (>= 0x80 in >70% of bytes).

### Mitmproxy `tls` addon to dump decrypted traffic

mitmproxy's `--ssl-insecure` mode plus the `tls` builtin addon writes server-side certificates to `/tmp/mitmproxy-ca-cert.pem`. Set `SSLKEYLOGFILE=/tmp/keys.log` on the *target* process to capture pre-master secrets (Chrome, Firefox, curl with `--sslkeylogfile`).

## TLS fingerprinting (JA3 / JA3S / JA4)

### JA3 / JA3S — legacy, still in many detection stacks

```bash
# Client JA3 (TLS ClientHello fingerprint)
tshark -r capture.pcap -Y "tls.handshake.type == 1" \
    -T fields -e tls.handshake.ja3

# Server JA3S (ServerHello fingerprint)
tshark -r capture.pcap -Y "tls.handshake.type == 2" \
    -T fields -e tls.handshake.ja3s
```

JA3 = `MD5(Grease,Version,Ciphers,Extensions,EllipticCurves,ECPointFormats)` — concatenated with commas. FingerprintDB at ja3er.com.

### JA4 — modern (FoxIO, replaces JA3 in 2025-2026 tooling)

JA4 family has three components:

- **JA4** (client fingerprint) — `t` (TLS) + `13` (version 1.3) + `d`/`i` (handshake type) + 2-char cipher count + 4-char ext count + 12-char hash of sorted ciphers + 12-char hash of sorted extensions + 1-char ALPN hash.
- **JA4S** (server fingerprint) — same structure, server side.
- **JA4X** (X.509 certificate fingerprint) — separate format.

Example JA4: `t13d1516h2_8daaf6152771_b0da82a5f1e4` — for a Chrome-like client.

```bash
# Wireshark 4.6+ exposes JA4 via tls.handshake.ja4
tshark -r capture.pcap -Y "tls.handshake.type == 1" \
    -T fields -e tls.handshake.ja4
```

### ClientHello reconstruction for fingerprint testing

```python
# Generate synthetic ClientHello bytes for fingerprint testing.
# Use Python's ssl module to build a TLS 1.3 ClientHello programmatically
# and feed to the server, then capture its JA3/JA4.
import ssl, socket

ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
ctx.set_ciphers("ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20")

with socket.create_connection(("example.com", 443)) as sock:
    with ctx.wrap_socket(sock, server_hostname="example.com") as ssock:
        ssock.send(b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")
        # JA3/JA4 of THIS handshake is observable from the server side.
```

## HTTP/1.1, HTTP/2, HTTP/3 (QUIC) analysis

### HTTP/1.1 capture and decode

```bash
tshark -r capture.pcap -Y "http.request" -T fields \
    -e ip.src -e ip.dst -e http.request.method -e http.request.uri -e http.host
```

### HTTP/2 (h2)

- Negotiated via ALPN in TLS — `application_protocol_h2`.
- Streams multiplexed; use `http2.streamid` filter to isolate.
- `tshark -r capture.pcap -Y "http2.headers.frame" -T fields -e http2.header.value` dumps `:authority`, `:path`, `:method`.

### gRPC over HTTP/2

- `content-type: application/grpc` or `application/grpc+proto`.
- 5-byte length-prefixed messages: `[compressed-flag:1][length:4][protobuf-payload:N]`.
- tshark filter: `http2.headers.content-type contains "application/grpc"`.

### HTTP/3 (QUIC)

- Identified by QUIC version 1 (0x00000001) in long header.
- Wireshark 4.6 has native HTTP/3 dissector — `http3.headers` field.
- Decryption requires QUIC Initial keys; obtainable by `SSLKEYLOGFILE` for Chromium-based clients.

```bash
tshark -r capture.pcap -Y "quic && http3" -V | head -200
```

## WebSocket analysis

```bash
# Filter WS frames
tshark -r capture.pcap -Y "websocket" \
    -T fields -e websocket.payload.text -e websocket.payload.len

# Reassemble text frames in order
tshark -r capture.pcap -Y "websocket.payload.text" \
    -T fields -e websocket.payload.text | head -50
```

mitmproxy treats WebSocket as a first-class protocol — frames appear under the same flow as the upgrade handshake.

## Protocol Buffers reverse engineering

### Field structure

```protobuf
message Frame {
    uint64 seq_no = 1;        // wire tag 0x08
    string from = 2;          // wire tag 0x12
    bytes payload = 10;       // wire tag 0x52
    repeated SubMessage subs = 15; // wire tag 0x7a
}
```

Wire format: `field_number << 3 | wire_type` followed by value:

- `wire_type=0` (varint) → variable-length int
- `wire_type=2` (length-delimited) → `[len:varint][bytes:N]` (most messages, strings, embedded messages)
- `wire_type=5` (32-bit) → 4 bytes

### Decode without schema

```python
# pip install protobuf blackboxprotobuf
import blackboxprotobuf
import sys

data = sys.stdin.buffer.read()
message, typedef = blackboxprotobuf.decode_message(data)
print(message)
print(typedef)
```

### CyberChef "Protobuf Decode" operation

CyberChef 10.x ships a **Protobuf Decode** recipe that takes a `.proto` definition (or schema-less heuristic) and decodes raw bytes. Pair with **From Hex** / **From Base64** upstream.

### `.proto` reconstruction tips

1. Capture multiple messages of the same type and diff them — fields that vary are candidates for typed values.
3. Look for **field 1 = varint 0x08** (often seq_no or version) and **field 2 = length-delimited 0x12** (often device ID or UUID).
4. Length-delimited fields with consistent length and high entropy are likely **embedded signed/encrypted blobs** (Prologue keys, Signal Protocol ratchet state).
5. WA Web uses **ProtoBuf** for the outer envelope around **Noise Protocol** frames — `.proto` schema partially documented at `wpp-connect/wa-js` repo.

## Custom Wireshark Lua dissector

```lua
-- custom_protocol.lua — load with: wireshark -X lua_script:custom_protocol.lua
local proto = Proto("myproto", "My Custom Protocol")

local f_magic   = ProtoField.string("myproto.magic", "Magic")
local f_version = ProtoField.uint16("myproto.version", "Version", base.HEX)
local f_type    = ProtoField.uint16("myproto.type", "Type", base.HEX)
local f_length  = ProtoField.uint32("myproto.length", "Length")
local f_payload = ProtoField.bytes("myproto.payload", "Payload")

proto.fields = { f_magic, f_version, f_type, f_length, f_payload }

local msg_types = {
    [0x0001] = "HELLO",
    [0x0002] = "HELLO_ACK",
    [0x0010] = "DATA",
    [0x00FF] = "CLOSE",
}

function proto.dissector(buffer, pinfo, tree)
    if buffer:len() < 12 then return end
    pinfo.cols.protocol = "MYPROTO"

    local subtree = tree:add(proto, buffer())

    subtree:add(f_magic,   buffer(0, 4))
    subtree:add(f_version, buffer(4, 2))

    local msg_type = buffer(6, 2):uint()
    local t_node   = subtree:add(f_type, buffer(6, 2))
    t_node:append_text(" (" .. (msg_types[msg_type] or "Unknown") .. ")")

    local length = buffer(8, 4):uint()
    subtree:add(f_length, buffer(8, 4))

    if length > 0 and buffer:len() >= 12 + length then
        subtree:add(f_payload, buffer(12, length))
    end
end

-- Register for a custom TCP port
local tcp_table = DissectorTable.get("tcp.port")
tcp_table:add(38888, proto)
```

Place dissectors in `~/.local/lib/wireshark/plugins/` (Linux) or `~/Library/Application Support/org.wireshark.Wireshark/plugins/` (macOS) for auto-load.

## mitmproxy addons + scripts

### WebSocket frame logging

```python
# ws_logger.py — `mitmdump -s ws_logger.py`
from mitmproxy import ctx

def websocket_message(flow):
    msg = flow.websocket.messages[-1]
    direction = "C→S" if msg.from_client else "S→C"
    if msg.content_type == "binary":
        ctx.log.info(f"[WS {direction}] {len(msg.content)} bytes: {msg.content[:32].hex()}...")
    else:
        ctx.log.info(f"[WS {direction}] {msg.content[:200]}")
```

### Addon state + options

```python
from mitmproxy import ctx, http
from mitmproxy.addonmanager import Loader

class State:
    def __init__(self):
        self.seen = 0

    def load(self, loader: Loader):
        loader.add_option(name="match_host", typespec=str, default="",
                          help="only log requests whose host contains this substring")

    def request(self, flow: http.HTTPFlow):
        if ctx.options.match_host and ctx.options.match_host not in flow.request.host:
            return
        self.seen += 1
        ctx.log.info(f"[{self.seen}] {flow.request.method} {flow.request.pretty_url}")

addons = [State()]
```

Run: `mitmdump -s state.py --set match_host=web.whatsapp.com`.

## CyberChef operations (the essentials)

CyberChef is the GCHQ-maintained web app at https://gchq.github.io/CyberChef/. Local install: `npm install -g cyberchef` and run `cyberchef` (CLI version `cyberchef-cli` available).

### Common RE recipes

| Task | Operations chained |
|---|---|
| Hex dump to ASCII | `From Hex` → `Render Text` |
| URL-decode + hex | `From URL-safe` → `From Hex` → `Render Text` |
| Base64 → gzip → Protobuf | `From Base64` → `Gunzip` → `Protobuf Decode` |
| Extract URLs from pcap strings | `Extract URLs` (regex pre-built) |
| JSONPath filter | `JSON Beautify` → `JSONPath query` (e.g., `$.messages[*].text`) |
| XOR brute force | `XOR Brute Force` (single byte, with entropy threshold filter) |
| Decrypt AES-CBC | `AES Decrypt` (key + IV in hex) |
| JWT decode | `JWT Decode` (no signature verification) |
| Hex → protobuf | `From Hex` → `Protobuf Decode` |

### CLI usage (`cyberchef-cli`)

```bash
# Decode base64 + hex
echo "SGVsbG8=" | cyberchef-cli -r "From Base64"
# "Hello"

# Chain
echo "1f8b08000000..." | cyberchef-cli -r "From Hex, Gunzip, From Base64"
```

## WA ecosystem (web / bundles RE)

### wa-diff repo (local)

Anderson has `/Users/andersongoliveira/wa-diff/` — a versioning + diffing tool for WA Web JS bundles. Stack:

- **`@vinikjkkj/wa-fetcher`** — `discoverBundleUrls()` enumerates every `.js` bundle URL referenced by `web.whatsapp.com`. URL-only mode skips the heavy fetch.
- **`wa-export`** — npm tool that downloads all bundles from a `urls.json` and saves them to `files/` with `--flat`.
- **Prettier** — formatter applied post-export.

```bash
cd /Users/andersongoliveira/wa-diff
npm install
npm run fetch     # fetches urls.json + downloads all bundles
```

Output: `files/` populated with ~19k+ bundle files. Daily cron + GitHub Actions publish diff releases.

### Protobuf schema for WA Web outer envelope

Schema files live at `wpp-connect/wa-js` and `sigsep/open-suspect` (community-maintained). Key types: `Message`, `HandshakeMessage`, `NoiseCertificate`, `AppVersion`. WA Web wraps Noise Protocol frames inside these protobuf messages.

### biscuit (community)

`@vinikjkkj/biscuit` (or `wa-crypto-tools/biscuit`) handles the WA token signing / decryption. Used to derive the pre-key bundle and to decrypt the encrypted media blobs (AES-GCM with key wrapped in protobuf).

### Common WA Web RE pipeline

1. **Capture HTTP/2 + WebSocket traffic** with mitmproxy (`mitmdump -w wa.flow --ssl-insecure`).
2. **Export WA bundles** with `wa-diff` daily.
3. **Diff bundles across versions** to spot protocol changes (`git diff` on `files/`).
4. **Extract Webpack modules** with `webcrack` to get class-level structure.
5. **Deobfuscate strings** with `restringer`.
6. **Recover protobufs** with CyberChef + `blackboxprotobuf`.
7. **Reconstruct signal-protocol handshake** from captured Noise frames + `biscuit`.

## JS bundle analysis (general web RE)

### unminify pipeline

```bash
# webcrack unpacks webpack/parcel bundles and emits module tree
npx webcrack input.bundle.js -o unpacked/

# Prettier the output
npx prettier --write unpacked/

# restringer cleans obfuscated string concat / control flow
npx restringer unpacked/main.js -o unpacked/main.restringer.js
```

### synchrony (WA legacy only)

`synchrony` was the canonical WA Web bundle deobfuscator until ~v2.2412. Still useful for archived bundles. ⚠️ Verify before use — repo activity sparse since 2024.

```bash
# ⚠️ Verify before use
git clone https://github.com/nicpottier/synchrony.git
cd synchrony && npm install
node bin/synchrony ../wa-diff/files/main.js -o deob.js
```

### Static analysis of unpacked modules

- **Identify entry points**: grep for `new App(` or webpack runtime bootstrap.
- **Find API endpoints**: regex `https?://[a-z0-9.-]+/(api|v[0-9]+)/[a-z/]+` on unpacked sources.
- **Find WS connections**: `new WebSocket(` or `socket = new WS(`.
- **Find protobuf classes**: grep for `.encode()`, `.decode()`, `Reader|Writer` imports.
- **Crypto usage**: grep for `crypto.subtle.`, `SubtleCrypto`, `import crypto from`.

## Anti-bot detection analysis

### puppeteer-extra + stealth

```javascript
// puppeteer-extra hides navigator.webdriver, plugins, languages, canvas fingerprint.
const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');

puppeteer.use(StealthPlugin());

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  await page.goto('https://example-protected.example/');
  // Mitmproxy can capture the WS frames that puppeteer-extra triggers.
})();
```

### Detection surfaces (reversed by Cloudflare / PerimeterX / DataDome / FP Pro)

- `navigator.webdriver`, `navigator.plugins.length`, `navigator.languages`
- Chrome DevTools Protocol signals (`Runtime.evaluate` artifacts)
- Canvas/WebGL/Audio fingerprinting via `HTMLCanvasElement.toDataURL()`
- Mouse movement entropy (TP bots have too-perfect straight lines)
- TLS fingerprint (JA3/JA4) — see §TLS fingerprinting
- HTTP/2 SETTINGS frame ordering (akamai-http2)

### For analysis: identify the fingerprint layer

1. **TLS layer**: capture the ClientHello and compute JA3/JA4 (see §TLS fingerprinting). If `ja3er.com` flags the fingerprint, that's a bot signal.
2. **JS layer**: open DevTools, look for `window._cf_chl_opt`, `cf-chl-bypass`, `x-cf-chl`, or `PPToken` cookies.
3. **Behavioral**: bots that don't move the mouse / scroll are easy to flag — visible in `requestAnimationFrame` and `pointermove` event density.

## Fuzzing

### Boofuzz — protocol-aware network fuzzer

```python
from boofuzz import Session, Target, Request, TCPSocketConnection

def main():
    session = Session(target=Target(connection=TCPSocketConnection("127.0.0.1", 38888)))

    req = Request("HELLO")
    req.add_static(b"\x50\x52\x4f\x54")    # "PROT" magic
    req.add_word(1, name="version", fuzzable=True)
    req.add_word(0x0001, name="type", fuzzable=False)
    req.add_dword(8, name="length")         # auto-computed if using sizer

    session.add_request(req)
    session.fuzz()

if __name__ == "__main__":
    main()
```

Boofuzz requires the target to **not crash the fuzzer host** — run against an isolated VM or a process-restart harness (e.g., a fork server).

### AFL++ with QEMU mode (binary-only target)

```bash
# Build AFL++ with QEMU
apt install afl++

# Fuzz an arbitrary binary (no source) via QEMU instrumentation
afl-fuzz -Q -i seeds/ -o out/ -- ./target_binary @@
```

`@@` = placeholder for input file. AFL++ expects files; for network targets use `afl-network-harness` (⚠️ Verify before use).

### radamsa as input mutator for Boofuzz / AFL

```bash
# Generate 1000 mutations of a seed file
radamsa seed.bin -n 1000 -o out/%n.bin
```

## Best practices — workflow

1. **Capture multiple sessions, different scenarios.** Repeat for auth flow, error flow, idle state, version mismatch.
3. **Identify message boundaries.** Look for length prefixes, magic bytes, idle gaps (TCP only).
4. **Map structure.** Fixed header → variable payload → trailer (often checksum/MAC).
5. **Identify fields.** Diff messages; identify bytes that vary.
6. **Document format.** Spec template in `resources/implementation-playbook.md`.
7. **Validate understanding.** Build a parser+generator in Python; round-trip real captures.
9. **Test edge cases.** Fuzz with Boofuzz or AFL++; observe server behavior.

### Common protocol signals to look for

- **Magic numbers/signatures** at message start (`0xAB`, `"ABCD"`, length-prefixed zero).
- **Version fields** for backward compatibility.
- **Length fields** before variable payloads — usually big-endian uint16/uint32.
- **Type/opcode fields** for message identification.
- **Sequence numbers** for ordering / replay protection.
- **Checksums/CRCs** for integrity (CRC32, MD5, custom polynomial).
- **Timestamps** for timing — watch for `time(NULL)` (epoch seconds) vs custom epoch.
- **Session/connection IDs** (UUID v4, custom 16-byte, noise public key).

## Ethics and authorization

Protocol RE can be legal or criminal depending on context:

- **Authorized**: your own services, bug bounty scope with explicit permission, CTF challenges, academic research with IRB approval, interoperability work for documented standards.
- **Illegal**: intercepting traffic on networks you don't own, circumventing copy protection (DMCA § 1201), extracting keys from proprietary products without permission, evading rate limits for unauthorized access.
- **Always**: document authorization scope before starting; respect rate limits even when authorized; never share captured private user data.

## Resources

- `resources/implementation-playbook.md` — detailed patterns: Wireshark filters, tcpdump, mitmproxy, Scapy, hex dump, TLS analysis, protocol spec template, Boofuzz skeleton, replay+modify. **Keep this file in sync with the SKILL.md** when adding new examples.
- `/Users/andersongoliveira/wa-diff/` — local WA Web bundle versioning + diffing tool (Anderson's repo).
- `reverse-engineer` skill — binary RE of executables.
- `malware-analyst` skill — combining network capture with static analysis.
- `firmware-analyst` skill — for embedded protocol RE (MQTT, CoAP, custom serial-to-IP).

## Integração com system-dissector

Esta skill é um **instrumento** consumido por `system-dissector` durante as fases 2-4:

- **Quando invocar**: Phase 2 (deep-dive) ou Phase 4 (extract) do `system-dissector`
- **Tipo de alvo**: source | binary | mobile | firmware | protocol
- **Output esperado**: wiki page ou extract component
- **Templates relacionados**: `templates/deep-dive-{architecture,module}.md.template`, `templates/extract-{components,patterns}.md.template`

**Contrato**:
- Path canônico: `dissects/<sistema>/<fase>/<arquivo>.md`
- Use `evidence: verified|estimated` em todo `file:line`
- Rubrica C1-C6 quando aplicável (consulte `extract-components.md.template`)
- Companion: `neodoo-integrate` para port-plan (Phase 5)

## References

- Wireshark 4.6.8 release notes (Wireshark Foundation, ago 2026)
- Wireshark 4.4.18 LTS release notes (ago 2026)
- mitmproxy 12.2.3 release notes (mai 2026)
- Scapy 2.6.x documentation (secdev/scapy GitHub) — ⚠️ Verify before use, exact patch version not confirmed
- CyberChef (GCHQ) — https://github.com/gchq/CyberChef
- Boofuzz documentation — https://github.com/jtpereyda/boofuzz
- AFL++ documentation — https://github.com/AFLplusplus/AFLplusplus
- FoxIO JA4 specification — https://github.com/FoxIO-LLC/ja4
- `@vinikjkkj/wa-fetcher` npm package — https://www.npmjs.com/package/@vinikjkkj/wa-fetcher
- Wireshark release notes 4.6.7 / 4.6.8 — note on "recent trend in AI-assisted vulnerability reports"
- Hex-Rays article "LLMs Have Reshaped How We Think About Decompilation and Collaboration" (30 jul 2026)