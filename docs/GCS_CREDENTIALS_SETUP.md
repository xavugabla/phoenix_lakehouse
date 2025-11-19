# GCS Credentials Setup Guide

## Credential Format: JSON (Recommended)

**Why JSON:**
- ✅ Modern, recommended format by Google Cloud
- ✅ Easier to use with Google Cloud SDK
- ✅ `GOOGLE_APPLICATION_CREDENTIALS` expects JSON
- ✅ Better security (can be scoped to specific resources)
- ✅ Easier to manage and rotate

## Getting GCS Credentials (JSON)

### Step 1: Create Service Account

1. Go to: https://console.cloud.google.com/iam-admin/serviceaccounts
2. Select your project
3. Click **Create Service Account**
4. Name: `lakehouse-platform` (or similar)
5. Click **Create and Continue**

### Step 2: Grant Permissions

**Minimum permissions needed:**
- **Storage Object Admin** (for read/write to GCS and Iceberg catalog metadata)

**Steps:**
1. In "Grant this service account access to project"
2. Select role: **Storage Object Admin**
3. Click **Continue** → **Done**

### Step 3: Create JSON Key

1. Click on the service account you just created
2. Go to **Keys** tab
3. Click **Add Key** → **Create new key**
4. Select **JSON** format
5. Click **Create**
6. **Download the JSON file** (save securely!)

### Step 4: Set Environment Variable

**Local Development:**
```bash
# Windows PowerShell
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\your\credentials.json"

# Linux/Mac
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/credentials.json"
```

**Production/Cloud:**
- Use Workload Identity (recommended for GKE/Cloud Run)
- Or set as environment variable in your deployment configuration

## Verification

Test credentials:

```python
from google.cloud import storage

# Should work without explicit credentials if GOOGLE_APPLICATION_CREDENTIALS is set
client = storage.Client()
buckets = list(client.list_buckets())
print([b.name for b in buckets])
```

## Security Best Practices

1. **Never commit credentials to git** - Add `*.json` to `.gitignore`
2. **Use least privilege** - Only grant necessary permissions
3. **Rotate keys regularly** - Update service account keys periodically
4. **Use Workload Identity** - For production cloud deployments
5. **Store securely** - Use secret management tools (GCP Secret Manager, etc.)
