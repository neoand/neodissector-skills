---
name: memory-forensics
description: "Memory forensics for incident response and malware analysis using Volatility 3 v2.28.2 (set 2026), Velociraptor 0.7.x, MemProcFS 5.x, WinPmem, LiME, osxpmem, and YARA. Covers Windows/Linux/macOS memory acquisition, plugin workflows (pslist, malfind, pebmasquerade, sockscan, etwpatch, banners), Mermaid renderer, and modern DFIR endpoint alternatives."
disable-model-invocation: true
risk: unknown
source: community
date_added: '2026-09-22'
---

> **DFIR companion — fora do workflow padrão do `system-dissector`.** Esta skill cobre aquisição/análise de memory dumps (Volatility 3, Velociraptor, MemProcFS). Não é invocada nas 4-5 fases normais do `system-dissector` (source/binary/mobile/firmware/protocol). Use apenas quando o alvo inclui memory dump pós-exploit. Veja seção "Integração com system-dissector" abaixo.

# Memory Forensics — Modern Toolchain (2026)

Memory acquisition, live endpoint analysis, and dump parsing for authorized IR, malware triage, and forensic investigations. Anchored on **Volatility 3 v2.28.2** (17 set 2026), with **Velociraptor 0.7.x** and **MemProcFS 5.x** as first-class DFIR endpoints. ⚠️ Versions marked "verify before use" were not pinned in the source research — confirm at runtime.

## TL;DR

- **Volatility 3 v2.28.2** (17 set 2026) — paridade funcional com V2 alcançada em **v2.26.0** (16 mai 2025). Releases mensais ativos.
- **Novos plugins críticos** (2025-2026): `windows.pebmasquerade` (v2.27.0), `linux.sockscan` (v2.28.0), `linux.process_spoofing` (v2.28.0), `windows.etwpatch` (v2.26.2), `windows.banners` (v2.28.0), `windows.vadyarascan` (v2.27.0).
- **Renderer Mermaid** (v2.28.2) — tree relationship visualization para reports visuais.
- **macOS analysis deprecated** desde v2.28.0 (PR #1972) — emite warning automático.
- **ruff** substitui linters legacy (v2.28.0); **Cryptodome** namespace suportado; **S3/GCS** layers (v2.5.2+).
- **Velociraptor 0.7.x** (⚠️ verify) — endpoint agent com VQL hunts, Notebooks, timelines.
- **MemProcFS 5.x** (⚠️ verify) — interface filesystem-style para memory.

## Use this skill when

- Working memory forensics tasks (acquisition, analysis, IOC extraction)
- Triaging malware a partir de process injection, rootkits, ou credential theft
- Construindo IR workflow sobre Volatility 3 + YARA
- Decidindo entre Volatility 3 standalone, Velociraptor endpoint, ou MemProcFS
- Operando em ambientes cloud (AWS / GCP) com snapshots de memória
- Modernizando DFIR pipeline (Cuckoo/Rekall → Vol3 + Velociraptor)

## Do not use this skill when

- O target é disco (disk forensics) — use `binary-analysis-patterns` ou disk image skills
- O target é firmware/IoT — use `firmware-analyst`
- O target é mobile (Android/iOS) — use `mobile-re`
- Você precisa só de static reversing sem análise runtime — use `reverse-engineer`
- Você precisa de código fonte — análise de código direto, sem memory artifacts

## Modern toolchain overview (set 2026)

| Tool | Version | Best for | License | Notes |
|---|---|---|---|---|
| Volatility 3 | **v2.28.2** (17 set 2026) | Memory dump analysis | VPL v2 (foundation) | Parity V2 desde mai 2025 |
| Velociraptor | **0.7.x** (⚠️ verify) | DFIR endpoint agent, VQL hunts | AGPLv3 | Notebooks, timeline, multi-tenant |
| MemProcFS | **5.x** (⚠️ verify) | Filesystem-style memory access | Apache 2.0 | FUSE-like, recursive mode |
| WinPmem | 4.x (2025) | Windows acquisition | Apache 2.0 | ReFS / pagefile / kernel modules |
| LiME | 1.9.x | Linux acquisition | GPLv2 | Kernel module, formato `.lime` |
| osxpmem | 2.x | macOS acquisition (legacy) | Apache 2.0 | Deprecated com Vol3 macOS |
| YARA | 4.5+ | Pattern scanning | VPL v2 | Via `windows.yarascan` / `vadyarascan` |
| FLOSS | 3.1.1 | Obfuscated strings | Apache 2.0 | Rust `floss` + Python legacy |
| Rekall | abandoned | Legacy V2 fork | Apache 2 | **NÃO usar** (último commit 2020-2021) |

### Volatility 3 release timeline (relevante para 2025-2026)

- **v2.28.2 (17 set 2026)**: rework banner output, renderers como package, novo **renderer Mermaid** (tree relationship), arrow renderer removido do binary (size).
- **v2.28.0 (30 abr 2026)**: Intel layer translation checks, Timeliner body format, Windows console UTF-8, **ruff** para lint+format, **linux.sockscan** plugin (eve-mem), **linux.process_spoofing** plugin, **windows.banners** support, Windows 11 intel detection, suporte **Cryptodome** namespace.
- **v2.27.0 (29 jan 2026)**: **windows.pebmasquerade** plugin, arrow/parquet renderer, `windows.dlllist` melhorado, `windows.vadyarascan`.
- **v2.26.2 (25 set 2025)**: malware plugins reorganizados (`linux.malware.*`, `windows.malware.*`), **windows.etwpatch** plugin, **volshell breakpoints** (watchpoints em layer/offset).
- **v2.26.0 (16 mai 2025)**: **paridade funcional com Volatility 2** alcançada. +Linux plugins: `graphics.fbdev`, `ip`, `kallsyms`, `module_extract`, `modxview`, `pscallstack`, `tracing.ftrace`, `tracing.perf_events`, `tracing.tracepoints`, `vmaregexscan`, `vmcoreinfo`. macOS `regexscan`. Windows `deskscan`, `desktops`, `direct_system_calls`, `indirect_system_calls`, `suspended_threads`, `vadregexscan`, `windows`, `windowstations`. `pyproject.toml` modernization.
- **v2.11.0 (16 jan 2025)**: Linux `boottime`, `ebpf`, `hidden_modules`, `kthreads`, `pagecache`, `pidhashtable`, `ptrace`. Windows `amcache`, `cmdscan`, `consoles`, `debugregisters`, `orphan_kernel_threads`, `pe_symbols`, `scheduled_tasks`, `unhooked_system_calls`.
- **v2.5.2 (31 jan 2024)**: **Amazon S3** + **Google Cloud Storage** como layers.
- **macOS support**: marcado como **deprecated warning** desde v2.28.0 (PR #1972) — emite warning em runtime, sem remoção imediata.

## Memory Acquisition

### Live acquisition tools

#### Windows (WinPmem — recommended)

```powershell
# WinPmem 4.x (2025): suporta Windows 11, ReFS, pagefile
winpmem_mini_x64.exe memory.raw

# Opções úteis
winpmem_mini_x64.exe -o memory.raw                 # explicit output
winpmem_mini_x64.exe memory.raw --pagefile         # inclui pagefile
winpmem_mini_x64.exe memory.raw --kernel-module    # dump kernel modules

# Alternativas GUI (legacy): DumpIt, Belkasoft RAM Capturer, Magnet RAM Capture
```

#### Linux (LiME)

```bash
# Compilar LiME matching kernel
make -C /path/to/lime

# Carregar módulo com formato lime (preserva offsets)
sudo insmod lime.ko "path=/tmp/memory.lime format=lime"

# Ou raw
sudo insmod lime.ko "path=/tmp/memory.raw format=raw"

# Alternativas: AVML (Microsoft, eBPF-based), dd /dev/mem (limitado), /proc/kcore (ELF)
sudo dd if=/dev/mem of=memory.raw bs=1M           # limitado, requer CAP_SYS_RAWIO
sudo cp /proc/kcore memory.elf                     # ELF, requer root
```

#### macOS (osxpmem — legacy)

```bash
# macOS acquisition marcado deprecated com Vol3 — ainda funciona para IR
sudo ./osxpmem -o memory.raw

# Alternativas: MacQuisition (commercial), Radare2 r2pmem
```

#### Virtual machine memory

```bash
# VMware: .vmem é raw memory
cp vm.vmem memory.raw

# VirtualBox
vboxmanage debugvm "VMName" dumpvmcore --filename memory.elf

# QEMU/KVM
virsh dump <domain> memory.raw --memory-only
virsh dump <domain> memory.lime --memory-only --format=lime

# Hyper-V: checkpoint contém memory state
```

### Cloud-native acquisition (v2.5.2+)

```bash
# AWS EC2: SSM Run Command + amlite (Microsoft, eBPF-based)
aws ssm send-command --instance-ids "i-0123..." \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["sudo yum install -y amlite && sudo amlite -o /tmp/memory.lime"]'

# Upload direto via v2.5.2+ layers (S3 ou GCS)
aws s3 cp /tmp/memory.lime s3://forensics-bucket/cases/case-001/
```

> **IR cloud tip**: prefira snapshot do volume EBS / persistent disk + boot debug, ou rode acquisition via SSM/Run Command sem precisar de SSH.

## Volatility 3 v2.28.2 — Installation

### Standard install

```bash
# PyPI
pip install volatility3

# Verificar versão
vol --version
# esperado: Volatility 3 Framework 2.28.2

# Symbol tables (Windows PDBs)
# Download matching OS version from
# https://downloads.volatilityfoundation.org/volatility3/symbols/

# Symbol path explícito
vol -f memory.raw -s /path/to/symbols windows.pslist

# Auto-detect symbol from BSoD dump
vol -f memory.raw windows.pslist  # tenta symbols built-in primeiro
```

### Development install (recommended para contrib)

```bash
git clone https://github.com/volatilityfoundation/volatility3.git
cd volatility3
python -m pip install -e .
pre-commit install                # ruff hooks (v2.28.0+)
```

### Dev environment (v2.28.0+)

- **ruff** substitui flake8/black/isort — `ruff check` e `ruff format` antes de PR
- Python 3.10+ required (3.12 LTS recomendado)
- **Cryptodome** namespace suportado automaticamente (fallback se `Crypto` não instalado)

## Process analysis plugins

### Core pslist/pstree (V3 equivalentes ao V2)

```bash
# Listagem simples
vol -f memory.raw windows.pslist

# Tree parent-child (renderer ASCII; v2.28.2+ também Mermaid)
vol -f memory.raw windows.pstree

# Hidden process detection via pool scanning
vol -f memory.raw windows.psscan

# Memória mapeada de um PID
vol -f memory.raw windows.memmap --pid 1234 --dump

# Environment variables
vol -f memory.raw windows.envars --pid 1234

# Command line (com argumentos unpacked)
vol -f memory.raw windows.cmdline

# Cross-reference (list + scan): detecta DKOM rootkits
vol -f memory.raw windows.pslist > pslist.txt
vol -f memory.raw windows.psscan > psscan.txt
diff pslist.txt psscan.txt   # processos em psscan mas não pslist = suspeitos
```

### NEW: `windows.pebmasquerade` (v2.27.0)

Detecta processos cuja PEB foi manipulada para esconder o caminho real do executável (técnica comum em EDR-evasion e APT tradecraft).

```bash
# Detecta PEB spoofing / masquerading
vol -f memory.raw windows.pebmasquerade

# Saída típica: PEB claims ImagePathName = C:\Windows\System32\svchost.exe
# mas VAD / SectionObject aponta para C:\Users\victim\appdata\malware.exe
```

### NEW: `linux.process_spoofing` (v2.28.0)

Equivalente Linux: detecta `comm`/`cmdline` mismatch (rootkit LKM esconde argv).

```bash
vol -f memory.lime linux.process_spoofing
# Cruza task->comm (user-visible) com task->mm->arg_start (real argv)
```

## Network analysis plugins

### Windows

```bash
# Conexões ativas (com pool scan, mais robusto que netstat)
vol -f memory.raw windows.netscan

# Estado de conexão (sk-based, requer symbols)
vol -f memory.raw windows.netstat

# Connections por processo
vol -f memory.raw windows.netscan | grep -i "<PID>"
```

### NEW: `linux.sockscan` (v2.28.0, portado do eve-mem)

Plugin avançado de socket scanning para Linux (análise completa de inode + sk_buff).

```bash
vol -f memory.lime linux.sockscan
vol -f memory.lime linux.sockscan --tcp
vol -f memory.lime linux.sockscan --udp --pid 1234
```

> **Origem**: baseado em [eve-mem/linux-sockscan](https://github.com/arget13/DDAC). V2.28.0 unificou upstream.

### Legacy V2 → V3 mapping (network)

| V2 plugin | V3 plugin | Notes |
|---|---|---|
| `connections` | `windows.netscan` | Pool scan |
| `connscan` | `windows.netscan` | Mesma engine |
| `sockets` | `windows.netscan` | Inclui sockets |
| `netstat` | `windows.netstat` | Sk-based |
| `sockscan` (linux) | `linux.sockscan` (v2.28.0) | Antes só em eve-mem |

## DLL & module analysis

```bash
# DLLs loaded em um processo
vol -f memory.raw windows.dlllist --pid 1234

# Detecta DLLs loaded fora do PEB Ldr list (injected)
vol -f memory.raw windows.ldrmodules --pid 1234

# Kernel modules
vol -f memory.raw windows.modules

# Dump módulos para análise estática
vol -f memory.raw windows.moddump --pid 1234 -o ./dumps/

# Linux
vol -f memory.lime linux.lsmod
vol -f memory.lime linux.lsof --pid 1234
vol -f memory.lime linux.module_extract --module <name>   # v2.26.0+
```

## Memory injection detection

### `windows.malfind` — clássico

```bash
# Detecta PAGE_EXECUTE_READWRITE + MZ header em VAD não-image
vol -f memory.raw windows.malfind
vol -f memory.raw windows.malfind --pid 1234 -o ./malfind_dumps/
```

### NEW: `windows.vadyarascan` (v2.27.0, melhorado)

YARA scan dentro de Virtual Address Descriptors (VAD) — substitui/estende o `vadyarascan` V2.

```bash
# Scan todos VADs com regra YARA
vol -f memory.raw windows.vadyarascan --yara-rules malware.yar

# Apenas um processo
vol -f memory.raw windows.vadyarascan --yara-rules malware.yar --pid 1234

# Output structured JSON (v2.27.0+)
vol -f memory.raw --renderer json windows.vadyarascan --yara-rules cobalt.yar > findings.json
```

### VAD analysis

```bash
vol -f memory.raw windows.vadinfo --pid 1234
vol -f memory.raw windows.vadwalk --pid 1234
```

## Registry analysis

```bash
# List registry hives
vol -f memory.raw windows.registry.hivelist

# Persistência clássica (Run / RunOnce / RunServices)
for KEY in \
  "Software\Microsoft\Windows\CurrentVersion\Run" \
  "Microsoft\Windows\CurrentVersion\RunOnce" \
  "Microsoft\Windows\CurrentVersion\RunServices"; do
  vol -f memory.raw windows.registry.printkey --key "$KEY"
done

# Dump hive offline (regipy / Registry Explorer)
vol -f memory.raw windows.registry.hivescan --dump -o ./hives/

# Execução recente + compat shim
vol -f memory.raw windows.registry.userassist
vol -f memory.raw windows.shimcache
```

## File system artifacts

```bash
# File objects (em memória, pode incluir deletados)
vol -f memory.raw windows.filescan

# Dump arquivo específico (por offset)
vol -f memory.raw windows.dumpfiles --virtaddr 0x....
vol -f memory.raw windows.dumpfiles --physaddr 0x....

# MFT analysis (master file table)
vol -f memory.raw windows.mftscan
vol -f memory.raw windows.mftparser.MFT --output mft.csv   # v2.11.0+

# Direct system calls (EDR evasion indicator)
vol -f memory.raw windows.direct_system_calls --pid 1234  # v2.26.0+
vol -f memory.raw windows.indirect_system_calls --pid 1234 # v2.26.0+
```

## NEW plugins 2025-2026 — quick reference

| Plugin | Introduced | Purpose | Use case |
|---|---|---|---|
| `windows.pebmasquerade` | v2.27.0 (jan 2026) | Detecta PEB spoofing | EDR-evasion tradecraft |
| `linux.sockscan` | v2.28.0 (abr 2026) | Socket scan completo | Linux C2 detection |
| `linux.process_spoofing` | v2.28.0 (abr 2026) | comm vs argv | Linux rootkits |
| `windows.etwpatch` | v2.26.2 (set 2025) | Detecta ETW patching | EDR-blind malware |
| `windows.banners` | v2.28.0 (abr 2026) | Banner/kbanner artifact | RDP/Telnet forensics |
| `windows.vadyarascan` | v2.27.0 (jan 2026) | YARA in VAD | Replaces v2 plugin |
| `windows.direct_system_calls` | v2.26.0 (mai 2025) | Syscall direto via syscall;ret | EDR bypass detection |
| `windows.indirect_system_calls` | v2.26.0 (mai 2025) | Syscall via unhooked helper | EDR bypass detection |
| `windows.suspended_threads` | v2.26.0 (mai 2025) | Threads em estado suspended | Injection staging |
| `windows.deskscan` | v2.26.0 | Desktop objects | User activity |
| `linux.pscallstack` | v2.26.0 | Callstack por task | Rootkit detection |
| `linux.tracing.ftrace` | v2.26.0 | ftrace buffers | Kernel tracing |
| `linux.tracing.perf_events` | v2.26.0 | perf event buffers | Profiling |
| `linux.tracing.tracepoints` | v2.26.0 | Tracepoint state | Kernel introspection |
| `linux.vmcoreinfo` | v2.26.0 | VMCOREINFO extraction | Kdump-compat |
| `linux.graphics.fbdev` | v2.26.0 | Framebuffer dump | Visual sessions |
| `linux.kallsyms` | v2.26.0 | Kernel symbols | Symbol resolution |

### `windows.etwpatch` (v2.26.2)

Detecta patches em ETW (Event Tracing for Windows) consumers — usado por malware para cegar EDRs baseados em ETW.

```bash
vol -f memory.raw windows.etwpatch
# Saída: endereços patcheados, processo injetor (geralmente ntdll ou próprio malware)
```

### `windows.banners` (v2.28.0)

Extrai banners de RDP, Telnet, SSH, SMB que apareceram em sessões de usuário.

```bash
vol -f memory.raw windows.banners
vol -f memory.raw windows.banners --type rdp
```

## NEW: Mermaid renderer (v2.28.2)

Renderer opcional para output em formato **Mermaid** (diagram-as-code). Útil para relatórios técnicos visuais.

```bash
# Pstree como Mermaid (tree relationship)
vol -f memory.raw --renderer mermaid windows.pstree > pstree.mmd

# Exemplo output:
# graph tree
#   0["System"]
#   4["System"]
#   628["smss.exe"]
#   704["csrss.exe"]
#   ...

# Renderizar com mmdc ou em markdown
npx -p @mermaid-js/mermaid-cli mmdc -i pstree.mmd -o pstree.svg

# Combinar com netstat para correlacionar processo↔conexão
vol -f memory.raw --renderer mermaid windows.netscan > netscan.mmd
```

> **Use case**: post-mortem reports, IR documentation, anexar ao Confluence/Notion.

## NEW: macOS deprecated warning (v2.28.0, PR #1972)

Desde **v2.28.0**, plugins macOS emitem warning de deprecation:

```
WARNING  volatility3.framework: macOS support is deprecated and will be removed
         in a future release. Consider migrating to Velociraptor or another
         DFIR endpoint tool for macOS analysis.
```

- Plugins **continuam funcionando** (sem remoção imediata) — `mac.pslist`, `mac.pstree`, `mac.netstat`, `mac.lsmod`, `mac.regexscan` (v2.26.0+)
- Para IR macOS moderno, migre para **Velociraptor** (integração osquery) ou ferramentas nativas (`log show`, Console.app)

## Velociraptor 0.7.x — DFIR endpoint alternative

⚠️ Versão exata não verificada — confirmar em [Velocidex/velociraptor/releases](https://github.com/Velocidex/velociraptor/releases) (série 0.7.x).

Velociraptor é **endpoint agent + server** para DFIR em escala. **Complementa** Volatility — não substitui.

Use quando: acquisition contínua, VQL hunts (SQL-like), timeline consolidado multi-host, Notebooks.

Componentes: `velociraptor` binary (agent) + server + GUI web.

```sql
-- VQL: hunt executáveis suspeitos em AppData
SELECT FullPath, Size, Mtime
FROM glob(globs="C:/Users/*/AppData/**/*.exe")
WHERE Size < 5MB AND Mtime > timestamp("2026-09-01")

-- VQL: memory artifact (V3.0+)
SELECT Pid, Name, CommandLine
FROM pslist()
WHERE Name =~ "(?i)powershell|cmd|wmic"
```

| Cenário | Ferramenta |
|---|---|
| Single host, single dump | **Volatility 3** |
| Fleet (100+ endpoints), caça proativa | **Velociraptor** |
| IR ad-hoc com coleta rápida | Velociraptor (agent) ou Vol3 (WinPmem) |
| Análise pós-coleta | Vol3 sobre dump do Velociraptor |
| macOS moderno | Velociraptor (Vol3 macOS deprecated) |

## MemProcFS — filesystem-style memory access

⚠️ Versão exata (5.x) não verificada — confirmar em [ufrisk/MemProcFS](https://github.com/ufrisk/MemProcFS).

MemProcFS monta uma memory dump como **filesystem virtual** (FUSE-like):

```bash
# Montar dump
./memprocfs -mount /mnt/mem -forensic memory.raw

# Navegar como filesystem
ls /mnt/mem/name/                 # processos
ls /mnt/mem/pid/1234/             # estrutura do processo
cat /mnt/mem/pid/1234/cmdline.txt
cat /mnt/mem/pid/1234/environ.json
ls /mnt/mem/sys/net/              # conexões
ls /mnt/mem/registry/             # registry hives
```

| Cenário | Ferramenta |
|---|---|
| Exploração rápida, integração com qualquer tool que lê FS | **MemProcFS** |
| Análise estruturada, plugins reproduzíveis, scripting | **Volatility 3** |

## YARA integration

### Memory YARA rules

```yara
import "pe"

rule Suspicious_Injection_Generic
{
    meta:
        description = "Detects common shellcode injection patterns"
        author = "ir-team"
        date = "2026-09-22"

    strings:
        $mz = { 4D 5A }
        $prologue1 = { 55 8B EC 83 EC ?? }        // push ebp; mov ebp,esp; sub esp
        $prologue2 = { 48 89 5C 24 ?? }            // mov [rsp+X], rbx
        $api_hash_push = { 68 ?? ?? ?? ?? 68 ?? ?? ?? ?? E8 }  // push-hash call pattern

    condition:
        $mz at 0 or any of ($prologue*) or $api_hash_push
}

rule Cobalt_Strike_Beacon_Memory
{
    meta:
        description = "Cobalt Strike beacon in process memory"
        severity = "high"

    strings:
        $cfg_marker = { 00 01 00 01 00 02 }
        $sleep_keyword = "sleeptime"
        $beacon_indicator = "%s (admin)" wide ascii
        $watermark = { B8 00 00 00 ?? }           // common CS xor key

    condition:
        2 of them
}

rule CobaltStrike_Default_Pipe
{
    meta:
        description = "Cobalt Strike default named pipe"
        strings:
        $pipe = "\\\\.\\pipe\\msagent_" ascii
        $pipe2 = "postex_" ascii
    condition:
        any of them
}
```

### Scanning memory with YARA

```bash
# Scan all process memory (vadyarascan — preferred post v2.27.0)
vol -f memory.raw windows.vadyarascan --yara-rules rules.yar

# Legacy yarascan (todos os address spaces)
vol -f memory.raw windows.yarascan --yara-rules rules.yar

# Kernel memory
vol -f memory.raw windows.yarascan --yara-rules rules.yar --kernel

# PID específico
vol -f memory.raw windows.yarascan --yara-rules cobalt.yar --pid 1234

# Output JSON para SIEM
vol -f memory.raw --renderer json windows.vadyarascan --yara-rules cobalt.yar > cobalt_findings.json
```

## String analysis (FLOSS)

```bash
# ASCII + Unicode (UTF-16 LE)
strings -a memory.raw > ascii.txt
strings -el memory.raw >> all_strings.txt

# Pattern matching (URLs, IPs)
grep -E "(https?://|[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})" all_strings.txt

# FLOSS 3.1.1 (Rust) — extrai strings obfuscadas (XOR, Base64, stack-strings)
floss malware.exe > floss_output.txt

# From process dump
vol -f memory.raw windows.memmap --pid 1234 --dump
floss pid.1234.dmp > process_floss.txt
```

## Data structures (referência)

### Windows: EPROCESS

```c
typedef struct _EPROCESS {
    KPROCESS Pcb;                    // Kernel process block (scheduling, affinity)
    EX_PUSH_LOCK ProcessLock;
    LARGE_INTEGER CreateTime;        // Process creation time (FILETIME)
    LARGE_INTEGER ExitTime;
    // ... (active links, token, quota, etc.)
    LIST_ENTRY ActiveProcessLinks;   // Doubly-linked list (DKOM target!)
    ULONG_PTR UniqueProcessId;       // PID
    // ...
    PEB* Peb;                        // Process Environment Block (usermode)
    // ...
} EPROCESS;
```

> **DKOM tradecraft**: `ActiveProcessLinks` removido para esconder processo de `pslist` (mantém visível em `psscan` — pool scan).

### Windows: PEB

```c
typedef struct _PEB {
    BOOLEAN InheritedAddressSpace;
    BOOLEAN ReadImageFileExecOptions;
    BOOLEAN BeingDebugged;           // Anti-debug indicator
    UCHAR Padding[1];
    // ...
    PVOID ImageBaseAddress;          // Base address of executable
    PPEB_LDR_DATA Ldr;               // Loader data (PPEB_LDR_DATA → InMemoryOrderModuleList)
    PRTL_USER_PROCESS_PARAMETERS ProcessParameters;  // CommandLine, ImagePathName
    // ...
} PEB;
```

> **PEB masquerade**: malware spoofa `ProcessParameters.ImagePathName` — `pebmasquerade` (v2.27.0) detecta via cross-reference com VAD/SectionObject.

### Windows: VAD (Virtual Address Descriptor)

```c
typedef struct _MMVAD {
    MMVAD_SHORT Core;
    union {
        ULONG LongFlags;
        MMVAD_FLAGS VadFlags;
    } u;
    // ...
    PVOID FirstPrototypePte;
    PVOID LastContiguousPte;
    PFILE_OBJECT FileObject;         // Null em memória privada
} MMVAD;

// Memory protection constants
#define PAGE_EXECUTE           0x10
#define PAGE_EXECUTE_READ      0x20
#define PAGE_EXECUTE_READWRITE 0x40  // ← malfind indicator (alta entropia + MZ)
#define PAGE_EXECUTE_WRITECOPY 0x80
```

## Detection patterns

### Process injection indicators

`malfind` signals (all detectable via Vol3 plugins):

- **Suspicious permissions**: PAGE_EXECUTE_READWRITE / PAGE_EXECUTE_WRITECOPY em VAD privada
- **MZ header em VAD não-image**: DLL injection / process hollowing staging
- **Shellcode patterns**: API hash + call (`push imm32; push imm32; call`), ROP gadgets, `syscall;ret`
- **PEB spoof**: `ProcessParameters.ImagePathName` ≠ VAD `FileObject` path → `windows.pebmasquerade`

Common injection techniques (todas detectáveis via `windows.malfind` + `vadyarascan`):

1. Classic DLL Injection — `VirtualAllocEx` + `WriteProcessMemory` + `CreateRemoteThread`
2. Process Hollowing — `CreateProcess(SUSPENDED)` + `NtUnmapViewOfSection` + `WriteProcessMemory`
3. APC Injection — `QueueUserAPC` targeting alertable threads
4. Thread Execution Hijacking — `SuspendThread` + `SetThreadContext` + `ResumeThread`
5. Process Doppelgänging — TxF transaction abuse (Win10+ removed)
6. Module Stomping — map legit PE, overwrite `.text` with shellcode
7. PEB spoofing — masquerade process path (`pebmasquerade` v2.27.0+)

### Rootkit detection

```bash
# Compare lists (DKOM)
vol -f memory.raw windows.pslist > pslist.txt
vol -f memory.raw windows.psscan > psscan.txt
diff pslist.txt psscan.txt

# Callbacks (registry, driver notification)
vol -f memory.raw windows.callbacks

# SSDT hooks (legacy, x86 only)
vol -f memory.raw windows.ssdt

# Driver objects
vol -f memory.raw windows.driverscan
vol -f memory.raw windows.driverirp
vol -f memory.raw windows.modules | grep -i "<rootkit>"

# Linux
vol -f memory.lime linux.lsmod | grep -v "^Module"
vol -f memory.lime linux.hidden_modules         # v2.11.0+
vol -f memory.lime linux.pscallstack --pid 1   # init — rootkits hooks aqui
```

### Credential extraction

```bash
# SAM/SYSTEM hashes (Windows)
vol -f memory.raw windows.hashdump             # requer SYSTEM hive offset
vol -f memory.raw windows.hashdump.Hashdump    # nome longo em v2

# LSA secrets
vol -f memory.raw windows.lsadump

# Cached domain credentials
vol -f memory.raw windows.cachedump

# Mimikatz-style: requer símbolos + LSA dump offline com mimikatz
# (Vol3 não extrai plaintext passwords diretamente — use sekurlsa::logonpasswords)
```

## Malware analysis workflow (atualizado v2.28.2)

```bash
# 1. Overview
vol -f memory.raw windows.pslist > processes.txt
vol -f memory.raw windows.pstree > pstree.txt

# 2. Network (sockets, conexões)
vol -f memory.raw windows.netscan > network.txt

# 3. Injection detection (VAD YARA + malfind)
vol -f memory.raw windows.malfind > malfind.txt
vol -f memory.raw windows.vadyarascan --yara-rules malware.yar > vad_yara.json

# 4. PEB spoof detection (v2.27.0+)
vol -f memory.raw windows.pebmasquerade > peb_masq.txt

# 5. ETW patch detection (v2.26.2+)
vol -f memory.raw windows.etwpatch > etw_patches.txt

# 6. Análise por PID suspeito
PID=1234
vol -f memory.raw windows.dlllist --pid $PID
vol -f memory.raw windows.handles --pid $PID
vol -f memory.raw windows.cmdline --pid $PID

# 7. Dump processo para análise estática
vol -f memory.raw windows.memmap --pid $PID --dump -o ./dumps/

# 8. Strings + FLOSS nos dumps
strings -a ./dumps/pid.$PID.dmp > ascii.txt
floss ./dumps/pid.$PID.dmp > floss.txt

# 9. Direct syscall detection (v2.26.0+)
vol -f memory.raw windows.direct_system_calls --pid $PID

# 10. YARA scan consolidado
vol -f memory.raw --renderer json windows.vadyarascan --yara-rules cobalt.yar > findings.json
```

## Incident response workflow (atualizado v2.28.2)

```bash
# 1. Timeline consolidado
vol -f memory.raw windows.timeliner > timeline.csv
vol -f memory.raw windows.timeliner.Timeliner --renderer mermaid > timeline.mmd  # v2.28.2

# 2. User activity
vol -f memory.raw windows.cmdline
vol -f memory.raw windows.consoles
vol -f memory.raw windows.cmdscan         # v2.11.0+

# 3. Persistence
vol -f memory.raw windows.registry.printkey \
    --key "Software\Microsoft\Windows\CurrentVersion\Run"
vol -f memory.raw windows.scheduled_tasks  # v2.11.0+
vol -f memory.raw windows.services.svcscan

# 4. Network forensics
vol -f memory.raw windows.netscan > network.txt
vol -f memory.raw windows.netstat

# 5. Banners (RDP/Telnet) — v2.28.0
vol -f memory.raw windows.banners

# 6. Kernel integrity
vol -f memory.raw windows.callbacks
vol -f memory.raw windows.modules
vol -f memory.raw windows.ssdt

# 7. YARA scan final
vol -f memory.raw windows.vadyarascan --yara-rules full_rules.yar --renderer json > final.json
```

## Linux analysis (v2.26.0+ parity)

```bash
# Core
vol -f memory.lime linux.pslist
vol -f memory.lime linux.pstree
vol -f memory.lime linux.bash               # bash history em memória
vol -f memory.lime linux.envars
vol -f memory.lime linux.mount

# Network (v2.28.0)
vol -f memory.lime linux.sockscan
vol -f memory.lime linux.sockstat

# Modules (v2.26.0+: modxview, kallsyms)
vol -f memory.lime linux.lsmod
vol -f memory.lime linux.hidden_modules     # v2.11.0+
vol -f memory.lime linux.modxview
vol -f memory.lime linux.kallsyms

# Process introspection (v2.11.0+: pidhashtable, ptrace; v2.26.0+: pscallstack; v2.28.0: process_spoofing)
vol -f memory.lime linux.lsof --pid 1234
vol -f memory.lime linux.pscallstack
vol -f memory.lime linux.process_spoofing

# Tracing (v2.26.0+)
vol -f memory.lime linux.tracing.ftrace
vol -f memory.lime linux.tracing.perf_events
vol -f memory.lime linux.tracing.tracepoints

# Kernel state
vol -f memory.lime linux.kthreads           # v2.11.0+
vol -f memory.lime linux.boottime           # v2.11.0+
vol -f memory.lime linux.vmcoreinfo         # v2.26.0+
vol -f memory.lime linux.ebpf               # v2.11.0+ (programs/maps)
vol -f memory.lime linux.pagecache          # v2.11.0+

# Files
vol -f memory.lime linux.module_extract --module <name>  # v2.26.0+
vol -f memory.lime linux.graphics.fbdev     # v2.26.0+ (framebuffer)

# Malware (v2.26.2+ reorganização)
vol -f memory.lime linux.malware.malfind
```

## Best practices

### Acquisition

1. **Minimize footprint** — use static binary (WinPmem_mini, LiME) sem install
2. **Hash immediately** — SHA-256 do dump assim que acquisition termina
3. **Chain of custody** — registre timestamp, host, tool, operator
4. **Acquire pagefile too** — `winpmem ... --pagefile` melhora pslist/netstat
5. **Document kernel version** — symbols V3 dependem do matching PDB

### Analysis

1. **Start broad, drill deep** — `pstree` → `netscan` → `malfind` → por PID
2. **Cross-reference** — pslist vs psscan (DKOM); PEB vs VAD (masquerade); VAD vs yara
3. **Use multiple renderers** — JSON para SIEM, Mermaid (v2.28.2) para reports visuais
4. **YARA iteration** — comece genérico, refine com base nos findings
5. **Correlate timelines** — memory + disk + network (velociraptor timeline aggregator)
6. **Validate findings** — re-run com plugin diferente para confirmar

### Modern IR pipeline (recommended)

```text
Velociraptor hunt (VQL)
  → identify compromised hosts
  → collect memory artifact (.lime / .raw)
  → upload to S3/GCS (v2.5.2+)
  → run Volatility 3 v2.28.2 locally
  → dump suspicious processes
  → YARA scan com FLOSS
  → timeline Mermaid renderer (v2.28.2)
  → correlate com osquery/Vol3 findings
```

## Common pitfalls

| Pitfall | Mitigation |
|---|---|
| **Stale dump** — acquisition demora, memória muda | Capture ASAP; documente hora de aquisição |
| **Incomplete dump** — pagefile não incluído | `winpmem ... --pagefile` |
| **Symbol mismatch** — PDB errado | Verifique build number exato (`ver`, `uname -r`); use Symbol Server |
| **Smear** — aquisição interfere no estado | Use passive DMA / sleep mínimo / static binary |
| **Encryption at rest** — BitLocker, FileVault, LUKS | Procure `.efi`, recovery key, ou use Velociraptor pre-boot |
| **macOS deprecated** | Migre para Velociraptor (⚠️ verify) ou ferramenta nativa |
| **Vol2 vs Vol3 confusão** | V3 plugins: `windows.*`, `linux.*`, `mac.*` (não `volatility.plugins.*`) |
| **Rekall** (abandoned) | **NÃO use** — Vol3 cobre tudo desde v2.26.0 |
| **WinPmem loading driver** | EDR pode flagar; assine/installer em ambiente controlado |
| **Velociraptor em produção** | Teste em lab primeiro — agent é persistente |
| **YARA rules não match** | Verifique encoding (UTF-8 vs UTF-16 LE), use `wide ascii` |
| **Cryptodome ausente** | `pip install pycryptodome` (v2.28.0+ resolve automaticamente) |
| **Renderer Mermaid não renderiza** | Use `@mermaid-js/mermaid-cli` ou GitHub Markdown direto |

## References

### Volatility 3 ecosystem

- **GitHub**: <https://github.com/volatilityfoundation/volatility3> (releases mensais, v2.28.2)
- **Docs**: <https://volatility3.readthedocs.io/>
- **Symbol tables**: <https://downloads.volatilityfoundation.org/volatility3/symbols/>
- **Microsoft Symbol Server**: `https://msdl.microsoft.com/download/symbols`
- **PDB Downloader**: <https://github.com/wumb0/pdb_downloader>

### DFIR endpoint alternatives

- **Velocidex/velociraptor**: <https://github.com/Velocidex/velociraptor> ⚠️ verify 0.7.x
- **ufrisk/MemProcFS**: <https://github.com/ufrisk/MemProcFS> ⚠️ verify 5.x
- **WinPmem**: distribuído via Velocidex (`/binaries`) — ReForge fork
- **LiME**: <https://github.com/504ensicsLabs/LiME>
- **osxpmem**: <https://github.com/Velocidex/osxpmem> (legacy, macOS deprecated no Vol3)

### Companion tools

- **YARA**: <https://virustotal.github.io/yara/>
- **FLOSS 3.1.1**: <https://github.com/mandiant/flare-floss> (Rust rewrite)
- **Mandiant CAPA**: <https://github.com/mandiant/capa> (static analysis companion)
- **Regipy** (Python registry parsing): <https://github.com/mkorman90/regipy>
- **Registry Explorer** (Eric Zimmerman): <https://ericzimmerman.github.io/RegistryExplorer/>
- **Mermaid CLI**: `npm install -g @mermaid-js/mermaid-cli`

### Source

- **HINDSIGHT research** (parent doc): `/Users/andersongoliveira/projects/engenharia reversa/HINDSIGHT/pesquisa-mercado-RE-2025-2026.md` §5

## Integração com system-dissector

> **Reclassificação**: Esta skill é **companion DFIR** — não usada em workflow `system-dissector` padrão. Invoque apenas se o alvo incluir memory dump (rastreamento de malware pós-exploit, incident response, forensic timeline). Para alvos binários/mobile/firmware regulares, use `reverse-engineer` ou `malware-analyst` em Phase 2.

- **Quando invocar (excepcional)**: Phase 2 (deep-dive) quando alvo = memory dump de sistema pós-exploit
- **Tipo de alvo**: memory dump (`.raw`, `.lime`, `.dmp`) — não é categoria nativa do `system-dissector`
- **Output esperado**: IOCs + process tree + injection map (não se encaixa em templates canônicos)
- **Templates ad-hoc**: criar manualmente em `dissects/<sistema>/deep-dive/memory-triage.md`

**Contrato (quando aplicável)**:
- Path: `dissects/<sistema>/deep-dive/memory-triage.md` (não usar `module-<n>.md`)
- Volatility 3 plugins → cite com version tag (`v2.28.2`)
- Companion: `malware-analyst` (YARA + FLOSS sobre strings extraídas)

## Author notes

- Research date: **22 set 2026**
- Source authority: HINDSIGHT §5 (✅ confirmed Vol3; ⚠️ verify Velociraptor/MemProcFS)
- Previous version (494 lines, 2026-02-27) generalized "Volatility 3" sem versão; este rewrite pin v2.28.2 + lineage + novos plugins 2025-2026