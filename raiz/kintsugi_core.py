"""Kintsugi core loader — real package first, vendored copy as fallback.

Resolution order, most authoritative first:

  1. ``KINTSUGI_PATH`` env var pointing at a Project-Kintsugi checkout
  2. an installed / importable ``kintsugi`` package
  3. the vendored verbatim copy in ``kintsugi_vendor/``

Everything in Raíz imports Kintsugi symbols from THIS module, so the same code
runs against the real engine on a dev box and against the vendor copy on a bare
deployment target. Pattern borrowed from Rivet's ``kintsugi_core.py``; if you
change one, look at the other.

``KINTSUGI_SOURCE`` records which of the three actually resolved. That matters:
a vendored copy and a live checkout can disagree, and a module that cannot say
which one it loaded is a provenance gap of exactly the kind this lab keeps
finding. Print it in any diagnostic that reports on the dreamer.

WHY VENDORED. ``kintsugi-engine`` declares 23 dependencies — FastAPI, uvicorn,
SQLAlchemy, asyncpg, celery+redis, OpenTelemetry, sentence-transformers. The
three modules Raíz uses import stdlib and numpy and nothing else. Installing a
web framework to obtain two dataclasses is the wrong trade. See
``kintsugi_vendor/README.md``.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_VENDOR = Path(__file__).resolve().parent.parent / "kintsugi_vendor"

KINTSUGI_SOURCE = "unresolved"


def _resolve() -> None:
    global KINTSUGI_SOURCE

    env_path = os.environ.get("KINTSUGI_PATH")
    if env_path and (Path(env_path) / "kintsugi" / "__init__.py").exists():
        sys.path.insert(0, env_path)
        KINTSUGI_SOURCE = f"checkout:{env_path}"
        return

    try:
        import kintsugi  # noqa: F401
        KINTSUGI_SOURCE = "installed"
        return
    except ImportError:
        pass

    if not (_VENDOR / "kintsugi" / "__init__.py").exists():
        # Say what is missing rather than letting the import below raise a
        # ModuleNotFoundError that names only `kintsugi` and not the reason.
        raise ImportError(
            f"Kintsugi is not resolvable: no KINTSUGI_PATH, no installed "
            f"package, and no vendored copy at {_VENDOR}. Raíz's dreamer needs "
            f"cognition.proactive_advisor and memory.cma_stage1."
        )
    sys.path.insert(0, str(_VENDOR))
    KINTSUGI_SOURCE = f"vendor:{_VENDOR}"


_resolve()

from kintsugi.cognition.proactive_advisor import (  # noqa: E402
    ProactiveAdvisor,
    ActivityRecord,
    Suggestion,
)
from kintsugi.memory.cma_stage1 import AtomicFact  # noqa: E402

__all__ = [
    "ProactiveAdvisor",
    "ActivityRecord",
    "Suggestion",
    "AtomicFact",
    "KINTSUGI_SOURCE",
]
