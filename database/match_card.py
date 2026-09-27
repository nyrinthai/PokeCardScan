import argparse
import sqlite3
from pathlib import Path

import imagehash
from PIL import Image


def main():
    parser = argparse.ArgumentParser(description="Generate a pHash for a cropped card photo")
    parser.add_argument("--database", type=Path, default=Path("catalog.sqlite3"))
    parser.add_argument("image", type=Path)
    args = parser.parse_args()

    with Image.open(args.image) as image:
        query_hash = imagehash.phash(image, hash_size=16)
    print(query_hash)
    
    with sqlite3.connect(args.database) as connection:
        references = connection.execute(
            """SELECT product_id, name, collector_number, fingerprint_blob
            FROM fingerprints
            JOIN card_images USING (image_id)
            JOIN cards USING (product_id)
            WHERE algorithm = 'phash' AND region = 'full'"""
        ).fetchall()

    print(f"Loaded {len(references)} reference fingerprints")
    
    matches = []
    
    for product_id, name, collector_number, fingerprint_blob in references:
        reference_hash = imagehash.hex_to_hash(fingerprint_blob.hex())
        distance = query_hash - reference_hash
        matches.append((distance, product_id, name, collector_number))

    matches.sort()
    
    for rank, match in enumerate(matches[:5], start=1):
        distance, product_id, name, collector_number = match
        print(rank, name, collector_number, product_id, distance)
    
if __name__ == "__main__":
    main()
