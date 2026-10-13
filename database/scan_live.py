import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from ultralytics import YOLO

from card_geometry import rectify_card
from match_card import match_card


def main():
    parser = argparse.ArgumentParser(description="Continuously detect and match card candidates")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--database", type=Path, default=Path("catalog.sqlite3"))
    parser.add_argument("--weights", type=Path, default=Path("models/card_pose_yolov8n.pt"))
    args = parser.parse_args()
    for path in (args.database, args.weights):
        if not path.is_file():
            parser.error(f"Missing file: {path}")

    model = YOLO(str(args.weights))
    camera = cv2.VideoCapture(args.camera)
    window = "PokeCardScan - Q: quit"
    previous_product = None
    agreement = 0
    try:
        if not camera.isOpened():
            raise SystemExit(f"Could not open camera {args.camera}")
        while True:
            success, frame = camera.read()
            if not success:
                raise SystemExit("Could not read a frame")
            result = model.predict(frame, imgsz=480, conf=0.25,
                                   device="cpu", verbose=False)[0]
            preview = frame.copy()
            lines = ["No valid card detected"]
            current_product = None
            if result.keypoints is not None:
                for index in result.boxes.conf.argsort(descending=True).tolist():
                    quad = result.keypoints.xy[index].cpu().numpy()
                    try:
                        crop = rectify_card(frame, quad)
                    except ValueError:
                        continue
                    image = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
                    matches = match_card(image, args.database)
                    distance, product_id, name, number = matches[0]
                    current_product = product_id
                    agreement = min(agreement + 1, 3) if product_id == previous_product else 1
                    previous_product = product_id
                    gap = str(matches[1][0] - distance) if len(matches) > 1 else "N/A"
                    status = "Stable candidate" if agreement == 3 else f"Checking {agreement}/3"
                    lines = [f"{status}: {name}",
                             f"Product: {product_id} | distance: {distance}/256 | gap: {gap}"]
                    points = np.rint(quad).astype(np.int32)
                    cv2.polylines(preview, [points], True, (0, 255, 0), 2)
                    break
            if current_product is None:
                previous_product = None
                agreement = 0
            for row, text in enumerate(lines):
                location = (10, 25 + row * 25)
                cv2.putText(preview, text, location, cv2.FONT_HERSHEY_SIMPLEX,
                            0.5, (0, 0, 0), 3)
                cv2.putText(preview, text, location, cv2.FONT_HERSHEY_SIMPLEX,
                            0.5, (255, 255, 255), 1)
            cv2.imshow(window, preview)
            if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                return
            if cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1:
                return
    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
