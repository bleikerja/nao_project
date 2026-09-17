import cv2
import pandas as pd
from ultralytics import YOLO
import time

# 1. Kompaktes YOLO-Pose Modell laden (Nano-Version)
# Das 'n' Modell ist extrem leichtgewichtig und ideal für die CPU-Nutzung optimiert.
print("Lade YOLOv8-Pose Modell...")
model = YOLO('yolov8n-pose.pt')

# 2. Ihr aufgenommenes Video laden
video_path = "downloaded_video_2_hell.avi"  # Hier den Pfad zu Ihrem Video eintragen
cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS)
print(fps)

# Namensliste der 17 Keypoints (Standard COCO-Format von YOLO)
KEYPOINT_NAMES = [
    "Nase", "l_Auge", "r_Auge", "l_Ohr", "r_Ohr",
    "LShoulderRoll", "RShoulderRoll", "LElbowRoll", "RElbowRoll",
    "LWrist", "RWrist", "LHipRoll", "RHipRoll",
    "LKnee", "RKnee", "LAnkle", "RAnkle"
]

all_frames_data = []
frame_count = 0

print(f"Starte Videoanalyse auf der CPU für: {video_path}")
start_time = time.time()

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    frame_count += 1
    
    # 3. KI-Erkennung explizit auf der CPU ausführen
    # device='cpu' erzwingt die Ausführung ohne Grafikkarte.
    results = model(frame, device='cpu', verbose=False)

    for result in results:
        # Prüfen, ob eine Person im Frame gefunden wurde
        if result.keypoints is not None and len(result.keypoints.xy) > 0:
            # Holt die 2D-Pixelkoordinaten [X, Y] der Gelenke der ersten erkannten Person
            joints = result.keypoints.xy[0].cpu().numpy() 
            
            # Zeilen-Dictionary für diesen Frame erstellen
            frame_row = {"Frame": frame_count}
            
            # Koordinaten für jedes Gelenk in die Zeile eintragen
            for idx, name in enumerate(KEYPOINT_NAMES):
                if idx < len(joints):
                    frame_row[f"{name}_X"] = int(joints[idx][0])
                    frame_row[f"{name}_Y"] = int(joints[idx][1])
                else:
                    # Falls ein Gelenk nicht im Bild ist, wird es mit 0 markiert
                    frame_row[f"{name}_X"] = 0
                    frame_row[f"{name}_Y"] = 0
            
            all_frames_data.append(frame_row)

cap.release()

# 4. Daten in eine übersichtliche CSV-Struktur bringen und speichern
if all_frames_data:
    df = pd.DataFrame(all_frames_data)
    output_file = "roboter_bewegungsdaten.csv"
    df.to_csv(output_file, index=False)
    
    elapsed_time = time.time() - start_time
    print(f"\nErfolgreich beendet!")
    print(f"{frame_count} Frames in {elapsed_time:.2f} Sekunden auf der CPU verarbeitet.")
    print(f"Datei gespeichert unter: {output_file}")
else:
    print("Es wurden keine Personen oder Bewegungsdaten im Video gefunden.")