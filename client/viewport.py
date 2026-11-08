"""World <-> screen transform for the whiteboard (no Tkinter, unit-testable).

Drawing data is always stored and sent in *world* coordinates (the fixed
PAGE_WIDTH x PAGE_HEIGHT page). The viewport maps those to canvas pixels:

    screen = world * zoom + offset
"""

PAGE_WIDTH = 1920
PAGE_HEIGHT = 1080
MIN_ZOOM = 0.1
MAX_ZOOM = 6.0


class Viewport:
    def __init__(self, page_width=PAGE_WIDTH, page_height=PAGE_HEIGHT):
        self.page_width = page_width
        self.page_height = page_height
        self.zoom = 1.0
        self.ox = 0.0
        self.oy = 0.0

    def to_screen(self, wx, wy):
        return wx * self.zoom + self.ox, wy * self.zoom + self.oy

    def to_world(self, sx, sy):
        return (sx - self.ox) / self.zoom, (sy - self.oy) / self.zoom

    def clamp_world(self, wx, wy):
        return (min(max(wx, 0.0), float(self.page_width)),
                min(max(wy, 0.0), float(self.page_height)))

    def inside_page(self, wx, wy):
        return 0 <= wx <= self.page_width and 0 <= wy <= self.page_height

    def zoom_at(self, factor, sx, sy):
        """Zoom by factor keeping the world point under (sx, sy) fixed."""
        new_zoom = min(MAX_ZOOM, max(MIN_ZOOM, self.zoom * factor))
        if new_zoom == self.zoom:
            return False
        wx, wy = self.to_world(sx, sy)
        self.zoom = new_zoom
        self.ox = sx - wx * new_zoom
        self.oy = sy - wy * new_zoom
        return True

    def set_zoom_centered(self, zoom, view_w, view_h):
        self.zoom_at(min(MAX_ZOOM, max(MIN_ZOOM, zoom)) / self.zoom, view_w / 2, view_h / 2)

    def fit(self, view_w, view_h, margin=24):
        """Scale and center the whole page inside the viewport."""
        view_w, view_h = max(1, view_w), max(1, view_h)
        avail_w = max(1, view_w - 2 * margin)
        avail_h = max(1, view_h - 2 * margin)
        self.zoom = min(MAX_ZOOM, max(MIN_ZOOM, min(avail_w / self.page_width,
                                                    avail_h / self.page_height)))
        self.ox = (view_w - self.page_width * self.zoom) / 2
        self.oy = (view_h - self.page_height * self.zoom) / 2

    def pan(self, dx, dy, view_w, view_h):
        """Pan and keep some of the page visible. Returns the applied (dx, dy)."""
        old = (self.ox, self.oy)
        self.ox += dx
        self.oy += dy
        self.clamp(view_w, view_h)
        return self.ox - old[0], self.oy - old[1]

    def clamp(self, view_w, view_h, keep=80):
        """Never let the page drift completely out of view."""
        page_w = self.page_width * self.zoom
        page_h = self.page_height * self.zoom
        keep_x = min(keep, page_w, view_w)
        keep_y = min(keep, page_h, view_h)
        self.ox = min(max(self.ox, keep_x - page_w), view_w - keep_x)
        self.oy = min(max(self.oy, keep_y - page_h), view_h - keep_y)
