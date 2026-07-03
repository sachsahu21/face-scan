"""
upload_index.py — push the local face_index.npz to OneDrive.

Run this after build_index.py to make the updated index available to HF Spaces.
The server's /reload-index endpoint is called automatically if SPACE_URL is set.

Usage (from v2/ folder with venv active):
    python scripts/upload_index.py

Optional env var:
    SPACE_URL=https://yourname-spacename.hf.space
    → triggers a hot-reload on the running Space after upload
"""
import os
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("upload_index")

# Allow running from either v2/ or v2/scripts/
sys.path.insert(0, str(Path(__file__).parent.parent))
import config


def _get_token() -> str:
    """Get a fresh access token using the local token cache."""
    import msal

    if not config.TOKEN_CACHE_PATH.exists():
        log.error(f"Token cache not found: {config.TOKEN_CACHE_PATH}")
        log.error("Run  python scripts/onedrive_auth.py  first")
        sys.exit(1)

    cache = msal.SerializableTokenCache()
    cache.deserialize(config.TOKEN_CACHE_PATH.read_text())

    app = msal.PublicClientApplication(
        config.ONEDRIVE_CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{config.ONEDRIVE_TENANT_ID}",
        token_cache=cache,
    )
    accounts = app.get_accounts()
    if not accounts:
        log.error("No accounts in token cache — run onedrive_auth.py again")
        sys.exit(1)

    result = app.acquire_token_silent(
        scopes=["https://graph.microsoft.com/Files.ReadWrite"],
        account=accounts[0],
    )
    if not result or "access_token" not in result:
        log.error(f"Token refresh failed: {result.get('error_description', 'unknown')}")
        sys.exit(1)

    # Persist refreshed cache
    if cache.has_state_changed:
        config.TOKEN_CACHE_PATH.write_text(cache.serialize())

    return result["access_token"]


def upload(token: str, local_path: Path, onedrive_path: str) -> None:
    import requests

    if not local_path.exists():
        log.error(f"Index not found: {local_path}")
        log.error("Run  python scripts/build_index.py  first")
        sys.exit(1)

    size_mb = local_path.stat().st_size / 1_048_576
    log.info(f"Uploading {local_path.name} ({size_mb:.1f} MB) → OneDrive:{onedrive_path}")

    url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{onedrive_path}:/content"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/octet-stream",
    }
    data = local_path.read_bytes()
    r = requests.put(url, headers=headers, data=data, timeout=180)
    r.raise_for_status()
    log.info("Upload complete")


def reload_space(space_url: str) -> None:
    import requests

    url = space_url.rstrip("/") + "/reload-index"
    log.info(f"Triggering reload on Space: {url}")
    try:
        r = requests.post(url, timeout=30)
        r.raise_for_status()
        data = r.json()
        log.info(f"Space reloaded — indexed faces: {data.get('indexed', '?')}")
    except Exception as e:
        log.warning(f"Reload call failed (Space may be sleeping): {e}")
        log.warning("The Space will pick up the new index on next restart")


def main():
    if not config.ONEDRIVE_CLIENT_ID:
        log.error("ONEDRIVE_CLIENT_ID not set in config.yaml or .env")
        sys.exit(1)

    token = _get_token()
    upload(token, config.INDEX_PATH, config.ONEDRIVE_INDEX_PATH)

    space_url = os.getenv("SPACE_URL", "").strip()
    if space_url:
        reload_space(space_url)
    else:
        log.info("Tip: set SPACE_URL=https://yourname-spacename.hf.space to auto-reload after upload")


if __name__ == "__main__":
    main()
