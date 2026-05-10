# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root, or
- **`CONTEXT-MAP.md`** at the repo root if it exists — it points at one `CONTEXT.md` per context. Read each one relevant to the topic.
- **`DECISIONS.md`** — architecture decision records for this repo.
- **`design.md`** / **`design_en.md`** — data model, entity/relationship inventory, ADRs.
- **`CONTEXT.md`** — domain glossary.

If any of these files don't exist, **proceed silently**. Don't flag their absence; don't suggest creating them upfront. The producer skill (`/grill-with-docs`) creates them lazily when terms or decisions actually get resolved.

## File structure

```
/
├── README.md               # Usage guide
├── design.md               # Data model + ADRs (Chinese)
├── design_en.md            # Data model + ADRs (English)
├── CONTEXT.md              # Domain glossary
├── DECISIONS.md            # ADRs
├── AGENTS.md               # Agent skills
├── schema/
│   ├── constraints.cypher
│   └── validation.cypher
├── data/
│   ├── companies.csv
│   ├── commodities.csv
│   ├── products.csv
│   └── edges_*.csv
├── scripts/
│   ├── 00_schema_init.py
│   ├── 01_load_data.py
│   └── 02_import_relations.py
└── queries/verification/
```

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `CONTEXT.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal — either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/grill-with-docs`).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0007 (event-sourced orders) — but worth reopening because…_
