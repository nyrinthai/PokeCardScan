import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from match_card import match_card

def collect_corner(event, x, y, flags, points):
    if event == cv2.EVENT_LBUTTONDOWN and len(points) < 4:
        points.append((x, y))
        print(f"Corner {len(points)}: ({x}, {y})")

def main():
    parser = argparse.ArgumentParser(description="Capture one webcam frame")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--database", type=Path, default=Path("catalog.sqlite3"))
    parser.add_argument(
        "output",
        type=Path,
        nargs="?",
        default=Path("webcam_frame.jpg"),
    )
    args = parser.parse_args()

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
        
        window = "Corners: TL, TR, BR, BL - Enter: confirm, R: reset, Esc: cancel"
        points = []
        cv2.namedWindow(window)
        cv2.setMouseCallback(window, collect_corner, points)

        while True:
            preview = frame.copy()
            for number, point in enumerate(points, start=1):
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

        source = np.array(points, dtype=np.float32)
        if not cv2.isContourConvex(source) or cv2.contourArea(source, oriented=True) <= 0:
            raise SystemExit("Select four distinct corners in order: TL, TR, BR, BL")

        top_left, top_right, bottom_right, bottom_left = source
        width = round(max(np.linalg.norm(top_right - top_left),
                          np.linalg.norm(bottom_right - bottom_left)))
        height = round(max(np.linalg.norm(bottom_left - top_left),
                           np.linalg.norm(bottom_right - top_right)))
        if width < 2 or height < 2:
            raise SystemExit("Selected card is too small")

        destination = np.array([
            (0, 0), (width - 1, 0),
            (width - 1, height - 1), (0, height - 1),
        ], dtype=np.float32)
        transform = cv2.getPerspectiveTransform(source, destination)
        frame = cv2.warpPerspective(frame, transform, (width, height))

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
