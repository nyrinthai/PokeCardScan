import argparse
import sqlite3
from pathlib import Path

import imagehash
from PIL import Image


def match_card(image, database):
    query_hash = imagehash.phash(image, hash_size=16)

    with sqlite3.connect(database) as connection:
        references = connection.execute(
            """SELECT product_id, name, collector_number, fingerprint_blob
            FROM fingerprints
            JOIN card_images USING (image_id)
            JOIN cards USING (product_id)
            WHERE algorithm = 'phash' AND region = 'full'"""
        ).fetchall()

    if not references:
        raise ValueError("No reference fingerprints found")

    matches = []
    
    for product_id, name, collector_number, fingerprint_blob in references:
        if len(fingerprint_blob) != 32:
            raise ValueError(
                f"Expected a 256-bit fingerprint for product {product_id}; "
                "regenerate reference fingerprints"
            )
        reference_hash = imagehash.hex_to_hash(fingerprint_blob.hex())
        distance = query_hash - reference_hash
        matches.append((distance, product_id, name, collector_number))

    matches.sort()
    return matches


def main():
    parser = argparse.ArgumentParser(description="Match a cropped card photo")
    parser.add_argument("--database", type=Path, default=Path("catalog.sqlite3"))
    parser.add_argument("image", type=Path)
    args = parser.parse_args()

    with Image.open(args.image) as image:
        matches = match_card(image, args.database)

    for rank, match in enumerate(matches[:5], start=1):
        distance, product_id, name, collector_number = match
        print(rank, name, collector_number, product_id, distance)


if __name__ == "__main__":
    main()
