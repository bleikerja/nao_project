# -*- coding: utf-8 -*-
"""
Konvertiert MediaPipe-3D-Landmarks in NAO-Gelenkwinkel (Radiant).

Wichtig:
- Mensch und NAO haben unterschiedliche Kinematik. Deshalb werden Posen
  retargetet, nicht geometrisch 1:1 kopiert.
- Arme und Kopf werden aus den vorhandenen Landmark-Vektoren abgeleitet.
- Beine werden nur ausgegeben, wenn USE_LEGS=True. Das ist in StandInit
  absichtlich standardmaessig deaktiviert, weil freie Beinbewegungen ohne
  Balance-/Ganzkoerperregelung zum Sturz fuehren koennen.
- Hand/Finger koennen aus Pose-Landmarks nicht rekonstruiert werden.

Ausgabe ist fuer angleInterpolation(..., isAbsolute=True) bestimmt.
"""
import csv
import math
import os
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_CSV = os.path.abspath(os.path.join(
    SCRIPT_DIR, '..', '..', 'generated', 'roboter_bewegungsdaten_3d.csv'))
OUTPUT_CSV = os.path.abspath(os.path.join(
    SCRIPT_DIR, '..', '..', 'generated', 'nao_arm_paths.csv'))

SMOOTHING_ALPHA = 0.35
MIN_VISIBILITY = 0.50
USE_HEAD = True
USE_LEGS = False

# NAO-Gelenkgrenzen in Radiant, konservativ innerhalb der Hardwaregrenzen.
LIMITS = {
    'HeadYaw': (-2.00, 2.00),
    'HeadPitch': (-0.60, 0.45),
    'LShoulderPitch': (-2.00, 2.00),
    'LShoulderRoll': (-0.30, 1.25),
    'LElbowYaw': (-2.00, 2.00),
    'LElbowRoll': (-1.50, -0.05),
    'LWristYaw': (-1.70, 1.70),
    'RShoulderPitch': (-2.00, 2.00),
    'RShoulderRoll': (-1.25, 0.30),
    'RElbowYaw': (-2.00, 2.00),
    'RElbowRoll': (0.05, 1.50),
    'RWristYaw': (-1.70, 1.70),
    'LHipYawPitch': (-0.75, 0.45),
    'LHipRoll': (-0.35, 0.65),
    'LHipPitch': (-1.50, 0.45),
    'LKneePitch': (-0.05, 2.00),
    'LAnklePitch': (-1.00, 0.80),
    'LAnkleRoll': (-0.35, 0.35),
    'RHipYawPitch': (-0.75, 0.45),
    'RHipRoll': (-0.65, 0.35),
    'RHipPitch': (-1.50, 0.45),
    'RKneePitch': (-0.05, 2.00),
    'RAnklePitch': (-1.00, 0.80),
    'RAnkleRoll': (-0.35, 0.35),
}

# Maximale Geschwindigkeit, die wir beim Erzeugen der Bewegung zulassen.

# Bewusst konservativ gewählt, damit ALMotion noch Reserve hat.

MAX_VELOCITY = {
    'HeadYaw': 2.0,
    'HeadPitch': 2.0,
    'LShoulderPitch': 3.0,
    'LShoulderRoll': 3.0,
    'LElbowYaw': 4.0,
    'LElbowRoll': 3.0,
    'LWristYaw': 3.0,
    'RShoulderPitch': 3.0,
    'RShoulderRoll': 3.0,
    'RElbowYaw': 4.0,
    'RElbowRoll': 3.0,
    'RWristYaw': 3.0,
    'LHipYawPitch': 2.0,
    'LHipRoll': 2.0,
    'LHipPitch': 2.0,
    'LKneePitch': 2.0,
    'LAnklePitch': 2.0,
    'LAnkleRoll': 2.0,
    'RHipYawPitch': 2.0,
    'RHipRoll': 2.0,
    'RHipPitch': 2.0,
    'RKneePitch': 2.0,
    'RAnklePitch': 2.0,
    'RAnkleRoll': 2.0,
}

REQUIRED_POINTS = [
    'Nase', 'l_Ohr', 'r_Ohr',
    'LShoulderRoll', 'RShoulderRoll',
    'LElbowRoll', 'RElbowRoll', 'LWrist', 'RWrist',
    'LHipRoll', 'RHipRoll', 'LKnee', 'RKnee', 'LAnkle', 'RAnkle'
]

ARM_JOINTS = [
    'RShoulderPitch', 'RShoulderRoll', 'RElbowYaw', 'RElbowRoll', 'RWristYaw',
    'LShoulderPitch', 'LShoulderRoll', 'LElbowYaw', 'LElbowRoll', 'LWristYaw'
]
HEAD_JOINTS = ['HeadYaw', 'HeadPitch']
LEG_JOINTS = [
    'LHipYawPitch', 'LHipRoll', 'LHipPitch', 'LKneePitch',
    'LAnklePitch', 'LAnkleRoll',
    'RHipYawPitch', 'RHipRoll', 'RHipPitch', 'RKneePitch',
    'RAnklePitch', 'RAnkleRoll'
]


def f(value):
    try:
        if value is None or str(value).strip() == '':
            return np.nan
        return float(value)
    except (TypeError, ValueError):
        return np.nan


def point(row, name):
    return np.array([f(row.get(name + '_' + axis)) for axis in 'XYZ'], dtype=float)


def visibility(row, name):
    value = f(row.get(name + '_visibility'))
    return 1.0 if not np.isfinite(value) and name in ('Nase', 'l_Ohr', 'r_Ohr') else value


def unit(vector, fallback):
    length = np.linalg.norm(vector)
    if not np.isfinite(length) or length < 1e-8:
        return np.asarray(fallback, dtype=float)
    return vector / length


def interpolate(data):
    data = np.asarray(data, dtype=float).copy()
    idx = np.arange(len(data))
    for axis in range(3):
        valid = np.isfinite(data[:, axis])
        if not np.any(valid):
            raise RuntimeError('Keine gueltigen Werte fuer Landmark-Achse vorhanden.')
        data[:, axis] = np.interp(idx, idx[valid], data[valid, axis])
    return data


def smooth(data, alpha):
    result = np.asarray(data, dtype=float).copy()
    for i in range(1, len(result)):
        result[i] = alpha * result[i] + (1.0 - alpha) * result[i - 1]
    return result


def smooth_angles(values, alpha):
    result = np.asarray(values, dtype=float).copy()
    for i in range(1, len(result)):
        result[i] = alpha * result[i] + (1.0 - alpha) * result[i - 1]
    return result


def make_angles_continuous(values):
    """

    Entfernt Spruenge an der -pi/+pi-Grenze.

    Beispiel:

        3.10, -3.10

    wird intern zu:

        3.10, 3.18

    """

    values = np.asarray(values, dtype=float)

    return np.unwrap(values)


def limit_joint_velocity(name, values, time_values):
    """

    Begrenzt die Aenderung zwischen zwei Frames so, dass das Gelenk

    MAX_VELOCITY[name] nicht ueberschreitet.

    """

    result = np.asarray(values, dtype=float).copy()

    max_velocity = MAX_VELOCITY.get(name, 2.0)

    corrections = 0

    worst_velocity = 0.0

    for i in range(1, len(result)):

        dt = float(time_values[i] - time_values[i - 1])

        if dt <= 0:
            continue

        delta = result[i] - result[i - 1]

        velocity = abs(delta) / dt

        worst_velocity = max(worst_velocity, velocity)

        max_delta = max_velocity * dt

        if abs(delta) > max_delta:
            result[i] = result[i - 1] + np.sign(delta) * max_delta

            corrections += 1

    return result, corrections, worst_velocity


def angle_between(a, b):
    a = unit(a, [1.0, 0.0, 0.0])
    b = unit(b, [1.0, 0.0, 0.0])
    return math.acos(float(np.clip(np.dot(a, b), -1.0, 1.0)))


def clip(name, value):
    low, high = LIMITS[name]
    return float(np.clip(value, low, high))


def local_components(vector, forward, left, up):
    return np.array([
        np.dot(vector, forward),
        np.dot(vector, left),
        np.dot(vector, up)
    ], dtype=float)


def arm_angles(side, shoulder, elbow, wrist, forward, left, up):
    upper = local_components(elbow - shoulder, forward, left, up)
    lower = local_components(wrist - elbow, forward, left, up)

    # NAO ShoulderPitch: 0 = Arm nach vorn, +pi/2 = Arm nach unten.
    shoulder_pitch = math.atan2(-upper[2], upper[0])

    # Seitliche Abduktion. Rechte und linke NAO-Vorzeichen sind gespiegelt.
    horizontal = math.sqrt(upper[0] ** 2 + upper[2] ** 2)
    lateral = math.atan2(upper[1], max(horizontal, 1e-8))
    shoulder_roll = lateral if side == 'L' else lateral

    # Beugewinkel: gestreckter Arm -> 0, gebeugter Arm -> groesserer Betrag.
    flexion = angle_between(upper, lower)
    elbow_roll = -flexion if side == 'L' else flexion

    # Drehung des Unterarms um die Oberarmachse. Aus drei Punkten nur
    # angenaehert, da die Handflaechenorientierung fehlt.
    upper_u = unit(upper, [1.0, 0.0, 0.0])
    reference = np.cross(upper_u, np.array([0.0, 0.0, 1.0]))
    if np.linalg.norm(reference) < 1e-6:
        reference = np.cross(upper_u, np.array([0.0, 1.0, 0.0]))
    reference = unit(reference, [0.0, 1.0, 0.0])
    lower_plane = lower - np.dot(lower, upper_u) * upper_u
    lower_plane = unit(lower_plane, reference)
    elbow_yaw = math.atan2(
        np.dot(np.cross(reference, lower_plane), upper_u),
        np.dot(reference, lower_plane)
    )

    return {
        side + 'ShoulderPitch': shoulder_pitch,
        side + 'ShoulderRoll': shoulder_roll,
        side + 'ElbowYaw': 0.0,
        side + 'ElbowRoll': elbow_roll,
        side + 'WristYaw': 0.0,
    }


def head_angles(nose, left_ear, right_ear, forward, left, up):
    ear_center = (left_ear + right_ear) / 2.0
    face = local_components(nose - ear_center, forward, left, up)
    yaw = math.atan2(face[1], max(abs(face[0]), 1e-8))
    pitch = -math.atan2(face[2], max(abs(face[0]), 1e-8))
    return {'HeadYaw': clip('HeadYaw', yaw), 'HeadPitch': clip('HeadPitch', pitch)}


def leg_angles(side, hip, knee, ankle, forward, left, up):
    thigh = local_components(knee - hip, forward, left, up)
    shin = local_components(ankle - knee, forward, left, up)
    hip_pitch = math.atan2(thigh[0], max(-thigh[2], 1e-8))
    hip_roll = math.atan2(thigh[1], max(-thigh[2], 1e-8))
    knee_pitch = math.pi - angle_between(thigh, shin)
    ankle_pitch = -(hip_pitch + knee_pitch)
    ankle_roll = -hip_roll
    return {
        side + 'HipYawPitch': 0.0,
        side + 'HipRoll': clip(side + 'HipRoll', hip_roll),
        side + 'HipPitch': clip(side + 'HipPitch', hip_pitch),
        side + 'KneePitch': clip(side + 'KneePitch', knee_pitch),
        side + 'AnklePitch': clip(side + 'AnklePitch', ankle_pitch),
        side + 'AnkleRoll': clip(side + 'AnkleRoll', ankle_roll),
    }


def timestamps(rows):
    raw = np.array([f(row.get('time')) for row in rows], dtype=float)
    if not np.all(np.isfinite(raw)):
        raise RuntimeError("Ungueltige Zeitwerte.")
    if len(raw) > 1:
        positive = np.diff(raw)[np.diff(raw) > 0]
        if len(positive) == 0:
            raise RuntimeError("Zeitwerte sind nicht aufsteigend.")
        dt = float(np.median(positive))
    else:
        dt = 0.1
    result = raw - raw[0] + dt
    if np.any(np.diff(result) <= 0):
        raise RuntimeError("Zeitwerte muessen streng aufsteigend sein.")
    return result


def main():
    if not os.path.isfile(INPUT_CSV):
        raise RuntimeError('Eingabedatei nicht gefunden: ' + INPUT_CSV)
    with open(INPUT_CSV, 'r', newline='', encoding='utf-8') as file:
        rows = list(csv.DictReader(file))
    if not rows:
        raise RuntimeError('Keine Eingabedaten vorhanden.')

    time_values = timestamps(rows)
    series = {}
    for name in REQUIRED_POINTS:
        values = []
        for row in rows:
            p = point(row, name)
            if not np.isfinite(visibility(row, name)) or visibility(row, name) < MIN_VISIBILITY:
                p[:] = np.nan
            values.append(p)
        series[name] = smooth(interpolate(values), SMOOTHING_ALPHA)

    output_joints = list(ARM_JOINTS)
    if USE_HEAD:
        output_joints = HEAD_JOINTS + output_joints
    if USE_LEGS:
        output_joints += LEG_JOINTS

    values = {name: [] for name in output_joints}
    prev_forward = np.array([0.0, 0.0, -1.0])
    prev_left = np.array([-1.0, 0.0, 0.0])
    prev_up = np.array([0.0, -1.0, 0.0])

    for i in range(len(rows)):
        ls, rs = series['LShoulderRoll'][i], series['RShoulderRoll'][i]
        lh, rh = series['LHipRoll'][i], series['RHipRoll'][i]
        shoulder_center = (ls + rs) / 2.0
        hip_center = (lh + rh) / 2.0
        up = unit(shoulder_center - hip_center, prev_up)
        left = unit(ls - rs, prev_left)
        forward = unit(np.cross(left, up), prev_forward)
        if np.dot(forward, np.array([0.0, 0.0, -1.0])) < 0:
            forward = -forward
        left = unit(np.cross(up, forward), prev_left)
        prev_forward, prev_left, prev_up = forward, left, up

        frame = {}
        frame.update(arm_angles('R', rs, series['RElbowRoll'][i],
                                series['RWrist'][i], forward, left, up))
        frame.update(arm_angles('L', ls, series['LElbowRoll'][i],
                                series['LWrist'][i], forward, left, up))
        if USE_HEAD:
            frame.update(head_angles(series['Nase'][i], series['l_Ohr'][i],
                                     series['r_Ohr'][i], forward, left, up))
        if USE_LEGS:
            frame.update(leg_angles('L', lh, series['LKnee'][i],
                                    series['LAnkle'][i], forward, left, up))
            frame.update(leg_angles('R', rh, series['RKnee'][i],
                                    series['RAnkle'][i], forward, left, up))
        for name in output_joints:
            values[name].append(frame[name])
    # smoothing
    print()

    print('=== MOTION DIAGNOSE ===')

    for name in output_joints:
        # 1. Winkelspruenge wie +pi -> -pi aufloesen
        joint_values = make_angles_continuous(values[name])
        # 2. Winkel glaetten
        joint_values = smooth_angles(
            joint_values,
            SMOOTHING_ALPHA
        )
        # 3. Auf erlaubten NAO-Winkelbereich begrenzen
        low, high = LIMITS[name]
        joint_values = np.clip(
            joint_values,
            low,
            high
        )
        # 4. Geschwindigkeit begrenzen
        joint_values, corrections, worst_velocity = limit_joint_velocity(
            name,
            joint_values,
            time_values
        )
        # 5. Nach der Geschwindigkeitsbegrenzung nochmals sicherstellen,
        #    dass kein Gelenklimit verletzt wird.
        joint_values = np.clip(
            joint_values,
            low,
            high
        )
        values[name] = joint_values
        print()
        print(name)
        print('  min: %.3f rad' % np.min(joint_values))
        print('  max: %.3f rad' % np.max(joint_values))
        print('  Geschwindigkeit vor Begrenzung: war'
              '%.3f rad/s' % worst_velocity)
        print('  Limit: %.3f rad/s' % MAX_VELOCITY.get(name, 2.0))
        print('  Korrigierte Frames:', corrections)

    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['time'] + output_joints)
        for i, timestamp in enumerate(time_values):
            writer.writerow([timestamp] + [values[name][i] for name in output_joints])

    print('Gelenkwinkel-CSV gespeichert:', OUTPUT_CSV)
    print('Frames:', len(rows), 'Dauer:', time_values[-1], 'Sekunden')
    print('Ausgegebene Gelenke:', ', '.join(output_joints))
    if not USE_LEGS:
        print('HINWEIS: Beine sind aus Sicherheitsgruenden deaktiviert (USE_LEGS=False).')
    print('HINWEIS: WristYaw bleibt 0, solange keine Hand-Landmarks vorliegen.')


if __name__ == '__main__':
    main()
