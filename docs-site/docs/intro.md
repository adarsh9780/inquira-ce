---
sidebar_position: 1
---

# Inquira Website

This Docusaurus project is the public-facing website for Inquira.

## Why this site exists

The desktop app and the website solve different problems:

- The desktop app is where users actually work.
- The website is where users learn, compare plans, and download releases.
- Future account management can live on the same domain without forcing Free users to log in just to use the app.

That split keeps the product simpler.

## What belongs here

- Product overview
- Pricing and plan comparison
- Download links for the latest desktop build
- Documentation and setup guides
- Future account and license management entry points

## What does not belong here

- The full desktop UI
- Heavy authenticated workflows
- Internal app-only screens that users never need on the public web

## Local development

Run the site locally:

```bash
cd docs-site
npm install
npm run start
```

The default development URL is `http://localhost:3000`.

## Before deploying

Replace the placeholder `url` value in `docs-site/docusaurus.config.ts` with your real domain.
