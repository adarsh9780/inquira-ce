# Inquira Terms & Conditions

Last Updated: 2024-09-21

These Terms & Conditions ("Terms") govern your use of the Inquira Community Edition ("Inquira", "the Software"). By using the Software, you agree to these Terms. If you do not agree, do not use the Software.

## 1. Overview & Scope
- Inquira is a local, desktop-first data analysis tool that generates and executes Python/DuckDB code based on your natural-language prompts.
- Community Edition runs on your machine. Inquira does not host or store your datasets on remote servers.
- Some features interact with third-party Large Language Model (LLM) providers (e.g., Google Gemini) using your API key. This is optional but required for AI-assisted code generation and schema enrichment.

## 2. Data Locations & Storage
The Software stores data only on your local device unless you explicitly configure third-party services.

- Application configuration and runtime data folder:
  - `~/.inquira/` (user home directory)

- Local database for application settings and catalog (SQLite):
  - `~/.inquira/inquira.db`

- Per-user data (created by runtime operations):
  - DuckDB database file: `~/.inquira/{user_id}/{user_id}_data.duckdb`
  - Schemas (JSON) and related assets: `~/.inquira/{user_id}/schemas/`
  - Preview caches (currently pickle format): `~/.inquira/{user_id}/` with filenames like `{user_id}_preview_{sample_type}.pkl`
  - Lightweight metadata files (JSON), if generated: `~/.inquira/{user_id}/*.json`

You may remove Inquira’s local data at any time by deleting the `~/.inquira/` folder. This will erase all local settings, caches, and user records for the application.

## 3. What We Collect (Locally)
Inquira persists the following information on your device:

- User account data (local-only): randomly generated `user_id`, `username`, password hash + salt, timestamps.
- Session cookie (local browser cookie): an HTTP-only session token used for authenticating to the local server.
- Settings per user:
  - LLM API key (e.g., Google Gemini) if provided.
  - Data file path you select.
  - Optional domain “context”/notes about your dataset.
- Dataset catalog entries (per file) with metadata: file path, computed fingerprint, inferred table name, file size, modified time, row count, file type, and schema path.
- Preview caches (small samples) for quicker UI previews.
- Generated schema JSON files and related details (e.g., column names, inferred types, descriptions).

No telemetry, analytics, or remote logging is performed by Inquira CE.

## 4. What Is Sent to LLM Providers
If you enable AI features by entering an LLM API key, Inquira sends only the information necessary to produce a useful response:

- Your prompt/question text.
- Schema-related metadata (e.g., table/column names, inferred types, short column descriptions, limited sample values when generating descriptions), and optional dataset “context” you provide.
- System and developer prompts required to instruct the model (templates included in the app).

What is NOT sent:
- Your full dataset files.
- Complete, large-scale row-level data. Inquira may derive tiny samples for descriptive purposes; these are limited and intended to avoid sending sensitive data. You control which files you point Inquira to, and you can avoid AI-driven schema enrichment if required.

Important: LLM providers process the input you send under their own terms and privacy policies. Review your provider’s documentation and configure data controls accordingly.

## 5. Code Execution & Safety
- Generated code executes locally, in-process, without a sandbox. This means code may access local files, environment variables, and network resources with your user’s permissions.
- You are responsible for reviewing generated code before executing.
- To keep data private, do not run Inquira in untrusted environments. Avoid opening unknown datasets or executing unreviewed code if you are unsure of its behavior.

## 6. File Access & Ingestion
- You select local files; the app does not upload your files to a remote server.
- Inquira converts selected files to a per-user DuckDB database for efficient querying. Tables are named based on file names.
- When a source file changes, Inquira updates the corresponding DuckDB table.
- For performance, small preview samples are cached locally. Currently this cache uses pickle format for speed; future versions may change to safer serialization formats.

## 7. Cookies, Sessions, and Authentication
- Local sessions are authenticated via an HTTP-only cookie set by the local server.
- Sessions expire after approximately 24 hours.
- User and session records are stored in the local SQLite database at `~/.inquira/inquira.db`.

## 8. Secrets (API Keys)
- If set in the app, your LLM API key is stored in the local SQLite database and used only to call the LLM provider you’ve configured.
- Alternatively, you may set the API key via environment variables and avoid persisting it locally.
- Delete the key in Settings or remove `~/.inquira/` to purge local storage.

## 9. Your Responsibilities
- Ensure you have the rights to use the datasets you analyze.
- Review and understand generated code before running it.
- Configure and manage any third-party LLM accounts and their data controls.
- Protect your device and local storage. Inquira CE does not provide encryption of local data by default.

## 10. Deleting Data
- Delete your user account from within the application to remove your local user and session data from the SQLite database.
- To completely remove all local Inquira data, delete the entire `~/.inquira/` folder.

## 11. Third-Party Services
- If you use LLM providers (e.g., Google Gemini), your prompts and associated metadata are subject to those providers’ terms and privacy policies. You are responsible for reviewing and accepting those terms with the provider.

## 12. Warranty Disclaimer
THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED. YOU USE THE SOFTWARE AT YOUR OWN RISK.

## 13. Limitation of Liability
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY ARISING FROM OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## 14. Changes to These Terms
We may update these Terms by publishing a new version with an updated “Last Updated” date. Continued use of the Software after changes indicates acceptance.

## 15. Contact
For issues or questions, please open an issue in the repository or consult the project README.

