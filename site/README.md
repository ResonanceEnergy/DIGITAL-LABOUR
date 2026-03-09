# Digital Labour Union — Website

Production website for [digitallabourunion.com](https://digitallabourunion.com).

## Deployment

This site is deployed via **GitHub Pages** from the `site/` directory.

## Domain Setup

### 1. Purchase Domain
Buy `digitallabourunion.com` from one of:
- **Namecheap** (~$9/yr) — namecheap.com
- **Cloudflare** (~$10/yr) — dash.cloudflare.com/domains

### 2. DNS Configuration
Add these DNS records at your registrar:

| Type  | Name | Value                      |
|-------|------|----------------------------|
| A     | @    | 185.199.108.153            |
| A     | @    | 185.199.109.153            |
| A     | @    | 185.199.110.153            |
| A     | @    | 185.199.111.153            |
| CNAME | www  | resonanceenergy.github.io  |

### 3. GitHub Pages Setup
1. Go to repo Settings → Pages
2. Source: Deploy from branch
3. Branch: `main`, folder: `/site`
4. Custom domain: `digitallabourunion.com`
5. Check "Enforce HTTPS"

### 4. Verify
- Wait 5-15 mins for DNS propagation
- Visit https://digitallabourunion.com
- HTTPS should auto-provision via Let's Encrypt
