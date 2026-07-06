"""
run_index_job.py — non-interactive index build + OneDrive upload + HF reload.

Designed to run inside a Docker container with no TTY (GitHub Actions, cron).
Exit codes: 0 = success, 1 = fatal error.

Required env vars (set as GitHub Secrets):
  ONEDRIVE_TOKEN_CACHE   — serialized MSAL token cache JSON
  ONEDRIVE_CLIENT_ID     — Azure app client ID
  ONEDRIVE_TENANT_ID     — 'consumers' for personal accounts
  ONEDRIVE_FOLDER        — OneDrive folder to scan, e.g. /Camera/face_scan
  ONEDRIVE_INDEX_PATH    — OneDrive path to store index, e.g. /FaceScanIndex/face_index.npz

Optional:
  SPACE_URL              — HF Space base URL to call /reload-index after upload
                           e.g. https://sachsahu21-face-scan.hf.space
  FORCE_REBUILD          — set to '1' to rebuild from scratch instead of incremental
  INDEX_PATH             — local path for the index file (default: /tmp/face_index.npz)
"""
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("index-job")


# ── Ensure the v2 package root is importable ─────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


def get_token(client_id: str, tenant_id: str) -> str:
    """Acquire access token from cached refresh token (env var)."""
    import msal

    cache_json = os.environ.get("ONEDRIVE_TOKEN_CACHE")
    if not cache_json:
        log.error("ONEDRIVE_TOKEN_CACHE env var not set")
        sys.exit(1)

    cache = msal.SerializableTokenCache()
    cache.deserialize(cache_json)

    app = msal.PublicClientApplication(
        client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
        token_cache=cache,
    )
    accounts = app.get_accounts()
    if not accounts:
        log.error("No accounts in token cache — re-run onedrive_auth.py locally and update the secret")
        sys.exit(1)

    result = app.acquire_token_silent(
        scopes=["Files.ReadWrite"],
        account=accounts[0],
    )
    if not result or "access_token" not in result:
        err = result.get("error_description", str(result)) if result else "None"
        log.error(f"Token refresh failed: {err}")
        sys.exit(1)

    log.info("Token acquired successfully")
    return result["access_token"]


def download_existing_index(token: str, onedrive_index_path: str, local_path: Path) -> bool:
    """Download existing index from OneDrive for incremental update. Returns True on success."""
    import requests

    url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{onedrive_index_path}:/content"
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=120)
    if r.status_code == 404:
        log.info("No existing index on OneDrive — will build from scratch")
        return False
    r.raise_for_status()

    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(r.content)
    size_mb = len(r.content) / 1_048_576
    log.info(f"Downloaded existing index: {size_mb:.1f} MB")
    return True


def upload_index(token: str, onedrive_index_path: str, local_path: Path):
    """Upload the built index to OneDrive."""
    import requests

    data = local_path.read_bytes()
    url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{onedrive_index_path}:/content"
    r = requests.put(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/octet-stream",
        },
        data=data,
        timeout=300,
    )
    r.raise_for_status()
    size_mb = len(data) / 1_048_576
    log.info(f"Uploaded index to OneDrive:{onedrive_index_path} ({size_mb:.1f} MB)")


def reload_hf_space(space_url: str):
    """Tell the HF Space to reload the index from OneDrive."""
    import requests

    url = space_url.rstrip("/") + "/reload-index"
    try:
        r = requests.post(url, timeout=60)
        r.raise_for_status()
        log.info(f"HF Space reloaded: {r.json()}")
    except Exception as e:
        log.warning(f"Could not reload HF Space (non-fatal): {e}")


def main():
    # ── Config from env ───────────────────────────────────────────────────────
    client_id          = os.environ.get("ONEDRIVE_CLIENT_ID", "")
    tenant_id          = os.environ.get("ONEDRIVE_TENANT_ID", "consumers")
    onedrive_folder    = os.environ.get("ONEDRIVE_FOLDER", "/Camera/face_scan")
    onedrive_index     = os.environ.get("ONEDRIVE_INDEX_PATH", "/FaceScanIndex/face_index.npz")
    space_url          = os.environ.get("SPACE_URL", "")
    force_rebuild      = os.environ.get("FORCE_REBUILD", "0").strip() == "1"
    local_index        = Path(os.environ.get("INDEX_PATH", "/tmp/face_index.npz"))

    if not client_id:
        log.error("ONEDRIVE_CLIENT_ID not set")
        sys.exit(1)

    log.info(f"Mode: {'FULL REBUILD' if force_rebuild else 'INCREMENTAL'}")
    log.info(f"OneDrive folder: {onedrive_folder}")
    log.info(f"OneDrive index : {onedrive_index}")

    # ── Auth ──────────────────────────────────────────────────────────────────
    token = get_token(client_id, tenant_id)

    # ── Download existing index for incremental mode ──────────────────────────
    if not force_rebuild:
        download_existing_index(token, onedrive_index, local_index)

    # ── Build index ───────────────────────────────────────────────────────────
    from app.sources.onedrive import OneDrivePhotoSource
    from app.core.indexer import build_index

    # OneDrivePhotoSource expects a token_cache_path — we supply the cache via env.
    # Write it to a temp file so the source can deserialize it.
    import msal
    import tempfile

    cache_json = os.environ["ONEDRIVE_TOKEN_CACHE"]
    tmp_cache = Path(tempfile.mktemp(suffix=".json"))
    tmp_cache.write_text(cache_json)

    try:
        source = OneDrivePhotoSource(
            client_id=client_id,
            tenant_id=tenant_id,
            folder=onedrive_folder,
            token_cache_path=tmp_cache,
        )
        total = build_index(source, local_index, force=force_rebuild)
    finally:
        tmp_cache.unlink(missing_ok=True)

    log.info(f"Index built: {total} faces")

    if total == 0:
        log.warning("No faces found — skipping upload")
        sys.exit(0)

    # Re-acquire token (long builds may expire the first one)
    token = get_token(client_id, tenant_id)

    # ── Upload to OneDrive ────────────────────────────────────────────────────
    upload_index(token, onedrive_index, local_index)

    # ── Reload HF Space ───────────────────────────────────────────────────────
    if space_url:
        reload_hf_space(space_url)
    else:
        log.info("SPACE_URL not set — skipping HF reload (Space will pick up index on next boot)")

    log.info("Job complete.")


if __name__ == "__main__":
    main()
