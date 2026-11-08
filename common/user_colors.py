"""Shared palette and collision-free participant color assignment."""
import colorsys
import re

USER_COLORS = [
    "#2563EB",  # blue
    "#E05252",  # red
    "#16A36A",  # green
    "#9333EA",  # purple
    "#D97706",  # orange
    "#0891B2",  # cyan
    "#DB2777",  # pink
    "#65A30D",  # lime
    "#4F46E5",  # indigo
    "#0F766E",  # teal
    "#B45309",  # amber
    "#7C3AED",  # violet
    "#BE123C",  # rose
    "#0369A1",  # sky
    "#4D7C0F",  # olive
    "#A21CAF",  # fuchsia
]
DEFAULT_USER_COLOR = "#2563EB"


def normalize_color(color, fallback=DEFAULT_USER_COLOR):
    if isinstance(color, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
        return color.upper()
    return fallback


def assign_unique_color(preferred_color, used_colors):
    """Use a preference when free; otherwise allocate the first free palette color.

    If the palette is exhausted, generate additional deterministic HSV colors.
    """
    used = {str(color).upper() for color in used_colors}
    preferred = normalize_color(preferred_color)
    if preferred not in used:
        return preferred

    for color in USER_COLORS:
        candidate = color.upper()
        if candidate not in used:
            return candidate

    # Supports rooms with more participants than the built-in palette.
    index = 0
    while True:
        hue = (index * 0.618033988749895) % 1.0
        red, green, blue = colorsys.hsv_to_rgb(hue, 0.72, 0.88)
        candidate = "#{:02X}{:02X}{:02X}".format(
            round(red * 255), round(green * 255), round(blue * 255)
        )
        if candidate not in used:
            return candidate
        index += 1


def build_viewer_color_map(viewer_id, viewer_preferred_color, participants):
    """Return colors as seen by one viewer, keyed by participant client_id.

    The viewer's preference is reserved first. Other participants keep their
    own preferences whenever possible; collisions receive a free palette color.
    Preferences are never modified by this presentation-only mapping.
    """
    people = []
    seen = set()
    for item in participants or []:
        if not isinstance(item, dict):
            continue
        pid = item.get("client_id") or item.get("user_id")
        if pid is None or pid in seen:
            continue
        seen.add(pid)
        people.append({
            "client_id": pid,
            "preferred_color": normalize_color(
                item.get("preferred_color", item.get("color", DEFAULT_USER_COLOR))
            ),
        })

    # Ensure the current viewer is represented even before the participant
    # list arrives from the server.
    if viewer_id is not None and viewer_id not in seen:
        people.insert(0, {"client_id": viewer_id,
                          "preferred_color": normalize_color(viewer_preferred_color)})
    elif viewer_id is not None:
        for person in people:
            if person["client_id"] == viewer_id:
                person["preferred_color"] = normalize_color(viewer_preferred_color)
                break

    # Viewer preference always wins locally, regardless of join order.
    people.sort(key=lambda person: person["client_id"] != viewer_id)
    reserved = {person["preferred_color"] for person in people}
    assigned = {}
    used = set()
    for person in people:
        preferred = person["preferred_color"]
        if preferred not in used:
            chosen = preferred
        else:
            chosen = assign_unique_color(preferred, used | reserved)
        assigned[person["client_id"]] = chosen
        used.add(chosen)
    return assigned


class StrokeColorResolver:
    """Keeps each drawing's display color fixed once it has been shown.

    When a participant changes their color, only their *new* strokes use it.
    A stroke's own draw-time color is carried in its event data. The first time
    a stroke is rendered it gets the viewer-relative color (which resolves
    collisions) if its author still has that color, otherwise its draw-time
    color; the result is remembered so later redraws never recolor it.
    """

    def __init__(self):
        self._cache = {}

    def reset(self):
        self._cache.clear()

    def resolve(self, event, color_map, current_preferences):
        data = event.get("data", {}) if isinstance(event.get("data"), dict) else {}
        uid = event.get("user_id")
        drawn = normalize_color(data.get("color", event.get("preferred_color", DEFAULT_USER_COLOR)))
        key = (event.get("sequence"), uid, drawn)
        if key in self._cache:
            return self._cache[key]
        current = current_preferences.get(uid)
        if current is None or normalize_color(current) == drawn:
            color = color_map.get(uid, drawn)
        else:
            color = drawn
        self._cache[key] = color
        return color
