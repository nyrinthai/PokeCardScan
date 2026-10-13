"""Evaluate duclvQ/tcg-card-detector (AGPL-3.0), revision 419633c."""
import argparse
import csv
from pathlib import Path
from statistics import median
from time import perf_counter

import cv2
import numpy as np
from ultralytics import YOLO
from PIL import Image

from match_card import match_card
from card_geometry import rectify_card


def main():
    parser = argparse.ArgumentParser(description="Draw pretrained card-corner predictions")
    parser.add_argument("--directory", type=Path, default=Path("test_images"))
    parser.add_argument("--output", type=Path, default=Path("detector_results"))
    parser.add_argument("--weights", type=Path, default=Path("models/card_pose_yolov8n.pt"))
    parser.add_argument("--confidence", type=float, default=0.25)
    parser.add_argument("--database", type=Path, default=Path("catalog.sqlite3"))
    args = parser.parse_args()
    if not 0 < args.confidence <= 1:
        parser.error("confidence must be between 0 and 1")
    paths = sorted(args.directory.glob("*_original.png"))
    if not paths:
        parser.error("no *_original.png images found")
    if not args.weights.is_file():
        parser.error(f"missing model weights: {args.weights}")
    if not args.database.is_file():
        parser.error(f"missing database: {args.database}")
    if args.output.resolve() == args.directory.resolve():
        parser.error("output must differ from the input directory")
    model = YOLO(str(args.weights))
    model.predict(np.zeros((480, 640, 3), dtype=np.uint8), imgsz=480,
                  conf=args.confidence, device="cpu", verbose=False)
    args.output.mkdir(parents=True, exist_ok=True)
    timings = []
    pipeline_timings = []
    with (args.output / "summary.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["image", "detections", "valid_quads", "detector_ms", "pipeline_ms", "corners", "matches"])
        for path in paths:
            frame = cv2.imread(str(path))
            if frame is None:
                raise ValueError(f"Could not read {path}")
            started = perf_counter()
            result = model.predict(frame, imgsz=480, conf=args.confidence,
                                   device="cpu", verbose=False)[0]
            elapsed = (perf_counter() - started) * 1000
            timings.append(elapsed)
            preview = frame.copy()
            quads = []
            rankings = []
            pipeline_ms = elapsed
            if len(result.boxes):
                if result.keypoints is None:
                    raise ValueError("Model does not provide corner keypoints")
                for index, quad in enumerate(result.keypoints.xy.cpu().numpy()):
                    quad = np.ascontiguousarray(quad, dtype=np.float32)
                    if quad.shape != (4, 2) or not np.isfinite(quad).all():
                        continue
                    height, width = frame.shape[:2]
                    if (quad < 0).any() or (quad[:, 0] >= width).any() or (quad[:, 1] >= height).any():
                        continue
                    if not cv2.isContourConvex(quad) or abs(cv2.contourArea(quad)) < 4:
                        continue
                    quads.append(quad.tolist())
                    processing_started = perf_counter()
                    try:
                        crop = rectify_card(frame, quad)
                    except ValueError:
                        quads.pop()
                        continue
                    image = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
                    matches = match_card(image, args.database)
                    pipeline_ms += (perf_counter() - processing_started) * 1000
                    rankings.append(matches[:5])
                    crop_path = args.output / f"{path.stem}_card{index + 1}.png"
                    if not cv2.imwrite(str(crop_path), crop):
                        raise OSError(f"Could not save {crop_path}")
                    for rank, (distance, product_id, name, number) in enumerate(matches[:5], 1):
                        print(f"  {rank}. {name} | product {product_id} | distance {distance}")
                    pixels = np.rint(quad).astype(np.int32)
                    cv2.polylines(preview, [pixels], True, (0, 255, 0), 2)
                    for label, point in zip(("TL", "TR", "BR", "BL"), pixels):
                        location = tuple(map(int, point))
                        cv2.circle(preview, location, 4, (0, 255, 0), -1)
                        cv2.putText(preview, label, location, cv2.FONT_HERSHEY_SIMPLEX,
                                    0.45, (0, 255, 0), 1)
                    print(f"  candidate {index + 1}: confidence {float(result.boxes.conf[index]):.3f}")
            if not cv2.imwrite(str(args.output / path.name), preview):
                raise OSError(f"Could not save preview for {path}")
            pipeline_timings.append(pipeline_ms)
            writer.writerow([path.name, len(result.boxes), len(quads), round(elapsed, 2),
                             round(pipeline_ms, 2), quads, rankings])
            print(f"{path.name}: {len(result.boxes)} detections, {len(quads)} valid quads, {elapsed:.1f} ms")
    print(f"CPU median: {median(timings):.1f} ms; previews and summary: {args.output}")
    print(f"Detection + rectification + matching median: {median(pipeline_timings):.1f} ms (excludes file I/O)")


if __name__ == "__main__":
    main()
