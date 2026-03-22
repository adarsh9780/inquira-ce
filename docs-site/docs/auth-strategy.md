# Authentication Strategy

This document recommends how Inquira should handle authentication as it evolves from a local-first desktop tool into a product with hosted docs, support, downloads, and user accounts.

## Short recommendation

Use a third-party identity provider for authentication.

Keep Inquira's own backend responsible for:

- user profile mapping
- plan and entitlement state
- workspace and conversation ownership
- billing and support metadata
- product-specific authorization rules

Do not keep building password and account recovery flows yourself inside the desktop app.

## Simple explanation

Right now, the app handles authentication like a small website:

- users sign in with a username and password
- the backend creates its own session cookie
- the desktop UI stays blocked until auth succeeds

That is workable for an early prototype, but it becomes a bad fit once the product needs:

- automatic sign-in on app launch
- social login
- password reset and account recovery
- hosted documentation and support
- optional web account management
- future billing or paid plans

In simple terms: the current setup makes Inquira responsible for all the hard parts of identity, but identity is not the core product.

## What the current code does

The current auth stack is local and app-owned:

- v1 auth routes issue and clear a `session_token` cookie
- sessions are stored in the local auth database
- users are modeled as `username + password_hash + salt`
- the desktop frontend blocks usage behind the auth modal

Relevant files:

- `backend/app/v1/api/auth.py`
- `backend/app/v1/services/auth_service.py`
- `backend/app/v1/models/user.py`
- `frontend/src/App.vue`
- `frontend/src/components/modals/AuthModal.vue`

## Problems with the current setup

### 1. It is web-style auth inside a desktop app

The app behaves like a website that refuses to load until sign-in is complete.

For a desktop tool, users expect:

- sign in once
- stay signed in
- reopen the app without re-entering credentials

The current design can simulate that for a short time, but it is not built around durable desktop sessions.

### 2. Session lifetime is too short for a modern desktop experience

Current sessions expire after 24 hours.

That means the product is not really using a "modern desktop app" sign-in model. It is using a short-lived local cookie model.

### 3. The identity model is too limited

The primary identifier is `username`, not email or external identity.

That creates product friction for:

- password recovery
- email verification
- support workflows
- billing
- download gating
- team or enterprise sign-in later

### 4. Password ownership becomes your long-term burden

If Inquira owns password auth, it also owns:

- reset emails
- compromised password handling
- lockouts and abuse protection
- account recovery edge cases
- social account linking
- identity merge issues
- security reviews around credential storage

This is a lot of product and security work that does not make the analysis tool better.

### 5. The UI already promises account flows that are not clearly backed end to end

The frontend exposes "change password" and "delete account" actions.

However, the v1 auth router currently exposes only:

- register
- login
- me
- logout

That mismatch is a warning sign. It means auth/account responsibilities are already spreading across the product faster than the backend contract.

### 6. A "third-party auth switch" already exists, but it is not real yet

The codebase includes a `supabase` auth provider option, but the repository implementation is still a placeholder that raises runtime errors.

This means migration has been anticipated, but not yet designed properly.

## Product decisions

### Desktop sign-in

Recommended flow:

1. User clicks `Sign in`.
2. Inquira opens the system browser.
3. The user completes OAuth or passwordless sign-in on a hosted page.
4. The auth provider redirects back to the desktop app using a native-app-safe flow.
5. Inquira stores the durable refresh/session secret in the OS keychain.
6. On future launches, Inquira silently restores the session.

This is the right mental model for a desktop product.

## Web versus desktop account management

### Change password

Recommendation: handle on the web, not in the desktop UI.

Reason:

- password change is account management, not core analysis workflow
- hosted providers already have reset/change flows
- the browser is a safer and more familiar place for sensitive identity operations

### Delete account

Recommendation: mostly handle on the web, with an optional `Manage account` deep link from desktop.

Reason:

- deletion usually becomes tied to billing, invoices, export, support, and retention policy
- it is easier to communicate consequences in a full web account portal

### Login options

Recommended initial options:

- Google
- Microsoft
- GitHub

Add Apple if macOS consumer distribution becomes important.

Avoid making email/password the primary path unless there is a clear business reason.

Preferred fallback if social-only feels too restrictive:

- magic link
- email OTP

These are better than plain password auth for a desktop-first product.

## Download gating recommendation

Do not require signup before download in the first rollout.

Recommended funnel:

- docs: public
- product site: public
- downloads: public
- account required only when the user wants cloud-backed features, billing, sync, support tiers, or premium services

Reason:

- forcing signup before download increases friction before the user has seen value
- desktop tools usually convert better when install comes before account creation

If download abuse later becomes a real problem, add soft gating:

- email capture for release updates
- optional account for beta builds
- gated premium builds or enterprise installers

Do not lead with a hard gate unless there is a proven business need.

## Provider shortlist

### Best pragmatic fit: Supabase Auth

Pros:

- good developer ergonomics
- built-in social auth and email-based auth options
- hosted flows are straightforward
- cheaper and simpler than some enterprise-oriented providers
- reasonable fit for an early-stage product

Cons:

- you still need to design the desktop redirect and token storage carefully
- account-management UX is not as polished as some auth-first products

Use Supabase if:

- you want fast implementation
- you are cost-sensitive
- you do not need enterprise identity features yet

### Best polished auth product: Clerk

Pros:

- strong hosted auth and account UX
- good social login support
- nice developer and end-user experience

Cons:

- higher product coupling to Clerk patterns
- can get expensive as usage grows

Use Clerk if:

- polished auth UX matters more than infra simplicity
- you want faster hosted account management with less custom work

### Best for future B2B and SSO: WorkOS

Pros:

- excellent long-term fit for orgs, SSO, enterprise identity
- good if team or organization accounts are likely

Cons:

- more than you need right now if this is still mostly single-user and self-serve

Use WorkOS if:

- enterprise or workspace-level auth is on the near-term roadmap

### Auth0

Pros:

- mature and flexible
- strong documentation and OAuth support

Cons:

- usually heavier to configure
- often more complexity than necessary for a product at this stage

Use Auth0 if:

- you specifically need its ecosystem or policies

## Recommended decision

For Inquira today:

- choose `Supabase Auth` if the goal is fastest practical migration
- choose `Clerk` if polished hosted auth and account UX is more important than cost and lock-in

If forced to pick one now, choose `Supabase Auth`.

Reason:

- the repo already anticipates it
- it covers the current product needs
- it is enough for desktop + hosted docs/support + social login
- it keeps the migration small enough to ship

## Architecture recommendation

Use the auth provider as the source of truth for identity.

Do not preserve the current local auth model as the main identity system with a thin adapter on top.

Recommended model:

1. Auth provider owns sign-in, passwordless or social login, password reset, and session refresh.
2. Desktop app holds provider session material in OS keychain.
3. Backend receives a verified user identity from the provider token or session.
4. Backend maps external identity to an internal principal record.
5. Inquira stores product data against the internal principal record.

In short:

- provider owns identity
- Inquira owns product state

## Desktop implementation notes

For desktop apps, use browser-based OAuth with PKCE and a native-app-safe redirect flow.

Do not embed provider login in a generic webview.

Store durable session material in the OS keychain, the same way the product already stores API keys in the host keychain.

## Migration plan

### Phase 1: Decision and schema preparation

- choose provider
- add an internal `external_auth_id` or equivalent identity mapping field
- stop expanding the current password-based auth surface
- define which account actions move to web

### Phase 2: Introduce provider-backed sign-in

- add hosted browser sign-in
- add social providers
- store refresh or session material in OS keychain
- restore session automatically on app launch

### Phase 3: Backend trust model

- verify provider identity on backend requests
- create or load the matching internal principal
- keep workspaces, preferences, conversations, and plans attached to the internal principal

### Phase 4: Decommission local auth

- remove username and password registration from desktop
- replace change-password UI with `Manage account`
- replace local delete-account flow with web-managed deletion or a backend-controlled account portal action

### Phase 5: Product site rollout

- launch hosted docs and support site
- keep downloads public at first
- require auth only where it adds value

## What should live where

### Desktop app

- sign in
- sign out
- restore session automatically
- show current plan and account summary
- link to `Manage account`

### Web account area

- password reset or password change
- email verification
- social account linking
- billing
- subscription management
- account deletion
- support and contact

## Final call

Inquira should move authentication to a third-party auth service.

The desktop app should sign users in once via the browser, restore sessions automatically from the OS keychain, and send users to the web for sensitive account management.

For the next implementation pass, the best default path is:

- provider: Supabase Auth
- desktop login methods: Google, Microsoft, GitHub, plus optional magic link
- password change: web only
- account deletion: web only
- downloads: public at first

## References

- [RFC 8252: OAuth 2.0 for Native Apps](https://www.rfc-editor.org/rfc/rfc8252)
- [Auth0: Authentication and Authorization Flows](https://auth0.com/docs/get-started/authentication-and-authorization-flow)
- [Supabase Auth: Password-based Auth](https://supabase.com/docs/guides/auth/passwords)
- [Supabase Auth: Redirect URLs](https://supabase.com/docs/guides/auth/redirect-urls)
- [Supabase Auth: Native Mobile Deep Linking](https://supabase.com/docs/guides/auth/native-mobile-deep-linking)
- [Clerk: Google social connection](https://clerk.com/docs/reference/social-login-with-google)
- [WorkOS AuthKit](https://workos.com/docs/authkit)
