---
name: binary-ninja
description: Binary Ninja 6.0 Krypton (set 2026) — modern Python-first RE platform. Covers 19 architectures, MCP server (official, free tier), Binary Similarity, IL stack (HLIL/MLIL/LLIL), plugin ecosystem, and AI-assisted workflows. Companion to `reverse-engineer` when BN is the chosen disassembler or MCP-driven RE is desired.
disable-model-invocation: true
risk: unknown
source: community
date_added: '2026-09-22'
---

# Binary Ninja 6.0 Krypton — Reverse Engineering Platform

Referência técnica focada no Binary Ninja como plataforma de RE: workflow ponta-a-ponta, IL stack, API Python 3.13, MCP server oficial, Binary Similarity, plugins essenciais e Free vs Commercial vs Ultimate.

Versão canônica: **Binary Ninja 6.0 "Krypton"** (03 set 2026, Vector 35). Última 5.x conhecida: **5.2** (13 nov 2025).

## Use this skill when

- Carregar um binário PE/ELF/Mach-O/WASM e decidir usar Binary Ninja como disassembler/decompiler.
- Construir scripts/plugins Python usando a API do BN (`binaryninja`, `BinaryView`, `Function`, HLIL/MLIL/LLIL).
- Configurar o **MCP server oficial** do BN 6.0 com Claude Desktop / Cursor / VS Code / Codex para RE agêntico.
- Usar **Binary Similarity** (Ultimate only) para diffing binário com BinDiff ou WARP.
- Precisar de plugins essenciais: BinSync, FindCrypt, Lighthouse, GoReSym, Delphinja, capa.
- Configurar o debugger (LLDB backend, TTD, memory map sidebar) integrado ao BN.
- Aplicar type system avançado (Type Fragments, HLIL_STRUCT_INITIALIZE, calling conventions customizadas).
- Triagem rápida com **Triage Summary** sem esperar análise completa.

## Do not use this skill when

- O alvo é **free e open-source** com preferência por Ghidra 12.1.4 (sem orçamento para Comercial/Ultimate) — usar `reverse-engineer` skill.
- A análise é puramente dinâmica (Frida 17.18 + Stalker) — usar `reverse-engineer` ou `ai-assisted-re`.
- O alvo é firmware embarcado com processador exótico sem suporte nas 19 do BN — verificar Rizin 0.9.1 ou Ghidra 12.1.4 primeiro.
- A tarefa é RE defensivo (anti-debugging, packing, obfuscation) — usar `anti-reversing-techniques`.
- Não há autorização legal para analisar o binário (sempre validar autorização primeiro).

## TL;DR

- **Único disassembler comercial com MCP first-party** (até no Free tier).
- **19 arquiteturas first-party** (5.x → 6.0 ganhou TMS320C6x; TriCore via Multiple Global Pointers).
- **Performance**: até 2.16× mais rápido e 55% menos memória vs 5.x (vmlinux: 761s → 352s).
- **IL stack de 3 níveis**: HLIL (alto, C-like), MLIL (médio, SSA com mem/data tracking), LLIL (baixo, instruções liftadas).
- **Binary Similarity (Ultimate)**: BinDiff (Google) + WARP + API Python/C++/Rust extensível.
- **Free tier inclui**: AArch64 decompiler, MCP server, build ARM64 Linux — mas Python API desabilitada, sem plugins.
- **Python 3.13 bundled** em todas as plataformas.

## Why Binary Ninja (vs IDA Pro 9.4 / Ghidra 12.1.4)

Decision matrix para escolher BN sobre alternativas comerciais/livres em 2026:

| Critério | IDA Pro 9.4 | Ghidra 12.1.4 | Binary Ninja 6.0 |
|---|---|---|---|
| Preço mínimo | IDA Pro caro; IDA Free limitado | **Grátis** | **Free tier** (não-comercial / eval) |
| Decompiler | Hex-Rays (pago à parte) | **Incluso** | **Incluso** (Free: AArch64; Commercial: todos os archs) |
| MCP first-party | Não (IDA Domain API v0.5) | Não | **Sim (Free incluso)** |
| API scripting | IDAPython (genérico) | Java + PyGhidra + Jython | **Python 3.13 first-party** |
| Performance binários grandes | Boa | Média | **2.16× mais rápido vs 5.x** |
| Arquiteturas | Primeiro evento (Hexagon, MCore, TriCore, SVE2, RP2350) | 23+ (NSA mantido) | **19 first-party** (foco qualidade) |
| Decompiler quality (C++) | **Melhor classe** (Hex-Rays) | Boa | Boa |
| Decompiler Swift/Rust | **Sim (Swift keywords auto)** | Parcial | Parcial |
| Binary diffing | Diaphora (third-party) | Não nativo | **BinDiff + WARP nativos (Ultimate)** |
| Collaborative RE | IDA Teams (Git backend) | Ghidra Server | **BinSync plugin** (decentralized Git) |
| Plugin ecosystem | Maduro (HEXXL, ClassInformer) | Maduro (SLEIGH) | Crescendo (BinSync, Lighthouse, GoReSym) |
| macOS ARM64 nativo | **Sim (9.4)** | Sim (12.1) | **Sim (6.0 Free)** |

**Quando escolher BN 6.0**:
1. **MCP-driven RE** com LLM agent — único com MCP first-party incluso no Free.
2. **Scripting Python-first** — API nativa, sem camadas de compatibilidade legadas.
3. **Binary diffing nativo** — BinDiff + WARP built-in (Ultimate).
4. **AArch64 decompiler grátis** — Free tier inclui armv8 decompilation.
5. **Plugin de Go/Delphi específico** — GoReSym, Delphinja têm suporte first-party.

**Quando escolher IDA Pro 9.4**:
1. Decompiler quality crítica (C++ VTables, complex structs) — Hex-Rays ainda é gold standard.
2. Hexagon QDSP6, MCore (CSky), TriCore — suporte mais maduro.
3. Swift calling convention auto-recuperada em stripped binaries.

**Quando escolher Ghidra 12.1.4**:
1. Orçamento zero e análise estática multi-arch genérica — sem nenhum custo.
2. Custom analyzers em SLEIGH (Sleigh crossbuild para arquiteturas paralelas).
3. Servidor centralizado (Ghidra Server) para times distribuídos.

## Editions comparison (Free / Commercial / Ultimate)

| Feature | Free | Commercial | Ultimate |
|---|---|---|---|
| Preço | Grátis (não-comercial / eval) | $$ (anuidade) | $$$ (anuidade) |
| Arquiteturas | **x86, x86-64, ARMv7, ARMv8** | Todos os 19 | **Todos os 19 + TMS320C6x** |
| Decompiler | **ARMv8 incluso**; outros archs limitado | Todos os archs | Todos os archs |
| Python API | **Desabilitada** | Habilitada | Habilitada |
| Plugins | **Não** | Todos | Todos |
| MCP server | **Sim** | Sim | Sim |
| LLIL/MLIL/HLIL | Reduzido | Completo | Completo |
| **Binary Similarity** | Não | Não | **BinDiff + WARP** |
| Collaboration (add-on por-seat) | Não | Não | **Sim (anlado)** |
| Enterprise Servers (self-hosted) | Não | Não | **Sim (sem licença separada)** |
| Linux ARM64 build | **Sim (6.0)** | Sim | Sim |
| Sidekick free tier mensal | Sim | Sim | Sim |
| IDA Teams on Git | — | — | BinSync |
| Debugger (LLDB + TTD) | Sim | Sim | Sim |

**Decisão prática**:
- **Free** para: AArch64 RE com LLM agent (MCP), estudantes, pesquisa não-comercial.
- **Commercial** para: RE profissional com scripting Python e plugins.
- **Ultimate** para: binary diffing, TMS320C6x, TMS320C5x, collaboration.

## Installation + first launch

### Instalação por plataforma

**macOS**: DMG oficial ou Homebrew Cask.
```bash
brew install --cask binary-ninja
```

**Linux x86-64 / ARM64**: AppImage ou tarball oficial.
```bash
# AppImage
chmod +x BinaryNinja-personal-6.0*.AppImage
./BinaryNinja-personal-6.0*.AppImage
```

**Windows**: MSI installer ou portable ZIP.

### First launch — New User Wizard

A 6.0 introduziu presets:
- **IDA-like**: keyboard shortcuts estilo IDA (`g` para jump, `n` para rename).
- **Ghidra-like**: layout multi-panel.
- **BN default**: shortcuts originais BN (`y` para type, `;` para comment, `n` para rename).

### Headless / batch mode

```bash
# Análise sem GUI — gera BNDB
binaryninja --headless --save-bndb sample.exe

# Análise + export para arquivo texto (HLIL)
binaryninja --headless --analysis-output=hli sample.exe
```

### Licenciamento

- **Free**: requer conta Vector 35 + aceite de termos não-comerciais.
- **Commercial/Ultimate**: serial key ou floating license server.
- **Floating license**: `binaryninja --license-server=host:port`.

## Core workflow: open file → analysis → navigation → renaming → decompilation

### Phase 1: Open + auto-analysis

```python
# BN Python API (Python 3.13 bundled)
from binaryninja import *

bv = BinaryView.open("/path/to/sample.exe")
bv.update_analysis_and_wait()  # blocking — espera análise completa

# Resumo pós-análise
print(f"Functions: {len(bv.functions)}")
print(f"Sections: {len(bv.sections)}")
print(f"Strings: {len(list(bv.strings))}")
```

**Expected output**:
```
Functions: 847
Sections: 5
Strings: 1234
```

### Phase 2: Navegação por entry points

```python
# Encontrar função main / entry point
for func in bv.functions:
    if func.name in ("main", "WinMain", "DllMain", "_start"):
        print(f"{func.name} @ {hex(func.start)}")
        print(f"  Args: {func.parameter_vars}")
        print(f"  Return: {func.return_type}")
```

### Phase 3: Cross-references e string xrefs

```python
# Strings → funções que as referenciam
for s in bv.strings:
    if len(s) < 6 or len(s) > 200:
        continue
    text = s.value.decode("utf-8", errors="replace")
    if any(kw in text.lower() for kw in ["auth", "login", "token", "password"]):
        for ref in bv.get_code_refs(s.start):
            caller = bv.get_function_at(ref.address)
            if caller:
                print(f"'{text}' referenced from {caller.name} @ {hex(ref.address)}")
```

### Phase 4: Renaming + typing

```python
# Renomear função baseada em xref de string
func.name = "auth_check_credentials"
func.return_type = Type.int(4)
func.parameter_vars[0].name = "username"
func.parameter_vars[0].type = Type.pointer(Type.char(), 4)
func.parameter_vars[1].name = "password"
func.parameter_vars[1].type = Type.pointer(Type.char(), 4)
```

### Phase 5: Decompilação HLIL

```python
# HLIL (high-level intermediate language) — pseudo C
for block in func.hlil:
    for line in block:
        print(line)
```

**Expected output** (exemplo):
```
int32_t auth_check_credentials(char* username, char* password) {
    int32_t result = 0x0;
    if (username == 0x0 || password == 0x0) {
        result = 0xffffffff;
    }
    else {
        result = bcrypt_check_password(username, password);
    }
    return result;
}
```

## IL Stack deep dive

Binary Ninja tem **3 ILs** principais + Lifted IL (LLIL pós-pipeline). Cada um é progressivamente mais baixo e detalhado.

### HLIL — High-Level IL

**Quando usar**: análise inicial, recuperação de tipos, leitura de fluxo de controle, decompilation output.

```python
# HLIL é o pseudo-C que aparece no painel de Decompile
for instr in func.hlil.instructions:
    print(instr)
```

**HLIL operations comuns** (`HlilOperation`):
- `HLIL_CALL`, `HLIL_CALL_PTR`
- `HLIL_ASSIGN`, `HLIL_ASSIGN_UNPACK`
- `HLIL_ADD`, `HLIL_SUB`, `HLIL_MUL`, `HLIL_DIVS`, `HLIL_DIVU`
- `HLIL_IF`, `HLIL_WHILE`, `HLIL_DO_WHILE`, `HLIL_FOR`
- `HLIL_STRUCT_FIELD`, `HLIL_ARRAY_INDEX`, `HLIL_DEREF`, `HLIL_ADDRESS_OF`
- `HLIL_STRUCT_INITIALIZE` (6.0+) — inicializações de struct preservam tipo mesmo após quebra em registradores.
- `HLIL_TYPE_FRAGMENT` (6.0+) — fragments de tipo preservados em chains de registradores.

**HLIL variables** (recuperação de tipos):
```python
for var in func.hlil.variables:
    print(f"{var.name}: {var.type} (storage: {var.storage})")
    # var.def_site, var.use_sites → propagação SSA
```

### MLIL — Medium-Level IL

**Quando usar**: análise SSA, propagação de constantes, data flow tracking, value-set analysis (VSA).

```python
# MLIL é SSA — cada variável tem versão única por definição
for block in func.mlil:
    for instr in block:
        if instr.operation == MediumLevelOperation.MLIL_CALL:
            print(f"Call {instr.dest} at {hex(instr.address)}")
        elif instr.operation == MediumLevelOperation.MLIL_ASSIGN:
            print(f"  {instr.dest} = {instr.src}")
```

**MLIL operations chave**:
- `MLIL_LOAD`, `MLIL_STORE` — acesso a memória com tipo conhecido.
- `MLIL_VAR`, `MLIL_VAR_SSA` — variáveis com versão SSA (`var#1`, `var#2`).
- `MLIL_CONST` — constantes.
- `MLIL_SET_VAR`, `MLIL_VAR_PHI` — phi nodes em joins.

**SSA tracking**:
```python
# Encontrar todas as versões de uma variável SSA
var = func.mlil.ssa_vars.get(var_name)
for version in var.versions:
    print(f"  {var_name}#{version}")
```

### LLIL — Low-Level IL

**Quando usar**: otimizações manuais, identificação de gadgets ROP/JOP, patch generation, análise de obfuscation.

```python
# LLIL é o mais próximo do assembly — cada instrução é um ILInstr
for block in func.llil:
    for instr in block:
        if instr.operation in (LowLevelOperation.LLIL_CALL, LowLevelOperation.LLIL_JUMP):
            print(f"{instr.operation} @ {hex(instr.address)} → {instr.dest}")
```

**LLIL operations essenciais**:
- `LLIL_CALL`, `LLIL_JUMP`, `LLIL_JUMP_TO` — control flow.
- `LLIL_LOAD`, `LLIL_STORE` — memory ops com tipo.
- `LLIL_PUSH`, `LLIL_POP`, `LLIL_REG`, `LLIL_CONST` — operandos.
- `LLIL_SET_REG`, `LLIL_FLAG_*` — register operations.
- `LLIL_INTRINSIC` — chamadas intrinsics do compilador (memcpy, strlen, etc.).

### Lifted IL — Lifted Intermediate Language

É o LLIL **após** pipeline de lifting (lifting passa antes de virar LLIL puro). Útil quando você quer ver o que o binário faz antes da análise do BN aplicar transformações. Raramente usado em workflow normal — acessar via API avançada.

### Quando usar cada IL

| Tarefa | IL |
|---|---|
| Ler pseudo-C | **HLIL** |
| Renomear variáveis automaticamente | **HLIL** |
| Propagação de constantes / VSA | **MLIL** |
| Encontrar call chains | **MLIL** ou **HLIL** |
| Detectar gadgets ROP/JOP | **LLIL** |
| Patch generation | **LLIL** (com tipos) |
| Anti-analysis bypass | **LLIL** + patches |
| Decompilation output para LLM | **HLIL** (texto limpo) |
| AI agent via MCP | **HLIL** (default) + MLIL quando precisar SSA |

## Python API essentials

A API Python do BN é **first-party** (sem IDAPython-style wrapping) e roda em Python 3.13 bundled. Módulos principais:

### `BinaryView` — núcleo do binário carregado

```python
from binaryninja import BinaryView, BinaryViewType

bv = BinaryView.open("sample.exe")           # auto-detecta tipo
bv = BinaryViewType["PE"].open("sample.exe") # força tipo PE
bv = BinaryViewType["ELF"].open("sample.so")
bv = BinaryViewType["Mach-O"].open("sample.dylib")
bv = BinaryViewType["WASM"].open("sample.wasm")

# Operações básicas
print(bv.arch.name)             # "x86_64"
print(bv.platform.name)         # "windows-x86_64" / "linux-x86_64"
print(len(bv))                  # tamanho do binário em bytes

# Ler bytes brutos
data = bv.read(0x401000, 16)
print(data.hex())

# Ler tipos
print(bv.address_size)          # 8 (x64), 4 (x86)
print(bv.entry_point)           # entry point do ELF/PE
```

### `Function` — uma função analisada

```python
func = bv.get_function_at(0x401000)  # endereço de início
print(f"Name: {func.name}")
print(f"Start: {hex(func.start)}")
print(f"End: {hex(func.end)}")
print(f"Basic blocks: {len(func.basic_blocks)}")
print(f"Parameters: {func.parameter_vars}")
print(f"Return type: {func.return_type}")
print(f"Calling convention: {func.calling_convention}")

# Acessors de IL
print(func.hlil)   # HighLevelILFunction
print(func.mlil)   # MediumLevelILFunction
print(func.llil)   # LowLevelILFunction

# Source-level linking (se houver PDB/DWARF)
print(func.source_function)  # LinkedFunction (se PDB presente)
```

### `BasicBlock` — bloco de controle de fluxo

```python
for block in func.basic_blocks:
    print(f"Block @ {hex(block.start)}-{hex(block.end)}")
    print(f"  Incoming edges: {len(block.incoming_edges)}")
    print(f"  Outgoing edges: {len(block.outgoing_edges)}")
    for edge in block.outgoing_edges:
        print(f"    -> {hex(edge.target.start)} ({edge.type})")
```

### `Symbol` — símbolos (imports, exports, locals)

```python
for sym in bv.symbols:
    if sym.type in (SymbolType.ImportSymbol, SymbolType.ExportSymbol):
        print(f"{sym.type}: {sym.name} @ {hex(sym.address)}")
```

### `Segment` / `Section` — layout do binário

```python
for seg in bv.segments:
    print(f"Segment {seg.name}: {hex(seg.start)}-{hex(seg.end)} r/w/x = {seg.readable}{seg.writable}{seg.executable}")

for sec in bv.sections:
    print(f"Section {sec.name}: {hex(sec.start)}-{hex(sec.end)}")
```

### `Architecture` — metadados da arquitetura

```python
print(bv.arch)            # Architecture("x86_64")
print(bv.arch.regs)       # [Register("rax"), Register("rbx"), ...]
print(bv.arch.call_conv_conventions)
```

## Type system + type libraries

### Tipos primitivos

```python
from binaryninja import Type

t_int32 = Type.int(4)           # 32-bit signed int
t_uint32 = Type.uint(4)         # 32-bit unsigned
t_char = Type.char()            # 8-bit char
t_void = Type.void()
t_float = Type.float(4)         # 32-bit float
t_double = Type.float(8)        # 64-bit double
t_bool = Type.bool()
```

### Tipos compostos

```python
# Pointer
t_str = Type.pointer(Type.char(), 4)  # char* (4 bytes address)
t_void_ptr = Type.pointer(Type.void(), 8)  # void* (8 bytes address)

# Array
t_arr = Type.array(Type.int(4), 16)  # int[16]

# Structure
struct = Type.structure()
struct.append("field_a", Type.int(4))
struct.append("next", Type.pointer(Type.named_type("Node"), 8))
struct.width = 16  # tamanho total em bytes
```

### NamedTypeReference + TypeLibrary

```python
# Type library — namespace de tipos reutilizáveis
lib = bv.new_type_library("my_lib")
lib.add_named_type("MyStruct", struct)

# NamedTypeReference aponta para um tipo em uma library
ref = Type.named_type("MyStruct", lib)
ptr_to_struct = Type.pointer(ref, 8)
```

### Calling conventions customizadas

A 6.0 refatorou calling conventions para suportar estruturas como parâmetros e retornos (necessário para Go e Pascal calling conventions). Plugins como Delphinja se beneficiam imediatamente.

```python
# Definir calling convention customizada
cc = CallingConvention(None, "my_cc")
cc.caller_saved_regs = [...]
cc.callee_saved_regs = [...]
cc.int_arg_regs = ["rdi", "rsi", "rdx", "rcx", "r8", "r9"]
cc.int_return_reg = "rax"
bv.platform.add_calling_convention(cc)
```

### Type Fragments (6.0)

Quando uma struct é quebrada em múltiplos registradores, **Type Fragments** rastreiam o tipo original através das operações de assembly:

```python
# Acessar fragments de uma variável HLIL
var = func.hlil.variables[0]
for fragment in var.type_fragments:
    print(f"Fragment: {fragment}")
```

## Plugins essenciais

Plugins ficam em `~/.binaryninja/plugins/` (macOS/Linux) ou `%APPDATA%\Binary Ninja\plugins\` (Windows).

### BinSync — collaborative RE via Git

Sincroniza renames, comentários, tipos entre múltiplos analysts usando Git como backend.

```bash
pip install binsync
```

```python
# binsync plugin — usar no console BN
import binsync
binsync.init("/path/to/repo")  # repo git local
binsync.sync()                 # pull + push renames/comments
```

### FindCrypt — crypto constants detector

Detecta constantes de algoritmos conhecidos (AES S-box, MD5 init, SHA rounds).

```bash
# Install: git clone https://github.com/vector35/binaryninja-api.git
# FindCrypt está em /examples no repositório oficial
```

```python
# output típico
# [FindCrypt] AES S-Box @ 0x401200
# [FindCrypt] SHA-256 K[0..63] @ 0x402000
# [FindCrypt] RC5 init @ 0x403000
```

### Lighthouse — code coverage visualization

Importa coverage traces de fuzzers (libFuzzer, AFL++, honggfuzz) e visualiza blocos cobertos vs não cobertos.

```python
# In BN Python console
import lighthouse
lighthouse.load_drcov("/path/to/coverage.drcov")
```

### GoReSym — Go binary symbol recovery

Recupera function names e tipos de binários Go stripped (usa pclntab e buildinfo parsing).

```bash
# Pré-requisito: instalar GoReSym CLI
go install github.com/mandiant/GoReSym@latest

# Output: JSON com symbols, types, buildinfo
GoReSym -t -d /path/to/go_binary > symbols.json
```

No BN, importar o JSON gerado via plugin ou script Python.

### Delphinja — Delphi/Pascal decompilation improvements

Melhora o reconhecimento de calling conventions e estruturas Delphi/Pascal (Register, cdecl, pascal, stdcall, safecall).

```bash
git clone https://github.com/nickvdyck/delphinja ~/.binaryninja/plugins/delphinja
```

Ativado automaticamente em binários Borland/Embarcadero.

### capa plugin (Mandiant) — capability detection

Integra CAPA 9.4 no BN UI. Mostra capabilities detectadas inline no decompiler.

```bash
pip install capa-binja
```

```python
# Configurar caminho do capa CLI em Settings → Plugins → capa
# Análise roda automaticamente após auto-analysis
# Output: tags como "communicate with HTTP", "encrypt data using AES", "create process"
```

## MCP server (Model Context Protocol) — primeira-party

**Apenas disassembler comercial com MCP oficial incluso no Free tier.**

### Variant GUI (todos os tiers)

Roda dentro do BN como HTTP server local:

- **URL**: `http://127.0.0.1:24642/mcp`
- **Auth**: Bearer token em `ui.mcp.token` (gerado automaticamente, visível em Settings → MCP)
- **Plataformas**: macOS, Linux, Windows

### Variant headless (Commercial/Ultimate — não Windows)

Binário `binaryninja_mcp` standalone (stdio) — sem GUI, sem license server necessário no macOS/Linux. Windows fica GUI-only por causa de filesystem locking.

```bash
binaryninja_mcp --binary sample.exe --stdio
```

### Configuração Claude Desktop

```json
{
  "mcpServers": {
    "binary-ninja": {
      "url": "http://127.0.0.1:24642/mcp",
      "headers": {
        "Authorization": "Bearer ${BN_MCP_TOKEN}"
      }
    }
  }
}
```

Variável `BN_MCP_TOKEN` definida como `ui.mcp.token` visível em Settings.

### Configuração Cursor

```json
{
  "mcpServers": {
    "binary-ninja": {
      "url": "http://127.0.0.1:24642/mcp",
      "transport": "http",
      "auth": {
        "type": "bearer",
        "token": "<ui.mcp.token>"
      }
    }
  }
}
```

### Configuração Codex / VS Code

Similar ao Claude Desktop via `mcp.json` ou settings.json do VS Code. Documentação oficial BN 6.0 release notes cobre todos os clients suportados.

### Operações expostas pelo MCP

- **Open files/databases**: carregar binário, listar BinaryViews abertos.
- **Drive analysis**: trigger analysis, query status, triage summary.
- **Navigation**: segments/sections/symbols/imports/exports/relocations/data vars/strings.
- **Raw memory**: read bytes em offset arbitrário.
- **Function inspection**: metadata, disassembly, Pseudo C, ILs (HLIL/MLIL/LLIL).
- **Edit operations**: rename functions/symbols, set types, create data vars.

Exemplo de tool call pelo LLM agent:
```
Tool: bn_get_function_info
Args: { "binary_view": "sample.exe", "address": "0x401000" }
Result: {
  "name": "sub_401000",
  "address": "0x401000",
  "size": 256,
  "hlil": "int32_t sub_401000(int32_t arg1, char* arg2) { ... }",
  "calling_convention": "cdecl",
  "parameters": [...]
}
```

## Binary Similarity (Ultimate only)

Framework pluggable com 2 providers built-in:
- **Google BinDiff**: structural diffing (CFG + instruction matching).
- **WARP**: exact match diffing (instruction-level + sequence hashing).

### Python API

```python
from binaryninja import similarity

# Diff entre dois binários
results = similarity.compare_databases(
    bv_a, bv_b,
    providers=["bindiff", "warp"],
    min_similarity=0.7,
)
for match in results:
    print(f"{match.function_a.name} ↔ {match.function_b.name}: {match.confidence:.2%}")
```

**Output esperado**:
```
auth_check_credentials ↔ authenticate_user: 0.94
parse_token ↔ decode_jwt: 0.87
sub_401500 ↔ sub_404500: 0.71
```

### C++ API

```cpp
#include <binaryninja/similarity.h>
auto results = BinaryNinja::Similarity::CompareDatabases(bvA, bvB, {"bindiff", "warp"}, 0.7);
```

### Rust API

```rust
use binaryninja::similarity::compare_databases;
let results = compare_databases(&bv_a, &bv_b, &["bindiff", "warp"], 0.7)?;
```

### Plugins customizados

```python
# Registrar provider customizado
from binaryninja import similarity

class MyProvider(similarity.SimilarityProvider):
    name = "my_provider"
    def compare(self, bv_a, bv_b):
        # custom logic
        return [...]
    def resolve(self, results):
        # pós-processamento
        return [...]

similarity.register_provider(MyProvider())
```

### Use cases

- **Vulnerability research**: encontrar variantes de funções vulneráveis entre versões.
- **CTF**: identificar funções conhecidas (AES, SHA, malloc wrappers) em binários stripped.
- **Code plagiarism**: detectar forks/copys de bibliotecas closed-source.
- **Patch analysis**: comparar duas builds de um mesmo binário para ver o que mudou.

## Triage Summary + quick analysis

A 6.0 introduziu **Triage Summary** que dá overview rápido sem esperar análise completa (vital para triagem inicial de malware).

```python
# Obter triage summary
summary = bv.get_triage_summary()
print(f"File type: {summary.file_type}")
print(f"Architecture: {summary.architecture}")
print(f"Entry: {hex(summary.entry_point)}")
print(f"Functions (estimate): {summary.function_count_estimate}")
print(f"Imports: {summary.import_count}")
print(f"Exports: {summary.export_count}")
print(f"Strings (count): {summary.string_count}")
print(f"Sections: {len(summary.sections)}")
print(f"Suspicious APIs: {summary.suspicious_imports}")
```

**Output esperado**:
```
File type: PE
Architecture: x86_64
Entry: 0x401000
Functions (estimate): 847
Imports: 134
Exports: 12
Strings (count): 1024
Sections: 5
Suspicious APIs: ['VirtualAlloc', 'WriteProcessMemory', 'CreateRemoteThread']
```

Útil em workflows:
1. Triagem rápida de amostras de malware antes de análise profunda.
2. CI/CD de security scanning — bloquear binários com suspicious APIs.
3. MFT inicial antes de decidir se vale análise completa.

## Debugger (LLDB backend + TTD)

### LLDB backend

Default debugger backend. Suporta breakpoints, memory map, register inspection, single-step, conditional breakpoints, watchpoints.

### Setup

1. `View → Debugger → Attach to process` ou `Launch`.
2. Selecionar target architecture (deve bater com o binário).
3. LLDB conecta via stub local (`lldb-server`) ou remoto (`lldb-server platform`).

### Comandos BN debugger

- `F9`: toggle breakpoint.
- `F10`: step over.
- `F11`: step into.
- `Shift+F11`: step out.
- `Ctrl+F5`: run.
- Memory Map sidebar: `View → Debugger → Memory Map`.

### TTD — Time Travel Debugging (WinDbg-style)

Permite navegar para trás no tempo de execução — replay até um ponto exato.

```python
# TTD navigation via API
dbg = bv.debugger
ttd = dbg.time_travel

# Próximo register write
ttd.step_to_next_register_write("rax")

# Anterior register write
ttd.step_to_previous_register_write("rax")

# Replay para posição específica
ttd.position = "0x401050:5"  # endereço:passo
```

**Casos de uso TTD**:
- Encontrar **onde** uma variável foi corrompida (não só quando).
- Reproduzir race conditions raras.
- Backtrack de chamadas de função que alteraram estado.

## Calling conventions customizadas

Para binários com calling convention exótica (Delphi, Go, Rust custom) você pode definir manualmente:

```python
# Exemplo Pascal calling convention (Delphi x86)
pascal_cc = CallingConvention("pascal_x86", "pascal")
pascal_cc.int_arg_regs = []     # args na stack, left-to-right
pascal_cc.int_return_reg = "eax"
pascal_cc.stack_arg_offset = 8

# Go calling convention x86-64 (múltiplos valores de retorno em regs)
go_cc = CallingConvention("go_x64", "go")
go_cc.int_arg_regs = ["rdi", "rsi", "rdx", "rcx", "r8", "r9", "r10", "rax"]
go_cc.int_return_regs = ["rax", "rbx", "rcx", "rdi", "rsi", "r8", "r9", "r10", "r11"]
```

Plugins como **Delphinja** automatizam isso para binários Borland/Embarcadero.

## Patching + export

### Patch in-memory (não escreve no arquivo)

```python
# Modificar bytes in-memory
original = bv.read(0x401020, 4)
print(f"Original: {original.hex()}")

# Trocar por NOP (0x90)
bv.write(0x401020, b"\x90\x90\x90\x90")

# Verificar
patched = bv.read(0x401020, 4)
print(f"Patched: {patched.hex()}")
```

**Output**:
```
Original: e835ffffff
Patched: 90909090
```

### Save BNDB (Binary Ninja Database)

```python
# Salvar análise (renames, tipos, comentários) em BNDB
bv.save("/path/to/sample.bndb")

# Recarregar BNDB depois
bv = BinaryView.open("/path/to/sample.bndb")
```

### Export patched binary

```bash
# Export binário patchado como arquivo standalone
binaryninja --headless --export-bin /path/to/patched.exe /path/to/original.bndb
```

Ou via menu: **File → Save a patched copy**.

### Diff entre dois BNDBs

```python
# Comparar duas versões
old_bv = BinaryView.open("old.bndb")
new_bv = BinaryView.open("new.bndb")

for old_func in old_bv.functions:
    new_func = new_bv.get_function_at(old_func.start)
    if new_func and old_func.name != new_func.name:
        print(f"Rename: {old_func.name} → {new_func.name}")
```

## Performance tips

### BASE mode sampling (default em 6.0)

Base address detection muito mais rápida (sampling em vez de exaustivo).

```python
# Desabilitar BASE sampling só se necessário (raro)
bv.set_analysis_option(bv.analysis_options, "analysis.detectBaseAddress", False)
```

### Analysis Cache

BN cacheia análise em `~/.binaryninja/cache/` (por hash do binário). Análise subsequentes são **instantâneas**.

```bash
# Forçar re-análise (não usar cache)
binaryninja --no-analysis-cache sample.exe
```

### Desabilitar análise custosa

```python
# Desabilitar análises pesadas em binários muito grandes
bv.set_analysis_option(bv.analysis_options, "analysis.types.Writer", False)
bv.set_analysis_option(bv.analysis_options, "analysis.liveness", False)
bv.set_analysis_option(bv.analysis_options, "analysis.types", False)

bv.update_analysis_and_wait()
```

### Memory profile

```python
# Medir consumo de memória após análise
import psutil
process = psutil.Process()
print(f"Memory: {process.memory_info().rss / 1e9:.2f} GB")
```

Benchmarks publicados Vector 35 (vmlinux 6.14): **17.29GB → 12.25GB** em 6.0.

## Custom plugins (esqueleto + exemplos)

### Esqueleto mínimo de plugin

```python
# ~/.binaryninja/plugins/my_plugin/__init__.py
from binaryninja import PluginCommand, BinaryView

def analyze_binary(bv: BinaryView):
    """Command: Analyze Binary → List Suspicious Imports"""
    suspicious = {"VirtualAlloc", "WriteProcessMemory", "CreateRemoteThread",
                  "InternetOpen", "URLDownloadToFile", "WinExec", "ShellExecute"}
    for sym in bv.symbols:
        if sym.type == bv.SymbolType.ImportSymbol and sym.name in suspicious:
            print(f"[!] Suspicious import: {sym.name} @ {hex(sym.address)}")

PluginCommand.register(
    "Analyze Binary\\List Suspicious Imports",
    "Print imports from a curated suspicious-API list",
    analyze_binary,
)
```

### Hook callback em auto-analysis

```python
# Quando uma função é analisada, aplica lógica custom
def on_function_analyzed(bv, func):
    """Callback chamado após análise de cada função"""
    if func.name.startswith("sub_") and "auth" in str(func.parameter_vars):
        func.name = func.name.replace("sub_", "auth_")

# Registrar
bv.function_analysis_changed_event.register(on_function_analyzed)
```

### Custom view (ex: hex highlight)

```python
from binaryninjaui import SidebarWidget

class MySidebar(SidebarWidget):
    def __init__(self, view, bv):
        super().__init__("My Sidebar")
        self.view = view
        self.bv = bv

    def paint(self, painter, size):
        painter.drawText(0, 20, f"Functions: {len(self.bv.functions)}")
        painter.drawText(0, 40, f"Strings: {len(list(self.bv.strings))}")
```

UI widgets requerem `binaryninjaui` (separado do `binaryninja` core).

### Plugin distribution

Use `binaryninja-plugin-manager` ou empacote via `pyproject.toml` com `[project.entry-points."binaryninja.plugins"]`.

## Cross-references com outras skills

### `reverse-engineer` (skill geral RE)

A skill `reverse-engineer` é a central; `binary-ninja` foca exclusivamente em BN. Use:
- `reverse-engineer` para seleção de ferramenta (decision matrix entre IDA/Ghidra/BN/Rizin).
- `binary-ninja` para workflow detalhado quando BN é escolhido.

### `ai-assisted-re` (MCP + LLM workflows)

A skill `ai-assisted-re` cobre MCP servers para múltiplos tools. Quando o workflow é **MCP-driven RE**, comece por lá para setup de cliente LLM; volte aqui para BN-specific operations.

### `malware-analyst` (CAPA, FLOSS, MobSF)

CAPA 9.4 plugin integration: usar `capa-binja` Python package e configurar caminho do CAPA CLI em Settings → Plugins → capa. Output aparece como tags inline no decompiler HLIL.

### `binary-analysis-patterns` (assembly patterns)

Quando o HLIL não é suficiente (obfuscated code, hand-written assembly, anti-analysis tricks), use `binary-analysis-patterns` para identificar padrões em LLIL.

### `firmware-analyst` (IoT/embedded RE)

BN 6.0 cobre 19 arquiteturas incluindo ARMv7/v8, MIPS, RISC-V, AVR, MSP430, PIC, TriCore, PowerPC, SuperH, V850, PA-RISC, 68k, cBPF, TMS320C6x (Ultimate) — adequado para firmware RE moderno. Para chips mais exóticos (Z80, 8051, M6800), Rizin 0.9.1 ou Ghidra 12.1.4.

## Common pitfalls

1. **Python API desabilitada no Free**: tentar `from binaryninja import BinaryView` no Free tier lança erro "Python API not available in Personal Edition". Solução: Commercial/Ultimate ou usar **MCP server** (que funciona no Free).

2. **Atualizar análise após edits**: chamar `bv.update_analysis_and_wait()` após renames/tipos para propagar mudanças.

3. **BNDB não atualiza patches**: patches são in-memory. Para persistir, `bv.save("/path/sample.bndb")`.

4. **Type Fragments confusion**: HLIL pode mostrar múltiplas variáveis para o mesmo dado físico. Use `var.type_fragments` para consolidar.

5. **Multiple Global Pointers (TriCore)**: TriCore tem 4 global registers. Aplicar Globals / Pointers em TriCore binário requer configuração específica.

6. **MCP token exposto**: `ui.mcp.token` permite controle total do BN. Não commitar em repo ou expor em logs.

7. **Windows filesystem locking**: variante headless `binaryninja_mcp` não funciona em Windows. Use GUI variant (`http://127.0.0.1:24642/mcp`).

## Security & ethics

### Authorized use only

- Security research com autorização explícita por escrito.
- CTF competitions e desafios educacionais.
- Malware analysis para propósitos defensivos.
- Vulnerability disclosure via canais responsáveis.
- Interoperability research.
- Penetration testing autorizado dentro de escopo definido.

### Never assist with

- Acesso não autorizado a sistemas/binários sem propriedade/operação.
- Criação de malware para fins maliciosos.
- Bypass de licenciamento de software ilegitimamente.
- Roubo de propriedade intelectual.
- Espionagem industrial.
- Ataques a devices sem permissão.

## Resources

- Vector 35 docs oficiais: https://binary.ninja/
- API Python docs: https://api.binary.ninja/
- Plugin examples: https://github.com/vector35/binaryninja-api/tree/master/examples
- BinSync: https://github.com/vector35/binsync
- capa-binja: https://github.com/mandiant/capa
- AI-assisted-RE skill — MCP + LLM integration
- Reverse-engineer skill — central RE workflow
- Anti-reversing-techniques — packer/obfuscation bypass
- Binary-analysis-patterns — disassembly patterns

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

- Binary Ninja 6.0 "Krypton" release notes (Vector 35, 03 set 2026)
- Binary Ninja 5.2 release notes (Vector 35, 13 nov 2025)
- Vector 35 blog: "Krypton Announcement" (28 jul 2026)
- Vector 35 docs: Python API, Plugins, MCP server
- research-mercado-RE-2025-2026.md §1.3 (HINDSIGHT, 22 set 2026)