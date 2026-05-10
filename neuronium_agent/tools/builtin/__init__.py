"""Real (non-mock) tool implementations.

These are opt-in. When `real_tools=True` is passed through the runtime, the
real shell and fs tools are registered instead of the MockMCP defaults.
Governance still applies — shell.run and fs.edit are gated through
`PolicyEngine` and human approval as before.
"""

from neuronium_agent.tools.builtin.safety import (
    DenyReason,
    is_destructive,
    safe_resolve,
)
from neuronium_agent.tools.builtin.shell import RealShellTool
from neuronium_agent.tools.builtin.fs import RealFsTools

__all__ = [
    "DenyReason",
    "RealFsTools",
    "RealShellTool",
    "is_destructive",
    "safe_resolve",
]
