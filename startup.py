"""
startup.py — runs before uvicorn on HF Spaces.

Downloads face_index.npz from OneDrive into the local /data directory so the
server starts with a valid index. If the download fails (no token, network
error) the server still starts — it will just have an empty index.
"""
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("startup")


def _get_token(client_id: str, tenant_id: str) -> str | None:
    """Acquire an access token using a stored refresh token (env secret)."""
    token_cache_json = os.getenv("ONEDRIVE_TOKEN_CACHE")
    if not token_cache_json:
        log.warning("ONEDRIVE_TOKEN_CACHE not set — skipping index download")
        return None

    import msal
    import json

    cache = msal.SerializableTokenCache()
    cache.deserialize(token_cache_json)

    app = msal.PublicClientApplication(
        client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
        token_cache=cache,
    )
    accounts = app.get_accounts()
    if not accounts:
        log.warning("No accounts in token cache — skipping index download")
        return None

    result = app.acquire_token_silent(
        scopes=["Files.ReadWrite"],
        account=accounts[0],
    )
    if not result or "access_token" not in result:
        log.warning("Token refresh failed — skipping index download")
        return None

    return result["access_token"]


def download_index(token: str, onedrive_path: str, local_path: Path) -> bool:
    """Download a file from OneDrive by its path. Returns True on success."""
    import requests

    url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{onedrive_path}:/content"
    headers = {"Authorization": f"Bearer {token}"}

    log.info(f"Downloading index from OneDrive: {onedrive_path}")
    r = requests.get(url, headers=headers, timeout=120)
    if r.status_code == 404:
        log.warning(f"Index not found on OneDrive at {onedrive_path} — server will start with empty index")
        return False
    r.raise_for_status()

    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(r.content)
    size_mb = len(r.content) / 1_048_576
    log.info(f"Index downloaded: {size_mb:.1f} MB → {local_path}")
    return True


def main():
    # Import config here so module load errors don't crash startup silently
    try:
        import config
    except Exception as e:
        log.error(f"Config load failed: {e}")
        sys.exit(1)

    if config.SOURCE_TYPE != "onedrive":
        log.info(f"SOURCE_TYPE={config.SOURCE_TYPE} — no OneDrive index download needed")
        return

    if not config.ONEDRIVE_CLIENT_ID:
        log.warning("ONEDRIVE_CLIENT_ID not set — skipping index download")
        return

    token = _get_token(config.ONEDRIVE_CLIENT_ID, config.ONEDRIVE_TENANT_ID)
    if not token:
        return

    try:
        download_index(token, config.ONEDRIVE_INDEX_PATH, config.INDEX_PATH)
    except Exception as e:
        log.error(f"Index download error: {e} — server will start with empty index")


if __name__ == "__main__":
    main()
