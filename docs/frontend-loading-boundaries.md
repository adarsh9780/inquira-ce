# Frontend loading boundaries

The normal workspace and chat path keeps expensive or infrequently used features
out of the application entry:

| Feature | Boundary |
| --- | --- |
| Settings | `SettingsModal.vue`, followed by one independently loaded settings tab |
| Code | `CodeTab.vue`, mounted only when the Code pane is selected |
| Terminal | `TerminalTab.vue`, followed by `NativeTerminalPane.vue` after consent |
| Tables, charts, runs | Independently loaded result-pane components |
| Plotly | One cached dynamic loader used only when a chart renders |
| Rich Markdown | `MarkdownContent.vue` and tool-output preview boundaries |

The full Plotly distribution is retained because Inquira accepts arbitrary Plotly
figures produced by the Python analysis worker. A custom trace-only build would
silently remove supported chart types and export behavior. The distribution is an
emitted on-demand chunk and is absent from the initial application path.

The main application chunk budget is 350 KiB gzip. CodeMirror, xterm, and Plotly
must not appear in the initial dependency graph.
