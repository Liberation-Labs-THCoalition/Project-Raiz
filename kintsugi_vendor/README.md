# Vendored Kintsugi Core (Raíz)

Verbatim copies of the **stdlib-only** cognition and memory modules from
[Liberation-Labs-THCoalition/Project-Kintsugi](https://github.com/Liberation-Labs-THCoalition/Project-Kintsugi)
at commit `ec077e5c4c186c2fea465ee53ee3a52f1f92977b` (2026-09-07).

| File | Origin | Modified? |
|---|---|---|
| `kintsugi/cognition/efe.py` | `kintsugi/cognition/efe.py` | verbatim |
| `kintsugi/cognition/proactive_advisor.py` | `kintsugi/cognition/proactive_advisor.py` | verbatim |
| `kintsugi/memory/cma_stage1.py` | `kintsugi/memory/cma_stage1.py` | verbatim |
| `kintsugi/memory/embeddings.py` | `kintsugi/memory/embeddings.py` | verbatim |

## Why vendored rather than installed

`kintsugi-engine` declares **23 dependencies** — FastAPI, uvicorn, SQLAlchemy,
asyncpg, alembic, celery+redis, three OpenTelemetry packages, sentence-transformers.
The transitive closure is **four modules** (computed with an AST walk, not by
reading imports by eye — my first pass said three and missed
`memory/embeddings`, which `cma_stage1` needs). Their only import-time
third-party dependency is **numpy**: `sentence_transformers` and `httpx` are
imported lazily inside the provider methods Raíz does not call, and
`EmbeddingProvider` is used only as a type annotation.
Installing a web framework and a task queue to obtain two dataclasses is the wrong
trade. Checked, not assumed: see the import lists in each file.

## Refreshing

These are verbatim. To update, re-copy from canonical and bump the commit hash
above — do not hand-edit. `raiz/kintsugi_core.py` prefers a real checkout
(`KINTSUGI_PATH`) or an installed package over this copy, so a dev box runs
against canonical and only a bare deployment falls back here.
