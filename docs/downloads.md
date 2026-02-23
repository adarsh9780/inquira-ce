# Downloads

## Latest release links

- [Latest release page](https://github.com/adarsh9780/inquira-ce/releases/latest)
- [All releases](https://github.com/adarsh9780/inquira-ce/releases)
- [PyPI package](https://pypi.org/project/inquira-ce/)

## Direct install commands

```bash
pip install inquira-ce
```

```bash
curl -fsSL https://raw.githubusercontent.com/adarsh9780/inquira-ce/master/scripts/install-inquira.sh | bash
```

```powershell
irm https://raw.githubusercontent.com/adarsh9780/inquira-ce/master/scripts/install-inquira.ps1 | iex
```

## Latest release assets (auto-loaded)

<div id="release-assets">Loading latest assets...</div>

<script>
(async () => {
  const el = document.getElementById('release-assets');
  try {
    const res = await fetch('https://api.github.com/repos/adarsh9780/inquira-ce/releases/latest');
    if (!res.ok) throw new Error(`GitHub API returned ${res.status}`);
    const rel = await res.json();
    const assets = Array.isArray(rel.assets) ? rel.assets : [];

    if (!assets.length) {
      el.innerHTML = `<p>No assets found in latest release.</p>`;
      return;
    }

    const rows = assets.map((a) => {
      const sizeMb = (a.size / (1024 * 1024)).toFixed(2);
      return `<tr><td><a href="${a.browser_download_url}">${a.name}</a></td><td>${sizeMb} MB</td></tr>`;
    }).join('');

    el.innerHTML = `<table><thead><tr><th>Asset</th><th>Size</th></tr></thead><tbody>${rows}</tbody></table>`;
  } catch (err) {
    el.innerHTML = `<p>Unable to load assets automatically. Use <a href="https://github.com/adarsh9780/inquira-ce/releases/latest">latest release</a>.</p>`;
  }
})();
</script>
