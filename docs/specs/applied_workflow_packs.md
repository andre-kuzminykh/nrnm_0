# Applied Workflow Packs

A Workflow Pack is a self-contained description of an applied domain. Neuronium ships built-in packs (`coding`, `marketing`, `hr`) and accepts user-installed packs in `<project>/.neuronium/packs/`.

## Registry lookup order

1. Built-in packs (`neuronium_agent.packs.builtin.*`).
2. User-installed packs (path provided via config).
3. Project-local packs (`<project>/.neuronium/packs/`).

## Selecting a pack at runtime

- Explicit: `--pack coding`.
- Implicit: the objective text is matched against `objectives[].user_phrases` of installed packs; the best match is suggested.

## Pack lifecycle

| Stage | Command |
| --- | --- |
| Inspect | `neuronium-agent packs list` |
| Show | `neuronium-agent packs show <pack>` |
| Validate | `neuronium-agent packs validate <path-or-id>` |
| Test | `neuronium-agent packs test <pack>` |
| Install | `neuronium-agent packs install <path>` |
| Remove | `neuronium-agent packs remove <pack>` |
| Init | `neuronium-agent packs init <name>` |
| Generate | `neuronium-agent packs generate <template.md> --out <path>` |

## Status of built-in packs

- **coding** — first applied pack, drives v0.1 vertical slice.
- **marketing** — DSL + mock tests; runtime executes the workflow with mock provider.
- **hr** — DSL + mock tests; runtime executes the workflow with mock provider.
- **sales / consulting / operations / finance** — deferred; documented as plan.

## Authoring a custom pack

1. Run `neuronium-agent packs init my_pack --name "My Pack"`.
2. Edit the generated YAML.
3. Add prompts under `prompts/packs/<id>/`.
4. Validate: `neuronium-agent packs validate ./packs/my_pack.yaml`.
5. Test in mock mode: `neuronium-agent packs test my_pack`.
6. Install: `neuronium-agent packs install ./packs/my_pack.yaml`.

## Simple markdown template

See `neuronium_agent/packs/templates/workflow_pack_template.md`. Filling it in and running:

```
neuronium-agent packs generate path/to/template.md --out packs/my_pack.yaml
```

produces a valid DSL draft.
