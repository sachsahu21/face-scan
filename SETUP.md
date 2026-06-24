# Setup & Run Guide

## Prerequisites

- Python 3.9 or later
- Git

---

## Step 1 — Clone & Create Virtual Environment

```powershell
cd C:\Users\ISSUser\Desktop\Sachin\git\face-scan

python -m venv venv
venv\Scripts\activate
```

> Run `venv\Scripts\activate` every time you open a new terminal.

---

## Step 2 — Install Dependencies

```powershell
pip install -r requirements.txt
```

> InsightFace downloads the `buffalo_l` face model (~300 MB) on first run — one-time only.

---

## Step 3 — Configure Paths

Open **`config/config.yaml`** and set:

```yaml
paths:
  root_dir:   "C:\\path\\to\\artifacts"    # where index + cache are stored
  photos_dir: "C:\\path\\to\\your\\photos" # REQUIRED — your photo collection
```

Or use a `.env` file to override without editing yaml:

```powershell
Copy-Item .env.example .env
# then edit .env and set ROOT_DIR and PHOTOS_DIR
```

---

## Step 4 — Build the Face Index

```powershell
python scripts/build_index.py
```

An interactive menu opens:

```
║  1 - Add new photos (incremental)    ║
║  2 - Rebuild index from scratch      ║
║  3 - Remove deleted photos from index║
║  4 - Show index status               ║
║  0 - Exit                            ║
```

| Option | When to use |
|---|---|
| 1 | Added new photos to your folder |
| 2 | Moved/renamed the folder, or something looks wrong |
| 3 | Deleted photos and want to clean the index |
| 4 | Check how many faces are indexed |

---

## Step 5 — Start the Server

```powershell
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Step 6 — Open the Web UI

**Same machine:**
```
http://localhost:8000
```

**From mobile on same WiFi** — find your PC's IP:
```powershell
ipconfig
# look for IPv4 Address under your WiFi adapter, e.g. 192.168.1.45
```
Then on mobile open:
```
http://192.168.1.45:8000
```

---

## Step 7 — Share Outside Your Network (ngrok)

Install ngrok once:
```powershell
winget install Ngrok.Ngrok
```

Sign up free at [ngrok.com](https://ngrok.com), copy your authtoken, then:
```powershell
ngrok config add-authtoken YOUR_TOKEN_HERE
```

Run alongside uvicorn in a separate terminal:
```powershell
ngrok http 8000
```

Share the `https://xxx.ngrok-free.app` URL. To skip the ngrok interstitial page append:
```
?ngrok-skip-browser-warning=true
```

---

## Switching Photo Collections

Update `photos_dir` in `config/config.yaml`, then run:

```powershell
python scripts/build_index.py
# choose option 2 (Rebuild from scratch)
```

---

## OneDrive Setup (optional)

To pull photos from OneDrive instead of local disk:

1. Register an app at [portal.azure.com](https://portal.azure.com) → Azure AD → App registrations
2. Add permission: **Microsoft Graph → Files.Read (delegated)**
3. Set in `config/config.yaml`:
   ```yaml
   source:
     type: onedrive
     onedrive:
       client_id: "your-client-id"
       folder: /Pictures
   ```
4. Authenticate once:
   ```powershell
   python scripts/onedrive_auth.py
   ```
5. Build index and start server as normal.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Web UI |
| `POST` | `/search` | Upload a face photo, get matches |
| `POST` | `/reload-index` | Hot-reload index without restarting |
| `GET` | `/health` | Server status + indexed face count |
| `GET` | `/photo?path=...` | Serve a matched photo by path |

### Search via curl

```powershell
curl -X POST http://localhost:8000/search -F "file=@C:\path\to\photo.jpg"
```

---

## Troubleshooting

| Error | Fix |
|---|---|
| `photos_dir is not configured` | Set `paths.photos_dir` in `config/config.yaml` |
| `No index found` | Run `python scripts/build_index.py` first |
| `No face detected` | Uploaded image has no detectable face |
| `Directory 'static' does not exist` | Run uvicorn from the project root folder |
| `OneDrive not authenticated` | Run `python scripts/onedrive_auth.py` |
| ngrok shows warning page | Add `?ngrok-skip-browser-warning=true` to the URL |
| InsightFace download slow | One-time ~300 MB download — wait for it |
