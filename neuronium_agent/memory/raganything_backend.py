"""Adapter for HKUDS/RAG-Anything.

This module integrates `raganything.RAGAnything` as a Neuronium MemoryBackend.
The dependency is optional: when not installed, the backend reports
`ready = False` and `retrieve` falls back to an empty result, but the adapter
itself remains importable so users can introspect/install hints.

Design choices:
- The adapter accepts an injected `client` to keep tests deterministic and avoid
  importing the heavy `raganything` stack in CI.
- Async API of RAG-Anything (`aquery`, `process_document_complete`) is wrapped
  in synchronous methods using `asyncio.run` when needed.
- LLM/embedding/vision functions are sourced from the Neuronium model registry
  when available; otherwise the adapter expects callables to be supplied via
  config (e.g. by a deployment harness).
"""

from __future__ import annotations

import asyncio
import importlib
import os
from typing import Any, Callable, Dict, List, Optional

from neuronium_agent.memory.backend import IngestDocument, MemoryConfig
from neuronium_agent.memory.graphrag import (
    Entity,
    Relationship,
    RetrievalQuery,
    RetrievalResult,
)


def _try_import_raganything() -> Optional[Any]:
    try:
        return importlib.import_module("raganything")
    except Exception:  # noqa: BLE001
        return None


def _run_async(coro: Any) -> Any:
    """Run an awaitable synchronously even when an outer loop exists."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return asyncio.ensure_future(coro)
    except RuntimeError:
        pass
    return asyncio.run(coro)


class RAGAnythingBackend:
    """Memory backend backed by HKUDS/RAG-Anything.

    Use one of:
    - Provide a fully constructed `client` (used in tests).
    - Provide `client_factory(config)` that returns a `RAGAnything` instance.
    - Let the adapter build one from `raganything.RAGAnything` and `RAGAnythingConfig`
      using `llm_model_func`, `embedding_func`, and optional `vision_model_func`
      passed via `extra_funcs`.
    """

    name = "raganything"

    def __init__(
        self,
        config: MemoryConfig,
        *,
        client: Optional[Any] = None,
        client_factory: Optional[Callable[[MemoryConfig], Any]] = None,
        extra_funcs: Optional[Dict[str, Callable[..., Any]]] = None,
    ) -> None:
        self.config = config
        self._documents: List[Dict[str, Any]] = []
        self._client: Optional[Any] = client
        self._client_factory = client_factory
        self._extra_funcs = extra_funcs or {}
        self._raganything_module = _try_import_raganything()
        self._init_error: Optional[str] = None
        if self._client is None and self._client_factory is not None:
            try:
                self._client = self._client_factory(config)
            except Exception as exc:  # noqa: BLE001
                self._init_error = f"client_factory failed: {exc}"
        elif self._client is None and self._raganything_module is not None:
            try:
                self._client = self._build_default_client()
            except Exception as exc:  # noqa: BLE001
                self._init_error = f"default client init failed: {exc}"
        elif self._client is None and self._raganything_module is None:
            self._init_error = (
                "raganything package not installed; "
                "install with `pip install 'raganything[all]'` or pass a client_factory"
            )

    # ---- properties ----

    @property
    def ready(self) -> bool:
        return self._client is not None and self._init_error is None

    # ---- backend protocol ----

    def ingest(self, documents: List[IngestDocument]) -> Dict[str, Any]:
        if not self.ready:
            return {
                "ingested": [],
                "skipped": [d.id for d in documents],
                "ready": False,
                "error": self._init_error,
            }
        added: List[str] = []
        skipped: List[str] = []
        for doc in documents:
            try:
                self._ingest_one(doc)
                added.append(doc.id)
                self._documents.append(doc.model_dump())
            except Exception as exc:  # noqa: BLE001
                skipped.append(f"{doc.id}: {exc}")
        return {"ingested": added, "skipped": skipped, "ready": True}

    def _ingest_one(self, doc: IngestDocument) -> None:
        client = self._client
        if doc.path and hasattr(client, "process_document_complete"):
            coro = client.process_document_complete(doc.path)
            _run_async(coro)
            return
        if doc.text is not None and hasattr(client, "insert_content_list"):
            payload = [{"id": doc.id, "content": doc.text, "metadata": doc.metadata}]
            insertion = client.insert_content_list(payload)
            if asyncio.iscoroutine(insertion):
                _run_async(insertion)
            return
        raise ValueError(
            f"document '{doc.id}' has neither a file path nor inline text"
        )

    def retrieve(
        self, query: RetrievalQuery, *, pack_id: Optional[str] = None
    ) -> RetrievalResult:
        if not self.ready:
            return RetrievalResult(entities=[], snippets=[])
        client = self._client
        result_text: str = ""
        try:
            if hasattr(client, "aquery"):
                coro = client.aquery(query.text, mode=self.config.query_mode)
                raw = _run_async(coro)
            elif hasattr(client, "query"):
                raw = client.query(query.text, mode=self.config.query_mode)
            else:
                raw = None
        except Exception as exc:  # noqa: BLE001
            return RetrievalResult(entities=[], snippets=[f"retrieval error: {exc}"])
        if isinstance(raw, str):
            result_text = raw
        elif isinstance(raw, dict):
            result_text = str(raw.get("answer") or raw.get("text") or raw)
        elif raw is None:
            result_text = ""
        else:
            result_text = str(raw)
        snippets = [s for s in result_text.split("\n") if s.strip()][: query.top_k]
        return RetrievalResult(entities=[], snippets=snippets)

    def write_back(
        self,
        entities: List[Entity],
        relationships: List[Relationship],
    ) -> None:
        # RAG-Anything indexes via documents; graph writeback is a no-op here.
        return None

    def diagnostics(self) -> Dict[str, Any]:
        return {
            "backend": self.name,
            "ready": self.ready,
            "raganything_installed": self._raganything_module is not None,
            "documents": len(self._documents),
            "working_dir": self.config.working_dir,
            "parser": self.config.parser,
            "query_mode": self.config.query_mode,
            "init_error": self._init_error,
        }

    # ---- default client construction ----

    def _build_default_client(self) -> Any:
        module = self._raganything_module
        if module is None:
            raise RuntimeError("raganything is not importable")
        RAGAnything = getattr(module, "RAGAnything")
        RAGAnythingConfig = getattr(module, "RAGAnythingConfig")
        working_dir = self.config.working_dir or os.path.join(".neuronium", "rag")
        os.makedirs(working_dir, exist_ok=True)
        rag_config = RAGAnythingConfig(
            working_dir=working_dir,
            parser=self.config.parser,
            parse_method=self.config.parse_method,
            enable_image_processing=self.config.enable_image_processing,
            enable_table_processing=self.config.enable_table_processing,
            enable_equation_processing=self.config.enable_equation_processing,
        )
        llm_func = self._extra_funcs.get("llm_model_func")
        embed_func = self._extra_funcs.get("embedding_func")
        vision_func = self._extra_funcs.get("vision_model_func")
        if llm_func is None or embed_func is None:
            raise RuntimeError(
                "RAGAnythingBackend default client requires llm_model_func and "
                "embedding_func in extra_funcs"
            )
        kwargs = {
            "config": rag_config,
            "llm_model_func": llm_func,
            "embedding_func": embed_func,
        }
        if vision_func is not None:
            kwargs["vision_model_func"] = vision_func
        return RAGAnything(**kwargs)


def factory(config: MemoryConfig) -> "RAGAnythingBackend":
    """Default factory used by the backend registry."""
    return RAGAnythingBackend(config)
