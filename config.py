"""
Configuration loader.

Priority (highest to lowest):
  1. Environment variables / .env file
  2. config/config.yaml
"""
import os
from pathlib import Path
import yaml
from dotenv import load_dotenv

load_dotenv()

# ── Load YAML ────────────────────────────────────────────────────────────────
_YAML_PATH = Path(__file__).parent / 'config' / 'config.yaml'
with open(_YAML_PATH) as f:
    _yaml = yaml.safe_load(f)

# ── Helpers ───────────────────────────────────────────────────────────────────
def _env(key: str, yaml_val) -> str:
    """Return env var if set, otherwise the yaml value as a string."""
    return os.getenv(key, str(yaml_val) if yaml_val is not None else '')


def _resolve(raw: str, root: Path) -> Path:
    """Resolve a path: absolute → use as-is, relative → anchor to root."""
    p = Path(raw)
    return p.resolve() if p.is_absolute() else (root / p).resolve()


# ── ROOT DIR ─────────────────────────────────────────────────────────────────
_root_raw = _env('ROOT_DIR', _yaml['paths']['root_dir'])
ROOT_DIR = Path(_root_raw).resolve() if _root_raw else Path(__file__).parent.resolve()

# ── PHOTOS DIR (independent of ROOT_DIR) ─────────────────────────────────────
_photos_raw = _env('PHOTOS_DIR', _yaml['paths']['photos_dir'])
if not _photos_raw:
    raise EnvironmentError(
        "photos_dir is not configured.\n"
        "Set it in config/config.yaml  →  paths.photos_dir: D:\\MyPhotos\n"
        "  or in .env                  →  PHOTOS_DIR=D:\\MyPhotos"
    )
PHOTOS_DIR = Path(_photos_raw).resolve()

# ── APP ARTIFACTS (all under ROOT_DIR) ───────────────────────────────────────
DATA_DIR         = _resolve(_env('DATA_DIR',         _yaml['paths']['data_dir']),         ROOT_DIR)
INDEX_PATH       = _resolve(_env('INDEX_PATH',       _yaml['paths']['index_path']),       ROOT_DIR)
TOKEN_CACHE_PATH = _resolve(_env('TOKEN_CACHE_PATH', _yaml['paths']['token_cache_path']), ROOT_DIR)

# ── SOURCE ────────────────────────────────────────────────────────────────────
SOURCE_TYPE        = _env('SOURCE_TYPE',        _yaml['source']['type'])
ONEDRIVE_CLIENT_ID = _env('ONEDRIVE_CLIENT_ID', _yaml['source']['onedrive']['client_id'])
ONEDRIVE_TENANT_ID = _env('ONEDRIVE_TENANT_ID', _yaml['source']['onedrive']['tenant_id'])
ONEDRIVE_FOLDER    = _env('ONEDRIVE_FOLDER',    _yaml['source']['onedrive']['folder'])

# ── SEARCH ────────────────────────────────────────────────────────────────────
SEARCH_THRESHOLD = float(_env('SEARCH_THRESHOLD', _yaml['search']['threshold']))
MAX_RESULTS      = int(_env('MAX_RESULTS',        _yaml['search']['max_results']))

# ── SERVER ────────────────────────────────────────────────────────────────────
HOST        = _env('HOST', _yaml['server']['host'])
PORT        = int(_env('PORT', _yaml['server']['port']))
TUNNEL_MODE = _env('TUNNEL_MODE', _yaml['server']['tunnel_mode']).lower() in ('true', '1', 'yes')
