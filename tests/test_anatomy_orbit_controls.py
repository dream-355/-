import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VIEWER = ROOT / "frontend" / "assets" / "modules" / "anatomy-atlas.js"


class AnatomyOrbitControlsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = VIEWER.read_text(encoding="utf-8")

    def test_orbit_is_model_centered_and_cannot_pan(self) -> None:
        self.assertIn("this.controls.enablePan = false;", self.source)
        self.assertIn("this.controls.zoomToCursor = false;", self.source)
        self.assertIn("this.controls.target.copy(center);", self.source)

    def test_camera_can_reach_full_sphere(self) -> None:
        self.assertIn("this.controls.minPolarAngle = 0;", self.source)
        self.assertIn("this.controls.maxPolarAngle = Math.PI;", self.source)
        self.assertIn("this.camera.position.set(center.x, center.y, center.z + distance);", self.source)

    def test_zoom_scales_view_around_screen_center(self) -> None:
        self.assertIn("this.camera.zoom = this.zoom;", self.source)
        self.assertNotIn(
            "this.defaultDistance / this.zoom",
            self.source,
        )

    def test_wheel_zooms_the_page_view_around_screen_center(self) -> None:
        self.assertIn("this.controls.enableZoom = false;", self.source)
        self.assertIn("this.onWheel = (event) => {", self.source)
        self.assertIn("this.setZoom(this.zoom * factor);", self.source)

    def test_body_drag_moves_model_and_blank_drag_rotates(self) -> None:
        self.assertIn("this.controls.mouseButtons.RIGHT = -1;", self.source)
        self.assertNotIn("dblclick", self.source)
        self.assertIn("const partIndex = this.ready ? this.findPartAt(x, y, true) : -1;", self.source)
        self.assertIn("this.startModelDrag(event);", self.source)
        self.assertIn("this.updateModelDrag(event);", self.source)
        self.assertIn(
            "this.canvas.addEventListener(\"pointerdown\", this.onPointerDown, {",
            self.source,
        )
        self.assertIn(
            "projection[8] += (2 * this.viewOffsetX * this.camera.zoom) / width;",
            self.source,
        )
        self.assertIn(
            "projection[9] -= (2 * this.viewOffsetY * this.camera.zoom) / height;",
            self.source,
        )
        self.assertIn(
            "this.viewOffsetX =\n"
            "      this.modelDragState.offsetX -\n"
            "      (event.clientX - this.modelDragState.startX) / this.zoom;",
            self.source,
        )

    def test_zoom_range_reaches_five_hundred_percent(self) -> None:
        self.assertIn("Math.min(5, Number(value) || 1)", self.source)
        self.assertIn("distance / 5", self.source)


if __name__ == "__main__":
    unittest.main()
