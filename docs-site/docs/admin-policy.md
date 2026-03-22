# Admin Policy Reference

This document defines the enterprise admin policy schema used to restrict sensitive runtime behavior.

- Template: `/inquira.policy.toml.example`
- Recommended path: `/etc/inquira/policy.toml` (or `INQUIRA_POLICY_PATH`)
- Precedence (highest first): admin policy > `inquira.toml` > UI/user preferences

## Meta

<a id="meta-version"></a>
### `meta.version`
- Type: `string`
- Purpose: policy schema version.

<a id="meta-owner"></a>
### `meta.owner`
- Type: `string`
- Purpose: owning team for support/audit.

<a id="meta-change-ticket"></a>
### `meta.change_ticket`
- Type: `string`
- Purpose: change reference for audit trail.

## Enforcement

<a id="enforcement-mode"></a>
### `enforcement.mode`
- Type: `string`
- Allowed: `enforce`, `audit`
- Purpose: choose strict blocking (`enforce`) or report-only mode (`audit`).

## UI

<a id="ui-hide-managed-settings"></a>
### `ui.hide_managed_settings`
- Type: `bool`
- Purpose: hide centrally managed settings in the UI.

## Observability

<a id="observability-allow"></a>
### `observability.allow`
- Type: `bool`
- Purpose: master gate for tracing/telemetry providers.

<a id="observability-redact-sensitive-content"></a>
### `observability.redact_sensitive_content`
- Type: `bool`
- Purpose: force redaction for sensitive fields in exported traces.

## Backend Phoenix

<a id="backend-phoenix-allow"></a>
### `backend.phoenix.allow`
- Type: `bool`
- Purpose: allow backend process trace export to Phoenix.

<a id="backend-phoenix-locked"></a>
### `backend.phoenix.locked`
- Type: `bool`
- Purpose: prevent user/UI overrides for backend Phoenix settings.

<a id="backend-phoenix-allowed-endpoints"></a>
### `backend.phoenix.allowed_endpoints`
- Type: `array[string]`
- Purpose: endpoint allowlist for backend Phoenix exporter.

## Agent Phoenix

<a id="agent-service-phoenix-allow"></a>
### `agent_service.phoenix.allow`
- Type: `bool`
- Purpose: allow agent process trace export to Phoenix.

<a id="agent-service-phoenix-locked"></a>
### `agent_service.phoenix.locked`
- Type: `bool`
- Purpose: prevent user/UI overrides for agent Phoenix settings.

<a id="agent-service-phoenix-allowed-endpoints"></a>
### `agent_service.phoenix.allowed_endpoints`
- Type: `array[string]`
- Purpose: endpoint allowlist for agent Phoenix exporter.

## LLM Controls

<a id="llm-allowed-providers"></a>
### `llm.allowed_providers`
- Type: `array[string]`
- Purpose: provider allowlist enforced by runtime.

<a id="llm-block-custom-base-url"></a>
### `llm.block_custom_base_url`
- Type: `bool`
- Purpose: block custom model base URLs when required by policy.

<a id="llm-block-user-api-keys"></a>
### `llm.block_user_api_keys`
- Type: `bool`
- Purpose: disallow user-provided API keys.

<a id="llm-models"></a>
### `llm.models.<provider>`
- Type: `array[string]`
- Purpose: model allowlist by provider.

## Tools

<a id="tools-allow"></a>
### `tools.allow`
- Type: `bool`
- Purpose: master gate for interactive tools.

<a id="tools-bash-allow"></a>
### `tools.bash.allow`
- Type: `bool`
- Purpose: enable/disable shell execution tool.

<a id="tools-bash-locked"></a>
### `tools.bash.locked`
- Type: `bool`
- Purpose: prevent user/UI override for bash tool.

<a id="tools-bash-allowed-commands"></a>
### `tools.bash.allowed_commands`
- Type: `array[string]`
- Purpose: strict allowlist for executable commands.

<a id="tools-pip-install-allow"></a>
### `tools.pip_install.allow`
- Type: `bool`
- Purpose: allow/deny package installs from prompts.

<a id="tools-pip-install-locked"></a>
### `tools.pip_install.locked`
- Type: `bool`
- Purpose: prevent user/UI override for package install tool.

## Execution Limits

<a id="execution"></a>
### `execution.max_timeout_seconds` / `execution.max_memory_mb` / `execution.max_output_kb`
- Type: `int`
- Purpose: hard runtime limits for safety and cost control.

## Network Controls

<a id="network-allowed-hosts"></a>
### `network.allowed_hosts`
- Type: `array[string]`
- Purpose: restrict outbound hosts when egress enforcement is enabled.

<a id="network-require-proxy"></a>
### `network.require_proxy`
- Type: `bool`
- Purpose: force organization proxy usage.

## Data Controls

<a id="data-allowed-workspace-roots"></a>
### `data.allowed_workspace_roots`
- Type: `array[string]`
- Purpose: constrain workspace roots to approved directories.

<a id="data-block-export"></a>
### `data.block_export`
- Type: `bool`
- Purpose: prevent data/artifact exports outside policy.

## Retention

<a id="retention-max-conversation-days"></a>
### `retention.max_conversation_days`
- Type: `int`
- Purpose: cap retention window for conversation history.

<a id="retention-max-artifact-hours"></a>
### `retention.max_artifact_hours`
- Type: `int`
- Purpose: cap retention window for artifacts.

## Audit

<a id="audit-log-policy-violations"></a>
### `audit.log_policy_violations`
- Type: `bool`
- Purpose: log attempts to override managed policy.

