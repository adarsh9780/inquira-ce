# Release v0.5.26 — 2026-03-29

## Better Startup Reliability

The app now waits more cleanly for the backend and kernel to be ready before showing the main UI. The startup and loading experience is more consistent, with fewer confusing or duplicate loading states.

## Improved Schema Editing

Schema editing has been refreshed to feel cleaner and easier to use. Context, descriptions, and aliases are easier to review and edit, and dataset/schema lists now refresh more reliably after uploads.

## More Stable Chat And Desktop Runtime

Chat streaming is more resilient, especially when responses are interrupted or arrive in incomplete chunks. This release also includes several desktop and Windows-focused fixes that improve runtime stability and reduce startup and execution failures.
