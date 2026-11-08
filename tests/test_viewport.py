import unittest

from client.viewport import Viewport, MIN_ZOOM, MAX_ZOOM


class ViewportTests(unittest.TestCase):
    def test_round_trip_world_screen(self):
        view = Viewport()
        view.zoom, view.ox, view.oy = 2.5, -120.0, 40.0
        for point in [(0, 0), (100, 200), (1919.5, 1079.5), (33.3, 77.7)]:
            back = view.to_world(*view.to_screen(*point))
            self.assertAlmostEqual(back[0], point[0])
            self.assertAlmostEqual(back[1], point[1])

    def test_zoom_keeps_point_under_cursor_fixed(self):
        view = Viewport()
        view.fit(1000, 600)
        cursor = (437, 211)
        world_before = view.to_world(*cursor)
        self.assertTrue(view.zoom_at(1.8, *cursor))
        world_after = view.to_world(*cursor)
        self.assertAlmostEqual(world_before[0], world_after[0])
        self.assertAlmostEqual(world_before[1], world_after[1])

    def test_zoom_is_clamped(self):
        view = Viewport()
        for _ in range(60):
            view.zoom_at(1.5, 100, 100)
        self.assertEqual(view.zoom, MAX_ZOOM)
        self.assertFalse(view.zoom_at(1.5, 100, 100))
        for _ in range(120):
            view.zoom_at(0.5, 100, 100)
        self.assertEqual(view.zoom, MIN_ZOOM)

    def test_fit_centers_and_contains_whole_page(self):
        view = Viewport()
        view.fit(1000, 600)
        x1, y1 = view.to_screen(0, 0)
        x2, y2 = view.to_screen(view.page_width, view.page_height)
        self.assertGreaterEqual(x1, 0)
        self.assertGreaterEqual(y1, 0)
        self.assertLessEqual(x2, 1000)
        self.assertLessEqual(y2, 600)
        self.assertAlmostEqual(x1, 1000 - x2)  # horizontally centered
        self.assertAlmostEqual(y1, 600 - y2)   # vertically centered

    def test_fit_handles_tiny_and_huge_windows(self):
        view = Viewport()
        view.fit(1, 1)
        self.assertEqual(view.zoom, MIN_ZOOM)
        view.fit(8000, 4500)
        self.assertLessEqual(view.zoom, MAX_ZOOM)
        self.assertGreater(view.zoom, 1.0)

    def test_pan_moves_content_and_cannot_lose_the_page(self):
        view = Viewport()
        view.zoom, view.ox, view.oy = 1.0, 0.0, 0.0
        dx, dy = view.pan(30, 20, 800, 600)
        self.assertEqual((dx, dy), (30, 20))
        view.pan(-100000, -100000, 800, 600)
        # at least `keep` pixels of the page remain visible
        right = view.ox + view.page_width * view.zoom
        bottom = view.oy + view.page_height * view.zoom
        self.assertGreaterEqual(right, 80)
        self.assertGreaterEqual(bottom, 80)
        view.pan(100000, 100000, 800, 600)
        self.assertLessEqual(view.ox, 800 - 80)
        self.assertLessEqual(view.oy, 600 - 80)

    def test_drawing_coordinates_are_view_independent(self):
        """The same pointer position on screen maps to the same world point
        that renders back to that exact pixel, at any zoom/pan."""
        view = Viewport()
        view.fit(900, 700)
        view.zoom_at(3.0, 300, 250)
        view.pan(-75, 40, 900, 700)
        world = view.to_world(512, 333)
        stored = (round(world[0], 1), round(world[1], 1))
        sx, sy = view.to_screen(*stored)
        self.assertAlmostEqual(sx, 512, delta=0.1 * view.zoom)
        self.assertAlmostEqual(sy, 333, delta=0.1 * view.zoom)
        # A different participant at a different zoom sees the same world point.
        other = Viewport()
        other.fit(1500, 900)
        ox, oy = other.to_screen(*stored)
        self.assertAlmostEqual(other.to_world(ox, oy)[0], stored[0])

    def test_clamp_world_and_inside_page(self):
        view = Viewport()
        self.assertEqual(view.clamp_world(-5, 99999), (0.0, float(view.page_height)))
        self.assertTrue(view.inside_page(10, 10))
        self.assertFalse(view.inside_page(-1, 10))
        self.assertFalse(view.inside_page(10, view.page_height + 1))


if __name__ == "__main__":
    unittest.main()
