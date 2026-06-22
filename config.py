from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv()

# All relative paths resolve from ROOT_DIR.
# Override ROOT_DIR in .env to store everything in a different location.
ROOT_DIR = Path(os.getenv('ROOT_DIR', Path(__file__).parent)).resolve()

# 'local' or 'onedrive'
SOURCE_TYPE = os.getenv('SOURCE_TYPE', 'local')

# Local source
LOCAL_PHOTOS_DIR = os.getenv(
    'LOCAL_PHOTOS_DIR',
    str(ROOT_DIR / 'photos')
)
if not Path(LOCAL_PHOTOS_DIR).is_absolute():
    LOCAL_PHOTOS_DIR = str(ROOT_DIR / LOCAL_PHOTOS_DIR)

# OneDrive source
ONEDRIVE_CLIENT_ID = os.getenv('ONEDRIVE_CLIENT_ID', '')
ONEDRIVE_TENANT_ID = os.getenv('ONEDRIVE_TENANT_ID', 'common')
ONEDRIVE_FOLDER    = os.getenv('ONEDRIVE_FOLDER', '/Pictures')

# Artifacts — all under ROOT_DIR by default
_index_env = os.getenv('INDEX_PATH', 'data/face_index.npz')
INDEX_PATH = _index_env if Path(_index_env).is_absolute() else str(ROOT_DIR / _index_env)

_token_env = os.getenv('TOKEN_CACHE_PATH', 'data/.onedrive_token_cache.bin')
TOKEN_CACHE_PATH = _token_env if Path(_token_env).is_absolute() else str(ROOT_DIR / _token_env)

STATIC_DIR = str(ROOT_DIR / 'static')

# Search tuning
SEARCH_THRESHOLD = float(os.getenv('SEARCH_THRESHOLD', '0.35'))
MAX_RESULTS      = int(os.getenv('MAX_RESULTS', '20'))

# Tunnel
TUNNEL_MODE = os.getenv('TUNNEL_MODE', 'false').lower() == 'true'

# Server
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', '8000'))
