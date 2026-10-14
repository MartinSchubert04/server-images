"""Build the kiosk dashboard config from kiosk/dashboard.yaml.

dashboard.yaml is written as one view per tab (easy to read and edit). Switching
between real Lovelace views re-creates the whole view, sidebar included, which
shows as a flicker on the Pi. So this merges every view into ONE view
(path "overview", so the kiosk URL stays the same):

  - the sidebar and the tab bar are rendered once and never redrawn;
  - each original view becomes a "page" (a layout-card with a fusion_page
    marker) that is shown or hidden instantly from the URL hash: #overview,
    #hub, #weather, ... All pages are built once on load, hidden;
  - `navigate` tap actions that point at a page become hash changes.

Usage (inside the homeassistant container):
    python3 build_dashboard.py dashboard.yaml out.json
"""

import copy
import json
import sys

import yaml


def page_of(view):
    """Return (sidebar, main_layout_card, content_cards) of a per-tab view."""
    sidebar, main = view["cards"][0], view["cards"][1]
    content = [c for c in main["cards"] if c.get("template") != "fusion_tabs"]
    return sidebar, main, content


def hash_actions(node, pages):
    """Turn `navigate` actions to a page path into a hash change, recursively."""
    if isinstance(node, dict):
        for key, value in list(node.items()):
            if (
                key.endswith("_action")
                and isinstance(value, dict)
                and value.get("action") == "navigate"
                and value.get("navigation_path") in pages
            ):
                node[key] = {
                    "action": "javascript",
                    "javascript": "[[[ location.hash = '%s'; ]]]" % value["navigation_path"],
                }
            else:
                hash_actions(value, pages)
    elif isinstance(node, list):
        for item in node:
            hash_actions(item, pages)


def build(src):
    config = {k: v for k, v in src.items() if not k.startswith("x-")}
    views = config["views"]
    pages = [v["path"] for v in views]

    first = views[0]
    sidebar, main, _ = page_of(first)
    tabs = next(c for c in main["cards"] if c.get("template") == "fusion_tabs")

    page_cards = []
    for view in views:
        _, _, content = page_of(view)
        content = copy.deepcopy(content)
        hash_actions(content, pages)
        # A plain layout-card per page (not nested in a button-card: button-card
        # would evaluate the inner cards' [[[ ]]] templates in its own context).
        # Its first card is an invisible fusion_page marker that registers the
        # page with the hash navigation and shows/hides it.
        page_cards.append(
            {
                "type": "custom:layout-card",
                "layout_type": "custom:grid-layout",
                "layout": {
                    "grid-template-columns": "minmax(0, 1fr)",
                    "grid-gap": 0,
                    "margin": 0,
                    "padding": 0,
                    "card_margin": "0px",
                },
                "cards": [
                    {"type": "custom:button-card", "template": "fusion_page", "variables": {"page": view["path"]}}
                ]
                + content,
            }
        )

    new_main = {k: copy.deepcopy(v) for k, v in main.items() if k != "cards"}
    tabs = copy.deepcopy(tabs)
    tabs.get("variables", {}).pop("active", None)
    new_main["cards"] = [tabs] + page_cards

    config["views"] = [
        {
            "title": "Kiosk",
            "path": first["path"],
            "type": first["type"],
            "theme": first.get("theme"),
            "layout": first["layout"],
            "cards": [sidebar, new_main],
        }
    ]
    return config


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as f:
        source = yaml.safe_load(f)
    result = build(source)
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        json.dump(result, f, separators=(",", ":"))
    print("pages:", [c["cards"][0]["variables"]["page"] for c in result["views"][0]["cards"][1]["cards"][1:]])
