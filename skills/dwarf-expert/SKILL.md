---
name: dwarf-expert
description: DWARF debug format expertise (v3, v4, v5). Analyzes DWARF sections using llvm-dwarfdump, readelf, and parsing libraries (libdwarf, pyelftools, gimli). Covers DWARF v5 specifics (split DWARF, rnglists, .debug_names, debuginfod), Go/Rust DWARF, verification workflows, and statistics metrics.
disable-model-invocation: true
allowed-tools:
  - Read
  - Bash
  - Grep
  - Glob
  - WebSearch
risk: unknown
source: community
date_added: '2026-09-22'
---
> **Companion de debug — útil em `system-dissector` Phase 2 quando alvo binário tem DWARF para analisar.** Fora desse escopo, esta skill não é rotineiramente consumida pelo workflow `system-dissector` (que cobre source/binary/mobile/firmware/protocol como tipos primários, não análise de debug-format isolada). Veja seção "Integração com system-dissector" abaixo.

# Overview
This skill provides technical knowledge and expertise about the DWARF standard and how to interact with DWARF files. Tasks include answering questions about the DWARF standard, providing examples of various DWARF features, parsing and/or creating DWARF files, and writing/modifying/analyzing code that interacts with DWARF data.

DWARF version coverage: **v3** (GCC default pre-2019), **v4** (LLVM/Clang default 2015-2019), **v5** (GCC 11+, Clang 14+, rustc default). For v5-specific features (split DWARF, rnglists, `.debug_names`, `.debug_loclists`, `.debug_aranges` removal), see **DWARF v5 specifics** below.

## When to Use This Skill
- Understanding or parsing DWARF debug information from compiled binaries
- Answering questions about the DWARF standard (v3, v4, v5)
- Writing or reviewing code that interacts with DWARF data
- Using `dwarfdump` or `readelf` to extract debug information
- Verifying DWARF data integrity with `llvm-dwarfdump --verify`
- Working with DWARF parsing libraries (libdwarf, pyelftools, gimli, etc.)
- Diagnosing DWARF-related issues in Go (1.18+) and Rust (DWARF5) binaries
- Setting up `debuginfod` clients (Ghidra 12.1+, Cutter 2.5+, BinSkim)
- Working with split DWARF (`.dwo` / `.dwp`) or thin-LTO objects
- Comparing debug-info quality across compiler versions / optimization levels

## When NOT to Use This Skill
- **DWARF v1/v2 Analysis**: Expertise limited to versions 3, 4, and 5.
- **General ELF Parsing**: Use standard ELF tools if DWARF data isn't needed.
- **Executable Debugging**: Use dedicated debugging tools (gdb, lldb, etc) for debugging executable code/runtime behavior.
- **Binary Reverse Engineering**: Use dedicated RE tools (Ghidra, IDA) unless specifically analyzing DWARF sections.
- **Compiler Debugging**: DWARF generation issues are compiler-specific, not covered here.
- **PDB/CodeView**: Microsoft Windows debug format — use a PDB-specific toolchain (`pdbparse`, `cv2pdb`, DIA SDK).

# Authoritative Sources
When specific DWARF standard information is needed, use these authoritative sources:

1. **Official DWARF Standards (dwarfstd.org)**: Use web search to find specific sections of the official DWARF specification at dwarfstd.org. Search queries like "DWARF5 DW_TAG_subprogram attributes site:dwarfstd.org" are effective. DWARF v5 is published as **Version 5, Issue 27 (PDF/RTF)** on the site.

2. **LLVM DWARF Implementation** (LLVM 14+ recommended): The LLVM project's DWARF handling code at `llvm/lib/DebugInfo/DWARF/` serves as a reliable reference implementation. Key files include:
   - `DWARFDie.cpp` — DIE handling and attribute access
   - `DWARFUnit.cpp` — Compilation unit parsing (DWO support added in LLVM 7, refined in 14+)
   - `DWARFDebugLine.cpp` — Line number information (v5 line program header in `DWARFDebugLine.cpp`)
   - `DWARFVerifier.cpp` — Validation logic
   - `DWARFDebugRnglists.cpp` — DWARF v5 rnglist parsing (replaces v4 `.debug_ranges`)
   - `DWARFDebugLoclists.cpp` — DWARF v5 loclist parsing (replaces v4 `.debug_loc`)
   - `DWARFDebugNames.cpp` — DWARF v5 `.debug_names` accelerator table
   - `DWARFAcceleratorTable.cpp` — Apple-style accelerator tables (pre-v5)

3. **libdwarf**: The reference C implementation at github.com/davea42/libdwarf-code provides detailed handling of DWARF data structures.

# Verification Workflows
Use `llvm-dwarfdump` verification options to validate DWARF data integrity. LLVM 14+ (`llvm-dwarfdump-14` or newer) is recommended for DWARF v5 fidelity.

## Structural Validation
```bash
# Verify DWARF structure (compile units, DIE relationships, address ranges)
llvm-dwarfdump --verify <binary>

# Detailed error output with summary
llvm-dwarfdump --verify --error-display=full <binary>

# Machine-readable JSON error summary
llvm-dwarfdump --verify --verify-json=errors.json <binary>

# Limit verification to one section (faster iteration)
llvm-dwarfdump --verify --debug-rnglists <binary>
llvm-dwarfdump --verify --debug-loclists <binary>
llvm-dwarfdump --verify --debug-names <binary>
llvm-dwarfdump --verify --debug-line <binary>
```

## Quality Metrics
```bash
# Output debug info quality metrics as JSON
llvm-dwarfdump --statistics <binary>

# Compare two builds for regressions
llvm-dwarfdump --statistics build-v1.o > stats-v1.json
llvm-dwarfdump --statistics build-v2.o > stats-v2.json
diff stats-v1.json stats-v2.json

# Useful metric names emitted in --statistics:
#   "scope_bytes_wasted", "abbrev_entries", "cu_count",
#   "...variable_coverage", "...type_coverage", "debug_str_size"
```

## Split-DWARF Verification
```bash
# Verify a .dwo file (split-DWARF object)
llvm-dwarfdump --verify foo.dwo

# Verify a .dwp (DWARF package — combined split DWARF archive)
llvm-dwarfdump --verify foo.dwp

# When the executable links against .dwo, dwarfdump resolves automatically:
llvm-dwarfdump --verify --use-split-dwarf=0 exe   # main binary only
llvm-dwarfdump --verify --use-split-dwarf=1 exe   # follow .dwo references
```

## Common Verification Patterns
- **After compilation**: Verify binaries have valid DWARF before distribution
- **Comparing builds**: Use `--statistics` to detect debug info quality regressions
- **Debugging debuggers**: Identify malformed DWARF causing debugger issues
- **DWARF tool development**: Validate parser output against known-good binaries
- **Post-link verification**: Catch DWO merge errors introduced by LTO / `lld` thin links

# DWARF v5 Specifics

DWARF v5 (released 2017, adopted by GCC 11 in 2021, Clang 14 in 2022, rustc default since 1.69) restructured several sections. Key changes:

## Split DWARF (`.dwo` / `.dwp`)

Split DWARF separates debug info from the main object so that build artifacts stay small and link-time I/O is reduced. The split is triggered at compile time:

```bash
# GCC: emit a .dwo companion for each TU/CU
gcc -g -gsplit-dwarf -c foo.c -o foo.o
# produces foo.o (main) + foo.dwo (skeleton debug info)

# Clang (same flag)
clang -g -gsplit-dwarf -c foo.cpp -emit-obj -o foo.o

# LTO: produces split files at link step
gcc -flto -gsplit-dwarf -O2 foo.c bar.c -o exe
# Output: exe, foo.dwo, bar.dwo (or combined foo.dwp below)
```

The `.dwp` (DWARF Package) is the **post-link consolidated archive** of all `.dwo` files:

```bash
# llvm-dwp combines multiple .dwo into one .dwp
llvm-dwp foo.dwo bar.dwo -o exe.dwp

# Place .dwp alongside exe; tools that understand split DWARF (gdb, lldb,
# llvm-dwarfdump, Ghidra 12.1+) will look up .dwp automatically
```

**Ghidra 12.1.4 integration** (set 2026): Ghidra auto-loads `.dwp` companions when a binary references them via `.gnu_debuglink`-like split sections.

### Skeleton vs. Split CUs

- **Skeleton CU** stays in the main `.o`/`.exe`: holds the CU header, DW_AT_dwo_name / DW_AT_dwo_id pointing into `.dwo`.
- **Split CU** lives in `.dwo`: full type/variable DIEs, line tables, everything.

Reading either alone is meaningless — the parser must follow the skeleton → split reference.

## RNG Lists — `.debug_rnglists` (DWARF v5)

DWARF v4's `.debug_ranges` was a parallel array of address pairs + base-address selections. v5 replaced it with a single `.debug_rnglists` section that encodes one offset table (like a string table) and each DIE's `DW_AT_ranges` points into it.

```bash
# Dump v5 rnglists (LLVM 14+)
llvm-dwarfdump --debug-rnglists <binary>

# Old .debug_ranges still appears when reading v4 binaries:
llvm-dwarfdump --debug-ranges <binary>     # v4 only
```

Format: each entry begins with a header byte encoding the entry type (RLE_end_of_list, RLE_base_addressx, RLE_startx_endx, RLE_startx_length, RLE_offset_pair, RLE_start_end, RLE_start_length, RLE_GNU_view_pair — vendor extensions included). The `*x` variants use **indexed address lookups** via `.debug_addr`, reducing link-time relocations.

## `.debug_aranges` Removal (DWARF v5)

`.debug_aranges` (the address-lookup accelerator) is **removed** from the v5 standard. Producers no longer emit it by default, and v5-aware consumers (`gdb`, `lldb`, `llvm-dwarfdump`) use:

1. **`.debug_names`** (new in v5, see below) for name-based lookup
2. **`.debug_addr`** + index tables for address ranges
3. **Linear scan of CUs** when no accelerator is present

For legacy v4 binaries still emitting `.debug_aranges`, `readelf --debug-aranges` and `llvm-dwarfdump --debug-aranges` continue to work, but don't expect them in v5+ output.

## `.debug_loclists` — Replaces `.debug_loc` (DWARF v5)

Same restructuring as rnglists: `.debug_loc` (v4) became `.debug_loclists` (v5) with offset-based entries, DW_LLE_* opcodes, and indexed-address support via `.debug_addr`. Use `--debug-loclists` in llvm-dwarfdump; the v4 flag is `--debug-loc`.

## `.debug_names` Accelerator (DWARF v5)

`.debug_names` is the v5 replacement for Apple-style `.debug_pubnames`/`.debug_pubtypes`/`.debug_aranges`. It hashes names + types into buckets that point at DIE offsets, enabling O(1) name lookup without scanning all CUs.

```bash
# Dump v5 names index
llvm-dwarfdump --debug-names <binary>

# Verify the index consistency with DIEs
llvm-dwarfdump --verify --debug-names <binary>
```

Used heavily by rustc and modern GDB. Malformed `.debug_names` entries are a common crash source for old DWARF parsers (see Common Issues below).

## `.debug_line` Line Program Header (DWARF v5)

v5 rewrote the line program header (the `DW_LNE_*`/`DW_LNS_*` opcode set stayed similar, but the **header encoding changed**):

| v4 header | v5 header |
|---|---|
| Fixed `header_length` after `version` | Variable header; encoding fields are explicit |
| Opcode tables fixed-size | Opcode tables declared in header |
| `maximum_operations_per_insn = 1` (implied) | `maximum_operations_per_insn` field explicit (needed for VLIW) |
| No directory/file format versioning | `directory_entry_format_count` + `directory_entry_format` array |
| 4-byte DWARF offset assumed | Offset size explicit (4 vs 8 bytes) |

To parse v5 line programs, ensure the parser reads the **header format fields**, not the v4 offsets. `llvm-dwarfdump --debug-line` (LLVM 14+) handles both transparently. Common pitfall: hand-rolled v4 parsers that hard-code the offset size crash on v5 line tables.

## DWARF Expressions v5

DWARF v5 added and revised several expression opcodes:

- **New composite location operators** (DW_OP_implicit_value, DW_OP_stack_value, DW_OP_implicit_pointer, DW_OP_entry_value, DW_OP_address_with_index) for **optimized code** (TLS, PC-relative, register-spilled args).
- **DW_OP_convert** and **DW_OP_reinterpret** for explicit type conversions in expressions.
- **DW_OP_nop** opcode stabilization (it existed in v4 but v5 clarifies its role).
- **TLS access**: v5 mandates specific patterns for thread-local variable access; pre-v5 code may use vendor extensions (`GNU_tls_*`).

Go 1.18+ and Rust both generate expressions with `DW_OP_implicit_pointer` for `&`-references and closures — IDA and Ghidra handle these; older `dwarfdump` from binutils < 2.40 may render them incorrectly.

## DW_AT_addr_base / Indexed Addresses

v5 added the **`.debug_addr` section**: a contiguous array of address values referenced by *index* rather than absolute offset. The CU header carries `DW_AT_addr_base` pointing to the relevant slice. This:

- Reduces `.debug_info` size (no per-DIE address relocation)
- Simplifies split DWARF (addresses in `.dwo` resolve via base + index)
- Required for `DW_OP_addrx`, `DW_RLE_startx_endx`, `DW_LLE_startx_endx` and friends

# debuginfod (Ghidra 12.1+, Cutter 2.5+)

**debuginfod** is an HTTP(S) protocol for fetching debug info for stripped binaries. Ghidra 12.1+ (set 2026) and Cutter 2.5+ (jun 2026) implement clients; the GNU `debuginfod` server is shipped by elfutils and Fedora.

```bash
# System-wide: set the URL of your debuginfod server
export DEBUGINFOD_URLS="https://debuginfod.elfutils.org https://mycorp.example.com/debuginfod"

# Try fetching debug info for a stripped binary
debuginfod-find debuginfo /usr/bin/stripped-binary
# Downloads to $HOME/.cache/debuginfod_client/<BUILDID>/debuginfo
```

In **Ghidra 12.1.4**:
1. Open the stripped binary
2. `Edit → DWARF External Debug Config` (or via Analysis auto-config)
3. Add debuginfod URLs; cache lives in `$HOME/.cache/debuginfod_client`
4. Ghidra will fetch matching DWARF + symbol tables by build-id

In **Cutter 2.5.0**: the analysis start dialog has a debuginfod URL field; fills automatically when `DEBUGINFOD_URLS` is exported.

# LLVM 14+ Improvements

Relevant LLVM/Clang changes that affect DWARF output:

- **LLVM 7+**: `-gsplit-dwarf` fully supported (Apple's flavor via `-gsplit-dwarf=single`).
- **LLVM 13+**: stable `.debug_names` generation enabled by default for Clang at `-O0`.
- **LLVM 14+**: DWARF v5 generated by default at `-g -gdwarf-5`; RNG/loclists fully spec-compliant.
- **LLVM 15+**: `.debug_addr` indexed addresses used aggressively for size.
- **`--strip-debug`** (a.k.a. `objcopy --strip-debug`): removes all `.debug_*` sections except line tables. Inverse: `--keep-debug` keeps them in the stripped output for later split-DWARF recovery.

```bash
# Strip but keep debug-info for later recovery
objcopy --strip-debug exe   # remove debug sections entirely
objcopy --only-keep-debug exe stripped-exe.debug

# Or: keep debug info in the stripped binary itself (split-friendly)
clang -g -gsplit-dwarf -O2 main.c -o main
# debug info lives in main.dwo; main has only skeletons
```

# Working with Go Binaries (Go 1.18+)

Go emits **DWARF alongside its custom `pclntab` table** for function names and source file mappings. IDA Pro 9.4 (jul 2026) and GoReSym v3.4.1 (sep 2026) handle both:

```bash
# llvm-dwarfdump on Go binary
llvm-dwarfdump --statistics ./go-binary
# Expect very high "abbrev_entries" + small ".debug_info" — Go uses a single mega-CU

# Common Go DWARF quirks:
# 1. One CU per package (sometimes per build)
# 2. All Go packages compile to DWARF v4 by default (Go 1.20+ supports v5 via GOFLAGS=-ldflags=-debugdwarf=5)
# 3. Closure variables show as DW_OP_implicit_value / DW_OP_implicit_pointer
# 4. Goroutine stacks are NOT in DWARF — use runtime.Stack() introspection

# pclntab inspection
go tool addr2line <addr>     # uses pclntab, not DWARF
go tool nm ./go-binary | head

# Strip but keep function names
strip -s ./go-binary         # strips only symbol table, leaves DWARF
# (For fully stripped Go: GoReSym 3.4.1 can recover function names from pclntab remnants)
```

IDA Pro 9.4 added **improved pclntab discovery** + **buildinfo parsing for Go 1.18+** + cleaner struct types — a major help when reverse engineering Go services.

# Working with Rust Binaries (DWARF5)

`rustc` defaults to **DWARF v5** since Rust 1.69 (Apr 2023). It emits `.debug_names` + split DWARF + aggressive indexed addresses.

```bash
# Inspect Rust binary DWARF
llvm-dwarfdump --debug-names ./rust-binary      # expect many buckets
llvm-dwarfdump --statistics ./rust-binary       # compare size across crate versions

# Generate cargo build with deterministic DWARF
RUSTFLAGS="-C debuginfo=2 -C strip=none" cargo build --release
# Or: RUSTFLAGS="-C split-debuginfo=packed" cargo build  (LLVM ≥ 17 → single .dwp)
```

**BinSkim v4.4.9.7** (mar 2026) fixed several DWARF5 parser crashes against Rust binaries: abbreviation-table terminator, address parsing, `ReadBlock` EOF. BinSkim now correctly classifies Rust binaries as in-scope for BA2025/BA2026 instead of false-flagging them.

# Common DWARF Issues

When DWARF parsing fails or produces bad output, walk through these in order:

| Symptom | Likely cause | Fix |
|---|---|---|
| "could not find abbreviation N" | Malformed abbrev table; bit-shift overflow; or abbrev # reused across CUs | `llvm-dwarfdump --verify`; check producer string; if Rust: rebuild with `-C strip=debuginfo` to drop corrupted sections |
| `DW_FORM_ref*` pointing outside CU | Truncated binary; partial download; `objcopy --extract-dwo` bug | Re-fetch from source / re-link |
| Address ranges overlapping across CUs | Multiple TUs inlined into the same function (LTO) | LTO merges ranges; this is **expected** at `-flto`. Use `--statistics` to confirm CU count dropped |
| "no .debug_aranges" warning | DWARF v5 binary; section removed | Not an error — `.debug_names` provides the lookup |
| Variables show as `<optimized out>` | Compiler dropped location; check `DW_OP_call_frame_cfa` for v5 | Recompile with `-O0 -g` to compare; production builds almost always drop locals |
| Closure variables missing | v5 uses `DW_OP_implicit_pointer`; older `dwarfdump` (< 2.40) renders blank | Upgrade binutils; or use `llvm-dwarfdump` |
| Parse crash at .debug_names | Abbreviation table terminator mismatch (BinSkim pre-v4.4.9.7) | Upgrade BinSkim or use llvm-dwarfdump instead |
| Thread-local variable missing | TLS pattern not recognized (Go 1.x pre-1.20) | Upgrade Go; or set `DEBUGINFOD_URLS` and re-fetch |
| Function names missing in stripped binary | Symbol table gone; DWARF may still have them via `DW_AT_linkage_name` | Use GoReSym 3.4.1 (Go), `llvm-symbolizer` (Rust/C++), or `nm` on unstripped copy |

**Always run `llvm-dwarfdump --verify --statistics <binary>` first** — it catches ~80% of structural problems before you start debugging downstream tools.

# Parsing DWARF Debug Information

## readelf
ELF files can be parsed via the `readelf` command ({baseDir}/reference/readelf.md). Use this for general ELF information, but prefer `dwarfdump` for DWARF-specific parsing.

```bash
readelf --debug-dump=info program            # .debug_info
readelf --debug-dump=line program            # .debug_line
readelf --debug-dump=decodedline program     # decoded v5 line tables
readelf --debug-dump=ranges program          # v4 only
readelf --debug-dump=frames program          # .debug_frame (EH/CFI)
```

## dwarfdump
DWARF files can be parsed via the `dwarfdump` command, which is more effective at parsing and displaying complex DWARF information than `readelf` and should be used for most DWARF parsing tasks ({baseDir}/reference/dwarfdump.md).

```bash
# llvm-dwarfdump (LLVM) — preferred; supports v5 properly
llvm-dwarfdump --all program                 # everything
llvm-dwarfdump --debug-info program          # .debug_info only
llvm-dwarfdump --debug-line=verbose program  # decoded line table
llvm-dwarfdump --debug-rnglists program      # v5 rnglists
llvm-dwarfdump --debug-loclists program      # v5 loclists
llvm-dwarfdump --debug-names program         # v5 .debug_names index
llvm-dwarfdump --eh-frame program            # exception unwind info
llvm-dwarfdump --debug-address program 0x401000  # reverse-lookup by addr

# binutils dwarfdump (older, less v5-correct)
dwarfdump -l program                        # line info
dwarfdump -i program                        # .debug_info
dwarfdump -a program                        # aranges (v4 only)
```

# Working With Code
This skill supports writing, modifying, and reviewing code that interacts with DWARF data. This may involve code that parses DWARF debug data from scratch or code that leverages libraries to parse and interact with DWARF data ({baseDir}/reference/coding.md).

## Library matrix

| Language | Library | v5 support | Notes |
|---|---|---|---|
| C | libdwarf (davea42) | full | Reference implementation; verbose but spec-correct |
| C++ | gimli (Rust, FFIdable) | full | Read-only; well-tested |
| Rust | gimli | full | First-class DWARF library for Rust tooling |
| Python | pyelftools | partial (v5 mostly works since 0.29) | Best for ELF + DWARF combined parsing |
| Python | pwntools (`pwnlib.elf`) | partial | Lower-level; good for exploit-adjacent analysis |
| Go | `debug/dwarf` stdlib | full | Ships with Go; used by `go tool addr2line` |
| Java | Classycle / dwarfdump wrappers | varies | Ghidra uses its own internal DWARF parser |

# Choosing Your Approach
```
+- Need to verify DWARF data integrity or catch regressions?
|  +- Use `llvm-dwarfdump --verify --statistics` (see Verification Workflows)
|  +- For split DWARF: include `.dwp` alongside the executable
|
+- Need to answer questions about the DWARF standard?
|  +- Search dwarfstd.org or reference LLVM/libdwarf source
|  +- v5-specific question? Check `.debug_names` / `.debug_rnglists` / `.debug_loclists`
|
+- Need simple section dump or general ELF info?
|  +- Use `readelf` ({baseDir}/reference/readelf.md)
|
+- Need to parse, search, and/or dump DWARF DIE nodes?
|  +- Use `llvm-dwarfdump` (preferred over binutils dwarfdump for v5)
|  +- Use `dwarfdump` ({baseDir}/reference/dwarfdump.md) for v4-only workflows
|
+- Working with stripped binary + no local DWARF?
|  +- Set `DEBUGINFOD_URLS`; Ghidra 12.1+ / Cutter 2.5+ will fetch automatically
|
+- Working with Go / Rust / mixed-language binaries?
|  +- Go: rely on pclntab (GoReSym, IDA 9.4) for function names
|  +- Rust: rely on .debug_names + DWARF5 (BinSkim 4.4.9.7+)
|  +- C++: classic .debug_info + .debug_line; check LTO for merged CUs
|
+- Need to write, modify, or review code that interacts with DWARF data?
   +- Refer to the coding reference ({baseDir}/reference/coding.md)
   +- Pick library by language (see Working With Code table above)
```

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

# References

- **Official standard**: https://dwarfstd.org/ — DWARF v5 (Issue 27), DWARF v4 (Issue 6.7)
- **LLVM DWARF implementation**: https://github.com/llvm/llvm-project/tree/main/llvm/lib/DebugInfo/DWARF
- **libdwarf**: https://github.com/davea42/libdwarf-code
- **llvm-dwarfdump**: https://llvm.org/docs/CommandGuide/llvm-dwarfdump.html
- **debuginfod**: https://sourceware.org/elfutils/Debuginfod.html
- **Ghidra 12.1.4 release notes**: DWARF External Debug Config + .dwp support (set 2026)
- **BinSkim v4.4.9.7** (Microsoft, 30 mar 2026): DWARF5 parser fixes for Rust binaries
- **IDA Pro 9.4** (Hex-Rays, 13 jul 2026): Go 1.18+ pclntab discovery, buildinfo parsing
- **GoReSym v3.4.1** (14 set 2026): Go symbol recovery from stripped binaries
- **Related skills**: `reverse-engineer`, `binary-analysis-patterns`, `firmware-analyst`
