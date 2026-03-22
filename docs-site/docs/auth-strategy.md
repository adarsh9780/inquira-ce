# Authentication Strategy

This page describes the current authentication model in the codebase and the product direction that follows from it.

## Simple explanation

Inquira is no longer on the old local username/password flow.

Today, authenticated desktop flows use Supabase-backed bearer auth:

- the desktop UI opens the browser for sign-in
- the frontend stores the resulting Supabase session locally on the device
- the backend verifies the bearer token against Supabase
- the app loads the user profile and plan after token verification succeeds

The public docs and download site do not currently provide a hosted account dashboard.

## What is true today

### Current implementation

- The backend expects a bearer token on authenticated API routes.
- User identity is resolved through Supabase `/auth/v1/user`.
- The desktop auth UI currently offers Google sign-in.
- Microsoft and GitHub are shown as planned providers in the UI, but are not enabled in the current sign-in screen.
- Logout clears the local Supabase session on the client side.
- The account settings screen can open a browser URL for account management if that URL is configured.

Relevant files:

- `backend/app/v1/api/auth.py`
- `backend/app/v1/api/deps.py`
- `backend/app/v1/services/auth_service.py`
- `frontend/src/stores/authStore.js`
- `frontend/src/services/supabaseAuthService.js`
- `frontend/src/components/modals/AuthModal.vue`

## What is not true today

The following should be treated as future direction, not current product behavior:

- a local username/password sign-in flow
- a hosted account portal on the docs site
- built-in billing or subscription management
- desktop support for multiple social providers beyond the currently enabled Google flow
- a no-login Free desktop experience

That last point matters: the product direction may be "Free without forced login," but the current desktop app still gates workspace access behind sign-in.

## Current risks and tradeoffs

### 1. Free users still hit an auth wall

The code still requires sign-in before the main workspace loads.

That creates friction for:

- first-run evaluation
- local-only usage
- users who only want the desktop app and public docs

### 2. The product surface is split

The docs and download site are public, but account-related behavior still lives in the desktop auth flow and configuration.

That means there is not yet one clear web account surface for:

- password/account recovery
- self-serve account management
- subscription handling
- download entitlement management

### 3. Session storage is local, but not keychain-backed

API keys are stored in the OS keychain.

Supabase auth session persistence is currently handled through the app's local Tauri storage, not the OS keychain. That is an important implementation detail when describing storage and security behavior.

## Recommended product direction

### Near term

- keep the docs and download site public
- remove forced login from the Free desktop path if the product can operate without account-bound features
- keep authenticated flows only where they are needed

### When account management becomes real

If the product grows into paid plans, hosted account settings, or enterprise identity features, then:

- keep Supabase or another provider as the identity layer
- let the website or a dedicated account surface handle account-management tasks
- keep the desktop app focused on workspace activity rather than identity administration

## Practical recommendation

The current Supabase-based direction is reasonable for now.

What should change is not the identity provider first. What should change first is the product boundary:

- public website and downloads stay public
- desktop Free usage should stop requiring sign-in if the feature set allows it
- account management should be described as optional or future-facing until a real hosted account surface exists
