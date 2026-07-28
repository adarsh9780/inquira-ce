# Runtime management

Inquira uses bundled UV as the runtime installer and resolver, but it does not
bundle a full Python installation. The recommended setup downloads the exact
Python version approved by the build's compatibility manifest. Organizations
can instead supply a Python 3.12 executable or route Python and package
downloads through internal mirrors.

## Compatibility contract

Every application build embeds one platform-specific JSON manifest beside UV.
The manifest records:

- manifest schema and compatible Inquira release range;
- UV version, source URL, verified archive size, archive SHA-256, and embedded
  executable SHA-256;
- operating system and architecture;
- Python implementation, exact managed version, and distribution;
- worker protocol version and locked dependency-file SHA-256;
- required runtime lifecycle capabilities.

The current managed runtime is CPython 3.12.13 from
`python-build-standalone`. External mode accepts an executable Python 3.12
interpreter and disables Python downloads. Both modes install the same locked
worker project and use the same Go-to-Python protocol.

Inquira validates the manifest, UV executable, and extracted worker lockfile
before changing a runtime. A mismatch makes the bundle unavailable instead of
silently installing an unreviewed combination.

## Transactional setup

Runtime state is stored separately from workspaces:

```text
runtime/
  tools/uv
  python/
  worker/
  environments/
    data-worker/           active verified environment
    data-worker.staging/   incomplete or in-progress setup
    data-worker.previous/  previous verified environment
```

Provisioning follows a staged lifecycle:

1. validate the requested mode and transient network configuration;
2. clear only the stale staging environment;
3. create and synchronize the worker in staging;
4. verify the worker import and write its lockfile marker;
5. save the non-secret configuration inside the staged environment;
6. move the active environment to `data-worker.previous`;
7. atomically rename staging to the active path.

The active environment is not modified before step 6. A failed or cancelled
setup removes staging and leaves the existing environment ready. A successful
replacement retains one previous verified environment. Rollback swaps active
and previous, so the action remains reversible.

If the application closes during setup, the staging directory may remain.
Settings reports the interrupted setup; starting setup again removes only that
incomplete staging directory and begins cleanly.

## Security boundaries

Mirror, package-index, proxy, and bypass values are process environment values
for one setup attempt. They are redacted from previews and errors, cleared from
the UI after the attempt, and never written to runtime configuration. Saved
configuration contains only the runtime mode, Python version or executable
path, and certificate preference.

UV archives are accepted only when their SHA-256 matches the trusted checksum
compiled into the build helper. The resulting UV executable is hashed again
and verified when extracted from the application.

## User controls

Workspace → Connections → Data runtime provides:

- **Install recommended runtime** for the approved managed configuration;
- **Company-managed setup** for external Python, mirrors, proxies, and
  certificates;
- **Cancel setup** while provisioning is active;
- **Runtime settings** to replace a ready runtime;
- **Roll back** when a previous verified runtime exists.

Repair/reset actions and a sanitized diagnostic export are planned as the next
runtime-management slice.
