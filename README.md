### Ablaufdiagramm des Programms

1. `nao-video-record.py` nimmt ein Video mit der NAO-Kamera auf.
2. `src/3D/1_detect_points_3d.py` erkennt die Person und schreibt relative 3D-Landmarks.
3. `src/3D/2_coordinates_to_angle_3d.py` berechnet Winkel aus den 3D-Punkten.
4. Die Winkel werden anschließend auf die NAO-Gelenke retargetiert.

### 3D-Hinweis

Die eingebaute NAO-Kamera ist eine normale RGB-Kamera und misst keine Tiefe. Das Projekt verwendet deshalb MediaPipe Pose als monokulares 3D-Pose-Lifting-Modell. Die Spalten `_X`, `_Y` und `_Z` in `generated/roboter_bewegungsdaten_3d.csv` sind eine relative 3D-Schätzung in Metern, bezogen auf den menschlichen Körper, keine absoluten Tiefenmessungen.

Der bisherige YOLO-Wert in `_Z` war nur eine Konfidenz. Er wird im neuen 3D-Skript nicht mehr als Tiefe verwendet; die Konfidenz steht in einer separaten `_visibility`-Spalte.

Installation auf dem Rechner, der das Video verarbeitet:

```bash
pip install mediapipe opencv-python numpy
```

Ausführung aus `src/3D`:

```bash
python 1_detect_points_3d.py
python 2_coordinates_to_angle_3d.py
```

Die Verarbeitung sollte auf einem PC erfolgen. Der NAO liefert das Video und erhält danach die retargetierten Winkel. Vor der Ausführung am Roboter müssen zusätzlich Kamera-/Körperkoordinatensystem, Gelenkgrenzen, Spiegelung und Glättung kalibriert werden.
