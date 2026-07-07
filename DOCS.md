# Face Scan — Complete Documentation

---

## Table of Contents

- [For Users](#for-users)
  - [What is Face Scan?](#what-is-face-scan)
  - [How to Use It](#how-to-use-it)
  - [Adding Photos](#adding-photos)
  - [Changing the Photo Folder](#changing-the-photo-folder)
  - [User FAQ](#user-faq)
- [For Developers](#for-developers)
  - [Architecture](#architecture)
  - [File-by-File Breakdown](#file-by-file-breakdown)
  - [Data Flow](#data-flow)
  - [Configuration Reference](#configuration-reference)
  - [Developer FAQ](#developer-faq)

---

# For Users

## What is Face Scan?

Face Scan lets you upload a photo of a person's face and instantly find all matching photos stored in your OneDrive. It runs 24/7 on Hugging Face Spaces (free) and automatically updates its index every night.

---

## How to Use It

1. Open the app: `https://sachsahu21-face-scan.hf.space`
2. Click **Choose File** or use the camera icon to take a photo
3. Upload a photo that clearly shows a face
4. Results appear — matching photos sorted by how closely the face matches

**Tips for better results:**
- Use a clear, front-facing photo with good lighting
- One face in the uploaded photo works best
- If multiple faces are in the photo, the largest face is used for matching

---

## Adding Photos

Just drop photos into your OneDrive folder: **`/Camera/face_scan`**

You can do this from any device — phone, PC, tablet. The nightly job picks them up automatically at **2 AM UTC (7:30 AM IST)** and adds them to the index. No action needed on your part.

If you want new photos indexed immediately (without waiting for the nightly run):
- Go to GitHub → Actions tab → **Nightly Face Index Rebuild** → **Run workflow** → Run

---

## Changing the Photo Folder

To point the app at a different OneDrive folder (e.g. `/Camera/family`):

1. Go to your GitHub repo → **Settings → Secrets and variables → Actions**
2. Edit the secret `ONEDRIVE_FOLDER` → set it to `/Camera/family`
3. Go to **Actions** tab → **Nightly Face Index Rebuild** → **Run workflow**
4. Check the **"Rebuild from scratch"** checkbox before running
5. Done — no changes needed in Hugging Face

> The HF Space does not need to know the folder name. It only downloads the pre-built index file.

---

## User FAQ

**Q: I added photos to OneDrive but they don't appear in search results.**
A: The index updates nightly. Wait until after 7:30 AM IST, or manually trigger the GitHub Actions job.

**Q: The search returned no results.**
A: Check `https://sachsahu21-face-scan.hf.space/health` — look at `indexed_faces`. If it's 0, the index didn't load on startup. Usually means the OneDrive token expired (see token refresh below).

**Q: Photos show as broken images after search.**
A: The app couldn't get a thumbnail URL from OneDrive. The token may have expired. Notify the developer.

**Q: How accurate is the matching?**
A: The similarity threshold is set to 0.35 (out of 1.0). Higher = stricter. If you're getting too many wrong matches, the threshold needs to be raised. If you're missing obvious matches, it needs to be lowered.

**Q: Can I search with a photo that has multiple people in it?**
A: Yes, but only the largest face in the photo is used for searching. For best results, crop to the face you want to find.

**Q: How often does the index update?**
A: Every night automatically. You can also trigger it manually from the GitHub Actions tab.

**Q: Is my data private?**
A: The HF Space should be set to **Private** so only you can access it. Photos never leave your OneDrive — the app only downloads thumbnails to display results.

---

# For Developers

## Architecture

```
Your OneDrive (/Camera/face_scan)
       │
       │  (nightly, 2 AM UTC)
       ▼
GitHub Actions
  └─ Pulls photos from OneDrive via Graph API
  └─ Runs InsightFace on each photo → 512-d embedding vector
  └─ Saves all embeddings to face_index.npz
  └─ Uploads face_index.npz back to OneDrive (/FaceScanIndex/)
  └─ Calls POST /reload-index on HF Space
       │
       │  (on container boot)
       ▼
Hugging Face Spaces (Docker)
  └─ startup.py downloads face_index.npz from OneDrive
  └─ FastAPI serves the UI and search API
       │
       │  (on search request)
       ▼
Browser
  └─ Uploads face photo → /search
  └─ Gets back [{image_id, score}]
  └─ Loads each result via /photo?path=<item_id>
  └─ /photo redirects to OneDrive CDN thumbnail URL
```

---

## File-by-File Breakdown

### `config/config.yaml` — Default Configuration
The base config file. All values here can be overridden by environment variables or a `.env` file. Edit this for local development. Never commit secrets here.

Key settings:
- `source.type` — `onedrive` or `local`
- `source.onedrive.folder` — which OneDrive folder to scan
- `source.onedrive.index_path` — where the built index is stored in OneDrive
- `search.threshold` — cosine similarity cutoff (0.35 default). Raise to get stricter matches, lower to get more matches.
- `search.max_results` — maximum results returned per search

---

### `config.py` — Configuration Loader
Reads `config.yaml` and merges with environment variables. Env vars always win. Exposes everything as module-level constants:

| Constant | What it is |
|---|---|
| `SOURCE_TYPE` | `"onedrive"` or `"local"` |
| `ONEDRIVE_CLIENT_ID` | Azure app client ID |
| `ONEDRIVE_TENANT_ID` | `"consumers"` for personal Microsoft accounts |
| `ONEDRIVE_FOLDER` | OneDrive folder to scan, e.g. `/Camera/face_scan` |
| `ONEDRIVE_INDEX_PATH` | OneDrive path for the index file |
| `INDEX_PATH` | Local path to `face_index.npz` |
| `TOKEN_CACHE_PATH` | Local path to the MSAL token cache binary |
| `SEARCH_THRESHOLD` | Similarity cutoff float |
| `MAX_RESULTS` | Max results per search |

---

### `main.py` — App Entry Point
Boots the FastAPI app. Mounts `/static` for the UI and registers all API routes. Run with:
```bash
uvicorn main:app --reload
```

---

### `startup.py` — Boot-time Index Download
Runs **before** uvicorn starts on HF Spaces (called from Dockerfile's CMD). Downloads `face_index.npz` from OneDrive so the server starts with a populated index. If the download fails (bad token, network issue), it logs a warning and the server starts anyway with an empty index — it does not crash.

Flow:
1. Read `ONEDRIVE_TOKEN_CACHE` env var
2. Use MSAL to get a fresh access token from the cached refresh token
3. Call `GET /me/drive/root:/{index_path}:/content` on Graph API
4. Write bytes to local `data/face_index.npz`

---

### `app/api/routes.py` — API Endpoints

| Endpoint | What it does |
|---|---|
| `GET /` | Serves the web UI (`static/index.html`) |
| `POST /search` | Accepts image upload → detects face → searches index → returns matches |
| `GET /photo?path=<item_id>` | Redirects browser to OneDrive CDN thumbnail URL for a given item ID |
| `POST /reload-index` | Re-reads `face_index.npz` from disk into memory. Called by GitHub Actions after nightly rebuild. |
| `GET /health` | Returns `{status, indexed_faces, model_loaded}` |
| `POST /warmup` | Pre-loads the face model so the first real search isn't slow |

**Important internals:**
- The face model (~300 MB) loads **lazily** on first `/search` request, not at boot. This keeps startup fast and the health check passes immediately.
- The OneDrive source is a **singleton** — one MSAL authentication shared across all `/photo` requests.
- The searcher is protected by a **RLock** so concurrent requests don't race during index reload.

---

### `app/core/indexer.py` — Face Detection + Index Building

Uses InsightFace's `buffalo_l` model (512-dimension embeddings, L2-normalized).

**`get_face_model()`** — loads model once per process, cached in a module-level global.

**`extract_embedding(model, img)`** — detects all faces in an image, picks the largest one, returns its 512-d normalized embedding. Returns `None` if no face found.

**`build_index(source, index_path, force=False)`** — the main indexing function:
- Loads the existing index if `force=False` (incremental mode)
- Lists all images from the source
- Skips images already in the index
- Runs face detection on each new image
- **Checkpoints to disk every 500 images** — if the process is killed mid-way, progress is not lost
- Returns total face count

The index file (`face_index.npz`) stores:
- `embeddings` — shape `(N, 512)` float32 array
- `image_ids` — shape `(N,)` array of OneDrive item IDs (or local paths)

---

### `app/core/searcher.py` — Search Engine

**`FaceSearcher`** — loads the index and performs similarity search.

**`search(query_embedding)`**:
1. Computes cosine similarity between query and all `N` stored embeddings via matrix multiply: `scores = embeddings @ query` (works because all embeddings are L2-normalized)
2. Filters results below `threshold`
3. Returns top `max_results` sorted by score descending

Format: `[{"image_id": "...", "score": 0.87}, ...]`

**`reload(index_path)`** — hot-reloads the index from disk without restarting the server. Called by `/reload-index`.

---

### `app/sources/base.py` — PhotoSource Interface

Abstract base class all photo sources implement:

| Method | What it does |
|---|---|
| `list_images()` | Returns list of image identifiers (file paths or OneDrive item IDs) |
| `read_image(image_id)` | Reads the image, returns BGR numpy array (OpenCV format) |
| `get_display_url(image_id)` | Returns a URL the browser can use to display the photo |

---

### `app/sources/local.py` — Local Disk Source

Used when `source.type = local`. Walks `photos_dir` recursively, supports `.jpg .jpeg .png .webp .bmp .tiff`.

`image_id` = absolute file path on disk.  
`get_display_url` = returns `/image/<relative_path>`.

---

### `app/sources/onedrive.py` — OneDrive Source

Used when `source.type = onedrive`. Authenticates via MSAL, talks to Microsoft Graph API.

**Auth priority:**
1. Token cache file on disk (`data/.onedrive_token_cache.bin`) — used locally
2. `ONEDRIVE_TOKEN_CACHE` env var — used on HF Spaces / GitHub Actions

**`list_images()`** — recursively paginates through the OneDrive folder using `$top=1000`. Handles subfolders. Returns **OneDrive item IDs** (not filenames).

**`read_image(image_id)`** — downloads image bytes via `GET /me/drive/items/{id}/content`.

**`get_display_url(image_id)`** — fetches `GET /me/drive/items/{id}/thumbnails/0/large` and returns the CDN URL. The browser fetches this URL directly — no proxying through the server.

> **Why item IDs instead of paths?** Item IDs are stable — if a file is renamed or moved in OneDrive, the item ID stays the same. The index stays valid even if the user reorganises their OneDrive folders.

---

### `scripts/onedrive_auth.py` — One-time Authentication

Run this once locally to get a token. Uses **device code flow** (opens a browser, user signs in). Saves the MSAL token cache to `data/.onedrive_token_cache.bin`. The refresh token inside this cache is valid for 90 days of inactivity.

```bash
python scripts/onedrive_auth.py
```

---

### `scripts/build_index.py` — Interactive Index Manager

Run locally to manage the index manually. Provides a menu:

| Option | What it does |
|---|---|
| 1 | Scan for new photos only (incremental) — does not re-process photos already indexed |
| 2 | Same as 1, then uploads the index to OneDrive |
| 3 | Delete existing index and rebuild from scratch |
| 4 | Same as 3, then uploads the index to OneDrive |
| 5 | Remove entries from the index for photos that no longer exist (local mode only) |
| 6 | Show current index stats (face count, size, source) |

```bash
python scripts/build_index.py
```

---

### `scripts/run_index_job.py` — Automated Index Job

Non-interactive version for GitHub Actions / Docker. No menus, no prompts. Reads all config from environment variables. Exit code 0 = success, 1 = error.

Flow:
1. Read env vars
2. Authenticate with OneDrive
3. Download existing index (incremental mode) or skip (force rebuild mode)
4. Run `build_index()` using `OneDrivePhotoSource`
5. Re-authenticate (long builds may expire the initial token)
6. Upload new index to OneDrive
7. Call `POST /reload-index` on the HF Space

---

## Data Flow

### Search Request (end-to-end)

```
Browser uploads photo
  → POST /search (routes.py)
  → cv2.imdecode (decode bytes to numpy array)
  → extract_embedding (indexer.py) — InsightFace detects face, returns 512-d vector
  → FaceSearcher.search (searcher.py) — matrix multiply against all stored embeddings
  → returns [{image_id, score}]
  → Browser renders results, calls /photo?path=<item_id> for each
  → GET /photo (routes.py) → OneDrivePhotoSource.get_display_url()
  → Graph API returns CDN thumbnail URL
  → 302 redirect to CDN URL
  → Browser loads image directly from OneDrive CDN
```

### Nightly Index Rebuild (end-to-end)

```
GitHub Actions (2 AM UTC)
  → run_index_job.py starts in Docker container
  → authenticate with OneDrive (MSAL from ONEDRIVE_TOKEN_CACHE secret)
  → download existing face_index.npz from OneDrive (incremental)
  → OneDrivePhotoSource.list_images() — get all item IDs in /Camera/face_scan
  → skip IDs already in the index
  → for each new image: download bytes → extract_embedding → append to index
  → checkpoint every 500 images
  → upload new face_index.npz to OneDrive (/FaceScanIndex/)
  → POST /reload-index on HF Space
  → HF Space: FaceSearcher.reload() reads new index from disk
```

---

## Configuration Reference

### Environment Variables (all optional, override config.yaml)

| Variable | Default | Description |
|---|---|---|
| `SOURCE_TYPE` | `onedrive` | `onedrive` or `local` |
| `ONEDRIVE_CLIENT_ID` | *(required)* | Azure app client ID |
| `ONEDRIVE_TENANT_ID` | `consumers` | `consumers` for personal accounts |
| `ONEDRIVE_FOLDER` | `/Camera/face_scan` | OneDrive folder to scan |
| `ONEDRIVE_INDEX_PATH` | `/FaceScanIndex/face_index.npz` | OneDrive path for index storage |
| `ONEDRIVE_TOKEN_CACHE` | *(from file)* | Serialized MSAL token JSON (for cloud/CI) |
| `INDEX_PATH` | `data/face_index.npz` | Local index file path |
| `TOKEN_CACHE_PATH` | `data/.onedrive_token_cache.bin` | Local token cache path |
| `SEARCH_THRESHOLD` | `0.35` | Similarity cutoff (0.0–1.0) |
| `MAX_RESULTS` | `20` | Max results per search |
| `ROOT_DIR` | *(project folder)* | Where data/ lives |
| `PHOTOS_DIR` | *(required for local mode)* | Local photo folder |
| `SPACE_URL` | *(empty)* | HF Space URL for post-rebuild reload call |
| `FORCE_REBUILD` | `0` | Set to `1` for full rebuild in CI job |

---

## Developer FAQ

**Q: Where do I change the similarity threshold?**
A: `config/config.yaml` → `search.threshold`. Or set env var `SEARCH_THRESHOLD`. Range 0.0–1.0. Current default: 0.35. Higher = stricter = fewer but more accurate results.

**Q: How do I add a new OneDrive folder without losing the existing index?**
A: You can't merge two folders into one index incrementally. You need to:
1. Change `ONEDRIVE_FOLDER` to the new path
2. Run a full rebuild (Option 4 in build_index.py, or trigger GitHub Actions with "Rebuild from scratch" checked)

**Q: The nightly job ran but HF Space still shows old results.**
A: The job calls `POST /reload-index` after upload. Check GitHub Actions logs — did it succeed? If `SPACE_URL` is not set, the Space won't reload until next restart. You can manually call: `curl -X POST https://your-space.hf.space/reload-index`

**Q: Where is the GitHub Actions workflow file?**
A: It should be at `.github/workflows/nightly_index.yml` — this file is currently missing from the repo and needs to be created.

**Q: How do I run the app locally?**
A:
```bash
pip install -r requirements.txt
python scripts/onedrive_auth.py    # one-time
python startup.py                   # downloads index
uvicorn main:app --reload
```
Open `http://localhost:8000`

**Q: How do I update the OneDrive token when it expires?**
A:
```bash
python scripts/onedrive_auth.py
```
Then copy `data/.onedrive_token_cache.bin` contents and update:
- HF Space secret `ONEDRIVE_TOKEN_CACHE`
- GitHub secret `ONEDRIVE_TOKEN_CACHE`
- Restart the HF Space (Settings → Factory reboot)

**Q: Why does the first search after the Space boots take so long?**
A: The face model (~300 MB) loads lazily on the first request. Subsequent searches are fast. Call `POST /warmup` to pre-load the model after boot.

**Q: How do I add support for a new photo source (e.g. Google Drive)?**
A: Create a new file in `app/sources/` that inherits from `PhotoSource` (base.py) and implements the three methods: `list_images()`, `read_image()`, `get_display_url()`. Then add a branch in `config.py` and `routes.py` to instantiate it.

**Q: What does the index file contain?**
A: `face_index.npz` is a NumPy archive with two arrays:
- `embeddings`: shape `(N, 512)` — one 512-dimension vector per indexed face
- `image_ids`: shape `(N,)` — one OneDrive item ID per face (parallel to embeddings)

**Q: Why are OneDrive item IDs used instead of file paths?**
A: Item IDs are permanent — they don't change if a file is renamed or moved. File paths would break the index every time the user reorganises their OneDrive.

**Q: How do I push code changes to HF Spaces?**
A:
```bash
git push origin main          # GitHub
git push hf main              # Hugging Face (triggers rebuild)
```
If the `hf` remote isn't set up yet:
```bash
git remote add hf https://huggingface.co/spaces/sachsahu21/face-scan
```

**Q: How do I create a new version tag?**
A:
```bash
git tag v3.0 -m "Description of what changed"
git push origin v3.0
```
View all versions on GitHub → Tags tab.
