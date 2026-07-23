# Inquira frontend

The desktop interface is a Vue 3 application embedded by Wails. Product data,
native dialogs, terminal sessions, model configuration, and analysis all cross
the generated Wails bridge into the Go application.

## Development

Install dependencies and start the browser-only UI preview:

```sh
npm install
npm run dev
```

The preview is useful for visual work. Native operations require the Wails
development process from the repository root:

```sh
wails dev
```

## Validation

Run the source-contract suite, component/runtime suite, and production build:

```sh
npm run test
npm run build
```

## Structure

- `src/components` contains the workspace, chat, analysis, settings, and shared
  UI components.
- `src/services` contains focused adapters over the Wails bindings.
- `src/stores` contains application and session state.
- `src/utils` contains framework-independent transformation and formatting
  helpers.
- `test` contains fast source-contract regression tests.
- `test-runtime` contains Vitest behavior tests.
- `wailsjs` is generated from the public methods exposed by the Go application.

Do not add a second transport path inside a service. New product capabilities
should be exposed by a typed Go method and consumed through the Wails bridge.
