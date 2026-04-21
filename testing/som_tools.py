"""
src/tools/som_tools.py

Set-of-Marks (SoM) screenshot tool for ARIA.

Instead of the LLM guessing pixel coordinates from a raw screenshot,
this module:
  1. Takes a screenshot
  2. Walks the Windows UI Automation tree to find all interactive elements
  3. Draws numbered red boxes + labels over each element
  4. Sends the annotated image to the LLM
  5. Stores a {number -> real screen coordinates} map in memory
  6. Exposes click_element(id) so the LLM just says "click 4"

No coordinate scaling math is needed at click time — the map stores
real screen coordinates directly.

Dependencies:
  pip install uiautomation pillow pyautogui
"""

import io
import base64
import pyautogui
from PIL import Image, ImageDraw, ImageFont

try:
    import uiautomation as auto
    _AUTO_AVAILABLE = True
except ImportError:
    _AUTO_AVAILABLE = False

# ─── Module-level element map ────────────────────────────────────────────────
# Persists across tool calls within a single ARIA session.
# Structure: { element_id (int) -> (real_cx, real_cy, label) }
_element_map: dict[int, tuple[int, int, str]] = {}

# Control types considered interactive / worth labelling
_INTERACTIVE_TYPES = {
    "ButtonControl",
    "EditControl",
    "HyperlinkControl",
    "ListItemControl",
    "MenuItemControl",
    "CheckBoxControl",
    "RadioButtonControl",
    "ComboBoxControl",
    "TabItemControl",
    "TreeItemControl",
    "DataItemControl",
}

# ─── Internal helpers ─────────────────────────────────────────────────────────

def _collect_elements(ctrl, results: list, depth: int = 0, max_depth: int = 6):
    """Recursively walk the UI Automation control tree and collect interactive elements."""
    if depth > max_depth:
        return
    try:
        ctype = ctrl.ControlTypeName
        rect = ctrl.BoundingRectangle
        # Skip invisible / zero-size elements
        if rect.width() < 4 or rect.height() < 4:
            return
        if ctype in _INTERACTIVE_TYPES:
            cx = rect.left + rect.width() // 2
            cy = rect.top + rect.height() // 2
            name = (ctrl.Name or ctrl.AutomationId or ctype)[:40]
            results.append((name, cx, cy, rect.left, rect.top, rect.right, rect.bottom))
    except Exception:
        pass

    try:
        for child in ctrl.GetChildren():
            _collect_elements(child, results, depth + 1, max_depth)
    except Exception:
        pass


def _get_font(size: int = 13):
    """Try to load a readable font; fall back to PIL default."""
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        try:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
        except Exception:
            return ImageFont.load_default()


# ─── Public tools ─────────────────────────────────────────────────────────────

def take_som_screenshot(max_elements: int = 40) -> dict:
    """
    Take a screenshot annotated with numbered bounding boxes over every
    detected interactive UI element in the currently focused window.

    Returns the annotated image as base64 JPEG plus an elements dict
    mapping each number to its label, so the LLM can reason about what
    to click without guessing pixel coordinates.

    Args:
        max_elements: Cap on how many elements to label (default 40).
                      Keeps the image readable and the LLM focused.

    Returns:
        {
            "image_base64": str,
            "width": int,
            "height": int,
            "elements": { "1": "Search box", "2": "Sign in button", ... },
            "element_count": int,
            "note": str   # human-readable usage hint for the LLM
        }
    """
    global _element_map
    _element_map = {}

    # 1. Capture raw screenshot at native resolution
    raw = pyautogui.screenshot()
    actual_w, actual_h = raw.size

    # 2. Collect interactive elements via UI Automation
    elements: list[tuple] = []
    if _AUTO_AVAILABLE:
        try:
            focused = auto.GetFocusedControl()
            root = focused.GetTopLevelControl()
            _collect_elements(root, elements)
        except Exception:
            pass

    # Cap to max_elements to avoid overwhelming the LLM
    elements = elements[:max_elements]

    # 3. Annotate the full-res image before downscaling
    annotated = raw.convert("RGB")
    draw = ImageDraw.Draw(annotated)
    font = _get_font(13)

    element_labels: dict[str, str] = {}

    for idx, (name, cx, cy, bx1, by1, bx2, by2) in enumerate(elements, start=1):
        _element_map[idx] = (cx, cy, name)
        element_labels[str(idx)] = name

        # Draw bounding box
        draw.rectangle([bx1, by1, bx2, by2], outline=(220, 40, 40), width=2)

        # Draw label badge (top-left of bbox)
        label = str(idx)
        badge_x, badge_y = bx1, max(0, by1 - 18)
        badge_w = len(label) * 9 + 6
        draw.rectangle([badge_x, badge_y, badge_x + badge_w, badge_y + 17], fill=(220, 40, 40))
        draw.text((badge_x + 3, badge_y + 2), label, fill=(255, 255, 255), font=font)

    # 4. Downscale to 1280×720 (matching existing take_screenshot behaviour)
    annotated.thumbnail((1280, 720))
    thumb_w, thumb_h = annotated.size

    # 5. Encode
    buffer = io.BytesIO()
    annotated.save(buffer, format="JPEG", quality=65, optimize=True)
    img_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    note = (
        "Numbered boxes mark every interactive element detected. "
        "Call click_element with the number of the element you want to interact with. "
        "Do NOT use click_at with guessed coordinates after a SoM screenshot — use click_element instead."
    )

    if not _AUTO_AVAILABLE:
        note = (
            "uiautomation is not installed so no elements were detected. "
            "Run: pip install uiautomation  — then retry."
        )

    return {
        "image_base64": img_b64,
        "width": thumb_w,
        "height": thumb_h,
        "elements": element_labels,
        "element_count": len(elements),
        "note": note,
    }


def click_element(element_id: int) -> dict:
    """
    Click a UI element by the number shown in the most recent SoM screenshot.

    Uses the real screen coordinates stored when take_som_screenshot() was
    last called — no scaling or guessing involved.

    Args:
        element_id: The number shown in the red badge on the annotated screenshot.

    Returns:
        {"success": bool, "element_id": int, "label": str, "clicked_at": [x, y]}
    """
    global _element_map
    if not _element_map:
        return {
            "success": False,
            "error": "No SoM map in memory. Call take_som_screenshot first.",
        }
    if element_id not in _element_map:
        return {
            "success": False,
            "error": (
                f"Element {element_id} not found in current map "
                f"(valid range: 1–{max(_element_map.keys())}). "
                "If the screen changed, call take_som_screenshot again."
            ),
        }

    cx, cy, label = _element_map[element_id]
    pyautogui.click(cx, cy)

    return {
        "success": True,
        "element_id": element_id,
        "label": label,
        "clicked_at": [cx, cy],
    }
