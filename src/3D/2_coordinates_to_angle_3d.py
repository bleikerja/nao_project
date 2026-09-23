import csv
import math
from pathlib import Path

import numpy as np


INPUT_FILE = Path("../../generated/roboter_bewegungsdaten_3d.csv")
OUTPUT_FILE = Path("../../generated/nao_angles_3d.csv")
MIN_VISIBILITY = 0.6
SMOOTHING = 0.35

def calculate_angle(a:tuple[int,int,int], b:tuple[int,int,int], c:tuple[int,int,int], negate = True) -> float:
    vector_ba = np.array([a[0] - b[0], a[1] - b[1], a[2] - b[2]])
    vector_bc = np.array([c[0] - b[0], c[1] - b[1], c[2] - b[2]])

    cos = np.dot(vector_ba, vector_bc) / (np.linalg.norm(vector_ba) * np.linalg.norm(vector_bc))
    return normalize_angle((-1 if negate else 1) * (math.pi - math.acos(cos)))

def normalize(vector):
    length = np.linalg.norm(vector)
    if length < 1e-8:
        return None
    return vector / length


def signed_angle(first, second, axis):
    """Signed angle from first to second around axis, in radians."""
    first = normalize(first)
    second = normalize(second)
    axis = normalize(axis)
    if first is None or second is None or axis is None:
        return None

    sine = np.dot(axis, np.cross(first, second))
    cosine = np.clip(np.dot(first, second), -1.0, 1.0)
    return math.atan2(float(sine), float(cosine))


def clamp(value, lower, upper):
    return max(lower, min(upper, value))


def read_point(row, name):
    values = np.asarray(
        [float(row["{}_{}".format(name, axis)]) for axis in "XYZ"], dtype=float
    )
    visibility = float(row.get("{}_visibility".format(name), 1.0) or 0.0)
    if not np.all(np.isfinite(values)) or visibility < MIN_VISIBILITY:
        return None
    return values


def calculate_angles(points):
    """Create NAO joint targets from normalized 3D human segment directions."""
    required = [
        "LShoulderRoll", "RShoulderRoll", "LElbowRoll", "RElbowRoll",
        "LWrist", "RWrist", "LHipRoll", "RHipRoll", "LKnee", "RKnee",
        "LAnkle", "RAnkle",
    ]
    if any(name not in points for name in required):
        return None

    left_shoulder = points["LShoulderRoll"]
    right_shoulder = points["RShoulderRoll"]
    left_hip = points["LHipRoll"]
    right_hip = points["RHipRoll"]
    torso_x = normalize(right_shoulder - left_shoulder)
    torso_y = normalize((left_shoulder + right_shoulder) / 2.0 - (left_hip + right_hip) / 2.0)
    if torso_x is None or torso_y is None:
        return None

    # Camera/world-independent body basis. The cross product defines the
    # forward/backward direction, which preserves the estimated depth motion.
    torso_z = normalize(np.cross(torso_x, torso_y))
    if torso_z is None:
        return None

    # Re-orthogonalize to avoid noisy MediaPipe landmarks.
    torso_y = normalize(np.cross(torso_z, torso_x))
    if torso_y is None:
        return None

    result = {}
    for side, shoulder_name, elbow_name, wrist_name, sign in (
        ("L", "LShoulderRoll", "LElbowRoll", "LWrist", 1.0),
        ("R", "RShoulderRoll", "RElbowRoll", "RWrist", -1.0),
    ):
        shoulder = points[shoulder_name]
        elbow = points[elbow_name]
        wrist = points[wrist_name]
        upper_arm = normalize(elbow - shoulder)
        forearm = normalize(wrist - elbow)
        if upper_arm is None or forearm is None:
            return None

        # ShoulderPitch: forward/backward movement in the torso sagittal plane.
        pitch = math.atan2(np.dot(upper_arm, torso_z), np.dot(upper_arm, torso_y))
        # ShoulderRoll: lateral movement relative to the torso.
        roll = math.asin(clamp(float(np.dot(upper_arm, torso_x) * sign), -1.0, 1.0))
        # ElbowRoll is the 3D flexion angle; the side sign matches NAO's joint
        # convention and is corrected again by the configured limits.
        elbow_angle = math.acos(clamp(float(np.dot(-upper_arm, forearm)), -1.0, 1.0))
        result["{}ShoulderPitch".format(side)] = pitch
        result["{}ShoulderRoll".format(side)] = sign * roll
        result["{}ElbowRoll".format(side)] = sign * (math.pi - elbow_angle)

    # Hip and knee pitch are included so leg movement can be transferred too.
    for side, hip_name, knee_name, ankle_name, sign in (
        ("L", "LHipRoll", "LKnee", "LAnkle", 1.0),
        ("R", "RHipRoll", "RKnee", "RAnkle", -1.0),
    ):
        thigh = normalize(points[knee_name] - points[hip_name])
        shin = normalize(points[ankle_name] - points[knee_name])
        if thigh is None or shin is None:
            return None
        result["{}HipPitch".format(side)] = math.atan2(
            np.dot(thigh, torso_z), np.dot(thigh, -torso_y)
        )
        result["{}HipRoll".format(side)] = sign * math.asin(
            clamp(float(np.dot(thigh, torso_x)), -1.0, 1.0)
        )
        result["{}KneePitch".format(side)] = math.acos(
            clamp(float(np.dot(-thigh, shin)), -1.0, 1.0)
        )

    return result


# Conservative NAO limits in radians. They are intentionally narrower than
# theoretical limits; verify them against the exact NAO model before use.
LIMITS = {
    "LShoulderPitch": (-2.0, 2.0), "RShoulderPitch": (-2.0, 2.0),
    "LShoulderRoll": (0.0, 1.3), "RShoulderRoll": (-1.3, 0.0),
    "LElbowRoll": (-1.5, -0.05), "RElbowRoll": (0.05, 1.5),
    "LHipPitch": (-1.0, 1.0), "RHipPitch": (-1.0, 1.0),
    "LHipRoll": (-0.5, 0.5), "RHipRoll": (-0.5, 0.5),
    "LKneePitch": (0.0, 2.1), "RKneePitch": (0.0, 2.1),
}


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError("CSV nicht gefunden: {}".format(INPUT_FILE.resolve()))
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with INPUT_FILE.open("r", newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        fieldnames = ["Frame"] + list(LIMITS)
        previous = {}

        with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as target:
            writer = csv.DictWriter(target, fieldnames=fieldnames)
            writer.writeheader()

            for row in reader:
                points = {}
                for name in set(name for triplet in [] for name in triplet):
                    pass
                for name in (
                    "LShoulderRoll", "RShoulderRoll", "LElbowRoll", "RElbowRoll",
                    "LWrist", "RWrist", "LHipRoll", "RHipRoll", "LKnee", "RKnee",
                    "LAnkle", "RAnkle",
                ):
                    try:
                        value = read_point(row, name)
                    except (KeyError, TypeError, ValueError):
                        value = None
                    if value is not None:
                        points[name] = value

                targets = calculate_angles(points)
                output = {"Frame": row.get("Frame", "")}
                for joint, limits in LIMITS.items():
                    value = None if targets is None else targets.get(joint)
                    if value is not None:
                        value = clamp(value, limits[0], limits[1])
                        if joint in previous:
                            value = previous[joint] + SMOOTHING * (value - previous[joint])
                        previous[joint] = value
                    output[joint] = "" if value is None else "{:.8f}".format(value)
                writer.writerow(output)

    print("Proportionale 3D-NAO-Winkel gespeichert: {}".format(OUTPUT_FILE.resolve()))


if __name__ == "__main__":
    main()
