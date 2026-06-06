# DNS Setup for api.axiepro.io

**Date:** 2026-01-20

## Current Status
- App Runner backend: **RUNNING**
- Service URL: `https://rhayicxxvw.us-east-1.awsapprunner.com`
- Health check: **PASSING**

## DNS Records Needed in Cloudflare

### Step 1: Certificate Validation Records (Add ALL 3)

These CNAME records are required for SSL certificate validation:

| Type | Name | Target |
|------|------|--------|
| CNAME | `_da20b188205e3188c2d4006826f7f8fc.api` | `_ff85584e70dfd445855116e70430b930.jkddzztszm.acm-validations.aws.` |
| CNAME | `_12bbd9b3aaae441113b9a1b5cfe2cf8c.2a57j78hsrstljvqlux8inqlkmoufug.api` | `_941a60f342105aae4d6b2f7af74c5c2c.jkddzztszm.acm-validations.aws.` |
| CNAME | `_f5015437af838e85b082faef8f60180f.www.api` | `_efa19b555e669e8ffe8215fbf72b014b.jkddzztszm.acm-validations.aws.` |

**Note:** In Cloudflare, remove the `.axiepro.io.` suffix from the Name column. Cloudflare adds the domain automatically.

### Step 2: Main API Record

After certificate validation completes (wait ~5 minutes after adding Step 1 records):

| Type | Name | Target | Proxy |
|------|------|--------|-------|
| CNAME | `api` | `rhayicxxvw.us-east-1.awsapprunner.com` | DNS Only (gray cloud) |

**Important:** Set proxy status to "DNS Only" (gray cloud icon), not "Proxied" (orange cloud). This is required for App Runner's load balancer to work correctly.

## How to Add in Cloudflare

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Select the `axiepro.io` domain
3. Go to **DNS** > **Records**
4. Click **Add record** for each record above
5. For validation records: paste the full name, Cloudflare will handle the domain suffix
6. Save each record

## Verification

After adding records, you can verify:

```bash
# Check certificate validation records
dig _da20b188205e3188c2d4006826f7f8fc.api.axiepro.io CNAME +short

# Check main API record (after Step 2)
dig api.axiepro.io CNAME +short

# Test API
curl https://api.axiepro.io/health
```

## Temporary Workaround

Until DNS is configured, the frontend is using the direct App Runner URL:
`https://rhayicxxvw.us-east-1.awsapprunner.com`
