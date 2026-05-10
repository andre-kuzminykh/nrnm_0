"""Neuronium Agent CLI."""

from __future__ import annotations

import json
import os
import sys
from typing import Optional

import click
import yaml
from rich.console import Console
from rich.table import Table

from neuronium_agent import __version__
from neuronium_agent.memory.backend import (
    IngestDocument,
    MemoryConfig,
    build_backend,
    list_backends,
)
from neuronium_agent.memory.graphrag import RetrievalQuery
from neuronium_agent.packs import (
    PackError,
    PackValidationError,
    compile_pack,
    parse_pack_file,
    validate_pack,
)
from neuronium_agent.packs.compiler import compile_pack as _compile_pack
from neuronium_agent.packs.generator import (
    generate_from_template_file,
    generate_pack_from_template,
    write_pack_yaml,
)
from neuronium_agent.packs.registry import PackRegistry
from neuronium_agent.runtime.objective_runner import ObjectiveRunner
from neuronium_agent.runtime.runs import list_runs, show_run
from neuronium_agent.tools.real import RealToolsConfig
from neuronium_agent.cli.repl import CodeRepl


console = Console()


@click.group(invoke_without_command=True)
@click.version_option(__version__, prog_name="neuronium-agent")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Neuronium Super Agent CLI."""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


# ---------- packs ----------


@cli.group()
def packs() -> None:
    """Manage applied workflow packs."""


@packs.command("list")
def packs_list() -> None:
    registry = PackRegistry()
    table = Table(title="Installed Workflow Packs")
    table.add_column("id")
    table.add_column("name")
    table.add_column("version")
    table.add_column("domain")
    for pack in registry.list():
        table.add_row(pack.pack.id, pack.pack.name, pack.pack.version, pack.pack.domain)
    if not registry.list():
        console.print("[yellow]No packs installed[/yellow]")
        return
    console.print(table)


@packs.command("show")
@click.argument("pack_id")
def packs_show(pack_id: str) -> None:
    registry = PackRegistry()
    try:
        pack = registry.get(pack_id)
    except PackError as exc:
        click.echo(f"error: {exc}", err=True)
        sys.exit(2)
    console.print(yaml.safe_dump(pack.model_dump(), sort_keys=False, allow_unicode=True))


@packs.command("validate")
@click.argument("path_or_id")
def packs_validate(path_or_id: str) -> None:
    try:
        if os.path.isfile(path_or_id):
            pack = parse_pack_file(path_or_id)
        else:
            registry = PackRegistry()
            pack = registry.get(path_or_id)
        validate_pack(pack)
    except PackValidationError as exc:
        click.echo("validation failed:", err=True)
        for err in exc.errors:
            click.echo(f"  - {err}", err=True)
        sys.exit(2)
    except PackError as exc:
        click.echo(f"error: {exc}", err=True)
        sys.exit(2)
    console.print(f"[green]ok[/green] pack '{pack.pack.id}' is valid")


@packs.command("install")
@click.argument("path", type=click.Path(exists=True))
def packs_install(path: str) -> None:
    registry = PackRegistry()
    pack = registry.install_from_file(path)
    console.print(f"[green]installed[/green] pack '{pack.pack.id}' from {path}")


@packs.command("remove")
@click.argument("pack_id")
def packs_remove(pack_id: str) -> None:
    registry = PackRegistry()
    registry.remove(pack_id)
    console.print(f"[green]removed[/green] {pack_id}")


@packs.command("test")
@click.argument("pack_id")
def packs_test(pack_id: str) -> None:
    """Test a pack in mock mode by compiling and running its tests' objectives."""
    registry = PackRegistry()
    try:
        compiled = registry.get_compiled(pack_id)
    except PackError as exc:
        click.echo(f"error: {exc}", err=True)
        sys.exit(2)
    runner = ObjectiveRunner(registry=registry, auto_approve=True)
    passes = 0
    fails = 0
    for test in compiled.pack.tests:
        try:
            result = runner.run(test.objective, pack_id=pack_id)
            ok = result.run.status.value == "succeeded"
            passes += int(ok)
            fails += int(not ok)
            status = "[green]ok[/green]" if ok else "[red]fail[/red]"
            console.print(f"{status} {test.id}")
        except Exception as exc:  # noqa: BLE001
            fails += 1
            console.print(f"[red]fail[/red] {test.id}: {exc}")
    console.print(f"\nresults: {passes} passed, {fails} failed")
    if fails:
        sys.exit(1)


@packs.command("init")
@click.argument("name")
@click.option("--out", "out_dir", default="./packs", help="Where to write the scaffold.")
def packs_init(name: str, out_dir: str) -> None:
    """Scaffold a new workflow pack."""
    out_path = os.path.join(out_dir, f"{name}.yaml")
    os.makedirs(out_dir, exist_ok=True)
    scaffold = {
        "pack": {
            "id": name,
            "name": f"{name} Workflow Pack",
            "version": "0.1.0",
            "schema_version": "0.1",
            "compatible_neuronium": ">=0.1.0",
            "domain": "custom",
            "description": f"Scaffold for {name} workflow pack.",
        },
        "objectives": [
            {
                "id": "primary_objective",
                "user_phrases": ["help me with this task"],
                "expected_outcomes": ["task completed"],
            }
        ],
        "tools": [
            {"ref": "doc.write", "kind": "mcp", "risk": "medium", "default_permission": "require_approval"}
        ],
        "agents": [
            {
                "id": "planner",
                "role": "planner",
                "goal": "plan the work",
                "tools": [],
                "permissions": {},
                "output_contract": {"type": "object", "required": ["plan"]},
            },
            {
                "id": "executor",
                "role": "executor",
                "goal": "execute the plan",
                "tools": ["doc.write"],
                "permissions": {"doc.write": "require_approval"},
                "output_contract": {"type": "object", "required": ["result"]},
            },
            {
                "id": "critic",
                "role": "critic",
                "goal": "check the result",
                "tools": [],
                "permissions": {},
                "output_contract": {"type": "object", "required": ["verdict"]},
            },
        ],
        "workflows": [
            {
                "id": "primary_workflow",
                "objective_match": "primary_objective",
                "phases": [
                    {"id": "plan", "agent": "planner", "outputs": ["plan"]},
                    {"id": "execute", "agent": "executor", "outputs": ["result"], "requires_approval": True},
                    {"id": "review", "agent": "critic", "outputs": ["verdict"]},
                ],
            }
        ],
        "quality_gates": [
            {"id": "critic_passes", "condition": "verdict == 'PASS'", "on_fail": "replan"}
        ],
        "outputs": [{"id": "summary", "type": "markdown", "includes": ["plan", "result"]}],
        "tests": [
            {
                "id": f"{name}_smoke",
                "objective": "help me with this task",
                "expected": ["Workflow reaches final phase"],
            }
        ],
    }
    write_pack_yaml(scaffold, out_path)
    console.print(f"[green]scaffold written[/green] {out_path}")


@packs.command("generate")
@click.argument("template_path", type=click.Path(exists=True))
@click.option("--out", "out_path", required=True, help="Output YAML path.")
@click.option("--id", "pack_id", default="custom", help="Pack id (default: custom).")
def packs_generate(template_path: str, out_path: str, pack_id: str) -> None:
    """Generate a pack YAML draft from the simple markdown template."""
    pack = generate_from_template_file(template_path, out_path, pack_id=pack_id)
    console.print(f"[green]generated[/green] {out_path}")


# ---------- memory ----------


def _memory_config_from_options(
    backend: str,
    working_dir: Optional[str],
    parser: str,
    query_mode: str,
) -> MemoryConfig:
    return MemoryConfig(
        backend=backend,
        working_dir=working_dir,
        parser=parser,
        query_mode=query_mode,
    )


@cli.group()
def memory() -> None:
    """Manage Neuronium memory backends (mock, raganything, ...)."""


@memory.command("backends")
def memory_backends() -> None:
    """List registered memory backends."""
    table = Table(title="Memory backends")
    table.add_column("name")
    for name in list_backends():
        table.add_row(name)
    console.print(table)


@memory.command("diagnostics")
@click.option("--backend", default="mock", help="Backend to query.")
@click.option("--working-dir", default=None, help="Backend working directory.")
@click.option("--parser", default="mineru", help="Parser for raganything.")
@click.option("--query-mode", default="hybrid", help="Query mode (raganything).")
def memory_diagnostics(
    backend: str, working_dir: Optional[str], parser: str, query_mode: str
) -> None:
    config = _memory_config_from_options(backend, working_dir, parser, query_mode)
    try:
        instance = build_backend(config)
    except KeyError as exc:
        click.echo(f"error: {exc}", err=True)
        sys.exit(2)
    diag = instance.diagnostics()
    click.echo(json.dumps(diag, indent=2, default=str))


@memory.command("ingest")
@click.argument("path", type=click.Path(exists=True))
@click.option("--backend", default="mock")
@click.option("--working-dir", default=None)
@click.option("--parser", default="mineru")
@click.option("--query-mode", default="hybrid")
@click.option("--pack", "pack_id", default=None, help="Tag documents with a pack id.")
@click.option("--id", "doc_id", default=None, help="Override document id.")
def memory_ingest(
    path: str,
    backend: str,
    working_dir: Optional[str],
    parser: str,
    query_mode: str,
    pack_id: Optional[str],
    doc_id: Optional[str],
) -> None:
    """Ingest a file or text snippet into a memory backend."""
    config = _memory_config_from_options(backend, working_dir, parser, query_mode)
    instance = build_backend(config)
    is_file = os.path.isfile(path)
    if is_file:
        # For mock backend (and any text-aware backend), read the contents.
        text = None
        if backend == "mock":
            try:
                text = open(path, "r", encoding="utf-8").read()
            except UnicodeDecodeError:
                text = None
        doc = IngestDocument(
            id=doc_id or os.path.basename(path),
            path=path,
            text=text,
            pack_id=pack_id,
        )
    else:
        doc = IngestDocument(id=doc_id or "inline", text=path, pack_id=pack_id)
    result = instance.ingest([doc])
    click.echo(json.dumps(result, indent=2, default=str))


@memory.command("query")
@click.argument("text")
@click.option("--backend", default="mock")
@click.option("--working-dir", default=None)
@click.option("--parser", default="mineru")
@click.option("--query-mode", default="hybrid")
@click.option("--pack", "pack_id", default=None)
@click.option("--top-k", default=5)
def memory_query(
    text: str,
    backend: str,
    working_dir: Optional[str],
    parser: str,
    query_mode: str,
    pack_id: Optional[str],
    top_k: int,
) -> None:
    """Issue a retrieval query against a memory backend."""
    config = _memory_config_from_options(backend, working_dir, parser, query_mode)
    instance = build_backend(config)
    result = instance.retrieve(RetrievalQuery(text=text, top_k=top_k), pack_id=pack_id)
    click.echo(
        json.dumps(
            {
                "backend": getattr(instance, "name", backend),
                "ready": getattr(instance, "ready", True),
                "entities": [e.model_dump() for e in result.entities],
                "snippets": result.snippets,
            },
            indent=2,
            default=str,
        )
    )


# ---------- objective ----------


@cli.group()
def objective() -> None:
    """Run objectives with a workflow pack."""


@objective.command("run")
@click.argument("objective_text")
@click.option("--pack", "pack_id", default=None, help="Workflow pack id to use.")
@click.option("--mock/--no-mock", default=True, help="Use deterministic mock providers.")
@click.option("--trace-dir", default=".neuronium/traces", help="Where to write trace files.")
@click.option("--auto-approve/--no-auto-approve", default=None, help="Auto-approve gates.")
@click.option("--input", "extra_inputs", multiple=True, help="key=value run input.")
@click.option("--json", "output_json", is_flag=True, help="Emit machine-readable JSON.")
@click.option("--memory-backend", default="mock", help="Memory backend name (mock|raganything|...).")
@click.option("--memory-working-dir", default=None, help="Backend working directory.")
@click.option("--memory-parser", default="mineru", help="Parser for raganything.")
@click.option("--memory-query-mode", default="hybrid", help="Query mode (raganything).")
@click.option("--provider", default="mock", help="Model provider (mock|anthropic|openai|gemini|multi).")
@click.option("--provider-model", default=None, help="Override model id (e.g. claude-opus-4-7).")
@click.option("--provider-max-tokens", default=None, type=int, help="Override max_tokens.")
@click.option("--provider-mock/--no-provider-mock", default=False, help="Make the chosen real provider run in mock mode (no API key needed).")
@click.option("--real-tools/--no-real-tools", default=False, help="Use real shell+fs tools.")
@click.option("--cwd", default=None, help="Working directory for real tools.")
@click.option("--allow-dir", multiple=True, help="Additional allowed root for real fs tools.")
@click.option("--shell-timeout-s", default=30, type=int)
@click.option("--allow-destructive/--no-allow-destructive", default=False)
def objective_run(
    objective_text: str,
    pack_id: Optional[str],
    mock: bool,
    trace_dir: str,
    auto_approve: Optional[bool],
    extra_inputs: tuple,
    output_json: bool,
    memory_backend: str,
    memory_working_dir: Optional[str],
    memory_parser: str,
    memory_query_mode: str,
    provider: str,
    provider_model: Optional[str],
    provider_max_tokens: Optional[int],
    provider_mock: bool,
    real_tools: bool,
    cwd: Optional[str],
    allow_dir: tuple,
    shell_timeout_s: int,
    allow_destructive: bool,
) -> None:
    """Run a free-text objective through the platform."""
    parsed_inputs = {}
    for entry in extra_inputs:
        if "=" not in entry:
            continue
        k, v = entry.split("=", 1)
        parsed_inputs[k.strip()] = v.strip()
    if auto_approve is None:
        auto_approve = mock
    memory_config = _memory_config_from_options(
        memory_backend, memory_working_dir, memory_parser, memory_query_mode
    )
    provider_options: dict = {}
    if provider_model:
        provider_options["model"] = provider_model
    if provider_max_tokens:
        provider_options["max_tokens"] = provider_max_tokens
    if provider_mock:
        provider_options["mock_mode"] = True
    rt_config: Optional[RealToolsConfig] = None
    if real_tools:
        cwd_resolved = cwd or os.getcwd()
        roots = [cwd_resolved] + list(allow_dir or [])
        rt_config = RealToolsConfig(
            cwd=cwd_resolved,
            allowed_roots=roots,
            timeout_s=shell_timeout_s,
            allow_destructive=allow_destructive,
        )
    runner = ObjectiveRunner(
        trace_dir=trace_dir,
        auto_approve=auto_approve,
        memory_config=memory_config,
        provider=provider,
        provider_options=provider_options,
        real_tools_config=rt_config,
    )
    try:
        result = runner.run(objective_text, pack_id=pack_id, inputs=parsed_inputs)
    except Exception as exc:  # noqa: BLE001
        click.echo(f"error: {exc}", err=True)
        sys.exit(2)
    if output_json:
        click.echo(
            json.dumps(
                {
                    "run_id": result.run.id,
                    "pack_id": result.run.pack_id,
                    "status": result.run.status.value,
                    "visited": result.visited_nodes,
                    "replans": result.replans,
                    "trace_path": result.run.trace_path,
                    "final_report": result.final_report,
                },
                indent=2,
            )
        )
        return
    console.rule(f"Run {result.run.id}")
    console.print(f"pack: [bold]{result.run.pack_id}[/bold]")
    console.print(f"status: [green]{result.run.status.value}[/green]")
    console.print(f"replans: {result.replans}")
    console.print(f"visited nodes: {' -> '.join(result.visited_nodes)}")
    if result.run.trace_path:
        console.print(f"trace: {result.run.trace_path}")
    console.rule("Final outcome")
    console.print(result.final_report)


# ---------- code (interactive coding mode) ----------


@cli.command()
@click.argument("objective_text", required=False)
@click.option("--pack", "pack_id", default="coding", help="Coding pack id.")
@click.option("--mock/--no-mock", default=True, help="Use deterministic mock providers.")
@click.option("--repl/--once", default=False, help="Multi-turn REPL or single-shot run.")
@click.option("--trace-dir", default=".neuronium/traces", help="Trace directory.")
@click.option("--memory-backend", default="mock")
@click.option("--memory-working-dir", default=None)
@click.option("--memory-parser", default="mineru")
@click.option("--memory-query-mode", default="hybrid")
@click.option("--provider", default="mock", help="Model provider (mock|anthropic|openai|gemini|multi).")
@click.option("--provider-model", default=None)
@click.option("--provider-max-tokens", default=None, type=int)
@click.option("--provider-mock/--no-provider-mock", default=False, help="Run real provider in mock mode (no API key needed).")
@click.option("--real-tools/--no-real-tools", default=False, help="Use real shell+fs tools.")
@click.option("--cwd", default=None, help="Working directory for real tools (defaults to .).")
@click.option("--allow-dir", multiple=True, help="Additional allowed root for real fs tools.")
@click.option("--shell-timeout-s", default=30, type=int, help="Per-command shell timeout.")
@click.option("--allow-destructive/--no-allow-destructive", default=False)
def code(
    objective_text: Optional[str],
    pack_id: str,
    mock: bool,
    repl: bool,
    trace_dir: str,
    memory_backend: str,
    memory_working_dir: Optional[str],
    memory_parser: str,
    memory_query_mode: str,
    provider: str,
    provider_model: Optional[str],
    provider_max_tokens: Optional[int],
    provider_mock: bool,
    real_tools: bool,
    cwd: Optional[str],
    allow_dir: tuple,
    shell_timeout_s: int,
    allow_destructive: bool,
) -> None:
    """Coding mode — single-shot or multi-turn REPL with `--repl`."""
    text = objective_text or "Help me with this codebase"
    memory_config = _memory_config_from_options(
        memory_backend, memory_working_dir, memory_parser, memory_query_mode
    )
    provider_options: dict = {}
    if provider_model:
        provider_options["model"] = provider_model
    if provider_max_tokens:
        provider_options["max_tokens"] = provider_max_tokens
    if provider_mock:
        provider_options["mock_mode"] = True
    rt_config: Optional[RealToolsConfig] = None
    if real_tools:
        cwd_resolved = cwd or os.getcwd()
        roots = [cwd_resolved] + list(allow_dir or [])
        rt_config = RealToolsConfig(
            cwd=cwd_resolved,
            allowed_roots=roots,
            timeout_s=shell_timeout_s,
            allow_destructive=allow_destructive,
        )

    def runner_factory(*, pack_id: str = pack_id) -> ObjectiveRunner:
        return ObjectiveRunner(
            trace_dir=trace_dir,
            auto_approve=mock,
            memory_config=memory_config,
            provider=provider,
            provider_options=provider_options,
            real_tools_config=rt_config,
        )

    if repl:
        repl_loop = CodeRepl(runner_factory, pack_id=pack_id, console=console)
        repl_loop.loop()
        return
    runner = runner_factory()
    try:
        result = runner.run(text, pack_id=pack_id)
    except Exception as exc:  # noqa: BLE001
        click.echo(f"error: {exc}", err=True)
        sys.exit(2)
    console.rule(f"Coding run {result.run.id}")
    console.print(f"status: {result.run.status.value}")
    console.print(f"changed files: {result.final_state.get('changed_files', [])}")
    console.rule("Outcome")
    console.print(result.final_report)


# ---------- providers ----------


@cli.group()
def providers() -> None:
    """Inspect installed model providers."""


@providers.command("list")
def providers_list() -> None:
    table = Table(title="Model providers")
    table.add_column("name")
    table.add_column("default model")
    table.add_column("installed")
    table.add_column("env var")
    rows = [
        ("mock", "—", True, ""),
        ("anthropic", "claude-opus-4-7", _module_installed("anthropic"), "ANTHROPIC_API_KEY"),
        ("openai", "gpt-4o", _module_installed("openai"), "OPENAI_API_KEY"),
        ("gemini", "gemini-2.5-pro", _module_installed("google.genai") or _module_installed("google.generativeai"), "GEMINI_API_KEY"),
    ]
    for name, default, installed, env_var in rows:
        marker = "[green]yes[/green]" if installed else "[yellow]no[/yellow]"
        env_state = ""
        if env_var:
            env_state = "set" if os.environ.get(env_var) else "not set"
        table.add_row(name, default, marker, f"{env_var} ({env_state})" if env_var else "")
    console.print(table)


def _module_installed(module_name: str) -> bool:
    try:
        import importlib

        importlib.import_module(module_name)
        return True
    except Exception:
        return False


# ---------- runs ----------


@cli.group()
def runs() -> None:
    """Inspect prior run traces."""


@runs.command("list")
@click.option("--trace-dir", default=".neuronium/traces")
def runs_list(trace_dir: str) -> None:
    summaries = list_runs(trace_dir)
    if not summaries:
        console.print(f"[yellow]no runs in {trace_dir}[/yellow]")
        return
    table = Table(title=f"Runs in {trace_dir}")
    table.add_column("run_id")
    table.add_column("pack")
    table.add_column("status")
    table.add_column("events")
    table.add_column("objective")
    for s in summaries:
        table.add_row(
            s.run_id,
            s.pack_id or "",
            s.status or "",
            str(s.event_count),
            (s.objective or "")[:60],
        )
    console.print(table)


@runs.command("show")
@click.argument("run_id_or_path")
@click.option("--trace-dir", default=".neuronium/traces")
@click.option("--kinds", default=None, help="Comma-separated event kinds to filter.")
def runs_show(run_id_or_path: str, trace_dir: str, kinds: Optional[str]) -> None:
    path = run_id_or_path
    if not os.path.isfile(path):
        path = os.path.join(trace_dir, f"{run_id_or_path}.jsonl")
    if not os.path.isfile(path):
        click.echo(f"error: trace not found: {path}", err=True)
        sys.exit(2)
    data = show_run(path)
    summary = data["summary"]
    console.rule(summary["run_id"])
    console.print(f"pack: {summary['pack_id']}, status: {summary['status']}, events: {summary['event_count']}")
    if summary["objective"]:
        console.print(f"objective: {summary['objective']}")
    filter_set = {k.strip() for k in kinds.split(",")} if kinds else None
    for event in data["events"]:
        if filter_set and event.get("kind") not in filter_set:
            continue
        console.print(
            f"#{event.get('seq', '?')} {event.get('kind')}: {json.dumps(event.get('payload', {}), default=str)[:200]}"
        )


@runs.command("replay")
@click.argument("run_id_or_path")
@click.option("--trace-dir", default=".neuronium/traces")
def runs_replay(run_id_or_path: str, trace_dir: str) -> None:
    """Replay a prior run in mock mode using the original objective + pack."""
    path = run_id_or_path
    if not os.path.isfile(path):
        path = os.path.join(trace_dir, f"{run_id_or_path}.jsonl")
    if not os.path.isfile(path):
        click.echo(f"error: trace not found: {path}", err=True)
        sys.exit(2)
    data = show_run(path)
    summary = data["summary"]
    objective = summary.get("objective") or "(unknown objective)"
    pack_id = summary.get("pack_id")
    if not pack_id:
        click.echo("error: trace has no pack id; cannot replay", err=True)
        sys.exit(2)
    runner = ObjectiveRunner(
        trace_dir=trace_dir + "/replay",
        auto_approve=True,
        provider="mock",
    )
    result = runner.run(objective, pack_id=pack_id)
    console.print(
        f"[green]replayed[/green] -> {result.run.status.value}, trace: {result.run.trace_path}"
    )


# ---------- mcp ----------


@cli.group()
def mcp() -> None:
    """Manage MCP server connections."""


@mcp.command("list")
@click.option("--config", "config_path", default=".neuronium/mcp.yaml")
def mcp_list(config_path: str) -> None:
    if not os.path.isfile(config_path):
        console.print(f"[yellow]no mcp config[/yellow] {config_path}")
        return
    import yaml

    with open(config_path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    table = Table(title=f"MCP servers from {config_path}")
    table.add_column("name")
    table.add_column("transport")
    table.add_column("target")
    for name, cfg in (data.get("mcp_servers") or {}).items():
        target = cfg.get("url") or cfg.get("command", "")
        if cfg.get("args"):
            target = f"{target} {' '.join(cfg.get('args', []))}"
        table.add_row(name, cfg.get("transport", "stdio"), target)
    console.print(table)


@mcp.command("test")
@click.argument("name")
@click.option("--config", "config_path", default=".neuronium/mcp.yaml")
def mcp_test(name: str, config_path: str) -> None:
    """Connect to one MCP server and list its tools."""
    if not os.path.isfile(config_path):
        click.echo(f"error: no config at {config_path}", err=True)
        sys.exit(2)
    import yaml

    from neuronium_agent.mcp.config import MCPServerConfig
    from neuronium_agent.mcp.loader import MCPLoader, _build_client  # type: ignore

    with open(config_path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    raw = (data.get("mcp_servers") or {}).get(name)
    if raw is None:
        click.echo(f"error: server '{name}' not in config", err=True)
        sys.exit(2)
    cfg = MCPServerConfig(name=name, **raw)
    try:
        client = _build_client(cfg)
        client.initialize()
        tools = client.list_tools()
        client.close()
    except Exception as exc:  # noqa: BLE001
        click.echo(f"error: {exc}", err=True)
        sys.exit(1)
    table = Table(title=f"{name} tools")
    table.add_column("tool")
    table.add_column("description")
    for t in tools:
        table.add_row(t.name, (t.description or "")[:80])
    console.print(table)


# ---------- doctor ----------


@cli.command()
def doctor() -> None:
    """Run preflight checks on the runtime environment."""
    registry = PackRegistry()
    console.rule("doctor")
    console.print(f"version: {__version__}")
    console.print(f"installed packs: {', '.join(registry.list_ids()) or '(none)'}")
    console.print(f"memory backends: {', '.join(list_backends())}")
    try:
        import importlib

        importlib.import_module("raganything")
        console.print("[green]raganything: installed[/green]")
    except Exception:  # noqa: BLE001
        console.print(
            "[yellow]raganything: not installed[/yellow] "
            "(install with `pip install 'raganything[all]'` to enable RAG-Anything backend)"
        )
    try:
        import importlib

        importlib.import_module("anthropic")
        if os.environ.get("ANTHROPIC_API_KEY"):
            console.print(
                "[green]anthropic: installed[/green] (ANTHROPIC_API_KEY present — "
                "`--provider anthropic` ready)"
            )
        else:
            console.print(
                "[yellow]anthropic: installed but ANTHROPIC_API_KEY not set[/yellow]"
            )
    except Exception:  # noqa: BLE001
        cmd = "pip install 'neuronium-agent[anthropic]'"
        console.print(
            f"[yellow]anthropic: not installed[/yellow] (install with `{cmd}` to enable real Claude calls)"
        )
    leaks = []
    for env_key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        if env_key in os.environ:
            leaks.append(env_key)
    if leaks:
        console.print(
            f"[yellow]warning[/yellow] env keys present: {leaks}. Trace will redact them."
        )
    else:
        console.print("[green]no provider env keys detected[/green]")


def main() -> None:
    cli(prog_name="neuronium-agent")


if __name__ == "__main__":
    main()
