# Cloudflare Configuration Guide

Production CDN and security configuration for Chatline using Cloudflare.

**Table of Contents**
- [Setup](#setup)
- [DNS Configuration](#dns-configuration)
- [SSL/TLS](#ssltls)
- [Security](#security)
- [Performance](#performance)
- [Caching](#caching)
- [Rate Limiting](#rate-limiting)
- [DDoS Protection](#ddos-protection)
- [Monitoring](#monitoring)

---

## Setup

### 1. Sign Up & Domain Transfer

1. Sign up at [cloudflare.com](https://www.cloudflare.com)
2. Add your domain
3. Update nameservers at domain registrar to Cloudflare's:
   - `ns1.cloudflare.com`
   - `ns2.cloudflare.com`

### 2. Verify DNS

```bash
# Check nameserver propagation (takes up to 24 hours)
nslookup -type=NS chatline.example.com
```

---

## DNS Configuration

### A Records

Create DNS records pointing to your Kubernetes Ingress/Load Balancer:

| Type | Name | Target | TTL | Proxy Status |
|------|------|--------|-----|--------------|
| A | chatline.example.com | your-ip-address | Auto | Proxied (orange) |
| A | api.chatline.example.com | your-ip-address | Auto | Proxied (orange) |
| CNAME | www | chatline.example.com | Auto | Proxied (orange) |

### Setup via Cloudflare Dashboard

1. Go to **DNS** > **Records**
2. Click **Add Record**
3. Select **A** (or **CNAME**)
4. Enter name and target
5. Set TTL to **Auto**
6. Toggle **Proxied** (orange icon)

---

## SSL/TLS

### Overview

Cloudflare manages SSL certificates automatically.

### Configuration Steps

1. Go to **SSL/TLS** tab
2. Select encryption mode: **Full (strict)**
3. Enable **Always Use HTTPS**
4. Configure Certificate

### Certificate Management

**Option 1: Automatic (Recommended)**
- Cloudflare auto-manages SSL certificates
- No action required
- Certificates renew automatically

**Option 2: Custom Certificate**
```bash
# Upload custom certificate
# SSL/TLS > Custom SSL/TLS > Add Certificate

# Generate with Let's Encrypt:
certbot certonly --standalone -d chatline.example.com
```

### Advanced Settings

```
SSL/TLS Settings:
- Minimum TLS Version: 1.2
- Opportunistic Encryption: On
- TLS 1.3: On
- Automatic HTTPS Rewrites: On
```

---

## Security

### HTTPS Redirect

Enable in **SSL/TLS** > **Edge Certificates**:
- ✅ Always Use HTTPS
- ✅ Automatic HTTPS Rewrites

### Security Headers

Configure in **Security** > **Headers** (Cloudflare Business plan+):

```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'
```

### WAF (Web Application Firewall)

**Setup:**

1. Go to **Security** > **WAF** > **Managed Rules**
2. Enable **Cloudflare Managed Ruleset**
3. Set sensitivity level
4. Add custom rules for your API

**Example: Protect /admin endpoint**

```
Rule: Block requests to /admin* unless from specific IP
Action: Block
```

### Bot Management

1. Go to **Security** > **Bot Management**
2. Select **Verified Bot Traffic**: Allow
3. Select **Likely Bot Traffic**: Challenge
4. Configure JavaScript Challenge for suspicious traffic

---

## Performance

### Caching

**Cache Level**: Aggressive (cache static assets)

```
Go to: Caching > Configuration

Cache Level: Aggressive
Browser Cache TTL: 1 month
Cache on Cookie: session_id (exclude from cache)
```

### Cache Rules

Create rules for optimal caching:

```
# Cache API responses for 1 minute
Path: /api/*
Cache Level: Cache Everything
Edge Cache TTL: 1 minute

# Cache static assets for 30 days
Path: /static/*
Cache Level: Cache Everything
Edge Cache TTL: 30 days

# Don't cache authenticated endpoints
Path: /api/auth/*
Cache Level: Bypass
```

### Minification

Enable in **Speed** > **Optimization**:
- ✅ Auto Minify (JavaScript, CSS, HTML)
- ✅ Brotli Compression

### Early Hints

Enable in **Speed** > **Optimization**:
- ✅ Early Hints (send Link headers before full response)

---

## Rate Limiting

### Basic Rate Limiting

1. Go to **Security** > **Rate Limiting**
2. Create rule:

```
Rate Limiting Rule:
Path: /api/*
Threshold: 100 requests per 10 seconds
Action: Block (HTTP 429)
```

### API-Specific Rules

```
# Strict limit on auth endpoints
Path: /api/auth/login
Threshold: 5 per minute
Action: Block

# Moderate limit on chat
Path: /api/chat
Threshold: 50 per minute
Action: Challenge

# General API limit
Path: /api/*
Threshold: 100 per minute
Action: Block
```

---

## DDoS Protection

### Cloudflare DDoS Protection (Free)

Automatically enabled for all domains:
- Network-layer DDoS protection
- Application-layer DDoS protection
- Rate-based attack mitigation

### Advanced DDoS (Business+)

Additional features:
- Custom DDoS rules
- Advanced analytics
- Managed rules

### Configuration

Go to **Security** > **DDoS**:
- Sensitivity Level: Medium (recommended)
- HTTP Flood Protection: On

---

## Monitoring

### Analytics

1. Go to **Analytics** > **Overview**
2. Monitor:
   - Requests (cached vs uncached)
   - Bandwidth usage
   - HTTP status codes
   - Top paths
   - Top referrers

### Real-Time Analytics

```
Analytics > Real-Time:
- Live request viewer
- Per-second metrics
- Cache status breakdown
```

### Security Analytics

```
Security > Overview:
- Bot score distribution
- Threat types blocked
- Countries blocked
- Top attacks
```

### Logs

Cloudflare Logs available on Enterprise plan.

For lower plans, use **Log Export** to send to third party.

---

## Advanced Configuration

### Page Rules (deprecated - use Rules Engine)

### Rules Engine (recommended)

1. Go to **Rules** > **Rules Engine**
2. Create rules for dynamic behavior:

```
# Example: Block requests with suspicious patterns
IF: Request path contains "admin" AND Is Known Bot == True
THEN: Block

# Example: Add security headers
IF: (Always)
THEN: Add header "X-Content-Type-Options: nosniff"
```

### Image Optimization

Enable in **Speed** > **Image Optimization**:
- ✅ Polish (compress images)
- ✅ Lazy Loading
- ✅ WebP Format

### Load Balancing

For multi-region setup (Cloudflare Business+):

```
1. Go to Traffic > Load Balancing
2. Create origin pool:
   - US: your-us-lb.example.com
   - EU: your-eu-lb.example.com
3. Create load balancer:
   - Default: US pool
   - Europe: EU pool (geo-routing)
```

---

## API Integration

### Using Cloudflare API

```bash
# Export DNS records
curl -X GET "https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records" \
  -H "X-Auth-Email: your-email@example.com" \
  -H "X-Auth-Key: your-api-key" \
  -H "Content-Type: application/json"

# Create cache purge
curl -X POST "https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache" \
  -H "X-Auth-Email: your-email@example.com" \
  -H "X-Auth-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"purge_everything":true}'
```

### Terraform Example

```hcl
resource "cloudflare_zone" "example" {
  zone = "chatline.example.com"
}

resource "cloudflare_record" "apex" {
  zone_id = cloudflare_zone.example.id
  name    = "chatline.example.com"
  value   = "your-ip-address"
  type    = "A"
  proxied = true
}

resource "cloudflare_firewall_rule" "rate_limit" {
  zone_id     = cloudflare_zone.example.id
  description = "Limit API requests"
  filter_id   = cloudflare_filter.rate_limit.id
  action      = "block"
}
```

---

## Troubleshooting

### DNS Not Resolving

```bash
# Check DNS propagation
nslookup chatline.example.com
dig chatline.example.com

# Should return Cloudflare IP
# If not, wait up to 24 hours for propagation
```

### SSL/TLS Errors

1. Check **SSL/TLS** > **Overview** for certificate status
2. Verify **Full (strict)** mode is enabled
3. Check origin server accepts HTTPS

### Cache Misses

1. Check cache headers from origin:
```bash
curl -I https://api.chatline.example.com
# Look for Cache-Control header
```

2. Add cache rules if needed
3. Use "Purge Cache" to manually clear

### Performance Issues

1. Check **Speed** > **Recommendations**
2. Enable suggested optimizations
3. Review **Analytics** for bottlenecks

---

## Best Practices

### Caching Strategy

- **Static assets** (JS, CSS, images): Cache 30 days
- **HTML**: Cache 1 hour (or bypass)
- **API responses**: Cache 1-5 minutes based on data
- **Authenticated endpoints**: Bypass cache

### Security Strategy

- Enable all recommended WAF rules
- Use strict SSL/TLS mode
- Enable DDoS protection
- Add rate limiting on sensitive endpoints
- Monitor security analytics

### Performance Strategy

- Minify assets
- Enable compression (Brotli)
- Use Early Hints
- Optimize images
- Cache aggressively where safe

### Monitoring Strategy

- Set up alerting for:
  - High error rates (4xx, 5xx)
  - Unusual traffic patterns
  - Attack attempts
  - Performance degradation

---

## Cost Optimization

### Free Plan

Sufficient for:
- Basic DNS
- DDoS protection
- CDN
- SSL/TLS

### Pro Plan ($20/month)

Adds:
- Advanced analytics
- Email forwarding
- Advanced rate limiting

### Business Plan ($200/month+)

Adds:
- Advanced WAF
- Load balancing
- Custom headers
- Dedicated support

---

## Additional Resources

- [Cloudflare Documentation](https://developers.cloudflare.com/)
- [WAF Rules](https://developers.cloudflare.com/waf/)
- [Page Rules (Legacy)](https://support.cloudflare.com/hc/en-us/articles/200172286)
- [Rules Engine](https://developers.cloudflare.com/rules/)
- [API Documentation](https://developers.cloudflare.com/api/)
- [Community Forum](https://community.cloudflare.com/)

---

## Example Full Configuration

### DNS Records

```
chatline.example.com          A  1.2.3.4       (Proxied)
api.chatline.example.com      A  1.2.3.4       (Proxied)
www                           CNAME chatline.example.com (Proxied)
```

### SSL/TLS

```
Mode: Full (strict)
Always HTTPS: On
Minimum TLS: 1.2
```

### Security

```
DDoS Protection: On
WAF: Managed Rules (On)
Bot Management: On
Rate Limiting:
  /api/auth/login:  5/minute
  /api/*:           100/minute
```

### Performance

```
Cache Level: Aggressive
Browser Cache: 30 days
Minify: On
Compression: Brotli
Early Hints: On
```

This configuration provides enterprise-level security, performance, and reliability for your Chatline platform.
