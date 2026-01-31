# Wallet Balance Feature - Deployment Troubleshooting

## Timeline: 2026-01-31

---

## Deployment Attempts

### Attempt 1 (18:36 UTC) - FAILED ❌
**Commit**: `3f9e8b8` - Initial implementation
**Issue**: Dependency injection bug - async context manager closing prematurely
**Symptom**: 404 Not Found on `/api/v1/wallets/{address}/balances`

**Root Cause**:
```python
# BROKEN CODE
async def get_wallet_balance_service(db: AsyncSession):
    rpc_client = RoninRPCClient()
    async with rpc_client:  # Context exits immediately after yield!
        yield WalletBalanceService(...)
```

The `async with` context manager was exiting right after `yield`, closing the httpx client before the request could use it.

---

### Attempt 2 (18:48 UTC) - FAILED ❌
**Commit**: `d59dab3` - Fixed context manager
**Issue**: Missing `Depends(get_db)` in dependency function
**Symptom**: 404 Not Found - routes not registered in OpenAPI spec

**Root Cause**:
```python
# STILL BROKEN
async def get_wallet_balance_service(db: AsyncSession):  # FastAPI doesn't inject db!
    ...
```

FastAPI requires explicit `Depends()` declaration for sub-dependencies. Without it, FastAPI didn't know how to inject the `db` parameter, causing the dependency to fail and preventing route registration.

---

### Attempt 3 (18:53 UTC) - IN PROGRESS ⏳
**Commit**: `dc811a9` - Fixed dependency injection completely
**Fix Applied**:
```python
# CORRECT CODE
from fastapi import Depends
from src.models.database import get_db

async def get_wallet_balance_service(
    db: AsyncSession = Depends(get_db)  # Explicit dependency!
):
    rpc_client = RoninRPCClient()
    await rpc_client.__aenter__()  # Manual context management
    try:
        yield WalletBalanceService(db=db, rpc_client=rpc_client, cache=cache)
    finally:
        await rpc_client.__aexit__(None, None, None)
```

**Changes**:
1. ✅ Added `= Depends(get_db)` to `db` parameter
2. ✅ Imported `Depends` from `fastapi`
3. ✅ Imported `get_db` from `src.models.database`
4. ✅ Manual context manager lifecycle (fixed in Attempt 2)

---

## Key Learnings

### 1. FastAPI Dependency Injection Rules
- **Rule**: Sub-dependencies MUST use explicit `Depends()` declarations
- **Example**: `db: AsyncSession = Depends(get_db)`, not just `db: AsyncSession`
- **Why**: FastAPI can't auto-inject without the `Depends()` marker

### 2. Async Context Managers in Dependencies
- **Issue**: `async with` inside dependency functions doesn't work with `yield`
- **Reason**: Context manager exits immediately after yield
- **Solution**: Manually call `__aenter__` before yield, `__aexit__` in finally block

### 3. Route Registration Failures
- **Symptom**: 404 on endpoints, missing from OpenAPI spec
- **Cause**: Dependency injection failure prevents route registration
- **Debug**: Check OpenAPI spec (`/openapi.json`) to see registered routes

### 4. GitHub Actions vs App Runner
- **Workflow**: GitHub Action pushes Docker image to ECR automatically
- **Deployment**: App Runner auto-deploys OR requires manual trigger
- **Issue**: Sometimes deployment doesn't trigger automatically
- **Fix**: Manually trigger with `aws apprunner start-deployment`

---

## Diagnostic Commands Used

### Check Deployment Status
```bash
# List App Runner services
aws apprunner list-services --region us-east-1

# Check service status
aws apprunner describe-service \
  --service-arn <ARN> \
  --region us-east-1 \
  --query "Service.Status"

# Trigger manual deployment
aws apprunner start-deployment \
  --service-arn <ARN> \
  --region us-east-1
```

### Check GitHub Actions
```bash
# List recent workflow runs
gh run list --limit 5 --repo cambridgetcg/AxiePro

# Watch build progress
gh run list --limit 1 --repo cambridgetcg/AxiePro
```

### Test API
```bash
# Test endpoint
curl "https://api.axiepro.io/api/v1/wallets/{address}/balances"

# Check OpenAPI spec for registered routes
curl "https://api.axiepro.io/openapi.json" | jq '.paths | keys[]'

# Test with verbose output
curl -v "https://api.axiepro.io/api/v1/wallets/{address}/balances"
```

### Verify ECR Image
```bash
# Check latest pushed image
aws ecr describe-images \
  --repository-name axiepro-backend \
  --region us-east-1 \
  --query 'sort_by(imageDetails,& imagePushedAt)[-1]'
```

---

## Code Pattern: Correct Dependency Injection

### For Services with Database + External Resources

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.database import get_db

async def get_my_service(
    db: AsyncSession = Depends(get_db)  # CRITICAL: Explicit Depends!
):
    """
    Dependency factory for MyService.

    IMPORTANT: Always use Depends() for sub-dependencies!
    """
    # Initialize external resources
    external_client = SomeClient()
    await external_client.__aenter__()

    try:
        service = MyService(
            db=db,
            client=external_client,
        )
        yield service  # Provide to endpoint
    finally:
        # Cleanup after request completes
        await external_client.__aexit__(None, None, None)
```

### In Endpoints

```python
@router.get("/{id}/something")
async def my_endpoint(
    id: int,
    service: MyService = Depends(get_my_service),  # Use the factory
):
    result = await service.do_something(id)
    return {"data": result}
```

---

## Prevention Checklist

Before deploying FastAPI endpoints:

- [ ] All dependency functions use explicit `Depends()` for parameters
- [ ] Imports include `from fastapi import Depends`
- [ ] Async context managers use try/finally, not `async with`
- [ ] Test locally if possible (requires database connection)
- [ ] Check OpenAPI spec after deployment (`/openapi.json`)
- [ ] Verify routes appear in spec before testing endpoints
- [ ] Have rollback plan ready (previous commit SHA)

---

## Current Status

**Build**: In progress (commit `dc811a9`)
**Expected**: ✅ Endpoints should register and work
**ETA**: 3-4 minutes (build + deploy)

**Next**: Test endpoint once deployment completes

---

**Created**: 2026-01-31 by Claude during deployment troubleshooting
