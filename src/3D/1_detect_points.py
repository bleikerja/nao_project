# -*- coding: utf-8 -*-

"""

Extrahiert mit der MediaPipe-Tasks-API dreidimensionale

Pose-Landmarks aus einem Video.

Getestete Zielversion:

    mediapipe==0.10.30

Ausgabe:

    ../../generated/roboter_bewegungsdaten_3d.csv

"""

import csv

import time

from pathlib import Path

import cv2

import mediapipe as mp

from mediapipe.tasks import python

from mediapipe.tasks.python import vision

# ============================================================

# DATEIPFADE

# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent

VIDEO_PATH = (

    SCRIPT_DIR

    / ".."

    / ".."

    / "example-data"

    / "downloaded_video_2_hell.avi"

).resolve()

OUTPUT_FILE = (

    SCRIPT_DIR

    / ".."

    / ".."

    / "generated"

    / "roboter_bewegungsdaten_3d.csv"

).resolve()

MODEL_PATH = (

    SCRIPT_DIR

    / ".."

    / ".."

    / "models"

    / "pose_landmarker_full.task"

).resolve()

# ============================================================

# MEDIAPIPE-LANDMARK-INDIZES

# ============================================================

#

# Die neue Tasks-API verwendet nicht mehr:

#

#     mp.solutions.pose.PoseLandmark

#

# Deshalb werden die offiziellen MediaPipe-Indizes direkt

# hinterlegt.

#

# MediaPipe Pose besitzt insgesamt 33 Landmarks.

# ============================================================

LANDMARK_MAP = {

    "Nase": 0,

    "l_Auge": 2,

    "r_Auge": 5,

    "l_Ohr": 7,

    "r_Ohr": 8,

    "LShoulderRoll": 11,

    "RShoulderRoll": 12,

    "LElbowRoll": 13,

    "RElbowRoll": 14,

    "LWrist": 15,

    "RWrist": 16,

    "LHipRoll": 23,

    "RHipRoll": 24,

    "LKnee": 25,

    "RKnee": 26,

    "LAnkle": 27,

    "RAnkle": 28,

}

# ============================================================

# HILFSFUNKTIONEN

# ============================================================

def create_fieldnames():

    """

    Erzeugt die Kopfzeile für die Ausgabe-CSV.

    """

    fieldnames = [

        "Frame",

        "time",

    ]

    for name in LANDMARK_MAP:

        fieldnames.extend([

            f"{name}_X",

            f"{name}_Y",

            f"{name}_Z",

            f"{name}_visibility",

        ])

    return fieldnames

def write_empty_landmarks(row):

    """

    Schreibt leere Koordinaten, falls in einem Frame

    keine Person erkannt wurde.

    Das Konvertierungsskript kann diese Lücken später

    interpolieren.

    """

    for name in LANDMARK_MAP:

        row[f"{name}_X"] = ""

        row[f"{name}_Y"] = ""

        row[f"{name}_Z"] = ""

        row[f"{name}_visibility"] = 0.0

def write_world_landmarks(row, world_landmarks):

    """

    Übernimmt MediaPipe World Landmarks in die CSV.

    Die World Landmarks sind relative 3D-Koordinaten

    in Metern. Der Ursprung liegt ungefähr im Zentrum

    der Hüfte.

    Es handelt sich nicht um absolute Koordinaten

    im Raum.

    """

    for name, landmark_index in LANDMARK_MAP.items():

        if landmark_index >= len(world_landmarks):

            raise RuntimeError(

                f"Landmark-Index {landmark_index} für "

                f"{name} ist nicht vorhanden."

            )

        landmark = world_landmarks[landmark_index]

        row[f"{name}_X"] = landmark.x

        row[f"{name}_Y"] = landmark.y

        row[f"{name}_Z"] = landmark.z

        visibility = getattr(

            landmark,

            "visibility",

            0.0,

        )

        if visibility is None:

            visibility = 0.0

        row[f"{name}_visibility"] = visibility

# ============================================================

# HAUPTPROGRAMM

# ============================================================

def main():

    # --------------------------------------------------------

    # Eingabedateien prüfen

    # --------------------------------------------------------

    if not VIDEO_PATH.is_file():

        raise RuntimeError(

            f"Video wurde nicht gefunden: {VIDEO_PATH}"

        )

    if not MODEL_PATH.is_file():

        raise RuntimeError(

            "\nDas MediaPipe-Pose-Modell wurde nicht gefunden.\n"

            f"Erwarteter Pfad:\n{MODEL_PATH}\n\n"

            "Lege dort die Datei "

            "'pose_landmarker_full.task' ab."

        )

    OUTPUT_FILE.parent.mkdir(

        parents=True,

        exist_ok=True,

    )

    # --------------------------------------------------------

    # Video öffnen

    # --------------------------------------------------------

    capture = cv2.VideoCapture(

        str(VIDEO_PATH)

    )

    if not capture.isOpened():

        raise RuntimeError(

            f"Video konnte nicht geöffnet werden: "

            f"{VIDEO_PATH}"

        )

    fps = capture.get(

        cv2.CAP_PROP_FPS

    )

    if not fps or fps <= 0:

        fps = 10.0

        print(

            "WARNUNG: Video-FPS konnten nicht gelesen "

            "werden. Verwende 10 FPS."

        )

    total_frames = int(

        capture.get(cv2.CAP_PROP_FRAME_COUNT)

    )

    print("")

    print("==========================================")

    print("MEDIAPIPE POSE LANDMARKER")

    print("==========================================")

    print("Video:")

    print(VIDEO_PATH)

    print("")

    print("Modell:")

    print(MODEL_PATH)

    print("")

    print("Ausgabedatei:")

    print(OUTPUT_FILE)

    print("")

    print(f"FPS: {fps:.2f}")

    print(f"Video-Frames: {total_frames}")

    print("")

    # --------------------------------------------------------

    # Pose-Landmarker konfigurieren

    # --------------------------------------------------------

    base_options = python.BaseOptions(

        model_asset_path=str(MODEL_PATH)

    )

    options = vision.PoseLandmarkerOptions(

        base_options=base_options,

        # VIDEO aktiviert zeitliches Tracking.

        running_mode=vision.RunningMode.VIDEO,

        # In deinem Video soll nur eine Person erkannt werden.

        num_poses=1,

        min_pose_detection_confidence=0.6,

        min_pose_presence_confidence=0.6,

        min_tracking_confidence=0.6,

        # Eine Segmentierungsmaske wird für die

        # NAO-Trajektorie nicht benötigt.

        output_segmentation_masks=False,

    )

    fieldnames = create_fieldnames()

    frame_count = 0

    detected_frames = 0

    missing_frames = 0

    start_time = time.time()

    try:

        with vision.PoseLandmarker.create_from_options(

            options

        ) as pose_landmarker:

            with OUTPUT_FILE.open(

                "w",

                newline="",

                encoding="utf-8",

            ) as csv_file:

                writer = csv.DictWriter(

                    csv_file,

                    fieldnames=fieldnames,

                )

                writer.writeheader()

                while True:

                    success, frame = capture.read()

                    if not success:

                        break

                    frame_count += 1

                    # ----------------------------------------

                    # Zeitstempel

                    # ----------------------------------------

                    #

                    # detect_for_video erwartet Millisekunden.

                    # Die Werte müssen streng monoton steigen.

                    #

                    # Für die CSV wird zusätzlich die Zeit

                    # in Sekunden gespeichert.

                    # ----------------------------------------

                    timestamp_seconds = (

                        frame_count / fps

                    )

                    timestamp_ms = int(

                        timestamp_seconds * 1000

                    )

                    # ----------------------------------------

                    # OpenCV BGR -> RGB

                    # ----------------------------------------

                    rgb_frame = cv2.cvtColor(

                        frame,

                        cv2.COLOR_BGR2RGB,

                    )

                    rgb_frame = (

                        rgb_frame.copy()

                    )

                    # ----------------------------------------

                    # NumPy-Bild in MediaPipe Image umwandeln

                    # ----------------------------------------

                    mp_image = mp.Image(

                        image_format=mp.ImageFormat.SRGB,

                        data=rgb_frame,

                    )

                    # ----------------------------------------

                    # Pose-Erkennung für aktuellen Frame

                    # ----------------------------------------

                    result = (

                        pose_landmarker.detect_for_video(

                            mp_image,

                            timestamp_ms,

                        )

                    )

                    row = {

                        "Frame": frame_count,

                        "time": timestamp_seconds,

                    }

                    # ----------------------------------------

                    # World Landmarks auslesen

                    # ----------------------------------------

                    if (

                        result.pose_world_landmarks

                        and

                        len(result.pose_world_landmarks) > 0

                    ):

                        world_landmarks = (

                            result.pose_world_landmarks[0]

                        )

                        write_world_landmarks(

                            row,

                            world_landmarks,

                        )

                        detected_frames += 1

                    else:

                        write_empty_landmarks(row)

                        missing_frames += 1

                    writer.writerow(row)

                    # ----------------------------------------

                    # Fortschritt ausgeben

                    # ----------------------------------------

                    if frame_count % 100 == 0:

                        if total_frames > 0:

                            percentage = (

                                frame_count

                                / total_frames

                                * 100.0

                            )

                            print(

                                f"Verarbeitet: "

                                f"{frame_count}/"

                                f"{total_frames} "

                                f"({percentage:.1f} %)"

                            )

                        else:

                            print(

                                f"Verarbeitet: "

                                f"{frame_count} Frames"

                            )

    finally:

        capture.release()

    elapsed = time.time() - start_time

    # --------------------------------------------------------

    # Ergebnis

    # --------------------------------------------------------

    print("")

    print("==========================================")

    print("POSE-ERKENNUNG ABGESCHLOSSEN")

    print("==========================================")

    print(f"Gesamte Frames: {frame_count}")

    print(f"Frames mit Pose: {detected_frames}")

    print(f"Frames ohne Pose: {missing_frames}")

    if frame_count > 0:

        detection_rate = (

            detected_frames

            / frame_count

            * 100.0

        )

        print(

            f"Erkennungsrate: "

            f"{detection_rate:.2f} %"

        )

    print(

        f"Verarbeitungsdauer: "

        f"{elapsed:.2f} Sekunden"

    )

    print("CSV:")

    print(OUTPUT_FILE)

    print("==========================================")

    if frame_count == 0:

        raise RuntimeError(

            "Das Video enthielt keine lesbaren Frames."

        )

    if detected_frames == 0:

        raise RuntimeError(

            "Im gesamten Video wurde keine Pose erkannt."

        )

if __name__ == "__main__":

    main()