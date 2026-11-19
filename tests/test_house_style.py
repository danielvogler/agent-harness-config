"""The house-style skill's scripts: they run, write parseable SVG and honour the override."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from types import ModuleType

import pytest

SKILL = Path(__file__).resolve().parent.parent / "custom" / "skills" / "house-style"
SCRIPTS = SKILL / "scripts"
EXAMPLE = SKILL / "examples" / "architecture.py"
BANNER_ARGS = [
    "--title",
    "my-tool",
    "--suffix=-cli",
    "--eyebrow",
    "Data pipeline",
    "--description",
    "Loads the nightly feed into the warehouse.",
    "--side-chip",
    "make load",
    "--side-item",
    "Ingest",
    "--side-item",
    "Publish",
]


def load_script(name: str) -> ModuleType:
    """Import a script without leaving __pycache__ in the skill, which installs as it is."""
    sys.path.insert(0, str(SCRIPTS))
    writes_bytecode, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec = importlib.util.spec_from_file_location(f"house_style_{name}", SCRIPTS / f"{name}.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPTS))
        sys.dont_write_bytecode = writes_bytecode


def run(script: str, *args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A folder that looks like a repo root, so the override search stops here."""
    (tmp_path / ".git").mkdir()
    return tmp_path


def svg(path: Path) -> str:
    text = path.read_text()
    root = ET.fromstring(text)
    assert root.tag == "{http://www.w3.org/2000/svg}svg"
    return text


class TestBanner:
    def test_writes_both_themes_in_the_default_palette(self, repo):
        # Act
        result = run("banner.py", *BANNER_ARGS, cwd=repo)

        # Assert
        assert result.returncode == 0, result.stderr
        light = svg(repo / "docs" / "assets" / "banner-light.svg")
        dark = svg(repo / "docs" / "assets" / "banner-dark.svg")
        assert {"#FDFDFB", "#0E0E10", "#6F6F6B", "#1F6F5C"} <= set(_colours(light))
        assert {"#0E0E10", "#FDFDFB", "#5FBFA6"} <= set(_colours(dark))
        assert "my-tool" in light and "-cli" in light and "Ingest" in light

    def test_takes_accent_and_font_from_house_style_json(self, repo):
        # Arrange
        override = {"accent": "#b03a2e", "accent_dark": "#E8857A", "font": "Source Sans 3"}
        (repo / ".house-style.json").write_text(json.dumps(override))

        # Act
        result = run("banner.py", *BANNER_ARGS, "--out", "out", cwd=repo)

        # Assert
        assert result.returncode == 0, result.stderr
        light = svg(repo / "out" / "banner-light.svg")
        dark = svg(repo / "out" / "banner-dark.svg")
        assert "#B03A2E" in light and "#1F6F5C" not in light
        assert "#E8857A" in dark and "#5FBFA6" not in dark
        assert 'font-family="Source Sans 3, Inter' in light

    def test_finds_the_override_from_a_subfolder(self, repo):
        # Arrange
        (repo / ".house-style.json").write_text('{"accent": "#123456"}')
        sub = repo / "docs"
        sub.mkdir()

        # Act
        run("banner.py", *BANNER_ARGS, "--out", ".", cwd=sub)

        # Assert
        assert "#123456" in (sub / "banner-light.svg").read_text()

    @pytest.mark.parametrize(
        ("override", "message"),
        [
            ({"accent": "green"}, "#RRGGBB"),
            ({"accnet": "#123456"}, "unknown keys"),
        ],
    )
    def test_rejects_a_bad_override(self, repo, override, message):
        # Arrange
        (repo / ".house-style.json").write_text(json.dumps(override))

        # Act
        result = run("banner.py", *BANNER_ARGS, cwd=repo)

        # Assert
        assert result.returncode != 0
        assert message in result.stderr

    def test_warns_and_exits_1_when_the_description_cannot_fit(self, repo):
        # Act
        result = run(
            "banner.py", "--title", "x", "--description", "word " * 80, "--out", ".", cwd=repo
        )

        # Assert
        assert result.returncode == 1
        assert "description" in result.stderr
        svg(repo / "banner-light.svg")


class TestDiagram:
    def test_draws_the_example_in_both_themes(self, repo):
        # Act
        result = run("diagram.py", str(EXAMPLE), "--out", ".", cwd=repo)

        # Assert
        assert result.returncode == 0, result.stderr + result.stdout
        light = svg(repo / "architecture-light.svg")
        dark = svg(repo / "architecture-dark.svg")
        assert "#1F6F5C" in light and "#5FBFA6" in dark
        assert "Answer service" in light and "TO CHOOSE" in light

    def test_takes_the_accent_from_house_style_json(self, repo):
        # Arrange
        (repo / ".house-style.json").write_text('{"accent": "#B03A2E"}')

        # Act
        run("diagram.py", str(EXAMPLE), "--out", ".", cwd=repo)

        # Assert
        light = svg(repo / "architecture-light.svg")
        assert "#B03A2E" in light and "#1F6F5C" not in light

    def test_reads_a_json_description(self, repo):
        # Arrange
        data = {
            "title": "Two tiles",
            "zones": [{"id": "z", "label": "Cloud", "kind": "cloud"}],
            "tiles": [
                {"id": "a", "zone": "z", "col": 0, "row": 0, "title": "Web"},
                {"id": "b", "zone": "z", "col": 1, "row": 0, "title": "Store"},
            ],
            "arrows": [{"from": "a", "to": "b", "label": "writes", "step": 1}],
        }
        (repo / "d.json").write_text(json.dumps(data))

        # Act
        result = run("diagram.py", "d.json", "--name", "two", cwd=repo)

        # Assert
        assert result.returncode == 0, result.stderr
        assert "writes" in svg(repo / "two-light.svg")

    def test_rejects_a_tile_in_an_unknown_zone(self, repo):
        # Arrange
        data = {
            "zones": [],
            "tiles": [{"id": "a", "zone": "nowhere", "col": 0, "row": 0, "title": "A"}],
        }
        (repo / "d.json").write_text(json.dumps(data))

        # Act
        result = run("diagram.py", "d.json", cwd=repo)

        # Assert
        assert result.returncode != 0
        assert "unknown zone" in result.stderr

    def test_no_arrow_runs_through_a_tile(self):
        # Arrange
        diagram = load_script("diagram")
        data = diagram.load_description(EXAMPLE)
        tiles = {t["id"]: t for t in data["tiles"]}
        grid = diagram.Grid(list(tiles.values()))

        # Act
        routes = diagram.route_all(data, tiles, grid)

        # Assert
        for points in routes:
            for a, b in zip(points, points[1:], strict=False):
                for tile in tiles.values():
                    x, y, w, h = grid.box(tile)
                    inner = (x + 1, y + 1, w - 2, h - 2)
                    assert not diagram.overlaps(diagram.seg_box(a, b, pad=0), inner), (a, b, tile)


class TestReport:
    def test_template_has_the_placeholders_and_both_themes(self):
        # Act
        html = (SKILL / "templates" / "report.html").read_text()

        # Assert
        for key in ("title", "eyebrow", "toc", "body", "footer"):
            assert "{{" + key + "}}" in html
        assert "prefers-color-scheme: dark" in html
        assert "position: sticky" in html and ".chip" in html

    def test_palette_override_reaches_both_css_blocks(self, repo):
        # Arrange
        report = load_script("report")
        palette = load_script("palette")
        (repo / ".house-style.json").write_text('{"accent": "#B03A2E", "accent_dark": "#E8857A"}')
        template = (SKILL / "templates" / "report.html").read_text()

        # Act
        html = report.apply_palette(template, palette.load(repo))

        # Assert
        assert "--accent: #B03A2E;" in html and "--accent: #E8857A;" in html
        assert "#1F6F5C" not in html and "#5FBFA6" not in html

    def test_converts_markdown_when_the_package_is_there(self):
        # Arrange
        pytest.importorskip("markdown")
        report = load_script("report")

        # Act
        title, body, toc = report.convert(
            "# Review\n\n## Findings\n\n| a | b |\n|---|---|\n| 1 | 2 |\n"
        )

        # Assert
        assert title == "Review"
        assert "<table>" in body and 'href="#findings"' in toc


def _colours(text: str) -> list[str]:
    return [c.upper() for c in re.findall(r"#[0-9A-Fa-f]{6}\b", text)]
