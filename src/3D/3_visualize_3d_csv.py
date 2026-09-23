import csv
from pathlib import Path

import cv2
import numpy as np
from scipy.constants import point

INPUT_FILE = "../../generated/roboter_bewegungsdaten_3d.csv"
OUTPUT_FILE = "../../generated/skelett_3d.csv.mp4"
FPS = 15
WIDTH = 1280
HEIGHT = 720

KEYPOINTS = [
    "Nase", "l_Auge", "r_Auge", "l_Ohr", "r_Ohr",
    "LShoulderRoll", "RShoulderRoll", "LElbowRoll", "RElbowRoll",
    "LWrist", "RWrist", "LHipRoll", "RHipRoll", "LKnee", "RKnee",
    "LAnkle", "RAnkle",
]

CONNECTIONS = [
    ("Nase", "l_Auge"), ("Nase", "r_Auge"),
    ("l_Auge", "l_Ohr"), ("r_Auge", "r_Ohr"),
    ("LShoulderRoll", "RShoulderRoll"),
    ("LShoulderRoll", "LElbowRoll"), ("LElbowRoll", "LWrist"),
    ("RShoulderRoll", "RElbowRoll"), ("RElbowRoll", "RWrist"),
    ("LShoulderRoll", "LHipRoll"), ("RShoulderRoll", "RHipRoll"),
    ("LHipRoll", "RHipRoll"), ("LHipRoll", "LKnee"),
    ("LKnee", "LAnkle"), ("RHipRoll", "RKnee"), ("RKnee", "RAnkle"),
]

FACE = {"Nase", "l_Auge", "r_Auge", "l_Ohr", "r_Ohr"}


def read_rows(path):
    with open(path, "r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def get_point(row, name):
    try:
        values = [float(row[f"{name}_{axis}"]) for axis in "XYZ"]
        visibility = float(row.get(f"{name}_visibility", 1.0) or 0.0)
        if not all(np.isfinite(values)) or visibility <= 0:
            return None
        return np.asarray(values, dtype=np.float32)
    except (KeyError, TypeError, ValueError):
        return None


def limits(rows):
    points = []
    for row in rows:
        points.extend(point(row, name) for name in KEYPOINTS)
    points = [item for item in points if item is not None]
    if not points:
        raise ValueError("Die CSV enthält keine gültigen 3D-Punkte.")

    data = np.asarray(points)
    minimum = data.min(axis=0)
    maximum = data.max(axis=0)
    center = (minimum + maximum) / 2.0
    span = max(float((maximum - minimum).max()), 0.1) * 1.25
    return center, span


def project(point, center, span, panel, mode):
    # MediaPipe: X rechts, Y unten, Z in Tiefenrichtung. Y wird für die
    # Darstellung invertiert, damit oben im Bild auch oben bleibt.
    x, y, z = point - center
    if mode == "front":
        horizontal, vertical = x, -y
    elif mode == "side":
        horizontal, vertical = z, -y
    else:
        # Schrägansicht: X und Z werden kombiniert, um Tiefe sichtbar zu machen.
        horizontal, vertical = x - z * 0.45, -y - z * 0.25

    px = int(panel[0] + (horizontal / span + 0.5) * panel[2])
    py = int(panel[1] + (0.5 - vertical / span) * panel[3])
    return px, py


def draw_panel(frame, row, title, panel, center, span, mode):
    x, y, width, height = panel
    cv2.rectangle(frame, (x, y), (x + width, y + height), (55, 55, 55), 1)
    cv2.putText(frame, title, (x + 12, y + 28), cv2.FONT_HERSHEY_SIMPLEX,
                0.7, (230, 230, 230), 2, cv2.LINE_AA)

    points = {name: get_point(row, name) for name in KEYPOINTS}
    points = {name: value for name, value in points.items() if value is not None}

    for first, second in CONNECTIONS:
        if first in points and second in points:
            cv2.line(frame, project(points[first], center, span, panel, mode),
                     project(points[second], center, span, panel, mode),
                     (220, 220, 220), 2, cv2.LINE_AA)

    for name, value in points.items():
        color = (0, 220, 255) if name in FACE else (0, 255, 80)
        cv2.circle(frame, project(value, center, span, panel, mode), 5, color, -1, cv2.LINE_AA)


def main():
    input_path = Path(INPUT_FILE)
    output_path = Path(OUTPUT_FILE)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = read_rows(input_path)
    if not rows:
        raise ValueError(f"Keine Frames in {input_path} gefunden.")

    center, span = limits(rows)
    writer = cv2.VideoWriter(
        str(output_path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (WIDTH, HEIGHT)
    )
    if not writer.isOpened():
        raise RuntimeError(f"Video konnte nicht geöffnet werden: {output_path}")

    panel_width = WIDTH // 3 - 20
    panel_height = HEIGHT - 70
    panels = [
        (10, 45, panel_width, panel_height),
        (WIDTH // 3 + 5, 45, panel_width, panel_height),
        (2 * WIDTH // 3, 45, panel_width, panel_height),
    ]

    try:
        for index, row in enumerate(rows):
            frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
            draw_panel(frame, row, "Frontansicht (X/Y)", panels[0], center, span, "front")
            draw_panel(frame, row, "Seitenansicht (Z/Y)", panels[1], center, span, "side")
            draw_panel(frame, row, "Schrägansicht (X/Y/Z)", panels[2], center, span, "oblique")

            frame_number = row.get("Frame", str(index + 1))
            cv2.putText(frame, f"Frame: {frame_number} | Z = relative Tiefe",
                        (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                        (0, 165, 255), 2, cv2.LINE_AA)
            writer.write(frame)
    finally:
        writer.release()

    print(f"3D-Video gespeichert: {output_path}")


if __name__ == "__main__":
    main()
