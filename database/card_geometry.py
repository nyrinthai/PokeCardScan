import cv2
import numpy as np


def rectify_card(frame, points):
    source = np.ascontiguousarray(points, dtype=np.float32)
    height, width = frame.shape[:2]
    if (source.shape != (4, 2) or not np.isfinite(source).all()
            or (source < 0).any() or (source[:, 0] >= width).any()
            or (source[:, 1] >= height).any() or not cv2.isContourConvex(source)
            or cv2.contourArea(source, oriented=True) <= 0):
        raise ValueError("Select valid corners in order: TL, TR, BR, BL")
    tl, tr, br, bl = source
    width = round(max(np.linalg.norm(tr - tl), np.linalg.norm(br - bl)))
    projected_height = max(np.linalg.norm(bl - tl), np.linalg.norm(br - tr))
    if width < 2 or projected_height < 2:
        raise ValueError("Selected card is too small")
    # Use card proportions rather than foreshortened image-space edge lengths.
    height = round(width * 88 / 63)
    destination = np.float32([[0, 0], [width - 1, 0],
                              [width - 1, height - 1], [0, height - 1]])
    transform = cv2.getPerspectiveTransform(source, destination)
    return cv2.warpPerspective(frame, transform, (width, height))
