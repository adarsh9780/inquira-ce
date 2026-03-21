# inquira-ce

Inquira CE is a local-first AI data analysis application.
This package ships the FastAPI backend and bundled frontend static assets so you can run the app after install.

## Install

```bash
pip install inquira-ce
```

## Run

```bash
inquira
```

By default, the server listens on `http://localhost:8000`.

## What the backend is responsible for

- Serving the FastAPI application used by the desktop shell.
- Managing workspace kernels used for schema reads, artifact access, and generated Python execution.
- Exposing the chat/runtime APIs consumed by the frontend.
- Acting as the execution bridge for `agent_v2`, so generated analysis code runs inside the active workspace kernel rather than inside the agent process.
