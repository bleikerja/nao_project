import cv2
import numpy as np
import pandas as pd


FACE_KEYPOINTS = {"Nase", "l_Auge", "r_Auge", "l_Ohr", "r_Ohr"}

# Verbindungen des Skeletts. Die Namen müssen zu den Spalten in der CSV
# passen, z.B. "LShoulderRoll_X", "LShoulderRoll_Y".
CONNECTIONS = [
    # Gesicht
    ("Nase", "l_Auge"),
    ("Nase", "r_Auge"),
    ("l_Auge", "l_Ohr"),
    ("r_Auge", "r_Ohr"),
    # Oberkörper & Arme
    ("LShoulderRoll", "RShoulderRoll"),
    ("LShoulderRoll", "LElbowRoll"),
    ("LElbowRoll", "LWrist"),
    ("RShoulderRoll", "RElbowRoll"),
    ("RElbowRoll", "RWrist"),
    # Torso / Hüfte
    ("LShoulderRoll", "LHipRoll"),
    ("RShoulderRoll", "RHipRoll"),
    ("LHipRoll", "RHipRoll"),
    # Beine
    ("LHipRoll", "LKnee"),
    ("LKnee", "LAnkle"),
    ("RHipRoll", "RKnee"),
    ("RKnee", "RAnkle"),
]


def _get_keypoints(df):
    """Ermittelt die Keypoint-Namen aus den Spalten <name>_X und <name>_Y."""
    keypoints = []
    for column in df.columns:
        if column.endswith("_X"):
            name = column[:-2]
            if f"{name}_Y" in df.columns:
                keypoints.append(name)
    return keypoints


def generate_skeleton_video(csv_path, output_path="skelett_bewegung.mp4", fps=10, confidence_threshold=0.0):
    # CSV einlesen
    df = pd.read_csv(csv_path)

    keypoints = _get_keypoints(df)
    if not keypoints:
        raise ValueError(
            "Die CSV enthält keine gültigen Koordinaten wie 'Nase_X'/'Nase_Y'."
        )

    # Numerische Spalten erzwingen und 0-Werte als 'nicht vorhanden' behandeln
    coord_cols = []
    for kp in keypoints:
        coord_cols.extend([f"{kp}_X", f"{kp}_Y"])
    df[coord_cols] = df[coord_cols].apply(pd.to_numeric, errors="coerce")

    # Breite und Höhe basierend auf gültigen Punkten berechnen
    valid_x = df[[f"{kp}_X" for kp in keypoints]].where(lambda s: s > 0)
    valid_y = df[[f"{kp}_Y" for kp in keypoints]].where(lambda s: s > 0)
    max_x = valid_x.max().max()
    max_y = valid_y.max().max()

    if pd.isna(max_x) or pd.isna(max_y):
        raise ValueError("Die CSV enthält keine gültigen Keypoint-Koordinaten.")

    width = max(2, int(np.ceil(max_x)) + 50)
    height = max(2, int(np.ceil(max_y)) + 50)
    width += width % 2
    height += height % 2

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    video = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    if not video.isOpened():
        raise RuntimeError(f"Video konnte nicht geöffnet werden: {output_path}")

    print(f"Starte Video-Generierung ({width}x{height}px)...")

    try:
        for idx, row in df.iterrows():
            frame_img = np.zeros((height, width, 3), dtype=np.uint8)
            current_coords = {}

            for kp in keypoints:
                x = row[f"{kp}_X"]
                y = row[f"{kp}_Y"]

                # Zero-Werte sind in der YOLO-CSV das Marker-Flag für 'nicht sichtbar'
                if pd.isna(x) or pd.isna(y) or x <= 0 or y <= 0:
                    continue

                # Optional: Z-/Visibility-Spalte filtern, falls vorhanden
                z_col = f"{kp}_Z"
                if confidence_threshold > 0 and z_col in df.columns:
                    z_value = pd.to_numeric(row[z_col], errors="coerce")
                    if pd.isna(z_value) or z_value < confidence_threshold:
                        continue

                current_coords[kp] = (int(round(x)), int(round(y)))

            # Linien zeichnen
            for kp1, kp2 in CONNECTIONS:
                if kp1 in current_coords and kp2 in current_coords:
                    pt1 = current_coords[kp1]
                    pt2 = current_coords[kp2]
                    cv2.line(frame_img, pt1, pt2, (255, 255, 255), 2)

            # Punkte zeichnen
            for kp, pt in current_coords.items():
                if kp in FACE_KEYPOINTS:
                    color = (0, 255, 255)
                    radius = 4
                else:
                    color = (0, 255, 0)
                    radius = 5
                cv2.circle(frame_img, pt, radius, color, thickness=-1)

            frame_value = row.get("Frame", idx + 1)
            try:
                frame_label = str(int(float(frame_value)))
            except (TypeError, ValueError):
                frame_label = str(idx + 1)

            cv2.putText(
                frame_img,
                f"Frame: {frame_label}",
                (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 165, 255),
                2,
            )
            video.write(frame_img)
    finally:
        video.release()

    print(f"Fertig! Das Video wurde als '{output_path}' gespeichert.")


if __name__ == "__main__":
    generate_skeleton_video(
        "../../generated/roboter_bewegungsdaten_3d.csv",
        "skelett_bewegung.mp4",
        fps=15,
        confidence_threshold=0.0,
    )
