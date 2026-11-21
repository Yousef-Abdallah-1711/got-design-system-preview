# Preview deployment guide

This repository contains the GØT design system and a browser-based storefront preview. It is a static UI demo. It does not process payments, create orders, save early-access signups, or connect to WooCommerce.

## Run locally

From the project folder, run:

```powershell
python -m http.server 8767 --bind 127.0.0.1
```

Open <http://127.0.0.1:8767/>. The storefront can also be opened directly at `ui_kits/storefront/index.html`. Stop the local server with `Ctrl+C`.

## Publish a static preview with Cloudflare Pages

The build script assembles only the files needed by the preview into `dist/`. It leaves the source folder unchanged and excludes project planning and brand source documents from the published artifact.

1. Push this repository to GitHub.
2. In Cloudflare, open **Workers & Pages → Create application → Pages → Connect to Git** and select the repository.
3. Set the production branch to `main`.
4. Set the build command to `python tools/prepare_pages.py` and the build output directory to `dist`.
5. Deploy. Cloudflare will provide a `*.pages.dev` preview URL. Each push to `main` triggers a new deployment; pull requests can use preview deployments.

The published root redirects to the storefront at `/ui_kits/storefront/index.html`. External React, ReactDOM, Babel, and Google Fonts resources are loaded from their configured CDNs, so the visitor's browser needs internet access.

## Connect a custom domain

In the Cloudflare Pages project, open **Custom domains → Set up a domain** and enter a domain you control. Follow the DNS instructions Cloudflare displays for that domain. A subdomain such as `preview.example.com` usually needs a CNAME to the Pages hostname. An apex domain such as `example.com` must use the DNS records Cloudflare shows; do not guess or copy records from another project. Wait for DNS and TLS certificate activation, then verify both `https://your-domain/` and `https://your-domain/ui_kits/storefront/index.html`.

If the domain's DNS is hosted elsewhere, add the exact records Cloudflare provides at that DNS provider. Do not change nameservers or existing production records unless you intend to move DNS management. A real domain can only be connected by someone with access to its DNS account.

## What this deployment does and does not do

The deployment hosts a public, static preview. It does not turn the prototype into a working shop. Catalog data and prices are samples; cart and wishlist behavior runs in the browser; checkout and account screens are demonstrations. Do not accept real customer data or orders through this preview.

For the live store, deploy the separate Sage/Blade WordPress theme to PHP hosting with WordPress and WooCommerce, then configure products, stock, shipping, payment/COD, order email, customer accounts, privacy and legal pages, and the domain's production DNS. The design-system preview is a visual reference for that implementation, not a replacement for it.

## Local build command

Run the same artifact preparation locally with:

```powershell
python tools/prepare_pages.py
```

The output is `dist/`. Preview the built artifact with `python -m http.server 8767 --directory dist --bind 127.0.0.1`.
