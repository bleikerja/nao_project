import csv
import math
from pathlib import Path

import numpy as np


INPUT_FILE = Path("../../generated/roboter_bewegungsdaten_3d.csv")
OUTPUT_FILE = Path("../../generated/nao_angles_3d.csv")
MIN_VISIBILITY = 0.6

# The names are NAO joint names. The point triplets are used to calculate
# anatomical 3D joint flexion angles. Values are written in radians.
ANGLE_DEFINITION = {
    "LShoulderRoll": ("LHipRoll", "LShoulderRoll", "LElbowRoll"),
    "LElbowRoll": ("LShoulderRoll", "LElbowRoll", "LWrist"),
    "RShoulderRoll": ("RHipRoll", "RShoulderRoll", "RElbowRoll"),
    "RElbowRoll": ("RShoulderRoll", "RElbowRoll", "RWrist"),
    "LHipRoll": ("LShoulderRoll", "LHipRoll", "LKnee"),
    "RHipRoll": ("RShoulderRoll", "RHipRoll", "RKnee"),
    "LKnee": ("LHipRoll", "LKnee", "LAnkle"),
    "RKnee": ("RHipRoll", "RKnee", "RAnkle"),
}


def read_point(row, name):
    values = np.asarray(
        [float(row[f"{name}_{axis}"]) for axis in "XYZ"], dtype=float
    )
    visibility = float(row.get(f"{name}_visibility", 1.0) or 0.0)
    return values, visibility


def angle_at(first, joint, last):
    """Return the 3D angle at joint in radians."""
    first_vector = first - joint
    last_vector = last - joint
    first_length = np.linalg.norm(first_vector)
    last_length = np.linalg.norm(last_vector)

    if first_length < 1e-8 or last_length < 1e-8:
        return None

    cosine = np.dot(first_vector, last_vector) / (first_length * last_length)
    return math.acos(float(np.clip(cosine, -1.0, 1.0)))


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"CSV nicht gefunden: {INPUT_FILE.resolve()}")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with INPUT_FILE.open("r", newline="", encoding="utf-8") as source:
        rows = csv.DictReader(source)
        fieldnames = ["Frame"] + list(ANGLE_DEFINITION)

        with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as target:
            writer = csv.DictWriter(target, fieldnames=fieldnames)
            writer.writeheader()

            for row in rows:
                angle_row = {"Frame": row.get("Frame", "")}

                for joint, (first_name, joint_name, last_name) in ANGLE_DEFINITION.items():
                    try:
                        first, first_visibility = read_point(row, first_name)
                        joint_point, joint_visibility = read_point(row, joint_name)
                        last, last_visibility = read_point(row, last_name)

                        if min(first_visibility, joint_visibility, last_visibility) < MIN_VISIBILITY:
                            angle_row[joint] = ""
                            continue

                        angle = angle_at(first, joint_point, last)
                        angle_row[joint] = "" if angle is None else f"{angle:.8f}"
                    except (KeyError, TypeError, ValueError):
                        angle_row[joint] = ""

                writer.writerow(angle_row)

    print(f"3D-Winkel gespeichert: {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()
