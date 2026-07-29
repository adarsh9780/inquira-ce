# Release management

Inquira Community Edition uses GitHub Releases as the public source and release
record. Cloudflare R2 provides stable, branded customer download URLs and the
atomic `latest.json` update pointer. The same checksum-verified installers remain
available as public GitHub Release assets.

## Cost boundary

The release workflow runs only when a stable GitHub Release is published. It
does not run on pull requests, does not install Playwright, and does not repeat
the full frontend and Python suites. Before building, it requires a successful
`ci.yml` run for the exact release commit. Each native build runs the Go tests
on its own operating system before packaging.

Each release consumes one native macOS ARM64 build and one native Windows x64
build. Rerunning a failed workflow consumes another pair of native build jobs,
so inspect the failed step before rerunning the complete workflow.

Ordinary pull-request and `main` CI uses Ubuntu runners only. Native runner
minutes are reserved for intentional releases. The release frontend is built
once on Ubuntu and reused by both native packaging jobs.

## Release flow

1. Merge the release changes into `main`.
2. Wait for the `CI` workflow on that `main` commit to pass.
3. In GitHub, open **Releases** and choose **Draft a new release**.
4. Create a stable `vMajor.Minor.Patch` tag, such as `v0.6.0`, targeting the
   green `main` commit.
5. Add the public release title and notes, then publish the release.
6. Watch the `Release desktop` workflow.

The workflow:

1. validates the tag and confirms that its commit belongs to `main`;
2. confirms that the exact commit already has successful CI;
3. builds the macOS application and checksum-verifies its bundled UV metadata;
4. builds the Windows application and NSIS installer with the same checks;
5. creates a DMG and stable, versioned installer filenames;
6. generates `manifest.json`, `latest.json`, and `SHA256SUMS.txt`;
7. attaches both installers, the version manifest, and checksums to the public
   GitHub Release;
8. uploads immutable versioned objects to Cloudflare R2;
9. uploads `latest.json` only after every other object succeeds;
10. verifies the public manifest and installer URLs.

If a build or versioned upload fails, the existing public `latest.json` remains
unchanged. Fix the problem or rerun the failed jobs. Re-publishing the same tag
is not required.

## GitHub configuration

The `inquira-ce` repository requires this Actions secret:

- `CLOUDFLARE_API_TOKEN`: a narrowly scoped token allowed to read and write
  objects in the release bucket.

It also requires these Actions variables:

- `CLOUDFLARE_ACCOUNT_ID`
- `CLOUDFLARE_R2_BUCKET` (currently `inquira-releases`)
- `PUBLIC_DOWNLOADS_BASE_URL` (currently
  `https://downloads.inquiraai.com`)

`PUBLIC_RELEASE_NOTES_URL` is optional. It defaults to the public desktop
distribution documentation so the customer-facing release guidance remains
stable independently of GitHub repository visibility.

## Versioning

Stable releases currently use `vMajor.Minor.Patch`. The release workflow rejects
prerelease version strings because Windows installer metadata requires a
numeric product version.

The release version is injected into:

- Wails application metadata;
- the macOS bundle metadata;
- Windows executable and installer metadata;
- the frontend build constant;
- installer filenames and download manifests.

The tracked development version remains available for local builds.

## Signing

macOS uses Wails' ad-hoc application signature but is not Apple-notarized.
Windows is not Authenticode-signed. The workflow reports the Windows signature
status without pretending that a self-signed certificate provides public
trust.

Free trusted Windows signing is available when distributing an MSIX through the
Microsoft Store, where Microsoft signs the accepted package. Direct public
distribution of the current NSIS installer requires a paid trusted-signing
option, so it is deliberately deferred.

## Manual recovery

The public-site repository retains
`scripts/uploadPublicDownloadsToR2.mjs` as a manual R2 recovery path. It accepts
one DMG and one EXE under an uploads directory and also publishes
`latest.json` last. Normal releases should use the GitHub workflow.
