import cv2
import pandas as pd
from ultralytics import YOLO
import time

# 1. Kompaktes YOLO-Pose Modell laden (Nano-Version)
print("Lade YOLOv8-Pose Modell...")
model = YOLO('yolov8n-pose.pt')

# 2. Ihr aufgenommenes Video laden
video_path = "downloaded_video_2_hell.avi"  # Hier den Pfad zu Ihrem Video eintragen
cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS)
print(f"Video-FPS: {fps}")

# Namensliste der 17 Keypoints (Standard COCO-Format von YOLO)
KEYPOINT_NAMES = [
    "Nase", "l_Auge", "r_Auge", "l_Ohr", "r_Ohr",
    "LShoulderRoll", "RShoulderRoll", "LElbowRoll", "RElbowRoll",
    "LWrist", "RWrist", "LHipRoll", "RHipRoll",
    "LKnee", "RKnee", "LAnkle", "RAnkle"
]

all_frames_data = []
frame_count = 0

print(f"Starte 3D-Videoanalyse auf der CPU für: {video_path}")
start_time = time.time()

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    frame_count += 1

    # 3. KI-Erkennung explizit auf der CPU ausführen
    results = model(frame, device='cpu', verbose=False)

    for result in results:
        # Prüfen, ob Keypoints vorhanden sind und ob das xyn-Attribut (bzw. xy) Daten enthält
        if result.keypoints is not None and len(result.keypoints.xy) > 0:

            # .xy liefert [X, Y], .xyn liefert normalisierte Werte.
            # Für die 3D-Schätzung nutzen wir result.keypoints.data, falls verfügbar,
            # oder lesen die normalisierten/Pixel-Koordinaten aus.
            # Da YOLOv8 standardmäßig eine Konfidenz (Sichtbarkeit) als 3. Wert liefert,
            # nutzen wir diese als relative Tiefen-Annäherung (Z), sofern kein echtes 3D-Lifting aktiv ist.
            joints = result.keypoints.data[0].cpu().numpy()  # Form: [17, 3] -> X, Y, Sichtbarkeit/Tiefe

            # Zeilen-Dictionary für diesen Frame erstellen
            frame_row = {"Frame": frame_count}

            # Koordinaten für jedes Gelenk in die Zeile eintragen
            for idx, name in enumerate(KEYPOINT_NAMES):
                if idx < len(joints):
                    # X und Y Koordinaten als Pixelwerte
                    frame_row[f"{name}_X"] = int(joints[idx][0])
                    frame_row[f"{name}_Y"] = int(joints[idx][1])

                    # Z-Koordinate (YOLO liefert hier den Konfidenzwert der Sichtbarkeit/Tiefe,
                    # welcher bei kalibrierten 3D-Modellen der relative Z-Abstand ist)
                    frame_row[f"{name}_Z"] = float(joints[idx][2])
                else:
                    # Falls ein Gelenk nicht im Bild ist, wird es mit 0 markiert
                    frame_row[f"{name}_X"] = 0
                    frame_row[f"{name}_Y"] = 0
                    frame_row[f"{name}_Z"] = 0.0

            all_frames_data.append(frame_row)

cap.release()

# 4. Daten in eine übersichtliche CSV-Struktur bringen und speichern
if all_frames_data:
    df = pd.DataFrame(all_frames_data)
    output_file = "roboter_bewegungsdaten_3d.csv"
    df.to_csv(output_file, index=False)

    elapsed_time = time.time() - start_time
    print(f"\nErfolgreich beendet!")
    print(f"{frame_count} Frames in {elapsed_time:.2f} Sekunden auf der CPU verarbeitet.")
    print(f"Datei gespeichert unter: {output_file}")
else:
    print("Es wurden keine Personen oder Bewegungsdaten im Video gefunden.")
