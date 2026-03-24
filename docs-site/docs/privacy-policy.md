# Privacy Policy

Last Updated: 2026-03-23

This Privacy Policy describes what Inquira processes today, where it is stored, and which parts depend on optional third-party services.

## 1. Scope

This policy applies to:

- the Inquira desktop application
- the public documentation and download site at `docs.inquiraai.com`
- optional third-party services that the user explicitly enables through the product

This policy does not describe future billing, subscription, or hosted account systems that are not currently shipped.

## 2. What Inquira Does Today

Inquira is a desktop-first data analysis product.

Today it can:

- help users analyze data locally with Python and DuckDB
- call third-party AI providers when the user enables those features
- use Supabase-backed authentication for desktop flows that require sign-in
- publish public docs and downloads through GitHub Pages and GitHub Releases

## 3. Information Processed Today

Depending on the feature in use, Inquira may process:

- Supabase-backed account identifiers such as user ID, email, or display information returned by the auth provider
- local product state such as workspaces, conversations, schemas, and runtime artifacts
- selected LLM provider settings and API key presence state
- prompts, schema context, and execution context sent to the user's chosen AI provider
- standard website request information handled by GitHub Pages or GitHub Releases when the public docs/download site is visited

Inquira does not currently operate its own hosted billing or subscription portal from the public docs site.

## 4. Data Stored On The User's Device

The desktop app stores operational data locally on the user's device. This may include:

- local app configuration and runtime files
- workspace metadata
- conversation and artifact state
- generated schemas and scratch outputs
- cached UI/runtime state
- persisted Supabase session storage used by the desktop app

Typical local data locations may include:

- `~/.inquira/`
- the app's Tauri application-data directory
- per-workspace or per-user runtime folders created by the product

## 5. Secrets And Credentials

Inquira treats different secrets differently:

- LLM API keys are stored through the host OS keychain when supported by the app's secure-storage path
- Supabase session persistence is currently stored through the app's local desktop storage layer, not the OS keychain

If these storage details change in a future release, this policy should be updated accordingly.

## 6. Authentication Data

When sign-in is enabled and used:

- the current desktop flow uses Supabase-backed authentication
- the current sign-in UI is centered around Google login
- the backend verifies bearer tokens against Supabase before granting access to authenticated API routes

The public docs/download site does not currently act as a hosted user account portal.

## 7. AI Provider Data (What the LLM Actually Sees)

Inquira CE's architecture guarantees that the bulk of your local dataset (CSV, Parquet, Excel, DuckDB files) is **never** uploaded to any cloud network.

When you ask a question, Inquira transmits **strictly the following** to your selected LLM provider (OpenAI, Anthropic, etc.):
1. **Your prompt/question**
2. **Schema metadata** (the names of your tables and the names/data types of your columns)
3. **Execution context** (system prompts, code execution errors, or Python print outputs required to fix failing code)
4. **Data Samples (Important Risk)**: Currently, the agent utilizes a tool called `sample_dataset` which retrieves a small handful of actual data rows (e.g., the top 5 rows) and sends them to the LLM to help it understand formatting or date structures. **This means tiny snippets of your real data *are* transmitted to the AI provider.**

> [!WARNING]  
> **Future Update:** In an upcoming release, the **`sample_dataset` tool will be disabled by default** to guarantee strict zero-row data transmission. Users who want the LLM to 'see' row data for better accuracy will be required to explicitly opt-in.

## 8. Public Docs And Download Site

The public website is currently documentation-and-download focused.

Today that means:

- docs are served through GitHub Pages
- the download experience may call the GitHub Releases API from the browser to resolve the latest installer assets
- GitHub and other infrastructure providers may receive standard web request information such as IP address, browser metadata, and request logs

Inquira does not currently claim that the public docs site is analytics-free at the hosting-provider level, because basic hosting logs may still exist outside the app itself.

## 9. Optional Observability

The codebase includes optional Phoenix tracing configuration.

That tracing is disabled by default in the checked-in configuration. If a user or operator explicitly enables it, runtime trace data may be sent to the configured tracing endpoint.

## 10. How Information Is Used

Information may be used to:

- authenticate desktop users where sign-in is required
- restore local desktop sessions
- operate local workspaces and runtime features
- call user-selected AI providers
- deliver public docs and downloads
- debug or support the product where the user has explicitly enabled or requested that behavior

## 11. Data Sharing

Inquira does not claim to sell user data.

Information may be disclosed to third parties only as required to operate the features the user chooses to use, such as:

- Supabase for authentication
- Google or another selected AI provider
- GitHub Pages and GitHub Releases for the public docs/download site
- an explicitly configured observability endpoint if tracing is enabled

## 12. Retention

Local desktop data remains on the user's device until the user deletes it or removes the product's local storage.

Retention behavior for third-party services depends on those providers and the user's configuration with them.

## 13. Security

Reasonable care can be taken in the product design, but no system is perfectly secure.

Users remain responsible for:

- protecting their own devices
- protecting local files and backups
- choosing whether to enable third-party providers
- reviewing generated code before execution

## 14. Changes To This Policy

This policy may be updated as the product changes. The `Last Updated` date reflects the latest revision.

## 15. Contact

For privacy or product questions, use the project repository support channels or the official contact method published by the project.
