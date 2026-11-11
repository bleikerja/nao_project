# -*- coding: utf-8 -*-
"""Konvertiert MediaPipe-3D-Koordinaten in sichere NAO-Handtrajektorien."""

import csv
import os

import numpy as np


# ============================================================
# DATEIPFADE
# ============================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

INPUT_CSV = os.path.abspath(
    os.path.join(
        SCRIPT_DIR, '..', '..', 'generated',
        'roboter_bewegungsdaten_3d.csv'
    )
)

OUTPUT_CSV = os.path.abspath(
    os.path.join(
        SCRIPT_DIR, '..', '..', 'generated',
        'nao_arm_paths.csv'
    )
)


# ============================================================
# PARAMETER
# ============================================================

NAO_SCHULTERABSTAND = 0.20
SMOOTHING_ALPHA = 0.35
CALIBRATION_FRAMES = 30
MIN_VISIBILITY = 0.50

# Konservative kartesische Arbeitsbereiche relativ zu FRAME_TORSO.
RIGHT_LIMITS = {
    'x': (0.08, 0.30),
    'y': (-0.30, 0.05),
    'z': (-0.05, 0.35),
}

LEFT_LIMITS = {
    'x': (0.08, 0.30),
    'y': (-0.05, 0.30),
    'z': (-0.05, 0.35),
}

REQUIRED_POINTS = [
    'LShoulderRoll', 'RShoulderRoll',
    'LHipRoll', 'RHipRoll',
    'LWrist', 'RWrist',
]


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def float_or_nan(value):
    try:
        if value is None or str(value).strip() == '':
            return np.nan
        return float(value)
    except (TypeError, ValueError):
        return np.nan


def point_from_row(row, prefix):
    """Liest einen 3D-Punkt; fehlende Werte werden zu NaN."""
    return np.array([
        float_or_nan(row.get(prefix + '_X')),
        float_or_nan(row.get(prefix + '_Y')),
        float_or_nan(row.get(prefix + '_Z')),
    ], dtype=float)


def visibility_from_row(row, prefix):
    return float_or_nan(row.get(prefix + '_visibility'))


def normalize(vector, fallback=None):
    length = np.linalg.norm(vector)
    if not np.isfinite(length) or length < 1e-8:
        if fallback is None:
            return np.zeros(3, dtype=float)
        return np.asarray(fallback, dtype=float)
    return vector / length


def interpolate_points(points):
    """Interpoliert fehlende Werte je Koordinatenachse linear."""
    points = np.asarray(points, dtype=float).copy()
    indices = np.arange(len(points))

    for axis in range(3):
        values = points[:, axis]
        valid = np.isfinite(values)

        if not np.any(valid):
            raise RuntimeError(
                "Eine komplette Koordinatenachse enthaelt keine gueltigen Werte."
            )

        points[:, axis] = np.interp(
            indices,
            indices[valid],
            values[valid]
        )

    return points


def smooth_points(points, alpha):
    """Exponentielle Glaettung einer Punktfolge."""
    if len(points) == 0:
        return points

    result = np.zeros_like(points, dtype=float)
    result[0] = points[0]

    for index in range(1, len(points)):
        result[index] = (
            alpha * points[index]
            + (1.0 - alpha) * result[index - 1]
        )

    return result


def clip_point(point, limits):
    return np.array([
        np.clip(point[0], *limits['x']),
        np.clip(point[1], *limits['y']),
        np.clip(point[2], *limits['z']),
    ], dtype=float)


def prepare_timestamps(rows):
    """Uebernimmt echte Videozeit und macht den ersten Wert positiv."""
    raw_times = np.array(
        [float_or_nan(row.get('time')) for row in rows],
        dtype=float
    )

    if not np.all(np.isfinite(raw_times)):
        raise RuntimeError(
            "Die Eingabe-CSV enthaelt fehlende oder ungueltige Zeitwerte."
        )

    if len(raw_times) > 1:
        differences = np.diff(raw_times)
        positive_differences = differences[differences > 0]
        if len(positive_differences) == 0:
            raise RuntimeError("Die Zeitwerte sind nicht aufsteigend.")
        frame_duration = float(np.median(positive_differences))
    else:
        frame_duration = 0.1

    times = raw_times - raw_times[0] + frame_duration

    if np.any(np.diff(times) <= 0):
        raise RuntimeError("Die Zeitwerte muessen streng aufsteigend sein.")

    return times


# ============================================================
# HAUPTPROGRAMM
# ============================================================

def main():
    print("Lese Eingabedatei:")
    print(INPUT_CSV)

    if not os.path.isfile(INPUT_CSV):
        raise RuntimeError("Eingabedatei nicht gefunden: " + INPUT_CSV)

    with open(INPUT_CSV, 'r', newline='', encoding='utf-8') as csv_file:
        rows = list(csv.DictReader(csv_file))

    if not rows:
        raise RuntimeError("Die Eingabe-CSV enthaelt keine Daten.")

    print("Anzahl Frames:", len(rows))
    times = prepare_timestamps(rows)

    point_series = {}
    for point_name in REQUIRED_POINTS:
        series = []
        for row in rows:
            point = point_from_row(row, point_name)
            visibility = visibility_from_row(row, point_name)

            # Unsichere Landmark-Messungen ebenfalls interpolieren.
            if not np.isfinite(visibility) or visibility < MIN_VISIBILITY:
                point[:] = np.nan

            series.append(point)

        series = interpolate_points(np.array(series, dtype=float))
        point_series[point_name] = smooth_points(series, SMOOTHING_ALPHA)

    left_shoulder = point_series['LShoulderRoll']
    right_shoulder = point_series['RShoulderRoll']
    left_hip = point_series['LHipRoll']
    right_hip = point_series['RHipRoll']
    left_wrist = point_series['LWrist']
    right_wrist = point_series['RWrist']

    calibration_count = min(CALIBRATION_FRAMES, len(rows))
    shoulder_distances = np.linalg.norm(
        left_shoulder[:calibration_count]
        - right_shoulder[:calibration_count],
        axis=1
    )
    shoulder_distances = shoulder_distances[
        np.isfinite(shoulder_distances) & (shoulder_distances > 1e-6)
    ]

    if len(shoulder_distances) == 0:
        raise RuntimeError("Kein gueltiger Schulterabstand bestimmbar.")

    mp_shoulder_distance = float(np.median(shoulder_distances))
    scale = NAO_SCHULTERABSTAND / mp_shoulder_distance

    print("MediaPipe-Schulterabstand (Median):", mp_shoulder_distance)
    print("NAO-Schulterabstand:", NAO_SCHULTERABSTAND)
    print("Skalierung:", scale)

    right_path = []
    left_path = []

    previous_up = np.array([0.0, -1.0, 0.0])
    previous_left = np.array([1.0, 0.0, 0.0])
    previous_forward = np.array([0.0, 0.0, -1.0])
    mediapipe_forward_reference = np.array([0.0, 0.0, -1.0])

    for index in range(len(rows)):
        l_shoulder = left_shoulder[index]
        r_shoulder = right_shoulder[index]
        l_hip = left_hip[index]
        r_hip = right_hip[index]

        shoulder_center = (l_shoulder + r_shoulder) / 2.0
        hip_center = (l_hip + r_hip) / 2.0

        up_axis = normalize(
            shoulder_center - hip_center,
            fallback=previous_up
        )
        left_axis = normalize(
            l_shoulder - r_shoulder,
            fallback=previous_left
        )
        forward_axis = normalize(
            np.cross(left_axis, up_axis),
            fallback=previous_forward
        )

        # Einheitliche Vorwaertsrichtung erzwingen.
        if np.dot(forward_axis, mediapipe_forward_reference) < 0:
            forward_axis = -forward_axis

        left_axis = normalize(
            np.cross(up_axis, forward_axis),
            fallback=previous_left
        )

        previous_up = up_axis
        previous_left = left_axis
        previous_forward = forward_axis

        right_arm = right_wrist[index] - r_shoulder
        left_arm = left_wrist[index] - l_shoulder

        human_right = np.array([
            np.dot(right_arm, forward_axis),
            np.dot(right_arm, left_axis),
            np.dot(right_arm, up_axis),
        ])
        human_left = np.array([
            np.dot(left_arm, forward_axis),
            np.dot(left_arm, left_axis),
            np.dot(left_arm, up_axis),
        ])

        nao_right = np.array([0.16, -0.10, 0.10]) + human_right * scale
        nao_left = np.array([0.16, 0.10, 0.10]) + human_left * scale

        nao_right = clip_point(nao_right, RIGHT_LIMITS)
        nao_left = clip_point(nao_left, LEFT_LIMITS)

        # Rotation bleibt ungenutzt, weil das Ausfuehrungsskript axisMask 7 nutzt.
        right_path.append([
            nao_right[0], nao_right[1], nao_right[2], 0.0, 0.0, 0.0
        ])
        left_path.append([
            nao_left[0], nao_left[1], nao_left[2], 0.0, 0.0, 0.0
        ])

    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)

    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow([
            'time',
            'R_X', 'R_Y', 'R_Z', 'R_WX', 'R_WY', 'R_WZ',
            'L_X', 'L_Y', 'L_Z', 'L_WX', 'L_WY', 'L_WZ'
        ])

        for index, timestamp in enumerate(times):
            writer.writerow(
                [timestamp]
                + right_path[index]
                + left_path[index]
            )

    right_array = np.asarray(right_path)
    left_array = np.asarray(left_path)

    print("")
    print("==========================================")
    print("BERECHNUNG ABGESCHLOSSEN")
    print("==========================================")
    print("Frames:", len(times))
    print("Dauer:", times[-1], "Sekunden")
    print("Rechter Arm X/Y/Z min:", np.min(right_array[:, :3], axis=0))
    print("Rechter Arm X/Y/Z max:", np.max(right_array[:, :3], axis=0))
    print("Linker Arm X/Y/Z min:", np.min(left_array[:, :3], axis=0))
    print("Linker Arm X/Y/Z max:", np.max(left_array[:, :3], axis=0))
    print("Gespeichert:", OUTPUT_CSV)
    print("==========================================")


if __name__ == '__main__':
    main()
