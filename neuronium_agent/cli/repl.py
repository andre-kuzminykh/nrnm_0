"""Multi-turn REPL for the `code` command.

Each turn appends to a session-scoped state dict that is fed back into the
ObjectiveRunner on subsequent turns. State persists in-memory for the life of
the REPL; `/save <path>` writes a JSON snapshot, `/resume <path>` loads one.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console

from neuronium_agent.runtime.objective_runner import ObjectiveRunner


HELP = """\
commands:
  /help            this help
  /exit            quit
  /clear           reset turn history
  /save <path>     save session state to JSON
  /resume <path>   load session state from JSON
  /pack <id>       switch the active workflow pack
  /provider <id>   switch model provider (mock|anthropic|openai|gemini)
"""


class CodeRepl:
    def __init__(
        self,
        runner_factory,
        *,
        pack_id: str = "coding",
        console: Optional[Console] = None,
    ) -> None:
        self.runner_factory = runner_factory
        self.pack_id = pack_id
        self.console = console or Console()
        self.history: List[Dict[str, Any]] = []
        self.state: Dict[str, Any] = {}

    def loop(self) -> None:
        self.console.print(
            f"[bold]Neuronium code REPL[/bold] — pack: {self.pack_id}. Type /help for commands."
        )
        while True:
            try:
                line = input("you> ").strip()
            except EOFError:
                self.console.print("\n(end)")
                return
            if not line:
                continue
            if line.startswith("/"):
                if self._handle_command(line):
                    return
                continue
            self._handle_turn(line)

    # ---- turn ----

    def _handle_turn(self, text: str) -> None:
        runner = self.runner_factory(pack_id=self.pack_id)
        prior_summary = self._compose_history_summary()
        inputs = dict(self.state)
        if prior_summary:
            inputs["history"] = prior_summary
        try:
            result = runner.run(text, pack_id=self.pack_id, inputs=inputs)
        except Exception as exc:  # noqa: BLE001
            self.console.print(f"[red]error[/red] {exc}")
            return
        self.console.rule(f"turn {len(self.history) + 1}")
        self.console.print(result.final_report)
        self.history.append(
            {
                "turn": len(self.history) + 1,
                "user": text,
                "run_id": result.run.id,
                "status": result.run.status.value,
                "trace_path": result.run.trace_path,
                "final_report": result.final_report,
                "verdict": result.final_state.get("verdict"),
                "changed_files": result.final_state.get("changed_files"),
            }
        )
        # Carry useful state forward so next turn knows what already happened.
        for key in ("changed_files", "test_result", "verdict"):
            if key in result.final_state:
                self.state[key] = result.final_state[key]

    def _compose_history_summary(self) -> str:
        if not self.history:
            return ""
        lines = ["Prior turns:"]
        for turn in self.history[-5:]:
            lines.append(
                f"#{turn['turn']} ({turn['status']}, verdict={turn.get('verdict')}): {turn['user']}"
            )
        return "\n".join(lines)

    # ---- commands ----

    def _handle_command(self, line: str) -> bool:
        parts = line.split(maxsplit=1)
        cmd = parts[0]
        arg = parts[1] if len(parts) > 1 else ""
        if cmd in {"/exit", "/quit"}:
            return True
        if cmd == "/help":
            self.console.print(HELP)
            return False
        if cmd == "/clear":
            self.history.clear()
            self.state.clear()
            self.console.print("[yellow]history cleared[/yellow]")
            return False
        if cmd == "/save":
            path = arg or ".neuronium/repl-session.json"
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(
                    {"pack_id": self.pack_id, "history": self.history, "state": self.state},
                    fh,
                    indent=2,
                    default=str,
                )
            self.console.print(f"[green]saved[/green] {path}")
            return False
        if cmd == "/resume":
            path = arg
            if not path or not Path(path).is_file():
                self.console.print(f"[red]no such file[/red] {path}")
                return False
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            self.pack_id = data.get("pack_id", self.pack_id)
            self.history = data.get("history") or []
            self.state = data.get("state") or {}
            self.console.print(
                f"[green]resumed[/green] pack={self.pack_id}, turns={len(self.history)}"
            )
            return False
        if cmd == "/pack":
            self.pack_id = arg or self.pack_id
            self.console.print(f"[green]pack[/green] = {self.pack_id}")
            return False
        if cmd == "/provider":
            os.environ["NEURONIUM_PROVIDER"] = arg or "mock"
            self.console.print(f"[green]provider[/green] = {arg}")
            return False
        self.console.print(f"[yellow]unknown command[/yellow] {cmd}")
        return False
