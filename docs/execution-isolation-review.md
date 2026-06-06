# Execution Isolation Review

## Current Truth

Python kernels and terminal commands run as the desktop user. They can access the user's filesystem,
network, processes, and available memory. Execution timeouts and captured-output limits are enforced.
Configured memory, import, and builtin limits are advisory and are not a security boundary.

## Required Design Decision

Before claiming sandboxed execution, choose and validate a platform-specific isolation boundary for
macOS and Windows. The design must cover CPU and memory limits, process spawning, filesystem mounts,
network access, package installation, kernel reuse, artifact export, and recovery after termination.

## Minimum Acceptance Criteria

- AI-generated and manual execution trust policies are explicit and separately configurable.
- Resource exhaustion cannot terminate the desktop shell or consume unbounded host memory.
- Workspace files are the only writable mounted user data unless the user explicitly grants access.
- Network and subprocess access are denied by default or clearly disclosed and granted.
- Limits are enforced by the operating-system boundary, not Python-level checks.
- Failure states identify whether execution was denied, killed, timed out, or partially completed.
- Cross-platform failure-injection and escape tests run before release.
