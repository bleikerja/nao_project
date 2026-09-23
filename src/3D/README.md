### 3D-CSV als Video darstellen

Nach der Erzeugung der CSV kann daraus ein Video mit drei Ansichten erzeugt werden:

```bash
cd src/3D
python 3_visualize_3d_csv.py
```

Das Ergebnis wird unter `generated/skelett_3d.csv.mp4` gespeichert:

- **Frontansicht:** X/Y
- **Seitenansicht:** Z/Y; hier ist die geschätzte Bewegung in der Tiefe sichtbar
- **Schrägansicht:** kombinierte X/Y/Z-Darstellung

Die Visualisierung verwendet die relativen MediaPipe-3D-Landmarks aus `roboter_bewegungsdaten_3d.csv`. Sie zeigt keine absolute Entfernung zur NAO-Kamera.
