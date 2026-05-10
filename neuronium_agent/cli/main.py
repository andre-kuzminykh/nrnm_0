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
def objective_run(
    objective_text: str,
    pack_id: Optional[str],
    mock: bool,
    trace_dir: str,
    auto_approve: Optional[bool],
    extra_inputs: tuple,
    output_json: bool,
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
    runner = ObjectiveRunner(
        trace_dir=trace_dir,
        auto_approve=auto_approve,
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
@click.option("--trace-dir", default=".neuronium/traces", help="Trace directory.")
def code(objective_text: Optional[str], pack_id: str, mock: bool, trace_dir: str) -> None:
    """Interactive coding mode (single-shot in v0.1)."""
    text = objective_text or "Help me with this codebase"
    runner = ObjectiveRunner(trace_dir=trace_dir, auto_approve=mock)
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


# ---------- doctor ----------


@cli.command()
def doctor() -> None:
    """Run preflight checks on the runtime environment."""
    registry = PackRegistry()
    console.rule("doctor")
    console.print(f"version: {__version__}")
    console.print(f"installed packs: {', '.join(registry.list_ids()) or '(none)'}")
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
