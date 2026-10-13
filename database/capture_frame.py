import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from match_card import match_card
from card_geometry import rectify_card
from ultralytics import YOLO

def collect_corner(event, x, y, flags, points):
    if event == cv2.EVENT_LBUTTONDOWN and len(points) < 4:
        points.append((x, y))
        print(f"Corner {len(points)}: ({x}, {y})")

def main():
    parser = argparse.ArgumentParser(description="Capture one webcam frame")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--database", type=Path, default=Path("catalog.sqlite3"))
    parser.add_argument("--weights", type=Path, default=Path("models/card_pose_yolov8n.pt"))
    parser.add_argument(
        "output",
        type=Path,
        nargs="?",
        default=Path("webcam_frame.jpg"),
    )
    args = parser.parse_args()

    if not args.weights.is_file():
        parser.error(f"Missing model weights: {args.weights}")
    if not args.database.is_file():
        parser.error(f"Missing database: {args.database}")
    model = YOLO(str(args.weights))

    camera = cv2.VideoCapture(args.camera)
    try:
        if not camera.isOpened():
            raise SystemExit(f"Could not open camera {args.camera}")

        while True:
            success, frame = camera.read()
            if not success:
                raise SystemExit("Could not read a frame")

            cv2.imshow("PokeCardScan - Space: capture, Q: quit", frame)
            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                return
            if key == ord(" "):
                break
        
        original_path = args.output.with_name(f"{args.output.stem}_original.png")
        if not cv2.imwrite(str(original_path), frame):
            raise SystemExit(f"Could not save {original_path}")
        print(f"Saved original frame to {original_path}")

        window = "Corners: TL, TR, BR, BL - Enter: confirm, R: reset, Esc: cancel"
        points = []
        result = model.predict(frame, imgsz=480, conf=0.25, device="cpu", verbose=False)[0]
        if result.keypoints is not None:
            for index in result.boxes.conf.argsort(descending=True).tolist():
                quad = result.keypoints.xy[index].cpu().numpy()
                try:
                    rectify_card(frame, quad)
                except ValueError:
                    continue
                points.extend(quad.tolist())
                print("Automatic corners found. Enter: accept; R: select manually.")
                break
        if not points:
            print("No valid automatic corners. Click TL, TR, BR, BL; Enter: confirm.")
        cv2.namedWindow(window)
        cv2.setMouseCallback(window, collect_corner, points)

        while True:
            preview = frame.copy()
            for number, point in enumerate(points, start=1):
                point = tuple(np.rint(point).astype(int).tolist())
                cv2.circle(preview, point, 5, (0, 255, 0), -1)
                cv2.putText(preview, str(number), (point[0] + 8, point[1] + 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.imshow(window, preview)
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")):
                return
            if key == ord("r"):
                points.clear()
            if key in (10, 13) and len(points) == 4:
                break

        try:
            frame = rectify_card(frame, points)
        except ValueError as error:
            raise SystemExit(str(error)) from error

        if not cv2.imwrite(str(args.output), frame):
            raise SystemExit(f"Could not save {args.output}")
        print(f"Saved {frame.shape[1]}x{frame.shape[0]} frame to {args.output}")

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb_frame)
        matches = match_card(image, args.database)

        for rank, match in enumerate(matches[:5], start=1):
            distance, product_id, name, collector_number = match
            print(rank, name, collector_number, product_id, distance)
    finally:
        camera.release()
        cv2.destroyAllWindows()

       
if __name__ == "__main__":
    main()
