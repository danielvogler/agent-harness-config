"""The house-style skill's scripts: they run, write parseable SVG and honour the override."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
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

    def test_skips_the_visual_key_that_check_visual_reads(self, repo):
        # Arrange
        override = {"accent": "#123456", "visual": {"extraPhrases": ["synergy"]}}
        (repo / ".house-style.json").write_text(json.dumps(override))

        # Act
        result = run("banner.py", *BANNER_ARGS, "--out", ".", cwd=repo)

        # Assert
        assert result.returncode == 0, result.stderr
        assert "#123456" in (repo / "banner-light.svg").read_text()

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


class TestVisualRules:
    def test_starter_takes_the_accent_into_both_css_blocks(self, repo):
        # Arrange
        (repo / ".house-style.json").write_text('{"accent": "#B03A2E", "accent_dark": "#E8857A"}')

        # Act
        result = run("starter.py", "out", "--example", cwd=repo)

        # Assert
        assert result.returncode == 0, result.stderr
        css = (repo / "out" / "starter.css").read_text()
        assert "--accent: #B03A2E;" in css and "--accent: #E8857A;" in css
        assert 'href="starter.css"' in (repo / "out" / "example.html").read_text()

    def test_every_banned_phrase_is_a_valid_pattern(self):
        # Arrange
        lines = (SKILL / "references" / "banned-phrases.txt").read_text().splitlines()
        patterns = [
            re.sub(r"^head: ", "", line) for line in lines if line and not line.startswith("#")
        ]

        # Act
        compiled = [re.compile(p, re.IGNORECASE) for p in patterns]

        # Assert
        assert len(compiled) > 20
        assert compiled[0].search("a Seamless flow")

    def test_starter_keeps_the_look_where_the_repo_sets_nothing(self, repo):
        # Arrange: the repo sets only its accent
        (repo / ".house-style.json").write_text('{"accent": "#B03A2E"}')

        # Act
        result = run("starter.py", "out", cwd=repo)

        # Assert
        assert result.returncode == 0, result.stderr
        css = (repo / "out" / "starter.css").read_text()
        assert "--accent: #B03A2E;" in css
        assert "--paper: #FDFDFB;" in css and "--ink: #0E0E10;" in css

    def test_starter_matches_every_token_in_look_md(self):
        # Arrange: the colour table of look.md, light and dark columns
        look = (SKILL / "references" / "look.md").read_text()
        css = (SKILL / "assets" / "starter.css").read_text()
        light_css, dark_css = css.split("@media (prefers-color-scheme: dark)", 1)
        rows = re.findall(r"^\| `(--[a-z0-9-]+)`(?: / `[^`]+`)? \| (.+?) \| (.+?) \|", look, re.M)

        # Act
        missing = []
        for token, light, dark in rows:
            names = [token, token + "-bg"] if " / " in light else [token]
            for name, lv, dv in zip(names, _colours(light), _colours(dark)):
                if f"{name}: {lv};" not in light_css:
                    missing.append(f"{name} light {lv}")
                if dv and dv not in ("SAME",) and f"{name}: {dv};" not in dark_css:
                    missing.append(f"{name} dark {dv}")

        # Assert
        assert len(rows) >= 11
        assert not missing, missing

    def test_example_flow_svgs_match_their_description(self, repo):
        # Act
        result = run(
            "diagram.py",
            str(SKILL / "assets" / "example_flow.py"),
            "--out",
            str(repo),
            "--name",
            "example-flow",
            cwd=repo,
        )

        # Assert
        assert result.returncode == 0, result.stderr
        for theme in ("light", "dark"):
            name = f"example-flow-{theme}.svg"
            assert (repo / name).read_text() == (SKILL / "assets" / name).read_text()

    def test_starter_puts_the_logo_and_mark_into_the_example(self, repo):
        # Arrange
        (repo / ".house-style.json").write_text(
            '{"accent": "#B03A2E", "visual": {"logo": "docs/logo.svg", "mark": "M2 2h12v12H2Z"}}'
        )

        # Act
        result = run("starter.py", "out", "--example", cwd=repo)

        # Assert
        assert result.returncode == 0, result.stderr
        page = (repo / "out" / "example.html").read_text()
        assert '<img src="docs/logo.svg" alt="">' in page
        assert page.count('d="M2 2h12v12H2Z"') == 1
        assert (repo / "out" / "chips.js").read_text().startswith("// Every number chip")

    def test_starter_takes_the_fade_and_rejects_a_bad_one(self, repo):
        # Arrange
        (repo / ".house-style.json").write_text(
            '{"visual": {"fade": ["#FF000D 0%", "#C0122F 50%", "#7A1236 100%"]}}'
        )

        # Act
        good = run("starter.py", "out", cwd=repo)
        (repo / ".house-style.json").write_text('{"visual": {"fade": ["red", "wine"]}}')
        bad = run("starter.py", "out2", cwd=repo)

        # Assert
        assert good.returncode == 0, good.stderr
        css = (repo / "out" / "starter.css").read_text()
        assert "--fade: linear-gradient(90deg, #FF000D 0%, #C0122F 50%, #7A1236 100%);" in css
        assert "--fade-v: linear-gradient(180deg, #FF000D 0%" in css
        assert "--num: #C0122F;" in css
        assert bad.returncode != 0 and "visual.fade" in bad.stderr

    def test_starter_takes_the_ramp_hue(self, repo):
        # Arrange
        (repo / ".house-style.json").write_text('{"visual": {"ramp": "#7A1236"}}')

        # Act
        result = run("starter.py", "out", cwd=repo)

        # Assert
        assert result.returncode == 0, result.stderr
        assert "--ramp: #7A1236;" in (repo / "out" / "starter.css").read_text()

    def test_red_accent_turns_good_to_ink_and_the_ramp_to_the_deep_stop(self, repo):
        # Arrange: a red brand with a three-stop fade and no ramp of its own
        (repo / ".house-style.json").write_text(json.dumps(
            {"accent": "#FF000D", "visual": {"fade": ["#FF000D 0%", "#C0122F 50%", "#7A1236 100%"]}}))

        # Act
        result = run("starter.py", "out", cwd=repo)

        # Assert
        assert result.returncode == 0, result.stderr
        css = (repo / "out" / "starter.css").read_text()
        assert "--ok: var(--ink); --ok-bg: var(--sunk);" in css
        assert "--ramp: #7A1236;" in css

    def test_green_accent_keeps_good_in_the_accent(self, repo):
        # Arrange
        (repo / ".house-style.json").write_text('{"accent": "#1F6F5C"}')

        # Act
        result = run("starter.py", "out", cwd=repo)

        # Assert
        assert result.returncode == 0, result.stderr
        assert "--ok: var(--accent);" in (repo / "out" / "starter.css").read_text()

    def test_dark_fade_and_font_file_reach_the_stylesheet(self, repo):
        # Arrange
        (repo / "docs").mkdir()
        (repo / ".house-style.json").write_text(json.dumps({"font": "Brand Sans", "visual": {
            "fade_dark": ["#FF5A63 0%", "#E0475A 50%", "#B23A5C 100%"], "font_file": "docs/brand.woff2"}}))

        # Act
        result = run("starter.py", "out", cwd=repo)

        # Assert
        assert result.returncode == 0, result.stderr
        css = (repo / "out" / "starter.css").read_text()
        dark = css.split("@media (prefers-color-scheme: dark)", 1)[1]
        assert "--fade: linear-gradient(90deg, #FF5A63 0%, #E0475A 50%, #B23A5C 100%);" in dark
        assert "--num: #E0475A;" in dark
        assert '@font-face { font-family: "Brand Sans"; src: url("../docs/brand.woff2")' in css

    def test_theme_toggle_copies_the_dark_tokens(self, repo):
        # Arrange
        (repo / ".house-style.json").write_text('{"accent": "#1F6F5C", "accent_dark": "#7FD6BE"}')

        # Act
        result = run("starter.py", "out", cwd=repo)

        # Assert: the toggle block carries the repo's dark accent too, and only once
        assert result.returncode == 0, result.stderr
        css = (repo / "out" / "starter.css").read_text()
        toggle = css.split(':root[data-theme="dark"] {', 1)[1]
        assert "--accent: #7FD6BE;" in toggle
        assert css.count("theme toggle: the dark tokens above") == 1

    def test_shipped_starter_has_a_current_theme_toggle(self):
        # Arrange
        starter = load_script("starter")
        css = (SKILL / "assets" / "starter.css").read_text()

        # Act
        regenerated = starter.theme_toggle(css)

        # Assert
        assert regenerated == css

    def test_starter_shows_the_dark_logo_in_the_dark_theme(self, repo):
        # Arrange
        (repo / ".house-style.json").write_text(json.dumps(
            {"visual": {"logo": "docs/logo.svg", "logo_dark": "docs/logo-dark.svg"}}))

        # Act
        result = run("starter.py", "out", "--example", cwd=repo)

        # Assert
        assert result.returncode == 0, result.stderr
        html = (repo / "out" / "example.html").read_text()
        assert '<img class="on-light" src="docs/logo.svg"' in html
        assert '<img class="on-dark" src="docs/logo-dark.svg"' in html

    def test_starter_implements_every_value_look_md_lists(self):
        # Arrange: the table of values in look.md §14, and the rules of starter.css
        look = (SKILL / "references" / "look.md").read_text()
        css = (SKILL / "assets" / "starter.css").read_text()
        section = look.split("## 14. Values the test holds", 1)[1]
        rows = re.findall(r"^\| [a-z ]+ \| `([^`]+)` \| `([^`]+)` \|$", section, re.M)

        # Act
        missing = []
        for selector, declaration in rows:
            blocks = re.findall(r"(?:^|\}|\n)\s*" + re.escape(selector) + r"\s*\{([^}]*)\}", css)
            if not any(declaration + ";" in b or b.strip().endswith(declaration) for b in blocks):
                missing.append(f"{selector} {{ {declaration} }}")

        # Assert
        assert len(rows) >= 40
        assert not missing, missing

    def test_brand_profile_writes_the_config_and_copies_its_files(self, repo, tmp_path_factory):
        # Arrange: a profile folder outside the repo, found through HOUSE_STYLE_BRANDS
        home = tmp_path_factory.mktemp("brands")
        (home / "acme").mkdir()
        (home / "acme" / "logo.svg").write_text("<svg/>")
        (home / "acme" / "mark.svg").write_text("<svg/>")
        (home / "acme" / "brand.json").write_text(json.dumps({
            "name": "Acme", "accent": "#B03A2E", "font": "Brand Sans",
            "fade": ["#B03A2E 0%", "#8E2E25 50%", "#5E1F19 100%"], "logo": "logo.svg", "mark": "mark.svg"}))

        # Act
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "brand.py"), "--brand", "acme", "--write"],
            cwd=repo, capture_output=True, text=True, check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "HOUSE_STYLE_BRANDS": str(home)},
        )

        # Assert
        assert result.returncode == 0, result.stderr
        config = json.loads((repo / ".house-style.json").read_text())
        assert config["accent"] == "#B03A2E" and config["font"] == "Brand Sans"
        assert config["visual"]["logo"] == "docs/assets/brand/logo.svg"
        assert (repo / "docs" / "assets" / "brand" / "mark.svg").is_file()

    def test_unknown_brand_profile_is_an_error(self, repo, tmp_path_factory):
        # Arrange
        home = tmp_path_factory.mktemp("brands")

        # Act
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "brand.py"), "--brand", "nobody"],
            cwd=repo, capture_output=True, text=True, check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "HOUSE_STYLE_BRANDS": str(home)},
        )

        # Assert
        assert result.returncode != 0 and "no brand profile 'nobody'" in result.stderr

    def test_detect_brand_writes_the_config_from_the_repo(self, repo):
        # Arrange: a logo, a favicon, a brand token and a font-face, no .house-style.json
        (repo / "assets" / "brand").mkdir(parents=True)
        (repo / "assets" / "brand" / "company-logo.svg").write_text("<svg/>")
        (repo / "public").mkdir()
        (repo / "public" / "favicon.svg").write_text("<svg/>")
        (repo / "web.css").write_text(
            ':root { --brand-primary: #b03a2e; }\n@font-face { font-family: "Brand Sans"; src: url(x.woff2); }'
        )

        # Act
        result = run("starter.py", "out", "--detect-brand", cwd=repo)

        # Assert
        assert result.returncode == 0, result.stderr
        config = json.loads((repo / ".house-style.json").read_text())
        assert config["accent"] == "#B03A2E" and config["font"] == "Brand Sans"
        assert config["visual"] == {"logo": "assets/brand/company-logo.svg", "mark": "public/favicon.svg"}
        assert "--accent: #B03A2E;" in (repo / "out" / "starter.css").read_text()

    def test_detect_brand_never_overwrites_the_config(self, repo):
        # Arrange
        (repo / ".house-style.json").write_text('{"accent": "#123456"}')
        (repo / "logo.svg").write_text("<svg/>")

        # Act
        result = run("brand.py", "--write", cwd=repo)

        # Assert
        assert result.returncode == 0
        assert (repo / ".house-style.json").read_text() == '{"accent": "#123456"}'

    def test_unknown_visual_key_is_an_error(self, repo):
        # Arrange
        (repo / ".house-style.json").write_text('{"visual": {"colours": ["#FF0000"]}}')

        # Act
        result = run("starter.py", "out", cwd=repo)

        # Assert
        assert result.returncode != 0
        assert "unknown visual keys" in result.stderr

    @pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
    def test_check_script_parses(self):
        # Act
        result = subprocess.run(
            ["node", "--check", str(SCRIPTS / "check_visual.js")],
            capture_output=True,
            text=True,
            check=False,
        )

        # Assert
        assert result.returncode == 0, result.stderr


def _can_render() -> bool:
    if shutil.which("node") is None:
        return False
    probe = subprocess.run(
        ["node", "-e", "require('playwright-core')"], capture_output=True, check=False
    )
    return probe.returncode == 0


BLAND_RASTER = """<!doctype html><html><head><link rel="stylesheet" href="starter.css"></head><body>
<main><div class="eyebrow"><b>Risks</b> · all items</div>
<h1 class="shows">Twelve risks by likelihood and impact</h1>
<p class="points"><span>12 risks</span><span>3 high</span></p>
<div class="raster">{cells}</div></main></body></html>"""


@pytest.mark.skipif(not _can_render(), reason="node with playwright-core is not available")
class TestCheckRenders:
    def test_example_page_passes(self):
        # Act
        result = subprocess.run(
            ["node", str(SCRIPTS / "check_visual.js"), str(SKILL / "assets" / "example.html")],
            capture_output=True, text=True, check=False,
        )

        # Assert
        assert result.returncode == 0, result.stdout + result.stderr

    def test_raster_of_neutral_chips_fails(self, tmp_path):
        # Arrange: twelve outlined ink chips on grey cells, the bland raster
        shutil.copy(SKILL / "assets" / "starter.css", tmp_path / "starter.css")
        chip = '<span class="n" style="background:none;border:1px solid #0E0E10">{}</span>'
        cells = "".join(
            f'<div class="y">{5 - r}</div>' + "".join(
                f'<div class="cell">{chip.format(r * 3 + c) if c < 3 else ""}</div>' for c in range(5)
            )
            for r in range(4)
        )
        page = tmp_path / "bland.html"
        page.write_text(BLAND_RASTER.format(cells=cells))

        # Act
        result = subprocess.run(
            ["node", str(SCRIPTS / "check_visual.js"), str(page)],
            capture_output=True, text=True, check=False,
        )

        # Assert
        assert result.returncode == 1
        assert "UNMARKED raster" in result.stdout

    def test_count_title_and_tall_head_fail(self, tmp_path):
        # Arrange: a title that opens with its count, the count again in the eyebrow and the
        # points, and a contents line plus key figures stacked under the head
        shutil.copy(SKILL / "assets" / "starter.css", tmp_path / "starter.css")
        page = tmp_path / "count.html"
        page.write_text("""<!doctype html><html><head><link rel="stylesheet" href="starter.css"></head><body>
<main><div class="eyebrow"><b>Risks</b> · 53 risks · for the board</div>
<h1 class="shows">53 risks of the group by likelihood and impact</h1>
<p class="points"><span>53 risks</span><span>7 high</span></p>
<p>On this page: overview, register, phases</p><p>Key figures: 53 risks, 50 placed</p>
<table><tr><td class="name">R1</td><td><span class="chip bad">late</span></td></tr>
<tr><td class="name">R2</td><td><span class="chip warn">waiting</span></td></tr></table></main></body></html>""")

        # Act
        result = subprocess.run(
            ["node", str(SCRIPTS / "check_visual.js"), str(page)],
            capture_output=True, text=True, check=False,
        )

        # Assert
        assert result.returncode == 1
        assert "FAIL  counts" in result.stdout and "FAIL  headrows" in result.stdout
        assert "FAIL  phrases" in result.stdout


FRAME = """<!doctype html><html><head><link rel="stylesheet" href="starter.css"></head><body>
<header class="top"><div class="top-row"><a class="brand" href="#"><svg viewBox="0 0 10 10"><rect width="10" height="10"/></svg>
<span class="board">Depot · plan</span></a>{tabs}</div></header>
<main class="paged"><nav class="toc"><p class="toc-name">Risks</p><ol>{toc}</ol></nav><div>
<div class="eyebrow">Assess · Risks</div><h1 class="title">Which <span class="em">risks</span> the depot carries</h1>
<p class="points"><span>likelihood and impact</span><span>estimated</span></p>{body}</div></main></body></html>"""
MARKED_TABLE = ('<div class="table">' + "<table><thead><tr><th>Item</th><th>Status</th></tr></thead><tbody>"
                + "".join(f'<tr><td class="name"><b>Item {i}</b></td><td><span class="chip warn">waiting</span></td></tr>'
                          for i in range(6)) + "</tbody></table></div>")


def _check_page(tmp_path: Path, tabs: str, toc: str = "<li><a href='#a'><b>1.1</b><span>Overview</span></a></li>",
                body: str = MARKED_TABLE, extra: str = "") -> subprocess.CompletedProcess:
    shutil.copy(SKILL / "assets" / "starter.css", tmp_path / "starter.css")
    page = tmp_path / "frame.html"
    page.write_text(FRAME.format(tabs=tabs, toc=toc, body=body + extra))
    return subprocess.run(["node", str(SCRIPTS / "check_visual.js"), str(page)],
                          capture_output=True, text=True, check=False)


@pytest.mark.skipif(not _can_render(), reason="node with playwright-core is not available")
class TestCheckFrame:
    def test_header_row_is_not_a_content_row(self, tmp_path):
        # Arrange: a header whose .top-row has no coloured mark, and a fully marked table
        tabs = '<nav class="tabs"><a class="on" href="#">Assess</a><a href="#">Plan</a></nav>'

        # Act
        result = _check_page(tmp_path, tabs)

        # Assert
        assert "PASS  marks" in result.stdout, result.stdout

    def test_weight_class_is_not_a_heading(self, tmp_path):
        # Arrange: the same number in sliders wrapped in .weight, once in the points
        tabs = '<nav class="tabs"><a class="on" href="#">Assess</a></nav>'
        sliders = "".join(f'<div class="weight">{n} 5</div>' for n in ("Cost", "Speed", "Fit", "Risk"))

        # Act
        result = _check_page(tmp_path, tabs, extra=sliders)

        # Assert
        assert "PASS  counts" in result.stdout, result.stdout

    def test_logo_link_and_labelled_page_group_count_once(self, tmp_path):
        # Arrange: four groups, a hairline and eight pages in a labelled group: 4 + 1 items
        groups = "".join(f'<a href="#">G{i}</a>' for i in range(4))
        pages = "".join(f'<a class="pg" href="#">Page {i}</a>' for i in range(8))
        tabs = (f'<nav class="tabs" aria-label="Groups">{groups}<span class="sep"></span>'
                f'<span class="pages" aria-label="Pages">{pages}</span></nav>')

        # Act
        result = _check_page(tmp_path, tabs)

        # Assert
        nav = next(line for line in result.stdout.splitlines() if " nav " in line)
        assert nav.startswith("PASS"), nav

    def test_long_left_column_label_fails(self, tmp_path):
        # Arrange: a section title used whole as the left-column label
        tabs = '<nav class="tabs"><a class="on" href="#">Assess</a></nav>'
        toc = ("<li><a href='#a'><b>1.1</b><span>Runners compete; the gate follows the runner; trigger, "
               "state and supervision stack</span></a></li>")

        # Act
        result = _check_page(tmp_path, tabs, toc=toc)

        # Assert
        assert "FAIL  contents" in result.stdout, result.stdout


def _colours(text: str) -> list[str]:
    return [c.upper() for c in re.findall(r"#[0-9A-Fa-f]{6}\b", text)]
