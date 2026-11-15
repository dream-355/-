"""Add male reproductive muscles and derive a complete female atlas from the male base."""

from __future__ import annotations

import copy
import gzip
import json
import math
import re
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "frontend" / "models"
MALE_PATH = MODEL_DIR / "atlas.json"
FEMALE_PATH = MODEL_DIR / "atlas-female.json"
FEMALE_SOURCE_PATH = ROOT / "scripts" / "female-hra-atlas-source.json"
MALE_MUSCLE_NAME = "male-reproductive-muscles.bin"
FEMALE_SUPPLEMENT_NAME = "female-anatomical-supplement.bin"
FEMALE_BODY_SCALE = [0.86, 0.96, 0.86]
BREAST_PATTERN = re.compile(
    r"areol|nipple|mammary|lactiferous|fat \(|suspensory ligament",
    re.IGNORECASE,
)
MALE_REPRODUCTIVE_VESSEL_IDS = {
    "FJ2056",
    "FJ2208",
    "FJ3426",
    "FJ3496",
    "FJ3497",
    "FJ3525",
    "FJ3532",
    "FJ3533",
    "FJ3592",
    "FJ3593",
    "FJ3610",
    "FJ3617",
    "FJ3618",
    "FJ3637",
}


def align4(value: int) -> int:
    return (value + 3) & ~3


def bounds_center(part: dict) -> list[float]:
    return [(low + high) / 2 for low, high in zip(*part["bounds"])]


def bounds_size(part: dict) -> list[float]:
    return [high - low for low, high in zip(*part["bounds"])]


def ellipsoid_geometry(
    center: tuple[float, float, float],
    radii: tuple[float, float, float],
    *,
    rings: int = 12,
    segments: int = 18,
) -> tuple[bytes, bytes, bytes, int, int, list[list[float]]]:
    positions: list[float] = []
    normals: list[float] = []
    indices: list[int] = []
    for ring in range(rings + 1):
        polar = math.pi * ring / rings
        sin_polar = math.sin(polar)
        cos_polar = math.cos(polar)
        for segment in range(segments + 1):
            azimuth = math.tau * segment / segments
            unit_x = sin_polar * math.cos(azimuth)
            unit_y = cos_polar
            unit_z = sin_polar * math.sin(azimuth)
            positions.extend(
                (
                    center[0] + unit_x * radii[0],
                    center[1] + unit_y * radii[1],
                    center[2] + unit_z * radii[2],
                )
            )
            normal = (
                unit_x / radii[0],
                unit_y / radii[1],
                unit_z / radii[2],
            )
            length = math.sqrt(sum(value * value for value in normal))
            normals.extend(value / length for value in normal)
    row = segments + 1
    for ring in range(rings):
        for segment in range(segments):
            a = ring * row + segment
            b = a + row
            indices.extend((a, b, a + 1, b, b + 1, a + 1))
    bounds = [
        [center[axis] - radii[axis] for axis in range(3)],
        [center[axis] + radii[axis] for axis in range(3)],
    ]
    return (
        struct.pack(f"<{len(positions)}f", *positions),
        struct.pack(
            f"<{len(normals)}h",
            *(max(-32767, min(32767, round(value * 32767))) for value in normals),
        ),
        struct.pack(f"<{len(indices)}I", *indices),
        len(positions) // 3,
        len(indices),
        bounds,
    )


def build_male_reproductive_muscles(male: dict) -> int:
    definitions = [
        ("bulbospongiosus-left", "左侧球海绵体肌", (0.012, 0.821, 0.059), (0.014, 0.030, 0.013)),
        ("bulbospongiosus-right", "右侧球海绵体肌", (-0.012, 0.821, 0.059), (0.014, 0.030, 0.013)),
        ("ischiocavernosus-left", "左侧坐骨海绵体肌", (0.025, 0.846, 0.028), (0.012, 0.031, 0.017)),
        ("ischiocavernosus-right", "右侧坐骨海绵体肌", (-0.025, 0.846, 0.028), (0.012, 0.031, 0.017)),
        ("cremaster-left", "左侧提睾肌", (0.020, 0.784, 0.052), (0.0105, 0.018, 0.0105)),
        ("cremaster-right", "右侧提睾肌", (-0.020, 0.784, 0.052), (0.0105, 0.018, 0.0105)),
    ]
    male["parts"] = [
        part
        for part in male["parts"]
        if not part.get("reproductiveMuscle")
        and part["system"] != "oral-soft-tissue"
    ]
    male_part_ids = {part["id"] for part in male["parts"]}
    male["concepts"] = [
        concept
        for concept in male["concepts"]
        if not concept["id"].startswith("M-REPRO-MUSCLE-")
        and set(concept["elements"]).issubset(male_part_ids)
    ]
    male["chunks"] = [
        chunk
        for chunk in male["chunks"]
        if MALE_MUSCLE_NAME not in chunk["gzip"]
        and "male-oral-supplement" not in chunk["gzip"]
    ]
    payload = bytearray()
    parts = []
    concepts = []
    for slug, name, center, radii in definitions:
        position_bytes, normal_bytes, index_bytes, vertex_count, index_count, bounds = (
            ellipsoid_geometry(center, radii)
        )
        positions = len(payload)
        payload.extend(position_bytes)
        payload.extend(b"\0" * (align4(len(payload)) - len(payload)))
        normals = len(payload)
        payload.extend(normal_bytes)
        payload.extend(b"\0" * (align4(len(payload)) - len(payload)))
        indices = len(payload)
        payload.extend(index_bytes)
        payload.extend(b"\0" * (align4(len(payload)) - len(payload)))
        part_id = f"M-REPRO-MUSCLE-{slug.upper()}"
        parts.append(
            {
                "id": part_id,
                "name": name,
                "conceptId": f"LOCAL:reproductive_muscle_{slug}",
                "system": "muscular",
                "chunk": len(male["chunks"]),
                "positions": positions,
                "normals": normals,
                "indices": indices,
                "vertexCount": vertex_count,
                "indexCount": index_count,
                "bounds": bounds,
                "reproductiveMuscle": True,
            }
        )
        concepts.append(
            {
                "id": f"M-REPRO-MUSCLE-CONCEPT-{slug.upper()}",
                "name": name,
                "elements": [part_id],
            }
        )
    compressed = gzip.compress(bytes(payload), compresslevel=9, mtime=0)
    (MODEL_DIR / f"{MALE_MUSCLE_NAME}.gz").write_bytes(compressed)
    (MODEL_DIR / MALE_MUSCLE_NAME).unlink(missing_ok=True)
    male["chunks"].append(
        {
            "url": f"/models/{MALE_MUSCLE_NAME}",
            "bytes": len(payload),
            "gzip": f"/models/{MALE_MUSCLE_NAME}.gz",
            "gzipBytes": len(compressed),
        }
    )
    male["parts"].extend(parts)
    male["concepts"].extend(concepts)
    male["maleReproductiveMuscles"] = {
        "structures": len(parts),
        "method": "Anatomical reference ellipsoids placed on the penile root and testes.",
    }
    return len(parts)


def female_source_parts(source: dict) -> list[tuple[dict, str]]:
    reproductive_terms = (
        "uter",
        "ovar",
        "fallopian",
        "vagina",
        "cervix",
        "placenta",
        "amnion",
        "umbilical",
        "broad ligament",
        "mesosalpinx",
        "mesovarium",
    )
    pelvic_names = {
        "Sacrum",
        "Coccyx",
        "Ilium compact bone (left)",
        "Ilium compact bone (right)",
        "Ilium spongy bone (left)",
        "Ilium spongy bone (right)",
        "Pubis spongy bone (left)",
        "Pubis spongy bone (right)",
        "Pubis compact bone (left)",
        "Pubis compact bone (right)",
        "Ischium compact bone (left)",
        "Ischium compact bone (right)",
        "Ischium spongy bone (left)",
        "Ischium spongy bone (right)",
    }
    selected: list[tuple[dict, str]] = []
    for part in source["parts"]:
        name = part["name"].lower()
        if part["system"] == "integumentary" and re.search(
            r"areol|nipple|mammary|lactiferous|fat \(|suspensory ligament",
            part["name"],
            re.IGNORECASE,
        ):
            selected.append((part, "body"))
        elif part["system"] == "urinary":
            selected.append((part, "body"))
        elif part["system"] in {"reproductive", "pregnancy"}:
            selected.append((part, "pelvis"))
        elif part["system"] == "skeletal" and part["name"] in pelvic_names:
            selected.append((part, "pelvis"))
        elif any(term in name for term in reproductive_terms):
            selected.append((part, "pelvis"))
    if "HRAF0825" not in {part["id"] for part, _ in selected}:
        raise RuntimeError("Female sacrum is missing from the pelvic supplement")
    return selected


def build_female_supplement(source: dict, male: dict) -> tuple[list[dict], list[dict], dict]:
    source_parts = female_source_parts(source)
    source_by_id = {part["id"]: part for part in source["parts"]}
    female_sacrum = source_by_id["HRAF0825"]
    male_sacrum = next(part for part in male["parts"] if part["id"] == "FJ3393")
    female_size = bounds_size(female_sacrum)
    male_size = bounds_size(male_sacrum)
    scale = [0.93, 1.044, male_size[2] / female_size[2]]
    female_center = bounds_center(female_sacrum)
    male_center = bounds_center(male_sacrum)
    translation = [
        male_center[index] - female_center[index] * scale[index]
        for index in range(3)
    ]
    male_parts_by_id = {part["id"]: part for part in male["parts"]}
    female_skin = next(part for part in source["parts"] if part["id"] == "HRAF0003")
    male_skin = male_parts_by_id["FJ2810"]
    body_scale = [
        male_value / female_value
        for male_value, female_value in zip(
            bounds_size(male_skin), bounds_size(female_skin)
        )
    ]
    female_skin_center = bounds_center(female_skin)
    male_skin_center = bounds_center(male_skin)
    body_translation = [
        male_skin_center[index] - female_skin_center[index] * body_scale[index]
        for index in range(3)
    ]
    breast_scale = [1.32, 1.32, 1.52]
    breast_offset = [0.022, 0.0, 0.015]

    def transform_body_point(values: list[float], breast_name: str = "") -> list[float]:
        mapped = [
            value * body_scale[axis] + body_translation[axis]
            for axis, value in enumerate(values)
        ]
        if not BREAST_PATTERN.search(breast_name):
            return mapped
        left = "left" in breast_name.lower()
        anchor = [0.08 if left else -0.08, 1.235, 0.085]
        return [
            anchor[axis]
            + (mapped[axis] - anchor[axis]) * breast_scale[axis]
            + (
                breast_offset[axis] * (1 if left else -1)
                if axis == 0
                else breast_offset[axis]
            )
            for axis in range(3)
        ]
    payload = bytearray()
    parts = []
    concepts = []
    for part, transform_kind in source_parts:
        part_scale = body_scale if transform_kind == "body" else scale
        part_translation = (
            body_translation if transform_kind == "body" else translation
        )
        chunk = source["chunks"][part["chunk"]]
        raw = gzip.decompress((MODEL_DIR / Path(chunk["gzip"]).name).read_bytes())
        position_values = struct.unpack_from(
            f"<{part['vertexCount'] * 3}f", raw, part["positions"]
        )
        transformed = []
        for offset in range(0, len(position_values), 3):
            point = list(position_values[offset : offset + 3])
            transformed.extend(
                transform_body_point(point, part["name"])
                if transform_kind == "body"
                else [
                    point[axis] * part_scale[axis] + part_translation[axis]
                    for axis in range(3)
                ]
            )
        positions = len(payload)
        payload.extend(struct.pack(f"<{len(transformed)}f", *transformed))
        payload.extend(b"\0" * (align4(len(payload)) - len(payload)))
        normals = len(payload)
        normal_end = part["normals"] + part["vertexCount"] * 3 * 2
        payload.extend(raw[part["normals"]:normal_end])
        payload.extend(b"\0" * (align4(len(payload)) - len(payload)))
        indices = len(payload)
        index_end = part["indices"] + part["indexCount"] * 4
        payload.extend(raw[part["indices"]:index_end])
        payload.extend(b"\0" * (align4(len(payload)) - len(payload)))
        part_id = f"FEMALE-{part['id']}"
        corner_a = (
            transform_body_point(part["bounds"][0], part["name"])
            if transform_kind == "body"
            else [
                part["bounds"][0][axis] * part_scale[axis] + part_translation[axis]
                for axis in range(3)
            ]
        )
        corner_b = (
            transform_body_point(part["bounds"][1], part["name"])
            if transform_kind == "body"
            else [
                part["bounds"][1][axis] * part_scale[axis] + part_translation[axis]
                for axis in range(3)
            ]
        )
        transformed_bounds = [
            [min(corner_a[axis], corner_b[axis]) for axis in range(3)],
            [max(corner_a[axis], corner_b[axis]) for axis in range(3)],
        ]
        parts.append(
            {
                **part,
                "id": part_id,
                "chunk": len(male["chunks"]),
                "positions": positions,
                "normals": normals,
                "indices": indices,
                "bounds": transformed_bounds,
            }
        )
        concepts.append(
            {
                "id": f"FEMALE-{part['conceptId']}",
                "name": part["name"],
                "elements": [part_id],
            }
        )
    compressed = gzip.compress(bytes(payload), compresslevel=9, mtime=0)
    (MODEL_DIR / f"{FEMALE_SUPPLEMENT_NAME}.gz").write_bytes(compressed)
    (MODEL_DIR / FEMALE_SUPPLEMENT_NAME).unlink(missing_ok=True)
    (MODEL_DIR / "female-reproductive-supplement.bin.gz").unlink(missing_ok=True)
    (MODEL_DIR / "female-reproductive-supplement.bin").unlink(missing_ok=True)
    chunk = {
        "url": f"/models/{FEMALE_SUPPLEMENT_NAME}",
        "bytes": len(payload),
        "gzip": f"/models/{FEMALE_SUPPLEMENT_NAME}.gz",
        "gzipBytes": len(compressed),
    }
    return parts, concepts, {
        "chunk": chunk,
        "scale": scale,
        "translation": translation,
        "bodyScale": body_scale,
        "bodyTranslation": body_translation,
        "breastScale": breast_scale,
        "breastOffset": breast_offset,
        "structures": len(parts),
    }


def main() -> None:
    male = json.loads(MALE_PATH.read_text(encoding="utf-8"))
    if FEMALE_SOURCE_PATH.exists():
        female_source = json.loads(FEMALE_SOURCE_PATH.read_text(encoding="utf-8"))
    else:
        female_source = json.loads(FEMALE_PATH.read_text(encoding="utf-8"))
        FEMALE_SOURCE_PATH.write_text(
            json.dumps(female_source, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    male["parts"] = [
        part
        for part in male["parts"]
        if not part.get("reproductiveMuscle")
        and part["system"] != "oral-soft-tissue"
    ]
    male_part_ids = {part["id"] for part in male["parts"]}
    male["concepts"] = [
        concept
        for concept in male["concepts"]
        if not concept["id"].startswith("M-REPRO-MUSCLE-")
        and set(concept["elements"]).issubset(male_part_ids)
    ]
    male["chunks"] = [
        chunk
        for chunk in male["chunks"]
        if MALE_MUSCLE_NAME not in chunk["gzip"]
        and "male-oral-supplement" not in chunk["gzip"]
    ]
    male.pop("maleReproductiveMuscles", None)
    male.pop("oralSupplement", None)
    (MODEL_DIR / f"{MALE_MUSCLE_NAME}.gz").unlink(missing_ok=True)
    (MODEL_DIR / MALE_MUSCLE_NAME).unlink(missing_ok=True)
    (MODEL_DIR / "male-oral-supplement.bin.gz").unlink(missing_ok=True)
    (MODEL_DIR / "male-oral-supplement.bin").unlink(missing_ok=True)
    MALE_PATH.write_text(
        json.dumps(male, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    female = copy.deepcopy(male)
    female["parts"] = [
        part
        for part in female["parts"]
        if part["system"] not in {"reproductive", "urinary"}
        and not part.get("reproductiveMuscle")
        and part["id"] not in MALE_REPRODUCTIVE_VESSEL_IDS
        and part["id"] != "FJ2815"
    ]
    surviving_ids = {part["id"] for part in female["parts"]}
    female["concepts"] = [
        concept
        for concept in female["concepts"]
        if set(concept["elements"]).issubset(surviving_ids)
    ]
    female_parts, female_concepts, supplement = build_female_supplement(
        female_source, male
    )
    female_chunk_index = len(female["chunks"])
    for part in female_parts:
        part["chunk"] = female_chunk_index
    female["chunks"].append(supplement["chunk"])
    female["parts"].extend(female_parts)
    female["concepts"].extend(female_concepts)
    female["sex"] = "female"
    female["version"] = "Complete female anatomy derived from male atlas v1"
    female["source"] = "BodyParts3D complete body with female reproductive and pelvic supplement"
    female["scope"] = (
        "Complete adult anatomy based on the male atlas, with male reproductive organs "
        "replaced by female reproductive anatomy and a smaller female body profile."
    )
    female["bodyScale"] = FEMALE_BODY_SCALE
    female["femaleSupplement"] = {
        "source": "Human Reference Atlas united-female v1.10",
        "structures": supplement["structures"],
        "scale": supplement["scale"],
        "translation": supplement["translation"],
        "bodyScale": supplement["bodyScale"],
        "bodyTranslation": supplement["bodyTranslation"],
        "breastScale": supplement["breastScale"],
        "breastOffset": supplement["breastOffset"],
        "method": "Fit to the male pelvic frame using the sacrum, then apply the female body profile.",
    }
    female["triangles"] = sum(part["indexCount"] // 3 for part in female["parts"])
    FEMALE_PATH.write_text(
        json.dumps(female, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"female structures: {len(female['parts'])}; "
        f"female supplement: {supplement['structures']}"
    )


if __name__ == "__main__":
    main()
