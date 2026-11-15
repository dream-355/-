import gzip
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "frontend" / "models"


class AnatomyAssetTests(unittest.TestCase):
    @staticmethod
    def load_manifest(name: str) -> dict:
        return json.loads((MODEL_DIR / name).read_text(encoding="utf-8"))

    def test_manifests_are_structurally_complete(self) -> None:
        for name in ("atlas.json", "atlas-female.json"):
            atlas = self.load_manifest(name)
            part_ids = [part["id"] for part in atlas["parts"]]
            concept_ids = [concept["id"] for concept in atlas["concepts"]]
            self.assertEqual(len(part_ids), len(set(part_ids)))
            self.assertEqual(len(concept_ids), len(set(concept_ids)))
            self.assertTrue(atlas["chunks"])
            self.assertGreater(atlas["triangles"], 1_000_000)

            known_parts = set(part_ids)
            for concept in atlas["concepts"]:
                self.assertTrue(concept["elements"])
                self.assertTrue(set(concept["elements"]).issubset(known_parts))

    def test_chunk_sizes_match_manifests(self) -> None:
        for name in ("atlas.json", "atlas-female.json"):
            atlas = self.load_manifest(name)
            for chunk in atlas["chunks"]:
                compressed_path = MODEL_DIR / Path(chunk["gzip"]).name
                self.assertTrue(compressed_path.exists(), compressed_path)
                payload = gzip.decompress(compressed_path.read_bytes())
                self.assertEqual(len(payload), chunk["bytes"], compressed_path.name)

    def test_sex_specific_reproductive_structures_are_separated(self) -> None:
        male = self.load_manifest("atlas.json")
        female = self.load_manifest("atlas-female.json")
        male_names = " ".join(part["name"].lower() for part in male["parts"])
        female_names = " ".join(part["name"].lower() for part in female["parts"])

        self.assertIn("睾丸", male_names)
        self.assertIn("前列腺", male_names)
        self.assertNotIn("子宫", male_names)
        self.assertNotIn("卵巢", male_names)

        self.assertIn("uterus", female_names)
        self.assertIn("ovary", female_names)
        self.assertNotIn("prostate", female_names)
        self.assertNotIn("testis", female_names)

    def test_female_supplement_includes_reproductive_and_pelvic_structures(self) -> None:
        female = self.load_manifest("atlas-female.json")
        supplement = [
            part for part in female["parts"] if part["id"].startswith("FEMALE-")
        ]
        self.assertGreaterEqual(len(supplement), 60)
        supplement_names = {part["name"] for part in supplement}
        self.assertTrue(any("uter" in name.lower() for name in supplement_names))
        self.assertTrue(any("ovar" in name.lower() for name in supplement_names))
        self.assertTrue(any("sacrum" in name.lower() for name in supplement_names))
        self.assertTrue(any("pubis" in name.lower() for name in supplement_names))
        supplement_bytes = sum(
            (MODEL_DIR / Path(chunk["gzip"]).name).stat().st_size
            for chunk in female["chunks"]
            if "female-anatomical-supplement" in chunk["gzip"]
        )
        self.assertLess(supplement_bytes, 8 * 1024 * 1024)

    def test_oral_soft_tissue_supplement_is_removed(self) -> None:
        male = self.load_manifest("atlas.json")
        self.assertFalse(
            any(part["system"] == "oral-soft-tissue" for part in male["parts"])
        )
        self.assertFalse(
            any("male-oral-supplement" in chunk["gzip"] for chunk in male["chunks"])
        )
        self.assertNotIn("oralSupplement", male)
        female = self.load_manifest("atlas-female.json")
        self.assertFalse(
            any(part["system"] == "oral-soft-tissue" for part in female["parts"])
        )
        self.assertFalse(
            any("oral-supplement" in chunk["gzip"] for chunk in female["chunks"])
        )
        self.assertNotIn("oralSupplement", female)
        self.assertEqual(female["femaleSupplement"]["breastScale"], [1.32, 1.32, 1.52])
        breast_fat = next(
            part
            for part in female["parts"]
            if part["name"] == "Fat (left)"
        )
        breast_size = [
            high - low
            for low, high in zip(*breast_fat["bounds"])
        ]
        self.assertGreaterEqual(breast_size[0], 0.11)
        self.assertGreaterEqual(breast_size[1], 0.24)
        self.assertGreaterEqual(breast_size[2], 0.14)

    def test_female_atlas_contains_complete_body_and_cranial_bones(self) -> None:
        female = self.load_manifest("atlas-female.json")
        self.assertEqual(female["bodyScale"], [0.86, 0.96, 0.86])
        muscular = [part for part in female["parts"] if part["system"] == "muscular"]
        self.assertEqual(len(muscular), 402)
        self.assertEqual(
            sum(part["system"] == "urinary" for part in female["parts"]), 87
        )
        self.assertEqual(
            sum(part["system"] == "integumentary" for part in female["parts"]), 20
        )
        self.assertEqual(
            sum(part["system"] == "pregnancy" for part in female["parts"]), 8
        )
        integumentary_names = {
            part["name"]
            for part in female["parts"]
            if part["system"] == "integumentary"
        }
        self.assertIn("皮肤", integumentary_names)
        self.assertNotIn("阴毛", integumentary_names)
        self.assertGreaterEqual(
            sum("mammary" in name.lower() for name in integumentary_names), 2
        )
        vascular_names = [
            part["name"]
            for part in female["parts"]
            if part["system"] in {"arterial", "venous"}
        ]
        self.assertFalse(
            any(
                term in name
                for name in vascular_names
                for term in ("阴茎", "睾丸", "精囊", "附睾")
            )
        )
        names = {part["name"] for part in female["parts"]}
        self.assertTrue(
            {
                "额骨",
                "左顶骨",
                "右顶骨",
                "枕骨",
                "下颌骨",
                "左上颌骨",
                "右上颌骨",
            }.issubset(names)
        )

    def test_male_muscle_layer_does_not_include_extra_reproductive_meshes(self) -> None:
        male = self.load_manifest("atlas.json")
        muscles = [part for part in male["parts"] if part.get("reproductiveMuscle")]
        self.assertEqual(muscles, [])
        self.assertEqual(
            sum(part["system"] == "muscular" for part in male["parts"]), 402
        )

    def test_female_display_names_have_a_translation_entry(self) -> None:
        female = self.load_manifest("atlas-female.json")
        translations = set(
            json.loads((MODEL_DIR / "anatomy-terms-zh.json").read_text(encoding="utf-8"))[
                "terms"
            ]
        )
        translations.update(
            json.loads(
                (MODEL_DIR / "anatomy-terms-zh-auto.json").read_text(encoding="utf-8")
            )["terms"]
        )
        missing = {
            part["name"]
            for part in female["parts"]
            if not any("\u3400" <= character <= "\u9fff" for character in part["name"])
            and part["name"].strip().lower() not in translations
        }
        self.assertEqual(missing, set())

    def test_deployable_anatomy_assets_stay_below_threshold(self) -> None:
        total = sum(path.stat().st_size for path in MODEL_DIR.iterdir() if path.is_file())
        self.assertLess(total, 90 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
