# Face Scan

A facial recognition search engine — index faces from a photo library and find matching photos by uploading a face image.

## How It Works

```
Your Photos  →  build_index.py  →  face_index.npz  →  Web UI / API  →  Matching Photos
```

1. **Index** — scans your photo folder, detects faces using InsightFace, stores a 512-dimension embedding per face
2. **Search** — upload any photo via the web UI; the app finds the most similar faces in the index

---

## Project Structure

```
face-scan/
├── app/
│   ├── api/
│   │   └── routes.py          # FastAPI route handlers
│   ├── core/
│   │   ├── indexer.py         # face detection + embedding extraction
│   │   └── searcher.py        # cosine similarity search
│   └── sources/
│       ├── base.py            # abstract PhotoSource interface
│       ├── local.py           # local filesystem source
│       └── onedrive.py        # Microsoft OneDrive source
├── config/
│   └── config.yaml            # all configuration (edit this)
├── scripts/
│   ├── build_index.py         # CLI: build/update the face index
│   └── onedrive_auth.py       # CLI: one-time OneDrive login
├── static/
│   └── index.html             # web UI
├── main.py                    # FastAPI app entry point
├── config.py                  # config loader (yaml + env overrides)
└── requirements.txt
```

---

## Configuration

All configuration lives in **[config/config.yaml](config/config.yaml)**.

The two most important values:

```yaml
paths:
  root_dir:   ""                  # where app artifacts are stored (index, cache)
                                  # blank = project folder
  photos_dir: "D:\\MyPhotos\\2024"  # REQUIRED — your photo collection
```

Secrets and machine-specific paths can also be set in a `.env` file (env vars override yaml values).

See [config/config.yaml](config/config.yaml) for all options with comments.

---

## Quick Start

See [SETUP.md](SETUP.md) for step-by-step instructions.

---

## Photo Sources

| Source | Description |
|---|---|
| `local` | Read photos from a folder on disk (`paths.photos_dir`) |
| `onedrive` | Read photos from Microsoft OneDrive via Graph API |

Switch by setting `source.type` in `config.yaml`.

---

## Search Tuning

| Setting | Default | Effect |
|---|---|---|
| `search.threshold` | `0.35` | Similarity cutoff — raise for stricter matches |
| `search.max_results` | `20` | Max results returned per search |

---

## Tech Stack

- **InsightFace** — face detection and embedding (`buffalo_l` model, ~300 MB, downloaded on first run)
- **FastAPI** — web server and REST API
- **NumPy** — embedding storage and cosine similarity
- **OpenCV** — image decoding
- **MSAL** — OneDrive OAuth (optional)
