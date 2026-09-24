---
name: reverse-engineer
description: Expert reverse engineer for IDA Pro 9.4, Ghidra 12.1.4, Binary Ninja 6.0 Krypton, Rizin 0.9, Frida 17.18, and modern RE toolchains. Covers static/dynamic analysis, decompilation, instrumentation, scripting (IDAPython, Ghidra scripting, BN Python API, r2pipe), and 2025-2026 AI-assisted workflows.
disable-model-invocation: true
risk: unknown
source: community
date_added: '2026-09-22'
---

# Reverse Engineering — Modern Toolchain (2025-2026)

Reverse engineering of binaries for authorized security research, CTF, malware analysis, interoperability, and vulnerability research. Targets: IDA Pro 9.4, Ghidra 12.1.4, Binary Ninja 6.0 Krypton, Rizin 0.9.1, Frida 17.18.

## Use this skill when

- Analyzing compiled binaries (PE, ELF, Mach-O, WASM, Dyld Shared Cache)
- Decompiling and deobfuscating native code (C, C++, Rust, Go, Swift, Objective-C)
- Building analysis scripts in IDAPython, Ghidra scripting (Java + Jython + PyGhidra), BN Python API, or r2pipe
- Instrumenting running processes with Frida 17.x
- Combining static + dynamic analysis (Ghidra-Debugger, IDA Debugger, BN debugger)
- Driving MCP-enabled tools from LLMs (Binary Ninja 6.0 MCP, IDA-MCP, GhidraMCP)

## Do not use this skill when

- The task is for unauthorized reverse engineering of proprietary software (piracy, license bypass)
- The user wants to develop malware, evade AV for malicious purposes, or extract cryptographic keys without authorization
- The target is source code (use code review/variant-analysis skills instead)
- The task is firmware RE only (use `firmware-analyst`)
- The task is mobile RE only (use `mobile-re`)

## Modern toolchain overview (Sep 2026)

| Tool | Version | Best for | Notes |
|---|---|---|---|
| IDA Pro | 9.4 (jul 2026) | Commercial gold standard, IDA Teams on Git | Hexagon QDSP6, MCore, TriCore, RISC-V RP2350, Swift calling convention, Pathfinder, Jump Anywhere, idalib for Home |
| IDA Free | 9.0/9.1 | x86/x86-64/arm/arm64 only, no decompiler | Evaluation only |
| Ghidra | 12.1.4 (set 2026) | Free, full decompiler, NSA maintained | Bitfields in Decompiler, Objective-C 2 rewritten, debuginfod, Hexagon module, Jython as extension, JDK 21 required |
| Binary Ninja | 6.0 "Krypton" (set 2026) | Modern Python-first platform, 19 archs | MCP server oficial incluso na Free, Binary Similarity, 2.16× faster, AArch64 decompiler no Free tier |
| Rizin | 0.9.1 (jun 2026) | OSS, scripting-friendly, Cutter 2.5 GUI | ESIL deprecated → RzIL, Marks subsystem, JOP/COP gadgets, statistical histograms |
| Cutter | 2.5.0 (jun 2026) | GUI for Rizin | debuginfod in analysis, register profile editor, Qt 6.11 |
| radare2 | 5.x (lagging) | Legacy Rizin-era tooling | Rizin is the active fork; r2 is in maintenance mode |
| Frida | 17.18.0 (set 2026) | Dynamic instrumentation, scripting | Stalker v2, TypeScript compiler, LanguageServer (LSP), Barebone (Linux `.ko`, macOS `.kext`), Btf API |
| Capstone | 6.0.0-Alpha11 (set 2026) / 5.0.9 stable | Disassembly framework | CVE-2026-55893/55894 fixed, RISC-V aliasing control, AArch64 NZCV |
| Unicorn 2 | 2.1.4 (set 2025) | CPU emulation (QEMU-backed) | LoongArch + S390x, ABI3 wheels, Rust `unicorn-engine-sys` standalone |
| Keystone | 0.9.x | Assembler framework | Use with Capstone/Unicorn for assembly-emulation loops |
| pwntools | 4.13+ | CTF, exploit dev, ROP gadget chains | Tied to pwndbg/gef workflows |
| angr | rolling (no formal releases) | Symbolic execution | `pip install angr`; components: angr, claripy, pyvex, ailment, angr-management |
| Triton | status uncertain (verify before use) | Symbolic + dynamic taint | Original repo changed ownership; verify via triton-library.github.io |

## Disassembler / Decompiler selection matrix

- **Need Hexagon QDSP6 / TriCore / MCore / Swift / RISC-V RP2350 (hazard3)** → IDA Pro 9.4 (best support) or Ghidra 12.1.4
- **Need MCP first-party for LLM agent** → Binary Ninja 6.0 (only one with official MCP server)
- **Free + full decompiler + 19 architectures** → Binary Ninja 6.0 Free tier (AArch64 decompiler incluso)
- **Free + extensive community + custom analyzers** → Ghidra 12.1.4
- **Fast scripted workflows, embedded-friendly** → Rizin 0.9.1 + r2pipe
- **Source-level decompilation of Objective-C/C++/Swift** → IDA Pro 9.4 (best) or Ghidra 12.1.4
- **Binary diffing, similarity search** → Binary Ninja 6.0 Ultimate (Google BinDiff + WARP providers) or Diaphora (free)
- **Headless automation without GUI** → IDA Pro `idalib` (Home/Pro 9.4+) or Ghidra headless (`analyzeHeadless`)

## Workflow phases

### Phase 1: Triage (15 min)
```bash
# File identification
file sample.bin
checksec --file=sample.bin   # RELRO, NX, PIE, stack canary
readelf -h sample.bin        # ELF header
otool -h sample.bin          # Mach-O header

# Hash + first strings
sha256sum sample.bin
strings -a -n 6 sample.bin | head -100

# Packer / compiler detection
diec sample.bin              # Detect It Easy (DB updated weekly)
floss sample.bin             # FLOSS 3.1.1 obfuscated strings
capa sample.bin --tag=misc   # CAPA 9.4 capability mapping
```

### Phase 2: Static analysis (1-4h)
1. **Load** in chosen tool. For Ghidra 12.1.4, pick architecture manually if not auto-detected; for IDA 9.4, let auto-analysis finish.
2. **Find entry points**: `main`, `WinMain`, `DllMain`, exported symbols, constructors in `.init_array`.
3. **Map program structure**: identify library code vs user code by symbol provenance (PDB, DWARF, `.symtab`).
4. **Rename + type aggressively**: every argument type improves decompilation downstream. Use IDA's `Y` (set type), BN's `y` (set type), Ghidra's `T`/`Ctrl+L`.
5. **Cross-reference**: data ↔ code, imports ↔ PLT/GOT, strings ↔ xrefs.
6. **Recover data structures**: declare structs (IDA `T`, BN right-click → Structure, Ghidra `Edit → Data Type Manager`).

### Phase 3: Dynamic analysis (when static is insufficient)
1. **Instrumentation**: prefer Frida 17 for live processes, BN debugger or GDB+pwndbg for native debugging.
2. **Breakpoints** at: API boundaries, comparison functions, crypto constants (`0x67452301` = MD5 init, `0x6a09e667` = SHA-256 init), file/network I/O.
3. **Trace execution**: Stalker (Frida) for code coverage; Intel Pin / DynamoRIO for instruction traces.
4. **Input mutation**: feed mutated inputs (AFL++, radamsa) and observe behavior changes.
5. **Memory snapshots**: take process dumps with `gcore`, Volatility 3 offline analysis for process internals.

### Phase 4: Documentation (ongoing)
1. Function signatures + purpose
2. Data structures (with field types and offsets)
3. Algorithms (pseudocode, control flow diagrams)
4. Findings (vulnerabilities, behaviors, credentials, IOCs)

## IDA Pro 9.4 — key features

### Modern workflow features
- **Pathfinder** (`Shift-F9`): trace call paths between two points in the database — essential for understanding deep call chains.
- **Jump Anywhere** (`g`): type-ahead unified search across names, expressions, function comments, live disassembly, pseudocode, hex previews, jump history.
- **Xrefs Graph redesign**: graph manager with informative node headers; integrates with Pathfinder output.
- **Unified Scripts window**: replaces Execute Script + Snippets.
- **IDB deep links**: share exact positions in a DB via URL.
- **Teams on Git**: backend Git (GitHub/GitLab/Bitbucket/self-hosted), no server required.
- **idalib for Home**: headless automation now included in Home tier with `-B` batch switch.

### Decompiler improvements (9.x)
- Edit type directly in pseudocode with `e` (was: switch to disasm, change, return).
- Inline casts, collapsed blocks (chevrons), invert if/else.
- Argument hints, automatic strings in strings list.
- memcpy fold into assignments.
- IEEE 754 → `fabs`/negation, `true/false`/`nullptr`.
- **Swift calling convention** keywords: `__swiftself`, `__swiftasync`, `__swiftthrows`, `__swiftcall`. Stripped binaries now recover these automatically.
- **Rust analysis**: rustc version + crate list, panic locations typed, dedicated Rust calling convention.
- **Go analysis**: pclntab improved discovery, buildinfo Go 1.18+, struct types cleaner.

### Apple-specific (9.4)
- **Dyld Shared Cache reimaginado**: supports iOS 27, Objective-C method prototypes recovered, libobjcMsgSend stubs auto-resolved.

### New processors (9.4)
- **Hexagon QDSP6** (Qualcomm DSP) with MBN boot-image loader (SBL/XBL).
- **MCore (CSky V1)**: stack-pointer tracking, auto stack-vars.
- **TriCore**: complete type system, register finder, switch tables, relocation support.
- **ARM SVE2 + SME** full disassembly, more modern console SDK switch patterns.
- **RISC-V**: RP2350 (hazard3), Zcmp/Zcmt/Zclsd compressed instructions, Soteria support.

### IDAPython 9.4
- Detects uv / Anaconda / Homebrew installs; warns on Python interpreter mismatch.
- Exposes database indexer for fast queries.

```python
# IDAPython: rename all functions based on strings (Binja/IDA pattern)
import idautils, idc, idaapi

def auto_rename():
    for s in idautils.Strings():
        if not s: continue
        name = str(s)
        if not (4 <= len(name) <= 40): continue
        if any(c < ' ' or c > '~' for c in name): continue
        for xref in idautils.XrefsTo(s.ea):
            func = idaapi.get_func(xref.frm)
            if func and idc.get_func_name(func.start_ea).startswith("sub_"):
                idc.set_name(func.start_ea, "fn_" + name[:32].replace(" ", "_"), idc.SN_FORCE)

auto_rename()
```

## Ghidra 12.1.4 — key features

### Decompiler
- **Bitfields in Decompiler**: read/write bitfield component names directly, no `>>/&` boilerplate. Multi-bitfield optimizations broken into individual components.
- **Microsoft Demangler** new output options: suppress UDT tags, anonymous namespace as `_anon_XXXX`.

### Objective-C 2 (rewritten)
- New `Objective-C Type Metadata Analyzer` + `Objective-C Message Analyzer` replace legacy analyzers.
- `_objc_msgSend$` stubs resolved to actual method.
- AARCH64 call-fixups reduce ARC artifacts.

### debuginfod (12.1+)
- Download DWARF from HTTP(S) debug info servers via `Edit → DWARF External Debug Config`.
- Cache in `$HOME/.cache/debuginfod_client`.

### Architecture expansion
- **Hexagon processor module** introduced with Sleigh crossbuild (pcode for parallel architectures).

### Python / Java
- **Jython Extension** now installed as an extension (not bundled). Install via `File → Install Extensions`.
- Python 3.9–3.14 supported.

### Server
- **RMI Serialization Filter** tightened for Ghidra Server and client.
- **PKI Authentication fix** in 12.1.4: vulnerability where attacker could authenticate as another user without private key (mitigated by TLS + filter combination).

### Project compatibility
- Binary 12.1+ incompatible with earlier versions; server 12.1 accepts clients ≥ 11.3.2.

### Requirements
- **JDK 21 minimum**.
- Python 3.9–3.14.

### Supported architectures (cumulative)
x86, x86-64, ARM/AARCH64, MIPS, PowerPC, RISC-V, AVR, MSP430, SuperH, V850, M68k, M6800/HD6301/HD6309, SPARC, PA-RISC, Z80, 8051, 6502, JVM, WebAssembly, Dalvik, Hexagon (QDSP6).

### Ghidra scripting (Java + PyGhidra)

```java
// Java: Fix function signatures + create structs
Function func = getFunctionAt(toAddr(0x401000));
func.setReturnType(IntegerDataType.dataType, SourceType.USER_DEFINED);

StructureDataType struct = new StructureDataType("MyStruct", 0);
struct.add(IntegerDataType.dataType, "field_a", null);
struct.add(PointerDataType.dataType, "next", null);
createData(toAddr(0x601000), struct);
```

```python
# PyGhidra: find dangerous function calls
from ghidra.program.model.listing import Function

for func in currentProgram.getFunctionManager().getFunctions(True):
    if func.getName() in ["strcpy", "sprintf", "gets", "scanf"]:
        refs = getReferencesTo(func.getEntryPoint())
        for r in refs:
            print(f"[!] {func.getName()} call at {r.getFromAddress()}")
```

```python
# PyGhidra + CAPA 9.4: capabilities via PyGhidra plugin
# Install CAPA plugin via PyPI; see https://github.com/mandiant/capa
```

## Binary Ninja 6.0 Krypton — key features

### MCP server oficial (free tier included)
Binary Ninja 6.0 is the **only commercial disassembler with a first-party MCP server**, included even in the free tier.

- GUI variant: built-in HTTP server at `http://127.0.0.1:24642/mcp`.
- Headless variant: `binaryninja_mcp` standalone (stdio), included with Commercial/Ultimate on macOS/Linux. Windows: GUI-only (filesystem locking).
- Auth: `ui.mcp.token` bearer.
- Exposed operations: open files/databases, BinaryView selection, drive analysis, triage summary, segments/sections/symbols/imports/exports/relocations/data vars/strings, raw memory, function inspection (metadata, disasm, Pseudo C, ILs), rename, types, data vars.

Configuration examples for Claude Desktop / Cursor / VS Code / Codex are documented in BN 6.0 release notes.

### Binary Similarity (Ultimate only)
- Pluggable framework with 2 built-in providers: **Google BinDiff** (structural) and **WARP** (exact matches).
- API in Python/C++/Rust.
- Plugins can register custom providers/resolvers.

### Performance
- Up to **2.16× faster**, **55% less memory** on real-world binaries:
  - `vmlinux 6.14`: 761s → 352s, 17.29GB → 12.25GB
  - `chrome`: 1186s → 584s, 43.85GB → 32.82GB

### Architecture coverage
- **19 first-party architectures**.
- **TMS320C6x** (Texas Instruments DSP) added in 6.0.

### IL stack improvements
- **HLIL_STRUCT_INITIALIZE** + **Type Fragments**: structures preserve type even when broken into registers.
- **Calling Convention Refactor**: structures as parameters/returns (Go, Pascal calling conventions new). Delphinja plugin benefits immediately.
- **Multiple Global Pointers**: required for TriCore (4 global registers).

### Free tier improvements (6.0)
- AArch64 (armv8) decompiler included.
- MCP server included.
- **Linux ARM64 build**.
- Python API still disabled in Free; no plugins.

### Python
- Python 3.13 bundled across platforms.
- Minimum Python 3.10 still supported.

### UI/UX
- Extension Manager replaces Plugin Manager; versioning, dependency auto-detection, snippets shipped default.
- New User Wizard with Ghidra-like / IDA-like presets.
- Debugger Memory Map sidebar, TTD (Time Travel Debugging) prev/next register write navigation, refined LLDB.

### BN Python API

```python
# Binary Ninja Python API (5.x+ → 6.0)
from binaryninja import *

bv = BinaryView.open("sample.bin")
bv.update_analysis_and_wait()

# Find function by name
target = None
for func in bv.functions:
    if func.name == "main":
        target = func
        break

# Iterate IL instructions
if target:
    for il_instr in target.hlil.instructions:
        print(il_instr)
        # Set variable types from HLIL
        for var in target.hlil.variables:
            print(f"  {var.name}: {var.type}")
```

```python
# BN: Apply struct across database
from binaryninja import types

struct_type = types.Structure()
struct_type.append("field_a", types.IntegerType.int(4))
struct_type.append("next", types.PointerType(types.NamedTypeReference("MyStruct"), 4))

# Type library
tl = bv.new_type_library("my_types")
tl.add_named_type("MyStruct", struct_type)
```

## Rizin 0.9.x — key features

### RzArch unified plugin model
- `RzAsm` removed from public API (compatibility layer).
- ESIL isolated in its own namespace, **ESIL deprecated** → **RzIL** is the successor.

### New architectures
- TMS320C54x, cBPF (classic BPF), SuperH-3, M680X (RS08, HCS12X), MCS96 (ISA 8096/80C196/80C296 with analysis), Infineon C166, MIL-STD-1750, DEC VAX (rewritten).

### Capstone 6 integration
- RISC-V rewritten via Capstone, HPPA-PA-RISC migrated, M68k ColdFire supported.

### RzIL uplifting
- Scalar x86 SSE/SSE2 floating-point, SPARC lifter complete, TMS320C5x series fully lifted.
- VM can halt on exceptions.

### Statistical visualizations
- χ², index of coincidence, min-entropy, serial correlation (with horizontal/vertical histograms and interactive minimap).

### Marks subsystem (`m` family)
- Add/remove/list named marks, color, comment, navigate.

### Type system
- `tk`/`tkl`/`tks` for typeclass, `tr` rename global, `tdf` define type from pf, `ica`/`ics` for classes.

### Analysis
- `afvc`/`avgc` value constraints, `avD` C++ devirtualization.

### ROP/JOP/COP gadgets
- `/J`, `/C`, `/R` — renames config vars from `rop.*` to `gadget.*`.

### Debugger heap namespacing
- `dmhg*` (glibc), `dmhw*` (Windows), `dmhj*` (jemalloc 5.3.0).

### Binary formats
- STABS debug, Luac 5.0–5.5 + LuaJIT 2.1, CaRT, Amiga hunk, MDT, PEF.
- NE rewritten; bootimg v1–v4.
- ELF coredump for LoongArch, s390x, RISC-V, PPC64, HPPA, DEC Alpha.
- Python 3.14 bytecode.

### Performance
- Hashtable-based `RzGraph`, faster primitives, ROP/JOP/COP gadget cache.

### Project format
- Bumped from 19 → 25 (migration path provided).

### r2pipe example

```python
import r2pipe

r = r2pipe.open("sample.bin")
r.cmd("aaa")          # full analysis
r.cmd("afl")          # list functions
r.cmd("pdf @ sym.main")  # disassemble main
r.quit()
```

## Frida 17.x — modern instrumentation

### Architecture: agent + frontend
- **Agent** runs inside target process (via injection).
- **Frontend** (Python/Node/Swift/.NET/Java) drives agent over IPC.
- **Barebone agents** (17.17+ Linux, 17.18+ macOS): no-gadget variant for kernel-mode and minimal environments.

### Barebone agents (17.18.0)
- Linux kernel module: `frida-agent.ko` loaded via `/dev/frida` (length-prefixed GVariant messages).
- macOS: `.kext` loaded natively via `/dev/frida` (previously required GDB/QEMU/JTAG).
- Windows NT (x86 + x64) and Windows 9x also have barebone variants.

### New APIs in 17.x

```javascript
// 17.12+ Native CFG analysis
const cfg = Process.findModuleByName("target").enumerateRanges("r-x");
const block = new ControlFlowGraph(ptr("0x401000"));
const blocks = block.getBlocks();
```

```javascript
// 17.18+ Btf API (Linux kernel symbols)
if (Btf.available) {
    const struct = Btf.getStruct("task_struct");
    const credOffset = struct.getField("pid");
}
```

```javascript
// 17.14+ Script interruption
const script = await Script.load("agent.js", scriptData);
setTimeout(() => script.interrupt(), 5000);  // Ctrl+C equivalent
```

```javascript
// 17.18+ LanguageServer (LSP) — for LLM IDE integration
const ls = new Frida.LanguageServer();
ls.start();  // Exposes agent processes to LSP clients (Claude/Cursor/VS Code)
```

### Stalker v2 (improved in 17.x)
- AVX-512 save/restore in Stalker.
- CodeSegment revival for modern iOS.
- `Gum.Memory.patch_code` safe mode.

### TypeScript Compiler
- `Frida.Compiler` upgraded to TypeScript 7.0.
- Write agent scripts in TS, compile to JS for the agent.

### Bindings
- Python, Swift, .NET, Java, Node, Qt bindings auto-generated from GIR (17.16+).
- Python async via `frida.aio`.

### Spawn-gating fail-safe (17.16+)
- Watchdog disables itself if it hangs (avoids runaway gate conditions).

### Common patterns

```javascript
// Hook function and inspect args
Interceptor.attach(Module.findExportByName(null, "open"), {
    onEnter(args) {
        console.log(`open(${args[0].readUtf8String()}, ${args[1].toInt32()})`);
    }
});

// Replace function with native code
const replacement = new NativeCallback((pathPtr, flags) => {
    console.log(`intercepted open: ${pathPtr.readUtf8String()}`);
    return -1;  // block
}, 'int', ['pointer', 'int']);

Interceptor.replace(Module.findExportByName(null, "open"), replacement);

// Stalker code coverage
Interceptor.attach(Module.findExportByName(null, "main"), {
    onEnter(args) {
        Stalker.follow({
            events: { call: true, ret: true, exec: false },
            onCallSummary(summary) {
                console.log(JSON.stringify(summary, null, 2));
            }
        });
    },
    onLeave() { Stalker.unfollow(); Stalker.flush(); }
});
```

## Calling conventions quick reference

| Arch | Args | Return | Caller-saved | Callee-saved |
|---|---|---|---|---|
| x86 cdecl | stack (caller cleans) | eax | eax, ecx, edx | ebx, esi, edi, ebp |
| x86 stdcall | stack (callee cleans) | eax | eax, ecx, edx | ebx, esi, edi, ebp |
| x64 Windows | rcx, rdx, r8, r9, then stack | rax | rax, rcx, rdx, r8-r11 | rbx, rbp, rdi, rsi, r12-r15 |
| x64 SysV (Linux/macOS) | rdi, rsi, rdx, rcx, r8, r9, then stack | rax (+rdx 128-bit) | rax, rcx, rdx, rdi, rsi, r8-r11 | rbx, rbp, r12-r15 |
| AArch64 | x0-x7, then stack | x0 (+x1 128-bit) | x0-x18 | x19-x28, x29 (fp), x30 (lr) |
| ARM32 | r0-r3, then stack | r0 (+r1 64-bit) | r0-r3, r12 | r4-r11, r13 (sp), r14 (lr) |
| RISC-V LP64D | a0-a7, then stack | a0 (+a1 128-bit) | t0-t6, a0-a7 | s0-s11, ra, sp, gp, tp |
| **Swift x86-64** | rdi, rsi, rdx, rcx, r8, r9 + **x14 (self)**, **x15 (async)** | rax | rax, rcx, rdx, r8-r11 | rbx, rbp, r12-r15 |
| **Swift arm64** | x0-x7 + **x20 (self)** | x0 | x0-x18 | x19-x28, x29 (fp), x30 (lr) |
| **Rust x86-64** | rdi, rsi, rdx, rcx, r8, r9 | rax | rax, rcx, rdx, r8-r11 | rbx, rbp, r12-r15 |

## Code pattern recognition

### Common patterns

```c
// String obfuscation (XOR)
for (int i = 0; i < len; i++) str[i] ^= key;

// Anti-debugging
if (IsDebuggerPresent()) exit(1);

// API hashing (malware)
hash = 0;
while (*name) hash = ror(hash, 13) + *name++;

// Stack string construction
char s[8];
*(DWORD*)s = 0x6C6C6548;   // "Hell"
*(DWORD*)(s+4) = 0x6F;      // "o\0"

// Swift decompilation marker (Swift calling conv)
// `self` in x14/x20, throws marker in x15/etc.

// Rust string (always starts with length prefix in std::string)
// mov rdi, ptr; mov rsi, len; mov rdx, cap
```

### Optimizer artifacts to watch for
- **Tail call optimization**: `jmp` instead of `call + ret` (no new stack frame).
- **Inlined functions**: function body expanded inline at call sites.
- **Dead code**: unreachable from optimization.
- **RIP-relative addressing**: position-independent code.
- **Constant folding**: arithmetic collapsed at compile time (e.g., `x*3` → `lea eax, [rax + rax*2]`).
- **Vectorization**: SSE/AVX loops replacing scalar code.

## AI-assisted RE workflows (2025-2026 trend)

See dedicated `ai-assisted-re` skill for full coverage. Highlights:

- **Binary Ninja 6.0 MCP**: configure Claude Desktop / Cursor / VS Code / Codex to drive BN via MCP.
- **IDA-MCP / GhidraMCP**: community MCP servers for IDA Pro and Ghidra (verify current repos — many have moved).
- **Frida.LanguageServer**: LSP-based integration of LLMs with Frida agent.
- **Variable naming + summaries**: LLMs excel at renaming variables and writing function summaries from decompiled code.
- **Anti-LLM evasion**: CAPA 9.4 includes `terminate-anthropic-session-via-magic-strings` rule (anti-LLM malware pattern).

## Security & ethics

### Authorized use only
- Security research with explicit written authorization
- CTF competitions and educational challenges
- Malware analysis for defensive purposes
- Vulnerability disclosure through responsible channels
- Understanding software for interoperability
- Authorized penetration testing within defined scope

### Never assist with
- Unauthorized access to systems or binaries you don't own/operate
- Creating malware for malicious purposes
- Bypassing software licensing illegitimately
- Intellectual property theft
- Industrial espionage
- Attacking devices without permission

## Example: end-to-end RE of a closed-source library

**User**: "I have a closed-source DLL with authentication; I need to understand the protocol for integration testing."

**Response** (authorized analysis within bug bounty scope):

1. **Triage**:
   ```bash
   file library.dll
   checksec --file=library.dll
   diec library.dll  # identify packer/compiler
   ```

2. **Static — load in IDA Pro 9.4** (best for Windows DLL):
   ```python
   # IDAPython: list exported functions
   import idautils, idc
   for ea, name in idautils.Names():
       if name.startswith("auth_"):
           print(f"{hex(ea)}: {name}")
   ```

3. **Find auth function**: rename based on string xrefs to "auth", "login", "token".

4. **Type recovery**: in IDA's pseudocode, set parameter types via `Y`. Watch for `__swiftcall` on Swift binaries, `__swiftself` keyword.

5. **Dynamic — hook with Frida 17**:
   ```javascript
   Interceptor.attach(Module.findExportByName("library.dll", "auth_login"), {
       onEnter(args) {
           console.log(`auth_login(username=${args[0].readUtf8String()}, password=${args[1].readUtf8String()})`);
       },
       onLeave(retval) {
           console.log(`auth_login → ${retval.toInt32()}`);
       }
   });
   ```

6. **Documentation**:
   ```c
   // auth_login(const char *username, const char *password) -> int
   // Returns 0 on success, -1 on bad credentials, -2 on rate-limit
   // Side effects: writes session token to TLS storage at offset 0x18
   ```

7. **Report**: function signatures, data structures, security considerations, exploitation paths (if any).

## Resources

- `resources/implementation-playbook.md` for detailed examples per tool
- `binary-ninja` skill — BN-specific workflows
- `ai-assisted-re` skill — MCP + LLM integration
- `anti-reversing-techniques` skill — protection bypasses
- `protocol-reverse-engineering` skill — network protocol RE
- `binary-analysis-patterns` skill — disassembly pattern library
- `firmware-analyst` skill — IoT/embedded RE
- `mobile-re` skill — Android/iOS RE
- `memory-forensics` skill — memory dump analysis
- `malware-analyst` skill — malware analysis workflow

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

- IDA Pro 9.4 release notes (Hex-Rays, jul 2026)
- Ghidra 12.1.4 release notes (NSA, set 2026)
- Binary Ninja 6.0 Krypton release notes (Vector 35, set 2026)
- Rizin 0.9.1 + Cutter 2.5.0 release notes (jun 2026)
- Frida 17.18.0 release notes (set 2026)
- Capstone 6.0.0-Alpha11 + 5.0.9 stable
- Unicorn 2.1.4 (set 2025)
- Hex-Rays article: "LLMs Have Reshaped How We Think About Decompilation and Collaboration" (30 jul 2026)