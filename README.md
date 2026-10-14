# PokeCardScan

Identify English Pokémon trading cards from photos or a webcam using a local SQLite catalog, 256-bit perceptual hashes, and YOLO card-corner detection.

## Features

- Import card metadata and market prices by finish from TCGTracking.
- Download reference images and generate or verify fingerprints.
- Rank the five closest matches for a cropped photo.
- Capture cards with automatic or manual corner selection and perspective correction.
- Scan live video with three-frame candidate stabilization.
- Evaluate saved frames with annotated images, card crops, and timing reports.

Detection and matching run locally on the CPU after the catalog is prepared.

## Setup

Use Python 3.12 (the development environment), `pip`, and internet access for installation and catalog preparation. Webcam tools also require a camera and a desktop display.

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r database/requirements.txt
cd database
```

On macOS/Linux, activate with `source .venv/bin/activate` instead.

[requirements.txt](database/requirements.txt) pins ImageHash, Pillow, OpenCV, and Ultralytics. NumPy is supplied through these dependencies; SQLite uses Python's standard library.

**Webcam model:** Place compatible YOLO pose weights at `database/models/card_pose_yolov8n.pt`. They are present locally but untracked, so a fresh checkout needs them separately. The model must predict corners in **top-left → top-right → bottom-right → bottom-left** order. No model download or training script is included.

### Prepare the catalog

Run all following commands from `database/`; default paths are relative to that directory. Replace `24722` with your desired TCGTracking English Pokémon set ID. The local catalog uses `24722` (`ME: 30th Celebration`).

```powershell
python import_set.py 24722
python download_images.py 24722
python generate_fingerprints.py 24722
```

This creates `catalog.sqlite3`, downloads references to `images/`, and stores fingerprints. Code cards are excluded. Repeat for additional sets, or verify existing data:

```powershell
python download_images.py 24722 --verify-only
python generate_fingerprints.py 24722 --verify-only
```

Reimporting replaces the set's prices and invalidates fingerprints when image URLs change. Rerun downloads and fingerprint generation afterward; back up the database if you need old prices.

## Usage

### Match a photo

```powershell
python match_card.py path/to/cropped_card.jpg
```

Use an upright, closely cropped full-card image; this command does not correct perspective. Output lists rank, name, collector number, product ID, and hash distance. Lower distances mean closer matches.

### Capture a card

```powershell
python capture_frame.py --camera 0 captured_card.jpg
```

Press **Space** to capture, then **Enter** to accept detected corners. For manual selection, press **R**, click **top-left → top-right → bottom-right → bottom-left**, and press **Enter**. **Q** quits; **Esc** cancels corner selection.

Saves `captured_card_original.png` and the corrected `captured_card.jpg`, then prints five matches.

### Scan live

```powershell
python scan_live.py --camera 0
```

Press **Q** or **Esc**, or close the window, to stop. Change `--camera` for another device. The preview shows one candidate, hash distance, and the gap to the next match; three consecutive agreements mark it stable.

**Matches are candidates, not confirmed identifications.** There is no rejection threshold, so unknown cards can receive a match. Catalog coverage, lighting, orientation, and crop quality affect results.

### Evaluate saved frames

Place `*_original.png` frames in `test_images/`:

```powershell
python evaluate_detector.py --directory test_images --output detector_results
```

Produces annotated images, corrected crops, and `summary.csv` with rankings and CPU timings. This is an inspection tool, not an accuracy benchmark. Capture and evaluation overwrite outputs with matching filenames.

All tools accept `--database`; download and fingerprint tools accept `--directory`; camera and evaluation tools accept `--weights`. Use each script's `--help` for options.

## Folder structure

```text
PokeCardScan/
├── README.md
├── .gitignore
└── database/
    ├── requirements.txt         # Dependencies
    ├── schema.sql               # SQLite schema
    ├── import_set.py            # Catalog and price import
    ├── download_images.py       # Reference download/verification
    ├── generate_fingerprints.py # Fingerprint generation/verification
    ├── match_card.py            # Shared matcher and photo CLI
    ├── card_geometry.py         # Corner validation and rectification
    ├── capture_frame.py         # Interactive webcam capture
    ├── scan_live.py             # Continuous scanning
    ├── evaluate_detector.py     # Saved-frame evaluation
    ├── catalog.sqlite3          # Local database
    ├── images/                  # Reference images
    ├── models/                  # Model weights
    ├── test_images/             # Evaluation inputs
    └── detector_results/        # Evaluation outputs
```

The database, reference images, model weights, and evaluation files are local files created or supplied during setup and use.

## License

No project license has been specified. Third-party dependencies, model
weights, artwork, and data remain subject to their respective licenses.
