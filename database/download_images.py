#!/usr/bin/env python3
import argparse
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def image_path(directory, image_id, image_url):
    suffix = Path(urlsplit(image_url).path).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        suffix = ".img"
    return directory / f"{image_id}{suffix}"


def main():
    parser = argparse.ArgumentParser(description="Download reference images for one imported set")
    parser.add_argument("set_id", type=int)
    parser.add_argument("--database", type=Path, default=Path("catalog.sqlite3"))
    parser.add_argument("--directory", type=Path, default=Path("images"))
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    with sqlite3.connect(args.database) as connection:
        rows = connection.execute(
            """SELECT image_id, image_url
               FROM card_images
               JOIN cards USING (product_id)
               WHERE set_id = ?
               ORDER BY image_id""",
            (args.set_id,),
        ).fetchall()
    if not rows:
        raise SystemExit(f"No image references found for set {args.set_id}")

    args.directory.mkdir(parents=True, exist_ok=True)
    downloaded = skipped = missing = 0
    # sequential downloads; add a small thread pool if full-catalog sync is too slow.
    for image_id, image_url in rows:
        destination = image_path(args.directory, image_id, image_url)
        if destination.is_file() and destination.stat().st_size > 0:
            skipped += 1
            continue
        if args.verify_only:
            missing += 1
            continue

        temporary = destination.with_suffix(destination.suffix + ".part")
        try:
            request = Request(image_url, headers={"User-Agent": "PokeCardScan/1"})
            with urlopen(request, timeout=30) as response, temporary.open("wb") as output:
                content_type = response.headers.get_content_type()
                if not content_type.startswith("image/"):
                    raise ValueError(f"unexpected content type {content_type} for image {image_id}")
                output.write(response.read())
            if temporary.stat().st_size == 0:
                raise ValueError(f"empty download for image {image_id}")
            temporary.replace(destination)
            downloaded += 1
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    if missing:
        raise SystemExit(f"Verification failed: {missing} of {len(rows)} images are missing")
    print(f"Verified {len(rows)} images: downloaded {downloaded}, already present {skipped}")


if __name__ == "__main__":
    main()
