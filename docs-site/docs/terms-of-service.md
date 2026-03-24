# Terms of Service

Last Updated: 2026-03-23

These Terms describe what Inquira is, what it does not promise, and the risks you accept when using it.

By using Inquira, you agree to these Terms. If you do not agree, do not use the product.

## 1. What Inquira Is

Inquira is a desktop-first data analysis product that helps users generate and run Python and DuckDB workflows, with optional AI-assisted features.

The public website currently provides documentation and downloads. It is not, by itself, a full hosted account portal.

## 2. Product Nature

Inquira is a tool for developers, analysts, and technical users.

It may:

- generate code
- run code locally
- produce incomplete or incorrect output
- rely on third-party AI providers chosen by the user

## 3. Radical Transparency & Main Risks

We do not over-promise the capabilities of AI. Large Language Models hallucinate, write bugs, and make confident mistakes. By using Inquira CE, you explicitly understand and accept the following risks:

- **The Agent makes mistakes:** The generated SQL or Python code may be completely incorrect, mathematically flawed, or logically unsound. You must verify critical calculations yourself.
- **Local File Risk:** The agent generates code that runs locally on your machine. While it runs in an isolated Jupyter kernel, that kernel currently has access to your local filesystem. The agent could theoretically generate code that reads, modifies, or deletes your local files.
- **Network Risk:** Python code executed by the agent can access the open internet, downloading or uploading data if your environment permits it.
- **AI Hallucinations:** Textual outputs, statistical summaries, or chart insights may contain factual, technical, or analytical fabrications.

You are **100% responsible** for reviewing the generated code before trusting the output, answering for its local execution side-effects, and maintaining local backups of your data.

## 4. Local Data And Execution

Inquira is designed to run primarily on the user's machine.

The product may store local application data such as:

- configuration
- workspace state
- generated schemas
- runtime artifacts
- cached session or UI state

Execution happens locally unless the user explicitly enables a third-party service that processes part of the workflow.

## 5. Authentication

Some product flows may require sign-in.

Today, authenticated desktop flows use Supabase-backed bearer auth, and the shipped sign-in UI is centered around Google login. Other providers may be added later, but they should not be treated as current guarantees unless they are enabled in the product.

## 6. AI Providers And Third-Party Services

If you enable AI-assisted features, you are responsible for:

- choosing which provider to use
- reviewing that provider's terms and privacy policies
- deciding whether your data is appropriate to send to that provider

Third-party services operate under their own terms.

## 7. Acceptable Use

You agree not to use Inquira:

- for unlawful activity
- to violate privacy, confidentiality, or intellectual property rights
- to intentionally generate malicious code or abuse third-party services
- to interfere with service or infrastructure supporting the product

## 8. License Scope

Use of Inquira remains subject to the repository license and any separate commercial licensing terms that may apply.

These Terms do not grant rights beyond the applicable software license.

## 9. No Warranty

INQUIRA IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND, EXPRESS OR IMPLIED.

## 10. Limitation Of Liability

TO THE MAXIMUM EXTENT PERMITTED BY LAW, THE AUTHORS, OPERATORS, AND CONTRIBUTORS OF INQUIRA ARE NOT LIABLE FOR INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, EXEMPLARY, OR SIMILAR DAMAGES ARISING FROM USE OF THE PRODUCT.

This includes, without limitation:

- data loss
- business interruption
- incorrect analysis
- incorrect model output
- code execution side effects

## 11. Changes To The Product

Features may be added, changed, limited, or removed at any time, including authentication behavior, website flows, download behavior, and AI integrations.

## 12. Changes To These Terms

These Terms may be updated from time to time. Continued use of the product after updates means you accept the revised Terms.

## 13. Governing Law

No specific governing law or jurisdiction is designated in this version of the Terms.

## 14. Contact

For product or legal questions, use the project repository support channels or the official contact method published by the project.
