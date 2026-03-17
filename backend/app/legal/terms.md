# Inquira Terms & Conditions

Last Updated: 2026-03-18

These Terms & Conditions ("Terms") explain what Inquira does, what it does not do, and what risks you accept when using it.

By using Inquira, you accept these Terms. If you do not accept them, do not use the product.

## 1. What Inquira Is
- Inquira is a local data analysis product that helps generate and run Python/DuckDB workflows.
- It can use an LLM provider selected by you to generate or explain analysis.
- Commercial usage is allowed.

## 2. What We Do Not Promise
- We do not claim perfect accuracy.
- We do not claim generated code is always safe.
- We do not claim your chosen LLM provider will handle your data in any specific way beyond that provider's own policies.

## 3. Main Risks (Read Carefully)
- Generated code runs with your local user permissions and can read, modify, move, or delete local files.
- Commands and code may access network resources if your environment allows it.
- Wrong code or wrong model output can produce wrong analysis, wrong business conclusions, or data loss.
- You are responsible for reviewing code before execution and maintaining your own backups.

## 4. Data Storage and Ownership
- Your files, questions, screenshots, generated schema, runtime outputs, and related project artifacts are stored on your device.
- Inquira does not upload your full selected data files by default.
- You remain the owner/responsible party for your data and outputs.

Typical local paths include:
- `~/.inquira/`
- `~/.inquira/inquira.db`
- Per-user runtime folders such as `~/.inquira/{user_id}/`

You can remove local data by deleting these folders/files.

## 5. What We Store About the User
We keep only information needed to operate the product lawfully and reliably, such as:
- username/account identifier
- payment or subscription status (where applicable)
- authentication/security/session details
- minimal operational records needed for abuse prevention, legal compliance, and account support

## 6. What Is Sent to LLM Providers
You choose the LLM provider and are responsible for what you send.

For AI features, the model may receive:
- your prompt/question
- schema context needed to generate code (table/column names, types, descriptions)
- data produced during execution that is required for explanation or follow-up analysis (for example result rows/summary output)
- system/developer instruction text needed to run the agent workflow

The model is not intended to receive your full raw dataset by default, but you are responsible for reviewing prompts and outputs to ensure sensitive content is not sent unintentionally.

Each provider processes data under its own terms and privacy policy. You are responsible for reviewing and accepting those provider terms.

## 7. Your Responsibilities
- Use the product lawfully and only with data you are authorized to use.
- Review generated code before running it.
- Decide whether to use LLM features for sensitive workloads.
- Maintain backups and operational safeguards on your own machine.

## 8. Commercial Use
Commercial use is permitted. You remain responsible for legal compliance in your jurisdiction and industry.

## 9. Governing Law and Jurisdiction
No governing law or jurisdiction is designated in this version of the Terms.

## 10. Warranty Disclaimer
INQUIRA IS PROVIDED "AS IS" WITHOUT WARRANTIES OF ANY KIND, EXPRESS OR IMPLIED. YOU USE IT AT YOUR OWN RISK.

## 11. Limitation of Liability
TO THE MAXIMUM EXTENT PERMITTED BY LAW, THE AUTHORS/OPERATORS ARE NOT LIABLE FOR INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR EXEMPLARY DAMAGES, OR FOR LOSS OF DATA, PROFITS, OR BUSINESS OPPORTUNITY ARISING FROM USE OF INQUIRA.

## 12. Changes to Terms
We may update these Terms. The "Last Updated" date will reflect the latest version.

## 13. Contact
For issues or questions, please open an issue in the repository or consult the project README.
