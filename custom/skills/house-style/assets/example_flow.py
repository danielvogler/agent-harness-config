"""Example hero picture for a README, drawn by diagram.py: a left-to-right flow, numbered
main steps, one colour per kind of place with a legend. The content is invented."""

DIAGRAM = {
    "eyebrow": "Fleet renewal",
    "title": "How a night charging plan is made",
    "zones": [
        {"id": "people", "label": "People", "kind": "people"},
        {"id": "cloud", "label": "Planning service", "kind": "cloud", "pill": "europe-west6"},
        {"id": "outside", "label": "Outside services", "kind": "outside"},
    ],
    "tiles": [
        {"id": "planner", "zone": "people", "col": 0, "row": 0, "title": "Depot planner",
         "product": "Web browser", "runs": ["Uploads the timetable,", "reads the plan"],
         "glyph": "P", "color": "#6F6F6B"},
        {"id": "api", "zone": "cloud", "col": 1, "row": 0, "title": "Plan service",
         "product": "Cloud Run", "runs": ["Splits the routes", "into charging slots"],
         "mark": "cloud", "glyph": "R"},
        {"id": "store", "zone": "cloud", "col": 2, "row": 0, "title": "Plans and runs",
         "product": "BigQuery", "runs": ["One table per night", "kept for a year"],
         "mark": "cloud", "glyph": "B"},
        {"id": "grid", "zone": "outside", "col": 2, "row": 1, "title": "Grid load",
         "product": "Utility API", "runs": ["Hourly limit for", "the depot connection"],
         "glyph": "U", "color": "#7C5CC4", "status": "planned"},
    ],
    "arrows": [
        {"from": "planner", "to": "api", "label": "uploads", "step": 1,
         "note": "The planner uploads the timetable"},
        {"from": "api", "to": "store", "label": "writes", "step": 2,
         "note": "The service writes the plan"},
        {"from": "grid", "to": "api", "label": "limits", "kind": "support"},
    ],
}
