---
title: Face Scan
emoji: 🔍
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# Face Scan

Upload a face photo → find all matching photos stored in your OneDrive. Runs 24/7 for free on Hugging Face Spaces. Index rebuilds automatically every night via GitHub Actions.

---

## Architecture

```
Your Phone/PC
  └─ adds photos to OneDrive /Camera/face_scan

GitHub Actions (free, runs nightly at 2 AM UTC)
  └─ Docker container scans OneDrive photos
  └─ builds face embeddings index
  └─ uploads index back to OneDrive
  └─ tells HF Space to reload

Hugging Face Spaces (free, always on)
  └─ on boot: downloads index from OneDrive
  └─ on search: detects face in uploaded photo, searches index
  └─ on /photo: fetches thumbnail URL from OneDrive, redirects browser

Browser
  └─ your-username-face-scan.hf.space
```

---

## File Structure

```
face-scan/
├── .github/
│   └── workflows/
│       └── nightly_index.yml       # Scheduled nightly rebuild (GitHub Actions)
│
├── app/
│   ├── api/
│   │   └── routes.py               # FastAPI endpoints (/search, /photo, /health, /reload-index)
│   ├── core/
│   │   ├── indexer.py              # Face detection + index building (InsightFace)
│   │   └── searcher.py             # Cosine similarity search against index
│   └── sources/
│       ├── base.py                 # PhotoSource interface
│       ├── local.py                # Local disk photo source
│       └── onedrive.py             # OneDrive photo source (Graph API)
│
├── config/
│   └── config.yaml                 # Default config (overridden by env vars)
├── scripts/
│   ├── onedrive_auth.py            # One-time OneDrive authentication (run locally)
│   ├── build_index.py              # Interactive index manager (run locally)
│   ├── upload_index.py             # Standalone index uploader
│   └── run_index_job.py            # Non-interactive job for GitHub Actions/Docker
│
├── static/
│   └── index.html                  # Browser UI
│
├── config.py                       # Config loader (YAML + env vars)
├── main.py                         # FastAPI app entry point
├── startup.py                      # Downloads index from OneDrive on container boot
├── Dockerfile                      # HF Spaces production image
├── Dockerfile.indexer              # Lightweight image for the nightly index job
└── requirements.txt                # Python dependencies
```

---

## Prerequisites

- Python 3.11+
- Git
- A Microsoft account with OneDrive
- A GitHub account
- A Hugging Face account

---

## Step 1 — Clone the Repository

```bash
git clone https://github.com/sachsahu21/face-scan.git
cd face-scan
```

---

## Step 2 — Register an Azure App (one-time)

This gives the app permission to read your OneDrive files.

1. Go to [portal.azure.com](https://portal.azure.com) → **Azure Active Directory** → **App registrations** → **New registration**
2. Fill in:
   - Name: `FaceScan`
   - Supported account types: **Personal Microsoft accounts only**
   - Redirect URI: leave blank
3. Click **Register**
4. Copy the **Application (client) ID** — you'll need it in the next steps

---

## Step 3 — Set Your Config

Edit `config/config.yaml`:

```yaml
source:
  type: onedrive
  onedrive:
    client_id: "YOUR_CLIENT_ID_HERE"   # from Step 2
    tenant_id: consumers
    folder: /Camera/face_scan          # OneDrive folder with your photos
    index_path: /FaceScanIndex/face_index.npz
```

Or use a `.env` file (takes priority over config.yaml):

```
ONEDRIVE_CLIENT_ID=your-client-id
ONEDRIVE_FOLDER=/Camera/face_scan
```

---

## Step 4 — Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Step 5 — Authenticate with OneDrive (one-time)

```bash
python scripts/onedrive_auth.py
```

- A browser window opens — sign in with your Microsoft account
- Accept the permissions
- Token is saved to `data/.onedrive_token_cache.bin`

---

## Step 6 — Build the Initial Face Index

```bash
python scripts/build_index.py
```

Select an option from the menu:
- **Option 2** — Scan new photos + upload index to OneDrive *(recommended for first run)*
- **Option 4** — Full rebuild + upload *(use if starting fresh)*

This scans your OneDrive folder, detects faces in every photo, and saves a `face_index.npz` file both locally and to OneDrive.

> Large libraries (1000+ photos) take 20–60 minutes on first run. Progress is checkpointed every 500 photos so a crash doesn't lose work.

---

## Step 7 — Deploy to Hugging Face Spaces

### 7a — Create a new Space

1. Go to [huggingface.co/new-space](https://huggingface.co/new-space)
2. Settings:
   - Space name: `face-scan`
   - SDK: **Docker**
   - Visibility: Private (recommended)

### 7b — Push the code

```bash
git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/face-scan
git push hf main
```

### 7c — Add HF Space Secrets

In your Space → **Settings → Variables and secrets → New secret**:

| Secret name | Value |
|---|---|
| `SOURCE_TYPE` | `onedrive` |
| `ONEDRIVE_CLIENT_ID` | Your Azure app client ID |
| `ONEDRIVE_TENANT_ID` | `consumers` |
| `ONEDRIVE_INDEX_PATH` | `/FaceScanIndex/face_index.npz` |
| `ONEDRIVE_TOKEN_CACHE` | Contents of `data/.onedrive_token_cache.bin` |

To get the token cache content:
```bash
# Windows
type data\.onedrive_token_cache.bin

# Mac/Linux
cat data/.onedrive_token_cache.bin
```
Copy the entire JSON output and paste it as the secret value.

After adding secrets, the Space will rebuild and start. Check the logs — you should see `Index downloaded` on boot.

---

## Step 8 — Set Up Nightly Auto-Rebuild (GitHub Actions)

### 8a — Add GitHub Secrets

In your GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret name | Value |
|---|---|
| `ONEDRIVE_TOKEN_CACHE` | Same JSON as the HF secret |
| `ONEDRIVE_CLIENT_ID` | Your Azure app client ID |
| `ONEDRIVE_TENANT_ID` | `consumers` |
| `ONEDRIVE_FOLDER` | `/Camera/face_scan` |
| `ONEDRIVE_INDEX_PATH` | `/FaceScanIndex/face_index.npz` |
| `SPACE_URL` | `https://YOUR_USERNAME-face-scan.hf.space` |

### 8b — Enable GitHub Actions

Go to your repo → **Actions** tab → confirm Actions are enabled.

The workflow `Nightly Face Index Rebuild` will appear in the sidebar. It runs automatically at **2:00 AM UTC (7:30 AM IST)** every day.

### 8c — Test it manually

Actions tab → **Nightly Face Index Rebuild** → **Run workflow** → Run

---

## Day-to-Day Usage

**Add new photos:** Drop them into your OneDrive `/Camera/face_scan` folder from any device.  
**Index updates:** Automatically every night. No action needed.  
**Search:** Open `https://YOUR_USERNAME-face-scan.hf.space` → upload or capture a face photo.

---

## Changing the Photo Folder

1. Update GitHub Secret `ONEDRIVE_FOLDER` to the new path
2. Actions → **Nightly Face Index Rebuild** → **Run workflow** → check **"Rebuild from scratch"**
3. Done — no changes needed in HF Spaces

---

## Versioning

Major versions are tagged in git:

| Tag | Description |
|---|---|
| `v2.0` | OneDrive + HF Spaces initial release |
| `v2.1` | Bug fixes: empty index crash, token scope, config cleanup |

To view or roll back to a previous version: GitHub repo → **Tags**

---

## Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Web UI |
| `/search` | POST | Upload a face photo, get matches |
| `/photo?path=<id>` | GET | Redirect to OneDrive thumbnail |
| `/reload-index` | POST | Re-read index from disk (called after nightly rebuild) |
| `/health` | GET | Server status + indexed face count |
| `/warmup` | POST | Pre-load face model |

---

## Troubleshooting

### No results after search
- Check `/health` — is `indexed_faces` > 0?
- If 0: the index download failed on boot. Check HF Space logs for `startup.py` errors.
- Common cause: `ONEDRIVE_TOKEN_CACHE` secret is expired or wrong.

### Photos not loading (broken images)
- The `/photo` endpoint failed to get a thumbnail URL from OneDrive.
- Token may be expired — refresh it (see below).

### GitHub Actions job fails with "Token refresh failed"
- Update the `ONEDRIVE_TOKEN_CACHE` GitHub Secret with a fresh token.

### Refreshing the Token

Microsoft refresh tokens last **90 days of inactivity**. If the nightly job runs daily they never expire. If expired:

```bash
python scripts/onedrive_auth.py
```

Sign in again, then copy `data/.onedrive_token_cache.bin` contents and update both:
- HF Space secret `ONEDRIVE_TOKEN_CACHE`
- GitHub secret `ONEDRIVE_TOKEN_CACHE`

Then restart the HF Space (Settings → Factory reboot).
