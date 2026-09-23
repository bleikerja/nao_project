import re
import cv2
import numpy as np
import pandas as pd
 
 
def generate_skeleton_video(csv_path, output_path="skelett_bewegung.mp4", fps=10):
    # 1. Daten einlesen
    df = pd.read_csv(csv_path)
 
    # Alle Spalten finden, die auf _X enden (z.B. Nase_X, l_Auge_X)
    x_cols = [c for c in df.columns if c.endswith("_X")]
    # Die dazugehörigen Basisnamen der Körperteile extrahieren (z.B. "Nase", "l_Auge")
    keypoints = [c[:-2] for c in x_cols]
 
    # Automatische Bestimmung der Videogröße basierend auf den maximalen Koordinaten
    max_x = int(df[[k + "_X" for k in keypoints]].max().max())
    max_y = int(df[[k + "_Y" for k in keypoints]].max().max())
 
    # Ein wenig Puffer hinzufügen, damit Punkte nicht am Rand kleben
    width = int(max_x + 50)
    height = int(max_y + 50)
 
    # 2. Definition der Verbindungen (Knochen) für das Skelett
    # Wir mappen hier die exakten Namen aus deiner CSV
    connections = [
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
 
    # 3. Video Writer aufsetzen
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    video = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
 
    print(f"Starte Video-Generierung ({width}x{height}px)...")
 
    # 4. Frames durchlaufen
    for idx, row in df.iterrows():
        # Schwarzer Hintergrund für jeden Frame
        frame_img = np.zeros((height, width, 3), dtype=np.uint8)
 
        # Wörterbuch für die aktuellen Koordinaten dieses Frames anlegen
        current_coords = {}
        for kp in keypoints:
            x = row[kp + "_X"]
            y = row[kp + "_Y"]
            if pd.notna(x) and pd.notna(y):
                current_coords[kp] = (int(x), int(y))
 
        # Zuerst Linien (Knochen) zeichnen, damit sie unter den Punkten liegen
        for kp1, kp2 in connections:
            if kp1 in current_coords and kp2 in current_coords:
                pt1 = current_coords[kp1]
                pt2 = current_coords[kp2]
                # Weiße Verbindungslinien mit Dicke 2
                cv2.line(frame_img, pt1, pt2, (255, 255, 255), 2)
 
        # Danach die Punkte (Gelenke) zeichnen
        for kp, pt in current_coords.items():
            # Gesichtspunkte bekommen eine andere Farbe als der Körper
            if kp in ["Nase", "l_Auge", "r_Auge", "l_Ohr", "r_Ohr"]:
                color = (0, 255, 255)  # Gelb für das Gesicht
                radius = 4
            else:
                color = (0, 255, 0)  # Grün für den restlichen Körper
                radius = 5
 
            cv2.circle(frame_img, pt, radius, color, thickness=-1)
 
        # Aktuelle Frame-Nummer oben links einblenden
        cv2.putText(
            frame_img,
            f"Frame: {int(row['Frame'])}",
            (10, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 165, 255),
            2,
        )
 
        # Frame ins Video schreiben
        video.write(frame_img)
 
    video.release()
    print(f"Fertig! Das Video wurde als '{output_path}' gespeichert.")
 
 
# Pfad zu deiner CSV-Datei angeben
generate_skeleton_video("../../generated/roboter_bewegungsdaten.csv", "skelett_bewegung.mp4", fps=15)