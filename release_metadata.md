Inquira Release

### Docs and website

- Added a Docusaurus-powered docs site with a product landing page, pricing page, and download page.
- Moved the maintained project documentation into the website project so the published docs and source markdown stay in sync.
- Switched GitHub Pages publishing from the old MkDocs setup to the Docusaurus build pipeline.
- Pointed the docs site at `https://docs.inquiraai.com` for the live custom-domain deployment.

### Branding and downloads

- Replaced the generic site branding with the existing animated Inquira SVG logo.
- Added direct macOS and Windows download buttons that resolve the latest installer assets from GitHub Releases without forcing users to open the release page first.
- Kept the download flow resilient by falling back to the latest GitHub release page if installer asset lookup fails.

### Product packaging direction

- Clarified the website structure for Free, Pro, and Enterprise editions so the public site can support future packaging and account-management flows.
- Kept the website focused on public docs, downloads, and product discovery while leaving room for future account surfaces on separate domains or routes.
