import argparse
from pathlib import Path

import cv2


def main():
    parser = argparse.ArgumentParser(description="Capture one webcam frame")
    parser.add_argument("--camera", type=int, default=0)
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

        success, frame = camera.read()
        if not success:
            raise SystemExit("Could not read a frame")

        if not cv2.imwrite(str(args.output), frame):
            raise SystemExit(f"Could not save {args.output}")

        print(f"Saved {frame.shape[1]}x{frame.shape[0]} frame to {args.output}")
    finally:
        camera.release()

       
if __name__ == "__main__":
    main()