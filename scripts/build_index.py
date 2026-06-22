"""
Build or update the face embeddings index.

Usage:
  python scripts/build_index.py           # incremental (skip already-indexed)
  python scripts/build_index.py --force   # rebuild from scratch
"""
import sys
import logging
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from app.indexer import build_index
from app.sources.local import LocalPhotoSource
from app.sources.onedrive import OneDrivePhotoSource

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

parser = argparse.ArgumentParser()
parser.add_argument('--force', action='store_true', help='Rebuild index from scratch')
args = parser.parse_args()

if config.SOURCE_TYPE == 'onedrive':
    source = OneDrivePhotoSource(
        client_id=config.ONEDRIVE_CLIENT_ID,
        tenant_id=config.ONEDRIVE_TENANT_ID,
        folder=config.ONEDRIVE_FOLDER,
    )
else:
    source = LocalPhotoSource(config.PHOTOS_DIR)

total = build_index(source, config.INDEX_PATH, force=args.force)
print(f"\nDone. {total} faces indexed → {config.INDEX_PATH}")
