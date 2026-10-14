# PokeCardScan

A Python command-line toolkit for identifying English Pokémon trading cards from cropped photos or a webcam. It imports card metadata and market prices from TCGTracking into SQLite, downloads reference images, and compares 256-bit perceptual hashes. Webcam tools use a YOLO pose model to locate card corners and correct perspective before matching.

## Features and benefits

- **Local reference catalog:** Store sets, cards, collector numbers, rarity, image URLs, and market prices by finish. Prices are stored as integer cents.
- **Repeatable preparation:** Reimport sets, reuse existing image downloads, and regenerate or verify reference fingerprints.
- **Photo matching:** Print the five closest candidates, including product IDs and hash distances.
- **Guided webcam capture:** Accept automatic corners or select them manually, save the original frame and corrected card image, then show matches.
- **Live scanning:** Display a candidate, hash distance, and gap to the next match. Three consecutive agreements mark a candidate as stable.
- **Detector evaluation:** Generate annotated previews, card crops, rankings, and CPU timing summaries from saved frames.

Recognition uses the locally prepared catalog; importing and downloading reference data require internet access. Detection and matching run locally on the CPU.

## Getting started

### Prerequisites

- Python 3.12 is available in the development workspace; other Python versions have not been verified.
- `pip` and a virtual environment.
- Internet access for dependency installation, catalog imports, and reference downloads.
- For webcam commands: a working camera, a desktop display for OpenCV windows, and card-corner model weights at `database/models/card_pose_yolov8n.pt`.

The weights are present in this workspace but are **not tracked by Git**. A fresh checkout needs a compatible YOLO pose model that predicts four corners in top-left, top-right, bottom-right, bottom-left order. The evaluator identifies the current model source as `duclvQ/tcg-card-detector`, revision `419633c`, under AGPL-3.0. No model download or training script is included.

### Install dependencies

From the repository root (`PokeCardScan/` inside this workspace), run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r database/requirements.txt
cd database
```

On macOS/Linux, replace the activation command with:

```bash
source .venv/bin/activate
```

The pinned dependencies in [requirements.txt](database/requirements.txt) are:

| Dependency | Version | Purpose |
| --- | --- | --- |
| ImageHash | 4.3.2 | Perceptual hash generation and comparison |
| Pillow | 12.3.0 | Image loading and conversion |
| opencv-python | 5.0.0 | Camera capture, windows, and perspective correction |
| ultralytics | 8.4.176 | YOLO card-corner detection |

NumPy is also imported directly by the camera and geometry tools and is supplied through the dependency stack. SQLite and HTTP requests use Python's standard library. There is no package installer, web server, or API-key configuration in the project.

### Prepare a reference set

Run all examples below from `database/` with the virtual environment active. Default paths are relative to the current working directory.

Use an English Pokémon set ID from TCGTracking. The local catalog currently contains set `24722` (`ME: 30th Celebration`); substitute your desired set ID in all three commands.

```powershell
python import_set.py 24722
python download_images.py 24722
python generate_fingerprints.py 24722
```

The importer creates `catalog.sqlite3` using [schema.sql](database/schema.sql). It imports metadata, image references, and available TCG market prices, excluding code cards. Downloads go into `images/`; hashes are saved in the database. Repeat the sequence to add another set.

Check existing preparation without downloading or generating hashes:

```powershell
python download_images.py 24722 --verify-only
python generate_fingerprints.py 24722 --verify-only
```

Image verification checks that files exist and are nonempty; fingerprint verification checks database entries and their size. These checks do not establish recognition accuracy.

Reimporting replaces the selected set's stored prices with the new response. Changed image URLs invalidate their old fingerprints, so rerun downloads and fingerprint generation after an import. Back up the catalog first if you need to retain earlier prices.

## Usage

### Match a cropped photo

```powershell
python match_card.py path/to/cropped_card.jpg
```

Use a closely cropped, upright, full-card image. This command does not detect corners or correct perspective. Each output row contains rank, card name, collector number, product ID, and hash distance. Lower distances are closer matches on a 256-bit hash.

### Capture and match a webcam image

```powershell
python capture_frame.py --camera 0 captured_card.jpg
```

1. Position the card in the preview and press **Space** to capture; **Q** quits.
2. Press **Enter** to accept automatic corners, or **R** to reset and click **top-left → top-right → bottom-right → bottom-left**.
3. Press **Enter** after four corners are selected. **Esc** or **Q** cancels corner selection.

The tool saves `captured_card_original.png`, writes the rectified card to `captured_card.jpg`, and prints five candidates. Existing files with these names are overwritten. Perspective correction uses the standard 63:88 card aspect ratio.

### Scan continuously

```powershell
python scan_live.py --camera 0
```

Press **Q** or **Esc**, or close the preview window, to stop. Change `--camera` if your webcam uses another device index. The scanner processes the highest-confidence detection with valid corners in each frame and displays one candidate at a time.

**A stable candidate is not a confirmed identification.** Matching ranks every available reference without an acceptance threshold. An unknown card can still receive a candidate, and three repeated matches only indicate consistency. Catalog coverage, glare, orientation, and crop quality affect results. Webcam commands do not display stored prices or maintain a collection inventory.

### Evaluate saved frames

Place original frames named `*_original.png` in `test_images/`, then run:

```powershell
python evaluate_detector.py --directory test_images --output detector_results
```

Outputs include annotated frames, rectified crops, and `summary.csv` with detections, valid corners, rankings, and timings. These are inspection results, not a labeled accuracy benchmark. Reusing an output directory overwrites matching output filenames and the summary.

The catalog tools accept `--database`; download and fingerprint tools also accept `--directory`. Camera and evaluation commands accept `--weights`. Inspect other options with:

```powershell
python import_set.py --help
python scan_live.py --help
python evaluate_detector.py --help
```

## Folder structure

```text
PokeCardScan/                    # Git repository root
├── README.md
├── .gitignore
└── database/
    ├── requirements.txt        # Pinned Python dependencies
    ├── schema.sql              # Catalog, prices, images, hashes, sync history
    ├── import_set.py           # Import one set and its prices
    ├── download_images.py      # Download/verify reference images
    ├── generate_fingerprints.py # Generate/verify 256-bit pHashes
    ├── match_card.py           # Shared matcher and photo CLI
    ├── card_geometry.py        # Shared corner validation and rectification
    ├── capture_frame.py        # Interactive capture and matching
    ├── scan_live.py            # Continuous webcam scanning
    ├── evaluate_detector.py    # Saved-frame evaluation
    ├── catalog.sqlite3         # Local catalog; ignored by Git
    ├── images/                 # Reference downloads; ignored by Git
    ├── models/                 # Local detector weights; currently untracked
    ├── test_images/            # Local evaluation inputs; currently untracked
    └── detector_results/       # Evaluation outputs; currently untracked
```

The scripts share image-path naming through `download_images.py`, matching through `match_card.py`, and perspective correction through `card_geometry.py`. Import synchronization outcomes are recorded in the database's `sync_runs` table.

## Help and contributions

Start with each command's `--help` and the relevant script linked in the [folder overview](#folder-structure). No dedicated support channel, contribution guide, or automated test suite is included in this checkout.

When reporting a problem to the repository maintainer, include the command, Python version, error output, and a reproducible image or camera description. For recognition changes, compare saved-frame crops and rankings with [evaluate_detector.py](database/evaluate_detector.py); for catalog changes, run the preparation verification commands. Keep machine-specific databases and downloaded images out of contributions.

## License

No project `LICENSE` file is included, so this checkout does not establish permission to redistribute or reuse the project's code. Ask the maintainer to clarify licensing before redistribution. Third-party packages and model weights have their own terms; [evaluate_detector.py](database/evaluate_detector.py) identifies the detector as AGPL-3.0. Card artwork and imported data are not licensed by this README.
