# API Endpoint Test Results

## Summary
**CRITICAL FINDING**: Your API key IS valid but `/graphql/axie-marketplace` is rate limited IMMEDIATELY (even on first request).

## Test Results

| Endpoint | Status | Rate Limit | Notes |
|----------|--------|------------|-------|
| `/graphql/axie-marketplace` | ❌ RATE LIMITED | 50/sec (claimed) | "API rate limit exceeded" on first request |
| `/graphql/mavis-marketplace` | ❌ WRONG API | 50/sec | No `axie` field |
| `/graphql/katana` | ❌ WRONG API | 5/sec | No `axie` field |
| `/rpc` | ✅ WORKS | 100/sec | Ronin RPC - works perfectly |
| `/axp/get/*` | ❓ UNKNOWN | 1000/min | Empty response (wrong format?) |
| Old public endpoint | ⚠️ PARTIAL | Unknown | Works but returns `class: null` for Axie #1 |

## Key Findings

1. **API Key is Valid**: 
   - ✅ Authenticated successfully on all endpoints
   - ✅ RPC endpoint works: `{"result": "0x3235443"}` (block 52,740,163)
   - ❌ But GraphQL axie-marketplace immediately rate limited

2. **Rate Limit Issue**:
   - Console shows: 50 reqs/sec, 20,000 reqs/day
   - Reality: Can't make even 1 request
   - Lambda executions last 24h: 31 runs × ~100 reqs = ~3,100 requests (UNDER limit)
   - **Conclusion**: Either:
     - API key is for DIFFERENT app than console shows
     - Key is shared/exhausted by other services
     - There's a hidden per-key limit not shown

3. **Old Public Endpoint**:
   - URL: `https://graphql-gateway.axieinfinity.com/graphql`
   - ✅ NO rate limiting
   - ❌ Returns `class: null` for Axie #1
   - ❌ Internal server error for newer axies

## Recommended Actions

### Option 1: Request Rate Limit Increase (YES - DO THIS)
**Answer to your question**: YES, request increase for `/graphql/axie-marketplace`
- Current limit appears exhausted despite 20k/day claim
- Request Intermediate tier
- Explain use case: metadata ingestion for ~1,000 active listings

### Option 2: Use RPC Endpoint (Long-term)
**Viable alternative**:
- Endpoint: `https://api-gateway.skymavis.com/rpc`
- Limit: 100 reqs/sec (WORKS with your API key)
- Method: Read on-chain Axie contract data
- Requires: Gene parsing library
- Benefit: No GraphQL dependency

### Option 3: Try axie.technology API (Immediate backup)
**Community alternative**:
- URL: `https://api.axie.technology/getaxies/{AXIE_ID}`
- No API key needed
- Has complete metadata
- Unofficial (risk of breaking)

## Immediate Next Step

**Check in Sky Mavis Developer Console**:
1. Go to https://developers.skymavis.com/
2. Find your app
3. Check current usage stats
4. See if API key matches the one in AWS Secrets
5. Request Intermediate tier if current usage shows exhausted

The API key `fErgMf1pASz9eXfrnybN...` might be:
- For a DIFFERENT app
- Already used by something else
- Need to generate a NEW key for AxiePro
