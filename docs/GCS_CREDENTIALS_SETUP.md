# GCS Credentials Setup Guide

## Credential Format: JSON vs P12

### ✅ **Use JSON Format (Recommended)**

**Why JSON:**
- ✅ Modern, recommended format by Google Cloud
- ✅ Easier to use with Prefect and Google Cloud SDK
- ✅ `GOOGLE_APPLICATION_CREDENTIALS` expects JSON
- ✅ Better security (can be scoped to specific resources)
- ✅ Easier to manage and rotate

**Why NOT P12:**
- ❌ Older format (deprecated)
- ❌ More complex to use
- ❌ Requires additional setup
- ❌ Not recommended for new projects

---

## Getting GCS Credentials (JSON)

### Step 1: Create Service Account

1. Go to: https://console.cloud.google.com/iam-admin/serviceaccounts
2. Select your project
3. Click **Create Service Account**
4. Name: `prefect-data-pipeline` (or similar)
5. Click **Create and Continue**

### Step 2: Grant Permissions

**Minimum permissions needed:**
- **Storage Object Admin** (for read/write to GCS)
- Or **Storage Object Creator** + **Storage Object Viewer**

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

---

## Setting Up Credentials

### Option 1: Environment Variable (Recommended)

**Set `GOOGLE_APPLICATION_CREDENTIALS`:**

**Windows PowerShell:**
```powershell
# Set for current session
$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\path\to\your\credentials.json"

# Set permanently (User level)
[System.Environment]::SetEnvironmentVariable('GOOGLE_APPLICATION_CREDENTIALS', 'C:\path\to\your\credentials.json', 'User')
```

**Windows CMD:**
```cmd
setx GOOGLE_APPLICATION_CREDENTIALS "C:\path\to\your\credentials.json"
```

**Linux/Mac:**
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/credentials.json"

# Add to ~/.bashrc or ~/.zshrc for permanent:
echo 'export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/credentials.json"' >> ~/.bashrc
```

**Or add to `.env` file:**
```env
GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\your\credentials.json
```

---

### Option 2: Prefect GCS Block (Recommended for Cloud)

**Create GCS block in Prefect Cloud:**

1. Go to: https://app.prefect.cloud/blocks
2. Click **Add Block** → **GCS Bucket**
3. Fill in:
   - **Block Name:** `gcs-data-pipeline`
   - **Bucket Name:** Your GCS bucket name
   - **Service Account Info:** Paste JSON key contents
4. Click **Create**

**Then use in your flows:**
```python
from prefect_gcp import GcsBucket

gcs_bucket = GcsBucket.load("gcs-data-pipeline")
# Use gcs_bucket in your sync tasks
```

---

### Option 3: Use Application Default Credentials

**If running on Google Cloud (GCE, GKE, Cloud Run):**
- Credentials are automatically available
- No need to set `GOOGLE_APPLICATION_CREDENTIALS`

---

## Security Best Practices

### ✅ DO:
- ✅ Store JSON file securely (not in git!)
- ✅ Use service account with minimal permissions
- ✅ Rotate keys regularly
- ✅ Use Prefect Blocks for cloud deployments
- ✅ Add `.json` files to `.gitignore`

### ❌ DON'T:
- ❌ Commit credentials to git
- ❌ Share credentials publicly
- ❌ Use overly broad permissions
- ❌ Hardcode credentials in code

---

## Verify Setup

**Test credentials work:**
```python
from google.cloud import storage

# Should work if GOOGLE_APPLICATION_CREDENTIALS is set
client = storage.Client()
buckets = list(client.list_buckets())
print(f"Found {len(buckets)} buckets")
```

**Or test with Prefect:**
```python
from prefect_gcp import GcsBucket

gcs = GcsBucket.load("gcs-data-pipeline")
print(f"Bucket: {gcs.bucket}")
```

---

## For Prefect Cloud Deployments

**Best approach:** Use Prefect GCS Block

1. Create GCS block in Prefect Cloud UI
2. Store credentials securely in block
3. Reference block in your flows
4. No need to set environment variables

**Benefits:**
- ✅ Credentials stored securely in Prefect Cloud
- ✅ No need to manage environment variables
- ✅ Easy to rotate/update
- ✅ Works across all deployments

---

## Summary

**Use JSON format** - it's the modern, recommended approach.

**Setup:**
1. Create service account in GCP
2. Grant Storage Object Admin permission
3. Create JSON key
4. Set `GOOGLE_APPLICATION_CREDENTIALS` OR create Prefect GCS block
5. Test credentials work

**For cloud:** Use Prefect GCS block (easiest and most secure)

