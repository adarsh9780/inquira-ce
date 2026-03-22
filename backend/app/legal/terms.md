# Inquira Terms & Conditions

Last Updated: 2026-03-23

These Terms & Conditions explain what Inquira does today, what it does not promise, and what risks you accept when using it.

By using Inquira, you accept these Terms. If you do not accept them, do not use the product.

## 1. What Inquira Is
- Inquira is a desktop-first data analysis product that helps generate and run Python/DuckDB workflows.
- It can use a third-party AI provider selected by you to generate or explain analysis.
- The public website currently provides documentation and downloads, not a full hosted account portal.

## 2. What We Do Not Promise
- We do not claim perfect accuracy.
- We do not claim generated code is always safe.
- We do not claim third-party providers will handle your data in any specific way beyond those providers' own policies.
- We do not claim that every planned auth, billing, or account-management feature already exists in the current product.

## 3. Main Risks (Read Carefully)
- Generated code runs with your local user permissions and can read, modify, move, or delete local files.
- Commands and code may access network resources if your environment allows it.
- Wrong code or wrong model output can produce wrong analysis, wrong business conclusions, or data loss.
- You are responsible for reviewing code before execution and maintaining your own backups.

## 4. Data Storage and Ownership
- Your files, questions, generated schema, runtime outputs, and related project artifacts are primarily stored on your device.
- Inquira does not upload your full selected data files by default.
- You remain the owner/responsible party for your data and outputs.

Typical local paths include:
- `~/.inquira/`
- the app's local application-data directory
- per-user or per-workspace runtime folders created by the product

You can remove local data by deleting these folders/files.

## 5. Authentication and Account State
- Some product flows may require sign-in.
- Current authenticated desktop flows use Supabase-backed bearer auth.
- The currently enabled desktop sign-in experience is centered around Google login.
- Other providers may be added later, but they should not be treated as a current guarantee unless they are enabled in the shipped UI.

## 6. What Is Sent to AI Providers
You choose the AI provider and are responsible for what you send.

For AI features, the model may receive:
- your prompt/question
- schema context needed to generate code
- execution context or result summaries needed for follow-up explanation
- system/developer instruction text needed to run the workflow

The model is not intended to receive your full raw dataset by default, but you are responsible for reviewing prompts and outputs to ensure sensitive content is not sent unintentionally.

Each provider processes data under its own terms and privacy policy. You are responsible for reviewing and accepting those provider terms.

## 7. Secrets and Session Storage
- AI provider API keys may be stored through the host OS keychain where supported by the app's secure-storage path.
- Current desktop auth session persistence is handled through local app storage rather than the OS keychain.

## 8. Your Responsibilities
- Use the product lawfully and only with data you are authorized to use.
- Review generated code before running it.
- Decide whether to use AI features for sensitive workloads.
- Maintain backups and operational safeguards on your own machine.

## 9. License Scope
Use of Inquira remains subject to the repository license and any separate commercial licensing terms that may apply.

These Terms do not grant rights beyond the applicable software license.

## 10. Governing Law and Jurisdiction
No governing law or jurisdiction is designated in this version of the Terms.

## 11. Warranty Disclaimer
INQUIRA IS PROVIDED "AS IS" WITHOUT WARRANTIES OF ANY KIND, EXPRESS OR IMPLIED. YOU USE IT AT YOUR OWN RISK.

## 12. Limitation of Liability
TO THE MAXIMUM EXTENT PERMITTED BY LAW, THE AUTHORS/OPERATORS ARE NOT LIABLE FOR INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR EXEMPLARY DAMAGES, OR FOR LOSS OF DATA, PROFITS, OR BUSINESS OPPORTUNITY ARISING FROM USE OF INQUIRA.

## 13. Changes to Terms
We may update these Terms. The "Last Updated" date will reflect the latest version.

## 14. Contact
For issues or questions, please open an issue in the repository or consult the project README.
