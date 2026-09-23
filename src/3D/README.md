### Proportionale 1:1-Übertragung

Die 3D-Pipeline verwendet jetzt ein kinematisches Retargeting statt die menschlichen Winkel direkt als NAO-Winkel zu behandeln.

Ablauf:

```text
3D-Landmarks
→ normalisierte Körpersegmentrichtungen
→ NAO-Gelenkorientierungen
→ NAO-Gelenkgrenzen
→ zeitliche Glättung
→ ALMotion
```

Die menschlichen und NAO-Gliedmaßen dürfen dadurch unterschiedliche Längen haben. Übertragen werden Bewegungsrichtung und Gelenkorientierung, nicht absolute Koordinaten. Das ist die sinnvolle Bedeutung von proportionaler 1:1-Übertragung bei unterschiedlichen Körperproportionen.

Ausführung auf Python 3:

```bash
cd src/3D
python 2_coordinates_to_angle_3d.py
```

Ausführung mit Python 2.7/NAOqi:

```bash
set NAO_IP=192.168.200.74
set NAO_PORT=9559
python 3_nao_make_moves_3d.py
```

Vor dem echten Roboterlauf:

1. mit Choregraphe oder angehobenen Roboterfüßen testen;
2. prüfen, ob links/rechts und Vorwärtsrichtung korrekt sind;
3. Gelenkgrenzen für das konkrete NAO-Modell validieren;
4. zunächst `setAngles` mit niedriger Geschwindigkeit verwenden;
5. eine Not-Aus-Möglichkeit bereithalten.

Die monokulare MediaPipe-Z-Tiefe bleibt eine Schätzung. Eine geometrisch exakte 1:1-Reproduktion ist mit der eingebauten RGB-Kamera nicht garantierbar.
