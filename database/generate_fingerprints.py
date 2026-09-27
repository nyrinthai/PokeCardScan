#!/usr/bin/env python3
import argparse
import sqlite3
from pathlib import Path

import imagehash
from PIL import Image

from download_images import image_path


def main():
    parser = argparse.ArgumentParser(description="Generate full-card pHashes for one imported set")
    parser.add_argument("set_id", type=int)
    parser.add_argument("--database", type=Path, default=Path("catalog.sqlite3"))
    parser.add_argument("--directory", type=Path, default=Path("images"))
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    with sqlite3.connect(args.database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        images = connection.execute(
            """SELECT image_id, product_id, image_url
               FROM card_images
               JOIN cards USING (product_id)
               WHERE set_id = ?
               ORDER BY image_id""",
            (args.set_id,),
        ).fetchall()
        if not images:
            raise SystemExit(f"No image references found for set {args.set_id}")

        if not args.verify_only:
            with connection:
                for image_id, product_id, image_url in images:
                    path = image_path(args.directory, product_id, image_url)
                    if not path.is_file() or path.stat().st_size == 0:
                        raise FileNotFoundError(f"missing image {path}")
                    with Image.open(path) as image:
                        fingerprint = bytes.fromhex(str(imagehash.phash(image)))
                    if len(fingerprint) != 8:
                        raise ValueError(f"pHash for image {image_id} is not 64 bits")
                    connection.execute(
                        """INSERT INTO fingerprints (image_id, algorithm, region, fingerprint_blob)
                           VALUES (?, 'phash', 'full', ?)
                           ON CONFLICT(image_id, algorithm, region) DO UPDATE SET
                               fingerprint_blob = excluded.fingerprint_blob""",
                        (image_id, fingerprint),
                    )

        valid = connection.execute(
            """SELECT count(*)
               FROM fingerprints
               JOIN card_images USING (image_id)
               JOIN cards USING (product_id)
               WHERE set_id = ? AND algorithm = 'phash' AND region = 'full'
                   AND length(fingerprint_blob) = 8""",
            (args.set_id,),
        ).fetchone()[0]
    if valid != len(images):
        raise SystemExit(f"Verification failed: {valid} valid fingerprints for {len(images)} images")
    print(f"Verified {valid} full-card 64-bit pHashes for set {args.set_id}")


if __name__ == "__main__":
    main()
