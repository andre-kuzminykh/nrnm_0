# Real shell + fs tools

`MockMCP` ships by default. To actually execute commands and edit files, opt in
with `real_tools=True` (Python API) or `--real-tools` (CLI). Real tools use the
**same** `<server>.<tool>` refs that the mock layer uses, so packs and policies
do not change.

## Implementations

| Tool ref | Class | Risk | Default permission |
| --- | --- | --- | --- |
| `shell.run` | `RealShellTool` | critical | `require_approval` |
| `fs.read` | `RealFsTools.read` | low | `allow` |
| `fs.write` | `RealFsTools.write` | high | `require_approval` |
| `fs.edit` | `RealFsTools.edit` | high | `require_approval` |
| `patch.apply` | `RealFsTools.patch_apply` | high | `require_approval` |
| `glob.search` | `RealFsTools.glob_search` | low | `allow` |
| `grep.search` | `RealFsTools.grep_search` | low | `allow` |
| `git.status` | `RealFsTools.git_status` | low | `allow` |
| `git.diff` | `RealFsTools.git_diff` | low | `allow` |

## Safety

- **Denylist** (in `safety.is_destructive`):
  - `rm -rf /` and `rm --recursive --force /`
  - `mkfs`, `dd if=/dev/zero of=/dev/...`
  - shell fork bombs
  - `shutdown`, `halt`, `reboot`, `poweroff`
  - redirects to `/dev/sd*`, `/dev/nvme*`
  - `chmod -R 777 /` and `chown -R user /`
  - `curl ... | bash`, `wget ... | sh`
  - `eval $(...)`, `nc -l`
- **Path sandbox** (in `safety.safe_resolve`): every `fs.*` and `glob`/`grep`
  call resolves the user-supplied path and refuses anything outside the
  configured `allowed_roots`.
- **Per-call timeout** for shell commands (default 30s).
- **Output cap** (default 64 KiB stdout + stderr) — anything beyond is dropped
  and `truncated: true` is set on the result.
- **Per-tool risk class** is preserved by `register_real_tools`, so the pack's
  permission policy still applies (most edits + shell.run still
  `require_approval`).

## CLI

```bash
neuronium-agent objective run "Unzip every archive under ~/Desktop/hmnd into a new folder 123" \
    --pack coding \
    --provider anthropic \
    --real-tools \
    --cwd ~/Desktop/hmnd \
    --allow-dir ~/Desktop/hmnd \
    --shell-timeout-s 60
neuronium-agent code "fix the failing test" --repl --real-tools --cwd .
```

By default `--allow-destructive` is off; set it explicitly only when running
in a sandbox.

## Diff preview

When the model (or an IR `ToolNode`) requests a tool whose decision is
`require_approval`, the gate renders a unified diff (or command preview) before
asking the operator:

| Tool | Preview |
| --- | --- |
| `fs.edit` | full unified diff between current file content and post-edit content |
| `fs.write` | "create / overwrite" header + truncated content |
| `patch.apply` | unified-diff blob (truncated at 16 KiB) |
| `shell.run` | `$ <command>` |

Implementation: `neuronium_agent/runtime/diff_preview.py`. Tests:
`tests/unit/test_runs_and_diff.py`.

## Tests

`tests/unit/test_real_tools.py` covers:
- denylist: positive + negative cases (`rm -rf /` blocked, `unzip a.zip -d 123` allowed)
- safe-path: reads inside sandbox; rejects `/etc/passwd`
- shell: simple run, timeout, output cap, invalid cwd
- fs: read / write / edit / patch.apply / glob / grep
- registry: real tools register with proper risk + JSON schemas

`tests/integration/test_real_tools_runner.py` exercises the runtime end-to-end
with `real_tools=True` and confirms the `tools.real_enabled` event fires.
