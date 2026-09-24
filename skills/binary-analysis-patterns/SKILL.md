---
name: binary-analysis-patterns
description: "Comprehensive patterns and techniques for analyzing compiled binaries across x86-64, ARM/AArch64 (incl. SVE2/SME), RISC-V (incl. RP2350/hazard3), Hexagon QDSP6, MCore (CSky V1), TriCore. Covers Swift/Rust calling conventions, control flow, data structures, modern decompilation patterns, and 2025-2026 processor extensions."
disable-model-invocation: true
risk: unknown
source: community
date_added: "2026-09-22"
---

# Binary Analysis Patterns

Comprehensive patterns and techniques for analyzing compiled binaries, understanding assembly code, and reconstructing program logic. Covers x86-64, ARM/AArch64 (including SVE2/SME), RISC-V (including Raspberry Pi RP2350 / hazard3), Hexagon QDSP6, MCore (CSky V1), TriCore, plus modern language calling conventions (Swift, Rust) and decompiler patterns.

## TL;DR

| Architecture | Tool support (best first) | Key markers |
|---|---|---|
| x86-64 | IDA Pro 9.4 / Ghidra 12.1.4 / Binary Ninja 6.0 / Rizin 0.9.1 | `mov rdi, ...` SysV / `mov rcx, ...` MS x64 |
| ARM/AArch64 | IDA Pro 9.4 / Ghidra 12.1.4 / BN 6.0 (decompiler in Free) | `stp x29, x30, [sp, #-16]!`; SVE2 uses `z0-z31`, `p0-p15` |
| ARM32 | IDA Pro 9.4 / Ghidra 12.1.4 / BN 6.0 | `push {fp, lr}` |
| RISC-V | IDA Pro 9.4 (RP2350/hazard3) / Ghidra 12.1.4 / Rizin (via Capstone 6) | `addi sp, sp, -16`; `sd ra, 8(sp)`; x0 = zero |
| Hexagon QDSP6 | **IDA Pro 9.4** / Ghidra 12.1.4 (new in 12.1) | packet syntax `{ insn1 ; insn2 :endloop0 }`; 32 GPRs R0–R31; `.L` hardware loop |
| MCore (CSky V1) | **IDA Pro 9.4** | GPR0=SP, GPR1=FP, GPR15=LR; 32 GPRs |
| TriCore | **IDA Pro 9.4** / Binary Ninja 6.0 (4 global pointers) | A0–A15 (address), D0–D15 (data), PSW |
| Apple Silicon (Mach-O) | IDA Pro 9.4 (Dyld Shared Cache rewrite) | dyld stubs `_objc_msgSend$`; Swift `__swiftself` in x14/x20 |

## Use this skill when

- Analyzing compiled binaries on x86-64, ARM/AArch64 (including SVE2/SME), RISC-V (including RP2350/hazard3)
- Reverse engineering Hexagon QDSP6 (Qualcomm DSP), MCore/CSky, TriCore, or other 2025-2026 era processors
- Recovering Swift, Rust, or modern language calling conventions from native binaries
- Understanding VLIW packet-based execution (Hexagon), scalable vector registers (SVE2/SME), or 4-register file architectures (TriCore)
- Decompiling Mac/iOS Mach-O binaries with dyld stubs and ObjC/Swift interop
- Identifying calling conventions across compilers and architectures
- Working with control flow, data structures, or arithmetic patterns in any of the above

## Do not use this skill when

- The task is about network protocols (use `protocol-reverse-engineering`)
- The task is about malware behavior analysis (use `malware-analyst`)
- The task is about firmware extraction/ unpacking (use `firmware-analyst`)
- The task is about AI/LLM-assisted workflows (use `ai-assisted-re`)
- The task is about dynamic instrumentation (use `reverse-engineer` skill with Frida)

## Disassembly Fundamentals

### x86-64 Instruction Patterns

#### Function Prologue/Epilogue
```asm
; Standard prologue
push rbp           ; Save base pointer
mov rbp, rsp       ; Set up stack frame
sub rsp, 0x20      ; Allocate local variables

; Leaf function (no calls)
; May skip frame pointer setup
sub rsp, 0x18      ; Just allocate locals

; Standard epilogue
mov rsp, rbp       ; Restore stack pointer
pop rbp            ; Restore base pointer
ret

; Leave instruction (equivalent)
leave              ; mov rsp, rbp; pop rbp
ret
```

#### Calling Conventions

**System V AMD64 (Linux, macOS)**
```asm
; Arguments: RDI, RSI, RDX, RCX, R8, R9, then stack
; Return: RAX (and RDX for 128-bit)
; Caller-saved: RAX, RCX, RDX, RSI, RDI, R8-R11
; Callee-saved: RBX, RBP, R12-R15

; Example: func(a, b, c, d, e, f, g)
mov rdi, [a]       ; 1st arg
mov rsi, [b]       ; 2nd arg
mov rdx, [c]       ; 3rd arg
mov rcx, [d]       ; 4th arg
mov r8, [e]        ; 5th arg
mov r9, [f]        ; 6th arg
push [g]           ; 7th arg on stack
call func
```

**Microsoft x64 (Windows)**
```asm
; Arguments: RCX, RDX, R8, R9, then stack
; Shadow space: 32 bytes reserved on stack
; Return: RAX

; Example: func(a, b, c, d, e)
sub rsp, 0x28      ; Shadow space + alignment
mov rcx, [a]       ; 1st arg
mov rdx, [b]       ; 2nd arg
mov r8, [c]        ; 3rd arg
mov r9, [d]        ; 4th arg
mov [rsp+0x20], [e] ; 5th arg on stack
call func
add rsp, 0x28
```

### ARM/AArch64 Patterns

#### ARM64 (AArch64) Calling Convention
```asm
; Arguments: X0-X7
; Return: X0 (and X1 for 128-bit)
; Frame pointer: X29
; Link register: X30

; Function prologue
stp x29, x30, [sp, #-16]!  ; Save FP and LR
mov x29, sp                 ; Set frame pointer

; Function epilogue
ldp x29, x30, [sp], #16    ; Restore FP and LR
ret
```

#### ARM SVE2 — Scalable Vector Extension (v2)

SVE2 uses **variable-length** vector registers (128–2048 bits, implementation-defined). The Vector Length (VL) is queryable via `RDVL`. Tools may not display width explicitly — analyze per-instruction semantics.

```asm
; SVE2 register file
;   Z0–Z31: scalable vector registers (variable length)
;   P0–P15: predicate registers (one bit per vector lane)
;   FFR:    first-fault register (used for non-faulting loads)

; Load vector with predicate
ld1w   {z0.s}, p0/z, [x0]        ; Load 32-bit elements, predicated by p0
ld1h   {z1.h}, p1/z, [x1, #2, mul vl]  ; Load + indexed (gather)

; Predicate operations
ptrue   p0.s              ; Set all predicate bits true (32-bit element group)
whilelt p1.s, x0, x1      ; While x0 < x1, set predicate bits
ptest   p0, p1.b          ; Test predicate (sets condition flags)

; Arithmetic with predicates
add     z0.s, p0/m, z1.s, z2.s  ; z0 = z1.s + z2.s, predicated
fmla    z3.s, p0/m, z4.s, z5.s  ; Fused multiply-accumulate, predicated

; Storing back
st1w    {z0.s}, p0, [x2]  ; Store with active predicate (no fault suppression)

; First-fault (non-faulting) loads — FFR pattern
ldff1w  {z0.s}, p0/z, [x0]  ; First-faulting load, FFR tracks first fault
setffr                      ; Set FFR = all active
rdffr  p0.b                 ; Read FFR into predicate
```

#### ARM SME — Scalable Matrix Extension

```asm
; SME introduces ZA storage (a 2D scalable matrix in a dedicated register file)
; and PSTATE.SM (Streaming Mode) to enable matrix-tile operations.

; Enter Streaming Mode (required for most SME instructions)
smstart                    ; PSTATE.SM = 1

; Zero ZA tile
zero  {za}                 ; Zero entire ZA matrix

; Outer product: ZA tile[outer_row, outer_col] = sum_k ZA[..,k] * ZA[k,..]
; SME accumulates into ZA tiles indexed by row/col
fmopa  za0.s, p0/m, p1/m, z0.s, z1.s   ; FMA outer product into ZA0

; Read tile slice back to Z register
mova   z0.s, za0.s[row, #0]            ; Extract row slice

; Exit Streaming Mode
smstop                     ; PSTATE.SM = 0 (back to NEON/SVE mode)
```

SME is supported in **IDA Pro 9.4** and **Ghidra 12.1.4**. Note: SME + SVE2 can coexist (or be exclusive) depending on hardware; consult SIE for specific SoCs (Apple M3+ supports SME on select cores).

#### ARM32 Calling Convention
```asm
; Arguments: R0-R3, then stack
; Return: R0 (and R1 for 64-bit)
; Link register: LR (R14)

; Function prologue
push {fp, lr}
add fp, sp, #4

; Function epilogue
pop {fp, pc}    ; Return by popping PC
```

### RISC-V Patterns (RV32 / RV64)

#### Register file
```text
x0       = zero (hardwired 0; writes ignored)
x1       = ra (return address)
x2       = sp (stack pointer)
x3       = gp (global pointer; ABI-reserved)
x4       = tp (thread pointer)
x5-x7    = t0-t2 (temporary, caller-saved)
x8       = s0/fp (saved register / frame pointer)
x9       = s1 (saved register)
x10-x17  = a0-a7 (function arguments / return values)
x18-x27  = s2-s11 (saved registers, callee-saved)
x28-x31  = t3-t6 (temporaries, caller-saved)
```

#### RV64 standard calling convention
```asm
; Arguments: a0-a7 (x10-x17)
; Return: a0 (+a1 for 128-bit)
; Caller-saved: t0-t6, a0-a7, ra (in tail position)
; Callee-saved: s0-s11, sp

; Prologue
addi  sp, sp, -16      ; allocate frame
sd    ra, 8(sp)         ; save return address
sd    s0, 0(sp)         ; save frame pointer
addi  s0, sp, 16        ; set FP (s0) to top of frame

; Argument passing
mv    a0, t0            ; a0 = first arg
li    a1, 42            ; a2 = immediate
ld    a2, 0(s1)         ; a2 = load from struct

; Epilogue
ld    ra, 8(sp)
ld    s0, 0(sp)
addi  sp, sp, 16
ret                     ; pc = ra + 4
```

#### Compressed instructions (C extension + Zcmp/Zcmt/Zclsd)
```asm
; Common 16-bit forms (RVC)
c.mv   t0, s0           ; mv t0, s0 (compressed)
c.addi sp, -16          ; addi sp, sp, -16 (compressed addi)
c.lw   a0, 0(sp)        ; lw a0, 0(sp) (compressed load)
c.sw   a1, 4(sp)        ; sw a1, 4(sp) (compressed store)

; Zcmp: pushed/popped register multi-instructions (for code size)
cm.push {ra,s0-s5}, -64  ; push multi-register, alloc frame
cm.pop  {ra,s0-s5}, 64   ; pop multi-register, dealloc frame

; Zcmt: table jumps (jump table for switch)
cm.jalt  t0, 1           ; jump via table at offset 1

; Zclsd: stack-load/store with displacement (RV32/RV64)
c.lwsp  a0, 0(sp)        ; load word from stack (sign-extended)
c.swsp  ra, 8(sp)        ; store word to stack
c.ldsp  a0, 0(sp)        ; load doubleword (RV64 only)
c.sdsp  ra, 8(sp)        ; store doubleword
```

#### RP2350 hazard3 (Raspberry Pi microcontroller)
```text
; RP2350 (Raspberry Pi) integrates dual RISC-V cores (Hazard3 + Cortex-M33).
; Hazard3 is a 32-bit RV32IMAC with custom opcodes.

; Hazard3-specific markers in disassembly:
;   * Side-channel hardening: random delay slots, scratch register use
;   * Custom SoC extensions visible as RISC-V ".insn" prefixed lines
;   * Soteria support: tagged pointers (16-bit tag in upper bits of address)
;
; Soteria-tagged pointer example:
;   li   t0, 0xCAFE_BABE    ; load 32-bit tag in upper bits
;   or   a0, a0, t0         ; OR into address -> tagged pointer
;   ld   t1, 0(a0)          ; load via tagged pointer
;   ; Soteria traps if tag mismatch (memory safety hardening)
```

RISC-V support is available in **IDA Pro 9.4** (RP2350/hazard3, Zcmp/Zcmt/Zclsd, Soteria), **Ghidra 12.1.4**, **Binary Ninja 6.0**, and **Rizin 0.9.x** (rewritten via Capstone 6).

### Hexagon QDSP6 Patterns (Qualcomm DSP)

#### Architecture overview
- **Packet-based execution**: instructions grouped into **packets** executed in parallel (VLIW-style). Maximum 4 instructions per packet (with .newvalue, .jump, etc. extensions allowing more).
- **Register file**: 32 general-purpose 32-bit registers **R0–R31**.
- **Control registers**: SA0, SA1 (start address for loop 0/1), LC0, LC1 (loop count for loop 0/1), USR, PC, GP, FP, LR, SP.
- **Predicates**: P0–P3 (single-bit predicate registers; newer Hexagon V60+ has P0–P15).
- **Loop hardware**: zero-overhead loops via `.L` and `.loop_end` markers; SA0/LC0 (or SA1/LC1) auto-managed.

#### Packet syntax (curly braces)
```asm
; Curly braces { ... } delimit a packet executed in parallel
; Semicolons separate packets; ':endloop0' / ':endloop1' mark loop end
; ':loop0' / ':loop1' (optionally with start address) mark loop start

{  r0 = add(r1, r2)                    ; packet 1: parallel add
   r3 = memw(r4)                       ; parallel load
   jump <addr>                         ; parallel jump
}:endloop0                             ; end of loop 0

{  r5 = memd(r6)                       ; packet 2: doubleword load
   r7 = combine(r8, r9)                ; combine low/high halfwords
   :loop0                              ; back-edge of loop 0 (start of next iter)
   p0 = cmp.eq(r0, #0)                 ; compare
} if (!p0.new) jump:t <skip>           ; conditional jump (predicate new)
```

#### Function prologue / epilogue
```asm
; Hexagon uses frame pointer (FP) and link register (LR)
; Allocations: allocframe(#N) saves FP/LR and allocates N bytes

; Prologue
allocframe(#0x40):raw                  ; alloc 64 bytes; save FP/LR/PC
memd(r0+#0x10) = r17:18                ; save callee-saved pair

; Epilogue
r17:18 = memd(r0+#0x10)                ; restore callee-saved pair
deallocframe:raw                       ; restore FP/LR/PC; sp = fp
```

#### Loop hardware
```asm
; Hardware loop registers: SA0/SA1 (start), LC0/LC1 (count)
; Compiler emits ":loop0(..)" to set loop registers; ":endloop0" marks end

{  r0 = #0                              ; init i = 0
   r1 = ##end_of_body                   ; compute loop end
   loop0(.L_loop_body, r1)              ; start loop 0 at .L_loop_body
} .L_loop_start:

{  memw(r2+r0<<2) = r3                  ; body: store r3 to array[i]
   r0 = add(r0, #1)                     ; i++
   p0 = cmp.gt(r0, #255)                ; i > 255?
} .L_loop_body:
{  if (!p0) jump:t .L_loop_start        ; continue if p0 false
   nop                                  ; padding
}:endloop0
```

#### Calling convention (Hexagon QDSP6)
```text
Arguments: R0:R1 (32/64-bit pair), R2:R3, R4:R5, R6:R7, R8:R9, R10:R11, then stack
Return:    R0:R1
Caller-saved: R0–R15
Callee-saved: R16–R31 (paired R17:18, R19:20, R21:22, R23:24, R25:26, R27:28, R29:30, R31:16)
Stack ptr:   SP
Frame ptr:   FP
Link reg:    LR
```

Hexagon QDSP6 was added in **IDA Pro 9.4** (with MBN boot-image loader SBL/XBL) and **Ghidra 12.1.4** (Hexagon processor module introduced via Sleigh crossbuild). Packet boundaries are critical for correct decompilation.

### MCore (CSky V1) Patterns

#### Architecture overview
- 32-bit embedded RISC, used in some CSky cores (now deprecated for CSky V2/V3 — but IDA 9.4 still supports V1).
- **Stack-pointer tracking** and **auto stack-vars** added in IDA 9.4 (similar to ARM/AArch64).

#### Register file
```text
R0–R31: 32 general-purpose registers
GPR0    = SP (stack pointer)
GPR1    = FP (frame pointer)
GPR15   = LR (link register)
```

#### Function prologue / epilogue
```asm
; Prologue (typical, with frame setup)
subi    sp, sp, 16       ; allocate locals (no FP save on leaf)
stm     r4-r7, (sp)      ; save callee-saved

; Or with full frame
subi    sp, sp, 32       ; allocate frame
stw     r1, (sp, 0)      ; save old FP at [sp]
stw     r15, (sp, 4)     ; save LR at [sp+4]
addi    r1, sp, 32       ; set FP = sp + 32

; Epilogue
ldw     r15, (sp, 4)     ; restore LR
ldw     r1, (sp, 0)      ; restore FP
addi    sp, sp, 32       ; deallocate
rts                     ; jump to LR (return)
```

#### Calling convention
```text
Arguments: R0 (32-bit) / R0:R1 (64-bit), R2, R3, then stack
Return:    R0 (and R1 for 64-bit)
Caller-saved: R0–R3
Callee-saved: R4–R11, R15 (LR)
```

MCore support is **IDA Pro 9.4** specific; Ghidra coverage is partial (not in core 12.1.4). Binary Ninja 6.0 does not list MCore.

### TriCore Patterns

#### Architecture overview
- 32-bit embedded RISC (Infineon AURIX TC2xx/TC3xx — automotive MCU).
- **IDA Pro 9.4** added complete type system, register finder, switch tables, relocation support.
- **Binary Ninja 6.0** supports TriCore via "Multiple Global Pointers" (4 global registers).

#### Register file
```text
Address registers:  A0–A15 (used for address/pointer calculations)
Data registers:     D0–D15 (used for general data; some pairs for 64-bit)
Special registers:
  A10 = SP (stack pointer)
  A11 = RA (return address)
  A15 = FP (frame pointer — some conventions)
  PSW  = Program Status Word (condition flags + control bits)
  PC   = Program Counter
  SP, RA, A11, A14, A15 are global registers (not banked)
```

#### Function prologue / epilogue
```asm
; TriCore uses "svlcx" (save lower context) / "rstv" (restore) for context switching
; Often no explicit frame setup on small leaf functions; compound functions use:

; Prologue
sub.a   sp, #16          ; allocate 16 bytes
st.a    [sp]   a14       ; save context (a14 = RA on TriCore)
st.a    [sp]4  a15       ; save frame pointer (a15)

; Or with explicit "svlcx" pattern
svlcx                   ; save lower context (PSW + global regs to stack)
sub.a   sp, #<N>         ; allocate locals

; Epilogue
add.a   sp, #<N>         ; deallocate locals
rstv                    ; or ldm restores context
ret                     ; or "rfe" / "rets" depending on mode
```

#### Switch tables (TriCore-specific)
```asm
; TriCore compiler emits:
;   movh.a  a4, #hi16(table_addr)
;   lea     a4, [a4 + lo16(table_addr)]
;   mov.u   d15, <index>
;   addsc.a a4, a4, d15, #<scale>
;   ji      a4                       ; indirect jump (jump table)

; IDA 9.4 reconstructs these as switch tables; older versions displayed raw
movh.a   a4, #0x8001                ; high 16 bits of table base
lea      a4, [a4 + 0x2000]          ; low 16 bits
mov.u    d15, d0                    ; index from switch var
addsc.a  a4, a4, d15, #2            ; scale index by 2 (per-entry size)
ji       a4                         ; jump via table
```

TriCore is supported in **IDA Pro 9.4** (complete type system + switch tables + relocation support) and **Binary Ninja 6.0** (via multiple global pointers feature).

## Calling Conventions — Comprehensive Table

| Arch | Args | Return | Caller-saved | Callee-saved | Self/Context regs |
|---|---|---|---|---|---|
| x86 cdecl | stack (caller cleans) | eax | eax, ecx, edx | ebx, esi, edi, ebp | — |
| x86 stdcall | stack (callee cleans) | eax | eax, ecx, edx | ebx, esi, edi, ebp | — |
| x64 Windows | rcx, rdx, r8, r9, then stack | rax | rax, rcx, rdx, r8-r11 | rbx, rbp, rdi, rsi, r12-r15 | — |
| x64 SysV (Linux/macOS) | rdi, rsi, rdx, rcx, r8, r9, then stack | rax (+rdx 128-bit) | rax, rcx, rdx, rdi, rsi, r8-r11 | rbx, rbp, r12-r15 | — |
| AArch64 | x0-x7, then stack | x0 (+x1 128-bit) | x0-x18 | x19-x28, x29 (fp), x30 (lr) | — |
| ARM32 | r0-r3, then stack | r0 (+r1 64-bit) | r0-r3, r12 | r4-r11, r13 (sp), r14 (lr) | — |
| RISC-V LP64D | a0-a7, then stack | a0 (+a1 128-bit) | t0-t6, a0-a7 | s0-s11, ra, sp, gp, tp | — |
| **Hexagon QDSP6** | R0:R1, R2:R3, ..., R10:R11, then stack | R0:R1 | R0–R15 | R16–R31 | — |
| **MCore** | R0, R1, R2, R3, then stack | R0 (+R1 64-bit) | R0–R3 | R4–R11, R15 | GPR0=SP, GPR1=FP, GPR15=LR |
| **TriCore** | D4–D7, A4–A7, then stack | D4 (and D5 for 64-bit) | D0–D7, A0–A3, A8, A9 | D8–D15, A10–A15 | A10=SP, A11=RA, A15=FP |
| **Swift x86-64** | rdi, rsi, rdx, rcx, r8, r9 + **x14 (self)** + **x15 (async/error)** | rax | rax, rcx, rdx, r8-r11 | rbx, rbp, r12-r15 | x14=`__swiftself`, x15=`__swiftasync`/`__swiftthrows` |
| **Swift arm64** | x0-x7 + **x20 (self)** + **x21 (swifterror)** | x0 | x0-x18 | x19-x28, x29 (fp), x30 (lr) | x20=`__swiftself`, x21=`__swifterror` |
| **Rust x86-64** | rdi, rsi, rdx, rcx, r8, r9 | rax | rax, rcx, rdx, r8-r11 | rbx, rbp, r12-r15 | — |
| **Rust arm64** | x0-x7 | x0 | x0-x18 | x19-x28, x29 (fp), x30 (lr) | — |
| **Go amd64 (1.17+)** | stack-based, AX/SX/BX/CX/DX for args+return | AX | — | — | BP=frame, SP=stack |

### Swift Calling Convention details

Swift uses a **register-based** convention but with extra implicit context registers. IDA Pro 9.4 detects these automatically and tags them with `__swiftself`, `__swiftasync`, `__swiftthrows`, `__swiftcall`. Ghidra 12.1.4 also recognizes Swift signatures when DWARF is available.

#### x86-64 Swift
```asm
; Registers:
;   x14 = __swiftself (context pointer for value types/methods)
;   x15 = __swiftasync / __swiftthrows (error/continuation slot)
;
; Swift allocates a 16-byte "Self" capture area on the stack at function entry.
; This area is addressed via SP-relative offsets after the prologue.

example_method:
    sub    rsp, 0x28         ; 16-byte Self capture + 16-byte alignment + locals
    mov    [rsp+0x10], x14   ; save self capture
    ; x14 still holds `self` pointer for method dispatch
    call   getSelfProperty
    mov    x14, [rsp+0x10]   ; reload self after call (call-clobbered)
    add    rsp, 0x28
    ret
```

#### arm64 Swift
```asm
; Registers:
;   x20 = __swiftself
;   x21 = __swifterror (error pointer)
;
; Swift on ARM64 stacks a "Self" context descriptor for non-methods and tail-allocates
; owned-by-self structs via stack frame offset.

example_method:
    sub    sp, sp, #32       ; allocate Self capture + locals
    str    x20, [sp, #16]    ; save self
    bl     getSelfProperty   ; x20 = self, x21 = error ptr
    ldr    x20, [sp, #16]    ; restore self (x20 is callee-saved anyway, but compiler saves explicitly)
    add    sp, sp, #32
    ret
```

#### Detecting Swift binaries
- Demangling: `_$s10Foundation6LocaleV7currentAC09canonicalA0vg` (Swift 5+ mangling; older used `_T0F...`)
- Library: `libswiftCore.dylib`, `libswiftFoundation.dylib` in Dyld Shared Cache
- Symbols: `__swift_FORCE_LOAD_$_swiftCore_*` markers
- Deoptimizer passes: IDA 9.4 detects stripped Swift binaries by recovering `__swiftcall` and the context-register convention from patterns alone

### Rust Calling Convention details

Rust uses the **same calling convention as C** for the target platform (System V AMD64 on Linux/macOS, MS x64 on Windows, AAPCS on ARM). However, distinguishing patterns exist:

#### x86-64 Rust
```asm
; Same args as C: rdi, rsi, rdx, rcx, r8, r9
; But Rust ABI annotations:
;   #[inline(never)]  -- rarely inline; function bodies tend to be larger than C
;   #[cold]           -- marked "cold" attribute, often out-of-line
;   #[no_mangle]      -- unmangled name (no hash)

; Panic markers (rustc panic = landingpad = invoke pattern):
;   call <fn>
;   ud2                          ; unreachable -- panic boundary
;   <landingpad code>            ; cleanup / unwind

; Rust string = std::string::String layout: { ptr, len, cap } in registers
;   Example: String constructor that passes ptr+len+cap:
mov    rdi, ptr_to_data
mov    rsi, length
mov    rdx, capacity
call   alloc_string
```

#### Detecting Rust binaries
- **rustc version detection**: IDA 9.4 reads `.rustc` section or string-table markers (`rustc version 1.xx.x`)
- **Crate list**: `.crate_*` sections enumerate compiled crates
- **Panic locations**: typed `panic_location_t` records
- **Demangling**: `_ZN3std2io5Write9write_fmt17h...E` — Rust v0 mangling prefix `_ZN`
- **Symbol naming**: `<crate_name>::<path>::<hash>::<fn_name>` (hash is u64 suffix)

#### arm64 Rust
```asm
; Same args as C: x0-x7
; Same as AArch64 C convention; distinguishing markers are the same (panic, demangling)
```

## Control Flow Patterns

### Conditional Branches

```asm
; if (a == b)
cmp eax, ebx
jne skip_block
; ... if body ...
skip_block:

; if (a < b) - signed
cmp eax, ebx
jge skip_block    ; Jump if greater or equal
; ... if body ...
skip_block:

; if (a < b) - unsigned
cmp eax, ebx
jae skip_block    ; Jump if above or equal
; ... if body ...
skip_block:
```

### Loop Patterns

```asm
; for (int i = 0; i < n; i++)
xor ecx, ecx           ; i = 0
loop_start:
cmp ecx, [n]           ; i < n
jge loop_end
; ... loop body ...
inc ecx                ; i++
jmp loop_start
loop_end:

; while (condition)
jmp loop_check
loop_body:
; ... body ...
loop_check:
cmp eax, ebx
jl loop_body

; do-while
loop_body:
; ... body ...
cmp eax, ebx
jl loop_body
```

### Switch Statement Patterns

```asm
; Jump table pattern
mov eax, [switch_var]
cmp eax, max_case
ja default_case
jmp [jump_table + eax*8]

; Sequential comparison (small switch)
cmp eax, 1
je case_1
cmp eax, 2
je case_2
cmp eax, 3
je case_3
jmp default_case
```

### ARM64 / TriCore switch recovery

```asm
; ARM64 jump table
adr    x9, jump_table
ldrsw  x10, [x9, x8, lsl #2]    ; load offset (signed 32-bit)
add    x9, x9, x10               ; add to base
br     x9                        ; indirect branch

; TriCore switch (see TriCore section)
```

## Data Structure Patterns

### Array Access

```asm
; array[i] - 4-byte elements
mov eax, [rbx + rcx*4]        ; rbx=base, rcx=index

; array[i] - 8-byte elements
mov rax, [rbx + rcx*8]

; Multi-dimensional array[i][j]
; arr[i][j] = base + (i * cols + j) * element_size
imul eax, [cols]
add eax, [j]
mov edx, [rbx + rax*4]
```

### Structure Access

```c
struct Example {
    int a;      // offset 0
    char b;     // offset 4
    // padding  // offset 5-7
    long c;     // offset 8
    short d;    // offset 16
};
```

```asm
; Accessing struct fields
mov rdi, [struct_ptr]
mov eax, [rdi]         ; s->a (offset 0)
movzx eax, byte [rdi+4] ; s->b (offset 4)
mov rax, [rdi+8]       ; s->c (offset 8)
movzx eax, word [rdi+16] ; s->d (offset 16)
```

### Linked List Traversal

```asm
; while (node != NULL)
list_loop:
test rdi, rdi          ; node == NULL?
jz list_done
; ... process node ...
mov rdi, [rdi+8]       ; node = node->next (assuming next at offset 8)
jmp list_loop
list_done:
```

## Apple Silicon (ARM64) macOS Binaries

### Mach-O vs ELF differences

| Aspect | ELF (Linux) | Mach-O (macOS/iOS) |
|---|---|---|
| Indirect call | PLT/GOT (lazy + non-lazy) | dyld stubs `_objc_msgSend$` |
| Sections | `.text`, `.data`, `.bss`, `.rodata` | `__TEXT __text`, `__DATA __data`, etc. |
| Linker | `ld-linux` | `ld64` |
| Header | `Elf64_Ehdr` | `mach_header_64` |
| Library path | `DT_NEEDED` | `LC_LOAD_DYLIB` |
| PIE base | ELF header `e_entry` | LC_SEGMENT_64 `vmaddr` of `__TEXT` |
| Page size | 4 KB or 2 MB | 16 KB (Apple Silicon) / 4 KB (Intel) |

### dyld stubs and objc_msgSend

```asm
; x86-64 (Intel Mac) - in stripped dyld cache:
; Indirect call through _objc_msgSend_stret or _objc_msgSend

; arm64 (Apple Silicon):
;   bl _objc_msgSend$10          ; dyld stub (10 = selector reference count)
;   ldr  x16, =@PAGEOFF(_objc_msgSend)
;   ; Or direct via PLT-like indirection
;
; Sample:
mov    x0, x19               ; receiver
adrp   x16, _OBJC_CLASS_$_MyClass@PAGE
add    x16, x16, _OBJC_CLASS_$_MyClass@PAGEOFF
ldr    x16, [x16]             ; load class
ldr    x1, [x8]               ; "myMethod" selector
bl     _objc_msgSend
```

IDA Pro 9.4's **Dyld Shared Cache rewrite** auto-resolves these stubs to actual ObjC method prototypes when the cache is available.

### Swift demangling in Mach-O

```asm
; Swift symbols have a recognizable prefix in mangled form:
;   _$s10Foundation6LocaleV7currentAC09canonicalA0vg
;
; Decompiler pattern:
;   1. Look for x14 (x86-64) or x20 (arm64) usage → Swift self context
;   2. Look for SP-relative access to Self capture area
;   3. Look for swift_retain / swift_release calls (ARC runtime)
;   4. IDA 9.4 + Ghidra 12.1.4 will demangle these automatically if symbol table present
```

### x86_64 Macros
```asm
; Apple x86-64 uses System V (Linux-style) calling convention
; Differences from Linux:
;   * Page size 16 KB on Apple Silicon (vs 4 KB Linux)
;   * Mach-O __stubs / __la_symbol_ptr instead of PLT
;   * Different OS API surface (Mach, Cocoa, not Linux syscalls)
```

## Common Code Patterns

### String Operations

```asm
; strlen pattern
xor ecx, ecx
strlen_loop:
cmp byte [rdi + rcx], 0
je strlen_done
inc rcx
jmp strlen_loop
strlen_done:
; ecx contains length

; strcpy pattern
strcpy_loop:
mov al, [rsi]
mov [rdi], al
test al, al
jz strcpy_done
inc rsi
inc rdi
jmp strcpy_loop
strcpy_done:

; memcpy using rep movsb
mov rdi, dest
mov rsi, src
mov rcx, count
rep movsb
```

### Arithmetic Patterns

```asm
; Multiplication by constant
; x * 3
lea eax, [rax + rax*2]

; x * 5
lea eax, [rax + rax*4]

; x * 10
lea eax, [rax + rax*4]  ; x * 5
add eax, eax            ; * 2

; Division by power of 2 (signed)
mov eax, [x]
cdq                     ; Sign extend to EDX:EAX
and edx, 7              ; For divide by 8
add eax, edx            ; Adjust for negative
sar eax, 3              ; Arithmetic shift right

; Modulo power of 2
and eax, 7              ; x % 8
```

### Bit Manipulation

```asm
; Test specific bit
test eax, 0x80          ; Test bit 7
jnz bit_set

; Set bit
or eax, 0x10            ; Set bit 4

; Clear bit
and eax, ~0x10          ; Clear bit 4

; Toggle bit
xor eax, 0x10           ; Toggle bit 4

; Count leading zeros
bsr eax, ecx            ; Bit scan reverse
xor eax, 31             ; Convert to leading zeros

; Population count (popcnt)
popcnt eax, ecx         ; Count set bits
```

## Decompilation Patterns

### Variable Recovery

```asm
; Local variable at rbp-8
mov qword [rbp-8], rax  ; Store to local
mov rax, [rbp-8]        ; Load from local

; Stack-allocated array
lea rax, [rbp-0x40]     ; Array starts at rbp-0x40
mov [rax], edx          ; array[0] = value
mov [rax+4], ecx        ; array[1] = value
```

### Function Signature Recovery

```asm
; Identify parameters by register usage
func:
    ; rdi used as first param (System V)
    mov [rbp-8], rdi    ; Save param to local
    ; rsi used as second param
    mov [rbp-16], rsi
    ; Identify return by RAX at end
    mov rax, [result]
    ret
```

### Type Recovery

```asm
; 1-byte operations suggest char/bool
movzx eax, byte [rdi]   ; Zero-extend byte
movsx eax, byte [rdi]   ; Sign-extend byte

; 2-byte operations suggest short
movzx eax, word [rdi]
movsx eax, word [rdi]

; 4-byte operations suggest int/float
mov eax, [rdi]
movss xmm0, [rdi]       ; Float

; 8-byte operations suggest long/double/pointer
mov rax, [rdi]
movsd xmm0, [rdi]       ; Double
```

## Modern Language Decompiler Patterns

### Swift closures

Closures in Swift lower to a struct containing:
- Function pointer (the closure body)
- Capture list pointer (the captured context)
- Sometimes a thunk

```asm
; Swift closure call site
; Closure = { (x: Int) -> Int in x + 1 }
; struct.closure = { fn = captured_body, ctx = captured_self }

; x86-64 Swift closure invocation:
mov    rdi, [rsp+0x18]   ; load ctx (captured self)
mov    rsi, [rdi+0x08]   ; load field from ctx
mov    rax, [rsp+0x10]   ; load fn pointer
call   rax               ; call closure body
```

IDA 9.4 detects this pattern and emits `(closure)(self, arg)` style pseudocode. The `__swiftself` register (x14/x20) is the captured-context pointer.

### Rust match expressions

`match` in Rust compiles to a switch (jump table) for dense ranges, or a sequence of `cmp + jne` for sparse. The `#[derive(PartialEq)]` enum generates a discriminant check.

```asm
; Rust enum match (dense)
;   enum E { A, B, C }
;   match e { A => ..., B => ..., C => ... }
;
; Compiled:
cmp    eax, 0          ; discriminant == 0?
je     case_a
cmp    eax, 1
je     case_b
cmp    eax, 2
je     case_c
jmp    unreachable      ; panic at match

; Or jump table for wider ranges:
movsxd rax, esi
lea    rcx, [rip + jump_table]
movsxd rdx, [rcx + rax*4]
add    rax, rdx
jmp    rax
```

### Rust panic / landingpad

```asm
; Pattern: invoke (Rust) → call + ud2 fallback → landingpad
call   some_function          ; regular call
ud2                          ; panic boundary (unreachable marker)

; landingpad (unwind path):
mov    rax, qword [rsp]       ; load landingpad selector
mov    rdi, rax
call   __gxx_personality_v0  ; unwind runtime
```

### Go goroutines

Goroutine stacks start at 8 KB and grow dynamically (up to 1 GB max by default in Go 1.x). The runtime manages these via `runtime.morestack_noctxt`.

```asm
; Goroutine stack frame (Go 1.17+ ABI: registers-based)
;   Stacks use a pointer at -8(sp) for runtime stack info
;
; Typical preamble:
sub    sp, sp, #96
mov    rbp, sp                  ; rbp = frame pointer (NOT used as saved-reg)
; Function calls use `call .InlinedCall` with regargs

; Goroutine identification:
;   - Function takes a `*g` argument (goroutine descriptor)
;   - `getg()` reads from thread-local storage (TLS on g0 offset)
;   - runtime.g struct has many fields; key offsets:
;       +0x30 = g.stack.lo
;       +0x38 = g.stack.hi
;       +0x40 = g.stackguard0

; IDA 9.4 Go analysis: detects `pclntab` (program counter line table) for function
; name recovery, parses `.gopclntab` section, applies Go ABI conventions.
```

### Go stack structure (Go 1.17+ ABI internal)

Go ABI internal uses register-based calling. The Go 1.17+ ABI0 is the legacy stack-based ABI. Modern binaries compiled with `-abi=internal` (Go 1.17 default) use registers.

```asm
; ABI internal (registers):
;   Args: AX, BX, CX, DI, SI, R8, R9, R10, R11
;   Return: AX, BX, CX, DI, SI, R8, R9, R10, R11
;
; ABI0 (legacy stack-based):
;   Args on stack; return in stack slot passed via AX
;
; IDA GoReSym + IDA 9.4 detect these and apply correct ABI per function.
```

## Ghidra Analysis Tips

### Improving Decompilation

```java
// In Ghidra scripting
// Fix function signature
Function func = getFunctionAt(toAddr(0x401000));
func.setReturnType(IntegerDataType.dataType, SourceType.USER_DEFINED);

// Create structure type
StructureDataType struct = new StructureDataType("MyStruct", 0);
struct.add(IntegerDataType.dataType, "field_a", null);
struct.add(PointerDataType.dataType, "next", null);

// Apply to memory
createData(toAddr(0x601000), struct);

// Ghidra 12.1.4: Bitfields in Decompiler
//   struct {
//       int flag_a : 1;   // offset 0, bit 0
//       int flag_b : 3;   // offset 0, bits 1-3
//       int pad    : 4;   // offset 0, bits 4-7
//   }
//   Reads/writes show `flag_a` directly without >> / & boilerplate
```

### Hexagon support (Ghidra 12.1.4+)

Ghidra's Hexagon processor module uses **Sleigh crossbuild** — pcode representations designed for parallel/VLIW architectures. Packet boundaries may not always be recovered correctly; manual annotation may be needed for heavily optimized packets.

### Pattern Matching Scripts

```python
# Find all calls to dangerous functions
for func in currentProgram.getFunctionManager().getFunctions(True):
    for ref in getReferencesTo(func.getEntryPoint()):
        if func.getName() in ["strcpy", "sprintf", "gets"]:
            print(f"Dangerous call at {ref.getFromAddress()}")
```

## IDA Pro Patterns

### IDAPython Analysis

```python
import idaapi
import idautils
import idc

# Find all function calls
def find_calls(func_name):
    for func_ea in idautils.Functions():
        for head in idautils.Heads(func_ea, idc.find_func_end(func_ea)):
            if idc.print_insn_mnem(head) == "call":
                target = idc.get_operand_value(head, 0)
                if idc.get_func_name(target) == func_name:
                    print(f"Call to {func_name} at {hex(head)}")

# Rename functions based on strings
def auto_rename():
    for s in idautils.Strings():
        for xref in idautils.XrefsTo(s.ea):
            func = idaapi.get_func(xref.frm)
            if func and "sub_" in idc.get_func_name(func.start_ea):
                # Use string as hint for naming
                pass

# 9.4: Swift calling convention detection
#   Iterate functions, look for __swiftself / __swiftasync keywords:
def find_swift_methods():
    for func in idautils.Functions():
        tif = idaapi.get_tinfo(func)
        if not tif:
            continue
        # Check funcattrs for __swiftself
        fa = idaapi.func_extra_data_t()
        for i in range(tif.get_funcargs_count()):
            arg_name = tif.get_funcarg_name(i)
            if arg_name and ("self" in arg_name.lower()):
                print(f"Swift method candidate: {idaapi.get_func_name(func.start_ea)}")

# 9.4: RP2350 hazard3 detection
#   Look for RISC-V ELF with Hazard3 markers; read build attributes:
def detect_rp2350():
    # Build attributes (.attributes section) include Tag_Hazard3 or
    # "hazard3" as a custom string; check via idautils
    pass
```

### IDA 9.4 New Processors at a glance

| Processor | Status | Notes |
|---|---|---|
| Hexagon QDSP6 | ✅ | Packet syntax, MBN loader (SBL/XBL) |
| MCore (CSky V1) | ✅ | Stack-pointer tracking, auto stack-vars |
| TriCore | ✅ | Type system, register finder, switch tables, relocation |
| ARM SVE2 | ✅ | Full disassembly |
| ARM SME | ✅ | Full disassembly (ZA tiles) |
| RISC-V | ✅ | RP2350 / hazard3, Zcmp/Zcmt/Zclsd, Soteria |
| V850 | ✅ | More switch patterns |
| ARM64 Windows-on-ARM | ✅ | Native build |

### Sleigh crossbuild (IDA 9.4 architecture-defining)

For new architectures, Hex-Rays uses **Sleigh crossbuild** to compile architecture spec files into the IDA binary. This means processor modules are now shipped as native code, not as processor-specific scripts. For plugin development, this affects what is modifiable vs read-only.

## Best Practices

### Analysis Workflow

1. **Initial triage**: File type (ELF / Mach-O / PE), architecture, imports/exports
2. **String analysis**: Identify interesting strings, error messages, Swift/Rust mangling
4. **Function identification**: Entry points, exports, cross-references
5. **Calling convention check**: Look for `__swiftself`, `__swiftasync`, `_ZN` (Rust), pclntab (Go)
6. **Control flow mapping**: Understand program structure; note hardware loop markers (Hexagon `.L`)
7. **Data structure recovery**: Identify structs, arrays, globals
8. **Algorithm identification**: Crypto, hashing, compression
9. **Architecture-specific**: Hexagon packets, SVE predicates, TriCore switch tables
10. **Documentation**: Comments, renamed symbols, type definitions

### Architecture-specific tips

- **Hexagon**: respect packet boundaries; misaligned disassembly across packets leads to wrong control flow. Use IDA's `Edit → Packet boundaries` menu to verify.
- **MCore/TriCore**: small leaf functions may omit frame pointer setup; IDA 9.4's auto stack-vars recovers these.
- **SVE2/SME**: register width is implementation-defined; don't assume 128-bit. Use `RDVL` query.
- **RISC-V**: look for compressed instructions (`c.*` mnemonics) in tight code; check `.attributes` for vendor extensions.
- **Swift**: stripped binaries — IDA 9.4 can recover `__swiftcall` from patterns. Look for `x14`/`x20` write-then-call sequences.
- **Rust**: panic markers (`ud2`) often follow `call` invocations; treat as function boundaries.

## Common Pitfalls

- **Optimizer artifacts**: Code may not match source structure
- **Inline functions**: Functions may be expanded inline
- **Tail call optimization**: `jmp` instead of `call` + `ret`
- **Dead code**: Unreachable code from optimization
- **Position-independent code**: RIP-relative addressing
- **Packet boundary errors** (Hexagon): one instruction displayed out-of-packet can break decompilation entirely. IDA 9.4 packet detection is good but not perfect.
- **Compressed instruction overlap** (RISC-V): an unaligned 32-bit instruction decode in a region with 16-bit forms produces noise. Verify with `.insn 4` markers if available.
- **SVE predicate mis-tracking**: forgetting the predicate mask `p0/m` in scalar SVE code can make predicated operations appear unconditional.
- **TriCore global register assumptions**: 4 global registers mean FP/SP/RA can shift between A10/A11/A15 depending on ABI variant; IDA 9.4 hints at convention.
- **Swift self capture confusion**: x14/x20 holds `self` only for methods; for free functions x14/x20 may be unused or hold arbitrary state.
- **Rust false panic detection**: `ud2` can be legitimate IL-injected exception marker, not a panic boundary.
- **Mach-O `__la_symbol_ptr` vs `__stubs`**: Apple Silicon uses dyld stubless resolution; don't look for `__stubs` on newer binaries.
- **Dyld Shared Cache resolution** (IDA 9.4): when analyzing an iOS/macOS system binary, the cache must be loaded separately (`File → Load Dyld Shared Cache`).
- **Go ABI switching**: Go 1.17+ uses ABI internal (registers); pre-1.17 binaries use ABI0 (stack). Check compiler version via `.go.buildinfo`.
- **SVE vector length changes**: predicates and lane-counts depend on VL. Tools may show "v#i" where `#` is unknown — verify by querying `RDVL` or using `sve-vl-from-env` auxiliary var if available.

## Resources

- See `reverse-engineer` skill for tool selection matrix and modern toolchain details
- Hex-Rays blog "LLMs Have Reshaped How We Think About Decompilation and Collaboration" (30 jul 2026)
- Ghidra Sleigh crossbuild documentation (NSA, 2026)
- IDA Pro 9.4 release notes (Hex-Rays, jul 2026) — for Swift/Rust/Dyld specifics
- ARM Architecture Reference Manual — SVE2 / SME official specifications
- Qualcomm Hexagon SDK documentation — VLIW packet semantics
- TriCore TC3xx architecture manual (Infineon)
- Raspberry Pi RP2350 datasheet — Hazard3 details

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
- Capstone 6.0.0-Alpha11 + 5.0.9 stable
- ARM Architecture Reference Manual (ARMv8-A, SVE2, SVE2.1, SME)
- Qualcomm Hexagon V65/V66/V67 Architecture Reference
- Infineon TriCore TC1.6 / TC3xx Architecture Manual
- RISC-V ISA Specification (2015-2024, ratified extensions including V, Bitmanip, Crypto, Zcmp)
- Raspberry Pi RP2350 datasheet (Hazard3 integration)
- Swift ABI documentation (swift.org, current as of Swift 5.10+)
- Rustonomicon — Rust ABI details