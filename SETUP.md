# Setup & Run Guide

---

## First-Time Setup (do once)

### 1 — Create Virtual Environment

```powershell
cd C:\Users\ISSUser\Desktop\Sachin\git\face-scan
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

> InsightFace downloads the `buffalo_l` face model (~300 MB) on first run — one-time only.

---

### 2 — Configure Paths

Open **`config/config.yaml`** and set both values:

```yaml
paths:
  root_dir:   "C:\\path\\to\\artifacts"    # where index is stored
  photos_dir: "C:\\path\\to\\your\\photos" # REQUIRED — your photo collection
```

---

### 3 — Build the Face Index

```powershell
venv\Scripts\activate
python scripts/build_index.py
```

Choose **option 1** (Add new photos) to scan and index all faces.

```
║  1 - Add new photos (incremental)    ║
║  2 - Rebuild index from scratch      ║
║  3 - Remove deleted photos from index║
║  4 - Show index status               ║
║  0 - Exit                            ║
```

| Option | When to use |
|---|---|
| 1 | First run, or added new photos |
| 2 | Moved/renamed photo folder, or index looks wrong |
| 3 | Deleted photos — cleans stale entries from index |
| 4 | Check how many faces are indexed |

---

---

## Daily Run (every time)

**Terminal 1 — start the app:**
```powershell
cd C:\Users\ISSUser\Desktop\Sachin\git\face-scan
venv\Scripts\activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Open in browser:**
```
http://localhost:8000
```

---

**Terminal 2 — share outside your network (optional):**
```powershell
ngrok http 8000
```
Share the `https://xxx.ngrok-free.app?ngrok-skip-browser-warning=true` URL with anyone.

---

## Access from Mobile

**Same WiFi** — find your PC's IP:
```powershell
ipconfig
# look for IPv4 Address under WiFi adapter, e.g. 192.168.1.45
```
Open on mobile:
```
http://192.168.1.45:8000
```

**Outside your network** — use ngrok (above).

---

## Manage the Index

Whenever your photo collection changes:

```powershell
venv\Scripts\activate
python scripts/build_index.py
```

| Scenario | Option |
|---|---|
| Added new photos | 1 |
| Deleted photos | 3 |
| Changed photo folder path | 2 |
| Just want to check status | 4 |

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

## ngrok Setup (one-time)

```powershell
winget install Ngrok.Ngrok
```

Sign up free at [ngrok.com](https://ngrok.com), copy your authtoken:
```powershell
ngrok config add-authtoken YOUR_TOKEN_HERE
```

After that just run `ngrok http 8000` anytime.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Web UI |
| `POST` | `/search` | Upload a face photo, get matches |
| `POST` | `/reload-index` | Hot-reload index without restarting server |
| `GET` | `/health` | Server status + indexed face count |
| `GET` | `/photo?path=...` | Serve a matched photo by path |

---

## Troubleshooting

| Error | Fix |
|---|---|
| `photos_dir is not configured` | Set `paths.photos_dir` in `config/config.yaml` |
| `No index found` | Run `python scripts/build_index.py` → option 1 |
| `No face detected` | Uploaded image has no detectable face |
| `Directory 'static' does not exist` | Run uvicorn from the project root folder |
| `OneDrive not authenticated` | Run `python scripts/onedrive_auth.py` |
| ngrok shows warning page | Add `?ngrok-skip-browser-warning=true` to the URL |
| InsightFace download slow | One-time ~300 MB download — wait for it |
