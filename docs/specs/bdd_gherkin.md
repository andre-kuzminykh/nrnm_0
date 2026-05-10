# Neuronium — BDD Scenarios

All scenarios are tagged with the requirement and the test ID they map to.

## Agent system

```gherkin
@NR-BDD-AGENT-001 @NR-FR-300 @NR-FR-303 @NR-UT-AGENT-002
Feature: Agent instances
  Scenario: Agent instances are created for a run
    Given a workflow pack defines planner, executor, and critic agents
    When a run starts with that pack
    Then Neuronium should create agent instances for the run
    And record agent_created events
```

```gherkin
@NR-BDD-AGENT-002 @NR-FR-304 @NR-IT-AGENT-001
Feature: Dynamic Agent Factory
  Scenario: Objective creates task-specific agents
    Given the user submits a complex consulting objective
    When objective planning starts
    Then Neuronium should propose task-specific agents
    And each generated agent should have tools, permissions, context budget, and output contract
```

## Workflow Pack DSL

```gherkin
@NR-BDD-PACK-001 @NR-FR-320 @NR-FR-323 @NR-IT-PACK-001
Feature: Workflow Pack DSL
  Scenario: Coding pack compiles into runtime definitions
    Given a valid coding workflow pack YAML
    When Neuronium compiles the pack
    Then it should produce agent definitions
    And tool policies
    And workflow definitions
    And tests
```

```gherkin
@NR-BDD-PACK-002 @NR-FR-325 @NR-FR-330 @NR-E2E-PACK-001
Feature: Coding Workflow Pack
  Scenario: User runs coding objective with coding pack
    Given the coding workflow pack is installed
    And mock MCP tools are enabled
    When the user runs "neuronium-agent objective run 'Fix failing tests' --pack coding --mock"
    Then Neuronium should select the coding pack
    And create coding agents
    And execute the coding workflow
    And produce final outcome
```

```gherkin
@NR-BDD-PACK-003 @NR-FR-328 @NR-E2E-PACK-002
Feature: Generate workflow pack from simple template
  Scenario: User describes HR workflow in markdown
    Given a simple workflow pack template is filled for HR recruiting
    When the workflow pack generator runs
    Then it should create a structured workflow pack YAML
    And validate it
    And create mock tests
```

```gherkin
@NR-BDD-PACK-004 @NR-FR-PACK-050
Feature: Workflow pack scaffolding
  Scenario: User creates new marketing workflow pack scaffold
    When the user runs "neuronium-agent packs init marketing"
    Then a valid workflow pack scaffold should be created
    And it should include agents, tools, workflows, prompts and tests
```

## Coding pack interactive mode

```gherkin
@NR-BDD-CODE-001 @NR-FR-CODE-001 @NR-FR-CODE-005
Feature: Interactive coding mode
  Scenario: User starts coding session
    Given the coding pack is installed
    When the user runs "neuronium-agent code"
    Then an interactive coding session should start
    And coding agents should be available
```

```gherkin
@NR-BDD-CODE-002 @NR-FR-CODE-003 @NR-FR-CODE-008
Feature: Safe code edit
  Scenario: Code editor requires approval before patch
    Given a coding run proposes a file edit
    When the edit is ready
    Then the user should see a diff preview
    And the edit should wait for approval
```

## Configuration and security

```gherkin
@NR-BDD-CONFIG-001 @NR-FR-CFG-003
Feature: Configuration hierarchy
  Scenario: Project config overrides global config
    Given global config defines model alias "fast"
    And project config overrides model alias "fast"
    When effective config is resolved
    Then the project alias should win
```

```gherkin
@NR-BDD-SEC-001 @NR-FR-SEC-002
Feature: Secret redaction
  Scenario: Trace export redacts API keys
    Given a tool input contains an API key
    When trace is exported
    Then the API key should be redacted
```
