# Neodissector Skills

> **Versão**: 1.0.0
> **Status**: canônico desde 2026-09-24
> **Owner**: Anderson Oliveira

Skills versionadas do framework **neodissector** — workflow de engenharia reversa sistemática. Este repo substitui a convenção original de manter skills em `~/.agents/skills/` e adiciona rastreabilidade de versão.

---

## O que é

22 skills organizadas em 2 grupos:

| Grupo | Skills | Função |
|---|---|---|
| **Core (orquestrador)** | `system-dissector` | Orquestrador mestre do workflow stateful de 5 fases |
| **RE adjacentes (15)** | `reverse-engineer`, `binary-ninja`, `binary-analysis-patterns`, `protocol-reverse-engineering`, `malware-analyst`, `firmware-analyst`, `memory-forensics`, `dwarf-expert`, `anti-reversing-techniques`, `ai-assisted-re`, `mobile-re`, `variant-analysis`, `audit-context-building`, `wiki-researcher`, `neodoo-integrate` | Ferramentas RE para o time sujo |
| **Companion (6)** | `neodissector-reconstructor`, `neodissector-brainstorm`, `neodissector-bug`, `neodissector-migration`, `neodissector-refactor`, `neodissector-pricing` | Times adjacentes: fecham o ciclo dissecação → código |

Mais 3 scripts Python (`scripts/verify-invocation.py`, `scripts/legacy_policy.py`, `scripts/session.py`) e 5 docs canônicos em `docs/`.

## Instalação

```bash
# Última versão
python3 install.py

# Versão específica
python3 install.py --version 1.0.0

# Dry-run (só mostra o que faria)
python3 install.py --dry-run

# Diretório customizado (default: ~/.agents/skills/)
python3 install.py --target /custom/path

# Atualizar para a mais recente (preserva customizações)
python3 install.py --update
```

Por padrão, instala em `~/.agents/skills/` (convenção original). Use `--target` para instalar em outro lugar.

## Uso após instalação

```bash
# Verificar que está tudo OK
python3 ~/.agents/skills/system-dissector/resources/scripts/verify-invocation.py

# Iniciar uma dissecação
python3 ~/.agents/skills/system-dissector/resources/scripts/dissect_utils.py init <sistema> --tipo source
```

## Versionamento

Este repo segue SemVer. Major versions podem ter mudanças incompatíveis no schema do workflow (e.g., mudança de estado em `dissects/<s>/state.json`).

`VERSION` na raiz é a fonte de verdade da versão atual. Cada `state.json` gerado por uma dissecação grava qual versão do neodissector foi usada — isso permite reproduzir uma dissecação com a mesma versão das skills.

## Estrutura

```
neodissector-skills/
├── README.md                        (este arquivo)
├── LICENSE                         (MIT)
├── VERSION                         (1.0.0)
├── CHANGELOG.md                    (histórico de versões)
├── install.py                      (CLI installer)
├── skills/                         (22 skills)
├── scripts/                        (3 scripts Python compartilhados)
└── docs/                           (5 docs canônicos)
```

## Inspiração

A arquitetura dual-track (`framework user-level + skills versionadas`) é inspirada em `sandeco/reversa` (paper ArXiv, framework MIT npm-installable). Adaptamos para Python com `install.py` mantendo a convenção `~/.agents/skills/` original.

## Compatibilidade

- Claude Code, Codex, OpenCode, Cursor e demais agentes compatíveis com **Agent Skills** (file-system based)
- Python 3.10+
- macOS, Linux, WSL

## Licença

MIT. Ver `LICENSE`.