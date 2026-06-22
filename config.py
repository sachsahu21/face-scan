from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv()

# ---------------------------------------------------------------------------
# ROOT DIRECTORY
# All subfolders and artifacts live under ROOT_DIR.
# Defaults to the project folder. Override in .env to point elsewhere,
# e.g. an external drive:  ROOT_DIR=D:\FaceData
# ---------------------------------------------------------------------------
ROOT_DIR = Path(os.getenv('ROOT_DIR', Path(__file__).parent)).resolve()


def _resolve(env_key: str, default_relative: str) -> Path:
    """Return an absolute Path: use env value if set, else ROOT_DIR / default."""
    val = os.getenv(env_key, '')
    p = Path(val) if val else ROOT_DIR / default_relative
    return p if p.is_absolute() else ROOT_DIR / p


# ---------------------------------------------------------------------------
# FOLDER LAYOUT  (all under ROOT_DIR unless overridden in .env)
# ---------------------------------------------------------------------------
PHOTOS_DIR        = _resolve('PHOTOS_DIR',        'photos')          # source photos
DATA_DIR          = _resolve('DATA_DIR',           'data')            # index + cache
STATIC_DIR        = _resolve('STATIC_DIR',         'static')          # web UI assets

# Derived artifact paths (inside DATA_DIR)
INDEX_PATH        = _resolve('INDEX_PATH',         'data/face_index.npz')
TOKEN_CACHE_PATH  = _resolve('TOKEN_CACHE_PATH',   'data/.onedrive_token_cache.bin')

# ---------------------------------------------------------------------------
# PHOTO SOURCE
# SOURCE_TYPE = 'local'     → read from PHOTOS_DIR on disk
# SOURCE_TYPE = 'onedrive'  → read from OneDrive via Microsoft Graph API
# ---------------------------------------------------------------------------
SOURCE_TYPE = os.getenv('SOURCE_TYPE', 'local')

# OneDrive credentials (only needed when SOURCE_TYPE=onedrive)
ONEDRIVE_CLIENT_ID = os.getenv('ONEDRIVE_CLIENT_ID', '')
ONEDRIVE_TENANT_ID = os.getenv('ONEDRIVE_TENANT_ID', 'common')
ONEDRIVE_FOLDER    = os.getenv('ONEDRIVE_FOLDER',    '/Pictures')

# ---------------------------------------------------------------------------
# SEARCH
# ---------------------------------------------------------------------------
SEARCH_THRESHOLD = float(os.getenv('SEARCH_THRESHOLD', '0.35'))   # 0.0–1.0; higher = stricter
MAX_RESULTS      = int(os.getenv('MAX_RESULTS',      '20'))

# ---------------------------------------------------------------------------
# SERVER
# ---------------------------------------------------------------------------
HOST        = os.getenv('HOST', '0.0.0.0')
PORT        = int(os.getenv('PORT', '8000'))
TUNNEL_MODE = os.getenv('TUNNEL_MODE', 'false').lower() == 'true'  # expose via ngrok
