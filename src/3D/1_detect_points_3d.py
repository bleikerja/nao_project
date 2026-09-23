import csv
import time
from pathlib import Path

import cv2
import mediapipe as mp


VIDEO_PATH = "../../example-data/downloaded_video_1_hell.avi"
OUTPUT_FILE = "../../generated/roboter_bewegungsdaten_1_3d.csv"

# MediaPipe Pose liefert 33 Landmarks. Diese Namen werden auf die im Projekt
# verwendeten Namen abgebildet.
LANDMARK_MAP = {
    "Nase": mp.solutions.pose.PoseLandmark.NOSE,
    "l_Auge": mp.solutions.pose.PoseLandmark.LEFT_EYE,
    "r_Auge": mp.solutions.pose.PoseLandmark.RIGHT_EYE,
    "l_Ohr": mp.solutions.pose.PoseLandmark.LEFT_EAR,
    "r_Ohr": mp.solutions.pose.PoseLandmark.RIGHT_EAR,
    "LShoulderRoll": mp.solutions.pose.PoseLandmark.LEFT_SHOULDER,
    "RShoulderRoll": mp.solutions.pose.PoseLandmark.RIGHT_SHOULDER,
    "LElbowRoll": mp.solutions.pose.PoseLandmark.LEFT_ELBOW,
    "RElbowRoll": mp.solutions.pose.PoseLandmark.RIGHT_ELBOW,
    "LWrist": mp.solutions.pose.PoseLandmark.LEFT_WRIST,
    "RWrist": mp.solutions.pose.PoseLandmark.RIGHT_WRIST,
    "LHipRoll": mp.solutions.pose.PoseLandmark.LEFT_HIP,
    "RHipRoll": mp.solutions.pose.PoseLandmark.RIGHT_HIP,
    "LKnee": mp.solutions.pose.PoseLandmark.LEFT_KNEE,
    "RKnee": mp.solutions.pose.PoseLandmark.RIGHT_KNEE,
    "LAnkle": mp.solutions.pose.PoseLandmark.LEFT_ANKLE,
    "RAnkle": mp.solutions.pose.PoseLandmark.RIGHT_ANKLE,
}


def main():
    video_path = Path(VIDEO_PATH)
    output_path = Path(OUTPUT_FILE)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Video konnte nicht geöffnet werden: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 10.0
    fieldnames = ["Frame"]
    for name in LANDMARK_MAP:
        fieldnames.extend([f"{name}_X", f"{name}_Y", f"{name}_Z", f"{name}_visibility"])

    frame_count = 0
    written_frames = 0
    start_time = time.time()

    # model_complexity=2 ist genauer, aber langsamer. Die Verarbeitung sollte
    # auf einem Rechner erfolgen; der NAO liefert nur den Videostream.
    with mp.solutions.pose.Pose(
        static_image_mode=False,
        model_complexity=2,
        smooth_landmarks=True,
        enable_segmentation=False,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6,
    ) as pose, open(output_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        while True:
            success, frame = cap.read()
            if not success:
                break

            frame_count += 1
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = pose.process(rgb_frame)
            row = {"Frame": frame_count}

            if result.pose_world_landmarks:
                landmarks = result.pose_world_landmarks.landmark
                for name, landmark_id in LANDMARK_MAP.items():
                    landmark = landmarks[landmark_id.value]
                    # MediaPipe world landmarks sind eine relative 3D-Schätzung
                    # in Metern, bezogen auf die Körpermitte (Hüfte). Sie sind
                    # keine gemessenen absoluten Weltkoordinaten.
                    row[f"{name}_X"] = landmark.x
                    row[f"{name}_Y"] = landmark.y
                    row[f"{name}_Z"] = landmark.z
                    row[f"{name}_visibility"] = landmark.visibility
                written_frames += 1
            else:
                for name in LANDMARK_MAP:
                    row[f"{name}_X"] = ""
                    row[f"{name}_Y"] = ""
                    row[f"{name}_Z"] = ""
                    row[f"{name}_visibility"] = 0.0

            writer.writerow(row)

    cap.release()
    elapsed = time.time() - start_time
    print(f"{written_frames}/{frame_count} Frames mit 3D-Pose gespeichert.")
    print(f"CSV: {output_path} | Video-FPS: {fps:.2f} | Dauer: {elapsed:.2f}s")


if __name__ == "__main__":
    main()
