"""
Face index manager — interactive menu.

Usage:
  python scripts/build_index.py
"""
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import config
from app.core.indexer import build_index
from app.sources.local import LocalPhotoSource
from app.sources.onedrive import OneDrivePhotoSource

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def upload_to_onedrive():
    """Push the local index NPZ to OneDrive after a build."""
    if config.SOURCE_TYPE != 'onedrive':
        print("  Skipping upload — source.type is not onedrive.")
        return
    if not config.ONEDRIVE_CLIENT_ID:
        print("  Skipping upload — ONEDRIVE_CLIENT_ID not set.")
        return

    import msal
    import requests

    print("\nUploading index to OneDrive...")

    cache = msal.SerializableTokenCache()
    cache.deserialize(config.TOKEN_CACHE_PATH.read_text())
    app = msal.PublicClientApplication(
        config.ONEDRIVE_CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{config.ONEDRIVE_TENANT_ID}",
        token_cache=cache,
    )
    result = app.acquire_token_silent(
        scopes=["https://graph.microsoft.com/Files.ReadWrite"],
        account=app.get_accounts()[0],
    )
    token = result["access_token"]
    if cache.has_state_changed:
        config.TOKEN_CACHE_PATH.write_text(cache.serialize())

    data = Path(config.INDEX_PATH).read_bytes()
    url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{config.ONEDRIVE_INDEX_PATH}:/content"
    r = requests.put(url, headers={"Authorization": f"Bearer {token}",
                                   "Content-Type": "application/octet-stream"}, data=data, timeout=180)
    r.raise_for_status()
    print(f"  Upload complete → OneDrive:{config.ONEDRIVE_INDEX_PATH}")


def get_source():
    if config.SOURCE_TYPE == 'onedrive':
        return OneDrivePhotoSource(
            client_id=config.ONEDRIVE_CLIENT_ID,
            tenant_id=config.ONEDRIVE_TENANT_ID,
            folder=config.ONEDRIVE_FOLDER,
            token_cache_path=config.TOKEN_CACHE_PATH,
        )
    return LocalPhotoSource(config.PHOTOS_DIR)


def show_status():
    index_path = Path(config.INDEX_PATH)
    if not index_path.exists():
        print("  No index found. Run option 1 to build it.")
        return
    data = np.load(index_path, allow_pickle=True)
    image_ids = list(data['image_ids'])
    alive  = sum(1 for p in image_ids if Path(p).exists())
    dead   = len(image_ids) - alive
    size   = index_path.stat().st_size / 1024
    print(f"  Index     : {index_path}")
    print(f"  Faces     : {len(image_ids)} total  |  {alive} photos exist  |  {dead} deleted")
    print(f"  Size      : {size:.1f} KB")
    print(f"  Photos dir: {config.PHOTOS_DIR}")


def purge_deleted():
    """Remove index entries whose source file no longer exists."""
    index_path = Path(config.INDEX_PATH)
    if not index_path.exists():
        print("No index found.")
        return
    data = np.load(index_path, allow_pickle=True)
    embeddings = list(data['embeddings'])
    image_ids  = list(data['image_ids'])

    before = len(image_ids)
    pairs  = [(e, i) for e, i in zip(embeddings, image_ids) if Path(i).exists()]
    if not pairs:
        print("No entries remain after purge — index would be empty. Aborting.")
        return

    kept_emb, kept_ids = zip(*pairs)
    np.savez(index_path,
             embeddings=np.array(kept_emb, dtype=np.float32),
             image_ids=np.array(kept_ids))
    removed = before - len(kept_ids)
    print(f"  Removed {removed} stale entries. Index now has {len(kept_ids)} faces.")


MENU = """
╔════════════════════════════════════════════════╗
║           Face Index Manager                   ║
╠════════════════════════════════════════════════╣
║  1 - Add new photos (incremental)              ║
║  2 - Add new photos + upload to OneDrive       ║
║  3 - Rebuild index from scratch                ║
║  4 - Rebuild from scratch + upload to OneDrive ║
║  5 - Remove deleted photos from index          ║
║  6 - Show index status                         ║
║  0 - Exit                                      ║
╚════════════════════════════════════════════════╝
"""

print(MENU)
while True:
    choice = input("Select option: ").strip()

    if choice == '1':
        print("\nScanning for new photos...")
        total = build_index(get_source(), config.INDEX_PATH, force=False)
        print(f"Done. {total} faces in index.\n")

    elif choice == '2':
        print("\nScanning for new photos...")
        total = build_index(get_source(), config.INDEX_PATH, force=False)
        print(f"Done. {total} faces in index.")
        upload_to_onedrive()
        print()

    elif choice == '3':
        confirm = input("This will delete and rebuild the entire index. Confirm? (y/n): ").strip().lower()
        if confirm == 'y':
            print("\nRebuilding index from scratch...")
            total = build_index(get_source(), config.INDEX_PATH, force=True)
            print(f"Done. {total} faces in index.\n")
        else:
            print("Cancelled.\n")

    elif choice == '4':
        confirm = input("This will delete and rebuild the entire index. Confirm? (y/n): ").strip().lower()
        if confirm == 'y':
            print("\nRebuilding index from scratch...")
            total = build_index(get_source(), config.INDEX_PATH, force=True)
            print(f"Done. {total} faces in index.")
            upload_to_onedrive()
            print()
        else:
            print("Cancelled.\n")

    elif choice == '5':
        print("\nRemoving deleted photo entries...")
        purge_deleted()
        print()

    elif choice == '6':
        print()
        show_status()
        print()

    elif choice == '0':
        print("Bye.")
        sys.exit(0)

    else:
        print("Invalid option. Enter 0–6.\n")

    print(MENU)
