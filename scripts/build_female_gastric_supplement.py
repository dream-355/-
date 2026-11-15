"""Add non-sex-specific stomach and esophagus meshes to the female atlas.

The HRA female reference does not contain stomach or esophagus geometry.
BodyParts3D contains both and both datasets are licensed CC BY 4.0. The
supplement is aligned independently in x/y/z using shared abdominal organs:
liver, pancreas, spleen, both kidneys, small intestine and bladder.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
MALE_MANIFEST = ROOT / "frontend" / "models" / "atlas.json"
MALE_CHUNKS = MALE_MANIFEST.parent
FEMALE_MANIFEST = ROOT / "frontend" / "models" / "atlas-female.json"
OUTPUT_BIN = ROOT / "frontend" / "models" / "female-supplement.bin"
OUTPUT_GZ = ROOT / "frontend" / "models" / "female-supplement.bin.gz"
SOURCE_PART_IDS = ("FJ2564", "FJ2563")  # stomach, esophagus
ORAL_KEYWORDS = (
    "口",
    "舌",
    "腭",
    "咽",
    "喉",
    "会厌",
    "声带",
    "杓状",
    "环状",
    "甲状软骨",
    "悬雍垂",
    "扁桃体",
    "牙",
    "齿",
    "龈",
    "唇",
    "颊",
    "颌",
    "气管",
)
ORAL_EXCLUDES = ("支气管", "肺段", "动脉", "静脉")
ORAL_SYSTEMS = {"skeletal", "muscular", "respiratory", "digestive", "connective", "lymphatic"}
SHARED_CONCEPT_IDS = (
    ("FMA7198", "HRA:pancreas"),
    ("FMA7196", "HRA:spleen"),
    ("FMA7205", "HRA:left_kidney"),
    ("FMA7204", "HRA:right_kidney"),
    ("FMA7200", "HRA:small_intestine"),
    ("FMA15900", "HRA:urinary_bladder"),
    ("FMA7197", "HRA:liver"),
)
ORAL_LANDMARKS = (
    ("FMA54640", "HRA:tongue"),
    ("FMA55021", "HRA:soft_palate"),
    ("FMA55109", "HRA:arytenoid_cartilage"),
    ("FMA9615", "HRA:cricoid_cartilage"),
    ("FMA55099", "HRA:thyroid_cartilage"),
    ("FMA7394", "HRA:trachea"),
)


def concept_bounds(atlas: dict, concept_id: str) -> np.ndarray | None:
    concept = next(
        (item for item in atlas["concepts"] if item["id"] == concept_id),
        None,
    )
    if concept is None:
        return None
    ids = set(concept["elements"])
    parts = [part for part in atlas["parts"] if part["id"] in ids]
    if not parts:
        return None
    low = np.min([part["bounds"][0] for part in parts], axis=0)
    high = np.max([part["bounds"][1] for part in parts], axis=0)
    return (low + high) / 2


def derive_alignment(male: dict, female: dict) -> tuple[np.ndarray, np.ndarray]:
    pairs = []
    for male_id, female_id in SHARED_CONCEPT_IDS:
        male_center = concept_bounds(male, male_id)
        female_center = concept_bounds(female, female_id)
        if male_center is not None and female_center is not None:
            pairs.append((male_center, female_center))
    if len(pairs) < 4:
        raise RuntimeError("Not enough shared abdominal landmarks for alignment.")
    male_points = np.array([pair[0] for pair in pairs])
    female_points = np.array([pair[1] for pair in pairs])
    scale = np.zeros(3)
    offset = np.zeros(3)
    for axis in range(3):
        scale[axis], offset[axis] = np.polyfit(male_points[:, axis], female_points[:, axis], 1)
    return scale, offset


def derive_oral_alignment(
    male: dict,
    female: dict,
) -> tuple[np.ndarray, np.ndarray]:
    pairs = []
    for male_id, female_id in ORAL_LANDMARKS:
        male_center = concept_bounds(male, male_id)
        female_center = concept_bounds(female, female_id)
        if male_center is not None and female_center is not None:
            pairs.append((male_center, female_center))
    if len(pairs) < 4:
        raise RuntimeError("Not enough shared oral landmarks for alignment.")
    male_points = np.array([pair[0] for pair in pairs])
    female_points = np.array([pair[1] for pair in pairs])
    scale = np.zeros(3)
    offset = np.zeros(3)
    for axis in range(3):
        scale[axis], offset[axis] = np.polyfit(male_points[:, axis], female_points[:, axis], 1)
    # X centers are almost all near the midline, making a fitted X scale
    # unstable. Preserve the source dental/airway width and fit Y/Z locally.
    scale[0] = 1.0
    offset[0] = 0.0
    return scale, offset


def oral_part_ids(male: dict) -> list[str]:
    selected: set[str] = set()
    for concept in male["concepts"]:
        name = concept["name"]
        if not any(keyword in name for keyword in ORAL_KEYWORDS):
            continue
        if any(excluded in name for excluded in ORAL_EXCLUDES):
            continue
        selected.update(concept["elements"])
    return sorted(
        part_id
        for part_id in selected
        if next(
            part for part in male["parts"] if part["id"] == part_id
        )["system"]
        in ORAL_SYSTEMS
    )


def read_part(male: dict, source_id: str) -> tuple[dict, np.ndarray, np.ndarray, np.ndarray]:
    part = next(item for item in male["parts"] if item["id"] == source_id)
    chunk = male["chunks"][part["chunk"]]
    source_file = MALE_CHUNKS / Path(chunk["url"]).name
    if source_file.exists():
        payload = source_file.read_bytes()
    else:
        payload = gzip.decompress(
            (MALE_CHUNKS / Path(chunk["gzip"]).name).read_bytes()
        )
    positions = np.frombuffer(
        payload,
        dtype="<f4",
        count=part["vertexCount"] * 3,
        offset=part["positions"],
    ).reshape(-1, 3)
    normals = np.frombuffer(
        payload,
        dtype="<i2",
        count=part["vertexCount"] * 3,
        offset=part["normals"],
    ).reshape(-1, 3).astype(np.float32)
    indices = np.frombuffer(
        payload,
        dtype="<u4",
        count=part["indexCount"],
        offset=part["indices"],
    )
    return part, positions.copy(), normals, indices.copy()


def align_geometry(
    positions: np.ndarray,
    normals: np.ndarray,
    scale: np.ndarray,
    offset: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    aligned_positions = positions * scale + offset
    aligned_normals = normals / scale
    lengths = np.linalg.norm(aligned_normals, axis=1, keepdims=True)
    aligned_normals = aligned_normals / np.maximum(lengths, 1e-8)
    # Source normals are signed 16-bit, so 1.0 is represented by 32767.
    aligned_normals = np.rint(aligned_normals * 32767).clip(-32767, 32767).astype("<i2")
    return aligned_positions.astype("<f4"), aligned_normals


def main() -> None:
    male = json.loads(MALE_MANIFEST.read_text(encoding="utf-8"))
    female = json.loads(FEMALE_MANIFEST.read_text(encoding="utf-8"))
    scale, offset = derive_alignment(male, female)
    oral_scale, oral_offset = derive_oral_alignment(male, female)

    female["parts"] = [
        part for part in female["parts"] if not part["id"].startswith("SUPP-")
    ]
    female["concepts"] = [
        concept for concept in female["concepts"] if not concept["id"].startswith("SUPP:")
    ]
    female["chunks"] = [chunk for chunk in female["chunks"] if "female-supplement" not in chunk["url"]]

    output = bytearray()
    supplement_parts = []
    source_ids = list(SOURCE_PART_IDS)
    source_ids.extend(
        part_id for part_id in oral_part_ids(male) if part_id not in source_ids
    )
    for source_id in source_ids:
        source_part, positions, normals, indices = read_part(male, source_id)
        part_scale, part_offset = (
            (scale, offset)
            if source_id in SOURCE_PART_IDS
            else (oral_scale, oral_offset)
        )
        aligned_positions, aligned_normals = align_geometry(
            positions,
            normals,
            part_scale,
            part_offset,
        )
        while len(output) % 4:
            output.append(0)
        positions_offset = len(output)
        output.extend(aligned_positions.tobytes())
        while len(output) % 4:
            output.append(0)
        normals_offset = len(output)
        output.extend(aligned_normals.tobytes())
        while len(output) % 4:
            output.append(0)
        indices_offset = len(output)
        output.extend(indices.astype("<u4").tobytes())
        low = aligned_positions.min(axis=0).astype(float).tolist()
        high = aligned_positions.max(axis=0).astype(float).tolist()
        supplement_parts.append(
            {
                "id": f"SUPP-{source_id}",
                "name": source_part["name"],
                "conceptId": f"SUPP:{source_id}",
                "system": source_part["system"],
                "chunk": len(female["chunks"]),
                "positions": positions_offset,
                "normals": normals_offset,
                "indices": indices_offset,
                "vertexCount": source_part["vertexCount"],
                "indexCount": source_part["indexCount"],
                "bounds": [low, high],
            }
        )

    OUTPUT_BIN.write_bytes(output)
    OUTPUT_GZ.write_bytes(gzip.compress(output, compresslevel=9))
    female["parts"].extend(supplement_parts)
    female["chunks"].append(
        {
            "url": "/models/female-supplement.bin",
            "bytes": len(output),
            "gzip": "/models/female-supplement.bin.gz",
            "gzipBytes": OUTPUT_GZ.stat().st_size,
        }
    )
    for part in supplement_parts:
        female["concepts"].append(
            {
                "id": part["conceptId"],
                "name": part["name"],
                "elements": [part["id"]],
            }
        )
    female["triangles"] = sum(part["indexCount"] // 3 for part in female["parts"])
    female["supplement"] = {
        "source": "BodyParts3D 4.0",
        "license": "CC BY 4.0",
        "structures": ["Stomach", "Esophagus", "Mouth and oropharynx"],
        "method": "Abdominal organs use seven shared landmarks; oral and airway structures use six shared local landmarks.",
        "abdominalScale": scale.tolist(),
        "abdominalOffset": offset.tolist(),
        "oralScale": oral_scale.tolist(),
        "oralOffset": oral_offset.tolist(),
    }
    FEMALE_MANIFEST.write_text(
        json.dumps(female, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(
        f"Added {len(supplement_parts)} structures; "
        f"{len(output)} bytes, {OUTPUT_GZ.stat().st_size} gzip bytes"
    )
    print(f"scale={scale.tolist()} offset={offset.tolist()}")


if __name__ == "__main__":
    main()
