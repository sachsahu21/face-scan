# Setup & Run Guide

## Prerequisites

- Python 3.9 or later
- Git

---

## Step 1 — Create a Virtual Environment

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

> InsightFace will download the `buffalo_l` face model (~300 MB) on first run. This is a one-time download.

---

## Step 3 — Configure

Open **`config/config.yaml`** and set your paths:

```yaml
paths:
  root_dir:   "C:\\Users\\ISSUser\\Desktop\\Sachin\\hdd\\face_scan_artifacts"
  photos_dir: "C:\\path\\to\\your\\photos"   # ← REQUIRED
```

Optionally create a `.env` file to override values without editing the yaml:

```powershell
Copy-Item .env.example .env
```

---

## Step 4 — Build the Face Index

```powershell
python scripts/build_index.py
```

This scans all photos in `photos_dir`, detects faces, and saves the index to `data/face_index.npz`.

To re-index from scratch (e.g. after deleting photos):

```powershell
python scripts/build_index.py --force
```

---

## Step 5 — Start the Server

```powershell
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Step 6 — Open the Web UI

```
http://localhost:8000
```

Upload any photo containing a face → the app returns the best matching photos from your library.

---

## Switching Photo Collections

Just update `photos_dir` in `config/config.yaml` and re-run the indexer:

```yaml
paths:
  photos_dir: "D:\\Photos\\NewAlbum"
```

```powershell
python scripts/build_index.py --force
```

---

## OneDrive Setup (optional)

To use OneDrive as the photo source instead of local files:

1. Register an app at [portal.azure.com](https://portal.azure.com) → Azure AD → App registrations
2. Add API permission: **Microsoft Graph → Files.Read (delegated)**
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
5. Build the index and start the server as normal.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Web UI |
| `POST` | `/search` | Upload a face image, get matches |
| `POST` | `/reload-index` | Hot-reload the index without restarting |
| `GET` | `/health` | Server status + indexed face count |

### Example — search via curl

```powershell
curl -X POST http://localhost:8000/search -F "file=@C:\path\to\photo.jpg"
```

---

## Troubleshooting

| Error | Fix |
|---|---|
| `photos_dir is not configured` | Set `paths.photos_dir` in `config/config.yaml` |
| `No index found` | Run `python scripts/build_index.py` first |
| `No face detected` | The uploaded image has no detectable face |
| `OneDrive not authenticated` | Run `python scripts/onedrive_auth.py` |
| InsightFace download slow | One-time download of ~300 MB — wait for it to finish |
