# Cloudflare DNS for GitHub Pages

GitHub Pages custom domains use DNS hostnames, not URL paths. A DNS target such as `dennislee928.github.io/pbx_estimation` is invalid because `/pbx_estimation` is a path.

For this site:

```text
Custom domain: mtk-pbx-estimation.dennisleehappy.org
GitHub Pages target: dennislee928.github.io
```

## Required Cloudflare DNS Records

Keep the GitHub ownership TXT record that GitHub created:

```text
Type: TXT
Name: _github-pages-challenge-dennislee928.mtk-pbx-estimation
Content: <GitHub challenge value>
Proxy status: DNS only
```

Add the actual routing record:

```text
Type: CNAME
Name: mtk-pbx-estimation
Content/Target: dennislee928.github.io
Proxy status: DNS only until GitHub Pages shows DNS check successful
TTL: Auto
```

After GitHub Pages reports the DNS check as successful and the site loads, you can switch the CNAME to proxied if you want to put Cloudflare Access/ZTNA in front of the site.

## ZTNA / Cloudflare Access

Protecting only the Pages hostname protects the UI, but it does not protect the RAG Worker if the browser still calls the public Workers URL:

```text
https://pbxanalyze.pcleegood.workers.dev/
```

To avoid direct RAG abuse, also put the Worker behind a Cloudflare-controlled hostname, for example:

```text
rag-pbx-estimation.dennisleehappy.org
```

Then protect both hostnames with Cloudflare Access:

```text
mtk-pbx-estimation.dennisleehappy.org
rag-pbx-estimation.dennisleehappy.org
```

Finally set the GitHub secret used by the frontend build:

```text
CLOUD_RAG_ENDPOINT=https://rag-pbx-estimation.dennisleehappy.org/
```

Do not rely on CORS alone for abuse prevention. CORS is browser-side control; it does not stop direct API clients.

## GitHub Repository Variables

Use repository variables, not secrets:

```text
PAGES_CUSTOM_DOMAIN=mtk-pbx-estimation.dennisleehappy.org
NEXT_PUBLIC_SITE_BASE_PATH=/
```

The workflow writes `site/CNAME` and builds frontend assets for root-domain hosting when these variables are set.

## Expected URLs

Custom domain:

```text
https://mtk-pbx-estimation.dennisleehappy.org/zh/
```

Default GitHub Pages project URL:

```text
https://dennislee928.github.io/pbx_estimation/zh/
```

Use `NEXT_PUBLIC_SITE_BASE_PATH=/pbx_estimation` only for the default project URL. Use `/` for the custom domain.
