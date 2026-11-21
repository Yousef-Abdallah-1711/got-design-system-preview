# Static preview deployment

This repository publishes a static GØT storefront preview to `https://got.rakmyat.online/` on the existing AWS EC2 host. The preview has sample products and browser-only cart behavior; it does not create orders, process payments, save signup data, or connect to WooCommerce.

The current host is the Servio staging instance. Its Caddy route must be added and released through the Servio deployment repository before the hostname can serve this site. The DNS A record already points to that host. Caddy will issue TLS after the explicit host route is installed. The current staging `noindex` response header is retained.

## Automatic deployment from `main`

`.github/workflows/build-and-deploy.yml` runs on pull requests and pushes to `main`:

1. The build job runs `tools/prepare_pages.py`, checks the prepared pages and local asset references with `tools/verify_pages.py`, and runs the release-sync safety checks.
2. For a successful push to `main`, the publish job builds that exact commit again and publishes an immutable GitHub prerelease containing the static archive and its SHA-256 manifest.
3. The EC2 host checks the public repository's `main` ref every two minutes. It deploys only an artifact whose tag and manifest match the current main commit and whose archive checksum matches. It extracts into a versioned directory and atomically switches the Caddy document root. The last five releases are retained for rollback.

The host sync uses outbound HTTPS only. The workflow needs no SSH key, server password, Cloudflare token, AWS access key, or repository secret. Because the repository and its releases are public, deployment archives must contain only public static files.

## One-time host setup

After the Servio Caddy route for `got.rakmyat.online` is live, check out this repository on the EC2 host and install the restricted sync service as root:

```bash
sudo tools/install_host_sync.sh
sudo systemctl list-timers got-site-sync.timer
sudo journalctl -u got-site-sync.service -n 50 --no-pager
```

The service runs as the unprivileged `got-site` account. It can write only to `/var/lib/servio-deployer/public/got`; Caddy sees that directory through its existing read-only release mount. It does not have Docker, SSH, or general root access.

## Build and inspect locally

```bash
python tools/prepare_pages.py
python tools/verify_pages.py
python -m http.server 8767 --directory dist --bind 127.0.0.1
```

Open <http://127.0.0.1:8767/>. The root page links to `/ui_kits/storefront/index.html`. React, ReactDOM, Babel, and Google Fonts load from their configured CDNs, so browsers need internet access.

## Rollback

The normal rollback is a revert commit merged to `main`; the pipeline builds and publishes it and the host sync deploys it. To switch to a retained release immediately, stop the timer, move the `current` symlink to a known good 40-character SHA under `releases/`, then restart the timer after the source fix is ready:

```bash
sudo systemctl stop got-site-sync.timer
sudo ln -s "releases/<known-good-sha>" /var/lib/servio-deployer/public/got/.current-rollback
sudo mv -Tf /var/lib/servio-deployer/public/got/.current-rollback /var/lib/servio-deployer/public/got/current
```

## Production store limitations

This is a visual prototype, not an online shop. Catalog data and prices are samples; cart and wishlist state runs in the browser; checkout and account screens are demonstrations. Do not collect customer data or orders through this preview. The live store still needs the separate Sage/Blade WordPress theme, WooCommerce, approved products, inventory, shipping, payment, email, customer accounts, privacy/legal pages, and production acceptance.
