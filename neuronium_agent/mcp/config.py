"""Pydantic config models for MCP servers."""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class MCPTransport(str, Enum):
    STDIO = "stdio"
    HTTP = "http"


class MCPServerConfig(BaseModel):
    """One MCP server. Either stdio (with `command` + `args`) or http (with `url`)."""

    model_config = ConfigDict(extra="forbid")
    name: str
    transport: MCPTransport = MCPTransport.STDIO
    command: Optional[str] = None
    args: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)
    url: Optional[str] = None
    headers: Dict[str, str] = Field(default_factory=dict)
    api_key_env: Optional[str] = None
    required: bool = False
    risk_default: str = "medium"  # default risk class for tools from this server
