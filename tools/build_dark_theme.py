"""Rebuild the generated dark-theme CSS.

The site is designed in light colours. For the dark theme, every colour
declaration in the light styles gets a "twin" that applies only when the page
has <html data-theme="dark">:

- light backgrounds become dark surfaces (pure white cards stay a little
  lighter than the near-white page so cards still stand out),
- dark text becomes light text,
- light borders become dark borders,
- accent colours (blue buttons, the dark footer, coloured badges) stay.

Twins set colour properties only, so widths, layouts and spacing still come
from the light rules. They keep the light rules' order and each one is one step
more specific, so the cascade works the same way in both themes. Print keeps
the light colours (all twins sit inside @media screen). Resume "paper"
previews keep their light colours, like a real document.

Sources and outputs:
- frontend/tailwind.css and frontend/account_workspace.css
  -> the block between the dark-theme markers at the end of account_workspace.css
- the first <style> block of each page
  -> <style id="darkThemeGenerated"> right after that block

Hand-tuned dark rules (colour variables, a few components) live after the
generated blocks and are never overwritten.

Run after changing any of those light styles: python tools/build_dark_theme.py
"""

from __future__ import annotations

import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
TAILWIND = FRONTEND / "tailwind.css"
SHARED_CSS = FRONTEND / "account_workspace.css"
PAGES = ("home_page.html", "analysis_result.html", "job_data_insights.html")

DARK = 'html[data-theme="dark"]'
CSS_START = "/* dark-theme:generated:start - built by tools/build_dark_theme.py from the light rules; do not edit by hand */"
CSS_END = "/* dark-theme:generated:end */"
PAGE_STYLE_ID = "darkThemeGenerated"

# Selectors for resume "paper" previews: their colours are kept as they are.
PAPER_SELECTORS = (".career-draft-page", ".sample-resume-sheet")

# Accent variables that are dark enough for button backgrounds but too dark for
# text on a dark page. When they are used as a text colour, the twin reads
# var(--name-text, var(--name)) so the dark theme can give text a lighter shade.
TEXT_VARIABLE_ALIASES = {
    "career-teal", "career-teal-deep", "studio-teal", "studio-teal-dark", "admin-teal", "admin-teal-deep",
}

TEXT_PROPS = {
    "color", "caret-color", "text-decoration-color", "-webkit-text-fill-color",
    "-webkit-text-stroke-color", "column-rule-color",
}
BORDER_COLOR_PROPS = {
    "border-color", "border-top-color", "border-right-color", "border-bottom-color", "border-left-color",
    "border-block-color", "border-inline-color", "border-block-start-color", "border-block-end-color",
    "border-inline-start-color", "border-inline-end-color", "outline-color",
}
BORDER_SHORTHANDS = {
    "border", "border-top", "border-right", "border-bottom", "border-left", "border-block", "border-inline",
    "border-block-start", "border-block-end", "border-inline-start", "border-inline-end",
}
GRAPHIC_PROPS = {"fill", "stroke", "stop-color", "flood-color", "lighting-color"}
SHADOW_PROPS = {"box-shadow", "text-shadow"}
BORDER_STYLES = {"none", "hidden", "dotted", "dashed", "solid", "double", "groove", "ridge", "inset", "outset", "auto"}
NAMED_COLORS = {"white": (255, 255, 255), "black": (0, 0, 0)}
GROUP_AT_RULES = {"@media", "@supports", "@container", "@layer"}


# ---------------------------------------------------------------- colour maths

def _linear(channel: float) -> float:
    channel /= 255
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def _encode(channel: float) -> int:
    channel = min(1.0, max(0.0, channel))
    value = 12.92 * channel if channel <= 0.0031308 else 1.055 * channel ** (1 / 2.4) - 0.055
    return round(value * 255)


def to_oklab(red: float, green: float, blue: float) -> tuple[float, float, float]:
    r, g, b = _linear(red), _linear(green), _linear(blue)
    l_ = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m_ = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def from_oklab(lightness: float, a: float, b: float) -> tuple[int, int, int]:
    l_ = lightness + 0.3963377774 * a + 0.2158037573 * b
    m_ = lightness - 0.1055613458 * a - 0.0638541728 * b
    s_ = lightness - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    return (
        _encode(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s),
        _encode(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s),
        _encode(-0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s),
    )


# Grey surfaces get a faint blue tint so the dark theme keeps the site's colour.
NEUTRAL_HUE = (-0.259, -0.966)  # OKLab direction of the brand blue


def _with(lightness: float, a: float, b: float, chroma: float, tint: float = 0.0) -> tuple[int, int, int]:
    current = math.hypot(a, b)
    if current < 0.012 and tint:
        return from_oklab(lightness, NEUTRAL_HUE[0] * tint, NEUTRAL_HUE[1] * tint)
    scale = chroma / current if current > 1e-6 else 0.0
    return from_oklab(lightness, a * scale, b * scale)


def map_rgb(rgb: tuple[float, float, float], alpha: float, role: str) -> tuple[int, int, int] | None:
    """Dark-theme colour for one light-theme colour, or None to keep it."""
    lightness, a, b = to_oklab(*rgb)
    chroma = math.hypot(a, b)
    if role in ("border", "shadow", "background") and alpha < 0.5:
        return None  # faint overlays (mostly on the already-dark footer)
    if role == "graphic":
        role = "border" if lightness > 0.85 else ("text" if lightness < 0.45 else "keep")
    if role == "background":
        if lightness >= 0.995:  # white cards: the lightest dark surface
            return _with(0.262, a, b, min(chroma * 1.5, 0.02), tint=0.016)
        if lightness >= 0.94:  # near-white page and section tints
            return _with(0.205 + (0.995 - lightness) * 0.85, a, b, min(chroma * 1.6, 0.03), tint=0.014)
        if lightness >= 0.62:  # light tints (chips, badges, hover states)
            return _with(0.27 + (0.94 - lightness) * 0.35, a, b, min(chroma * 1.3, 0.06), tint=0.014)
        if lightness < 0.36 and chroma > 0.06:  # navy buttons would vanish on a dark page
            return _with(0.47, a, b, chroma)
        return None
    if role == "text":
        if lightness <= 0.66:
            return _with(0.97 - lightness * 0.42, a, b, chroma, tint=0.012)
        return None
    if role in ("border", "shadow"):
        if lightness > 0.62:
            return _with(0.33 + (1 - lightness) * 0.3, a, b, min(chroma * 1.3, 0.05), tint=0.018)
        return None
    return None


# ---------------------------------------------------------------- CSS parsing

def strip_comments(css: str) -> str:
    out, index, size = [], 0, len(css)
    while index < size:
        char = css[index]
        if char in "\"'":
            end = index + 1
            while end < size and css[end] != char:
                end += 2 if css[end] == "\\" else 1
            out.append(css[index:end + 1])
            index = end + 1
        elif css.startswith("/*", index):
            end = css.find("*/", index + 2)
            index = size if end < 0 else end + 2
        else:
            out.append(char)
            index += 1
    return "".join(out)


def _skip_string(text: str, index: int) -> int:
    quote, index = text[index], index + 1
    while index < len(text) and text[index] != quote:
        index += 2 if text[index] == "\\" else 1
    return index


def _matching_brace(css: str, open_index: int) -> int:
    depth, index = 0, open_index
    while index < len(css):
        char = css[index]
        if char in "\"'":
            index = _skip_string(css, index)
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return len(css)


def _next_structural(css: str, index: int) -> int:
    depth = 0
    while index < len(css):
        char = css[index]
        if char in "\"'":
            index = _skip_string(css, index)
        elif char in "([":
            depth += 1
        elif char in ")]":
            depth -= 1
        elif depth == 0 and char in "{};":
            return index
        index += 1
    return -1


def parse_blocks(css: str) -> list:
    """("rule", selector, body) and ("group", at-rule prelude, children) nodes."""
    nodes, index = [], 0
    while True:
        stop = _next_structural(css, index)
        if stop < 0:
            return nodes
        prelude = css[index:stop].strip()
        if css[stop] in ";}":
            index = stop + 1
            continue
        end = _matching_brace(css, stop)
        body = css[stop + 1:end]
        if prelude.startswith("@"):
            name = prelude.split(None, 1)[0].lower()
            if name in GROUP_AT_RULES:
                nodes.append(("group", prelude, parse_blocks(body)))
            # @keyframes, @font-face, @page and similar are left alone.
        elif prelude:
            nodes.append(("rule", prelude, body))
        index = end + 1


def split_top_level(text: str, separator: str) -> list[str]:
    parts, depth, start, index = [], 0, 0, 0
    while index < len(text):
        char = text[index]
        if char in "\"'":
            index = _skip_string(text, index)
        elif char in "([":
            depth += 1
        elif char in ")]":
            depth -= 1
        elif char == separator and depth == 0:
            parts.append(text[start:index])
            start = index + 1
        index += 1
    parts.append(text[start:])
    return parts


def parse_declarations(body: str) -> list[tuple[str, str, bool]]:
    declarations = []
    for part in split_top_level(body, ";"):
        if ":" not in part:
            continue
        prop, _, value = part.partition(":")
        prop, value = prop.strip().lower(), value.strip()
        important = bool(re.search(r"!\s*important\s*$", value, re.I))
        value = re.sub(r"\s*!\s*important\s*$", "", value, flags=re.I)
        if prop and value:
            declarations.append((prop, value, important))
    return declarations


# ---------------------------------------------------------------- value mapping

def _close_paren(text: str, open_index: int) -> int:
    depth, index = 0, open_index
    while index < len(text):
        char = text[index]
        if char in "\"'":
            index = _skip_string(text, index)
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return len(text) - 1


def _format(rgb: tuple[int, int, int], alpha: float, alpha_text: str | None) -> str:
    if alpha_text and "var(" in alpha_text:
        return f"rgb({rgb[0]} {rgb[1]} {rgb[2]}/{alpha_text.strip()})"
    if alpha < 1:
        return f"rgba({rgb[0]},{rgb[1]},{rgb[2]},{alpha_text.strip() if alpha_text else alpha})"
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _parse_alpha(alpha_text: str | None) -> float:
    if not alpha_text or "var(" in alpha_text:
        return 1.0
    alpha_text = alpha_text.strip()
    return float(alpha_text[:-1]) / 100 if alpha_text.endswith("%") else float(alpha_text)


def _hsl_to_rgb(hue: float, saturation: float, light: float) -> tuple[float, float, float]:
    chroma = (1 - abs(2 * light - 1)) * saturation
    x = chroma * (1 - abs((hue / 60) % 2 - 1))
    m = light - chroma / 2
    sector = int(hue // 60) % 6
    r, g, b = [(chroma, x, 0), (x, chroma, 0), (0, chroma, x), (0, x, chroma), (x, 0, chroma), (chroma, 0, x)][sector]
    return (r + m) * 255, (g + m) * 255, (b + m) * 255


def _map_function(text: str, role: str) -> str:
    name = text[:text.index("(")].lower()
    args = text[text.index("(") + 1:-1]
    main, _, alpha_text = args.partition("/")
    parts = [part for part in re.split(r"[\s,]+", main.strip()) if part]
    alpha_text = alpha_text or None
    if len(parts) == 4 and alpha_text is None:
        alpha_text = parts.pop()
    try:
        if name.startswith("rgb"):
            rgb = tuple(float(part[:-1]) * 2.55 if part.endswith("%") else float(part) for part in parts[:3])
        else:
            hue = float(re.sub(r"deg$", "", parts[0]))
            rgb = _hsl_to_rgb(hue % 360, float(parts[1].rstrip("%")) / 100, float(parts[2].rstrip("%")) / 100)
        alpha = _parse_alpha(alpha_text)
    except (ValueError, IndexError):
        return text
    mapped = map_rgb(rgb, alpha, role)
    return text if mapped is None else _format(mapped, alpha, alpha_text)


def _map_hex(digits: str, role: str) -> str | None:
    if len(digits) in (3, 4):
        digits = "".join(char * 2 for char in digits)
    if len(digits) not in (6, 8):
        return None
    rgb = tuple(int(digits[index:index + 2], 16) for index in (0, 2, 4))
    alpha = int(digits[6:8], 16) / 255 if len(digits) == 8 else 1.0
    mapped = map_rgb(rgb, alpha, role)
    if mapped is None:
        return None
    return _format(mapped, alpha, None) if alpha >= 1 else "rgba({},{},{},{:.3f})".format(*mapped, alpha)


def map_value(value: str, role: str) -> str:
    """Map every colour inside a CSS value; url(...) contents are never touched."""
    out, index = [], 0
    while index < len(value):
        rest = value[index:]
        if re.match(r"url\(", rest, re.I):
            end = _close_paren(value, index + 3)
            out.append(value[index:end + 1])
            index = end + 1
            continue
        function = re.match(r"(rgba?|hsla?)\(", rest, re.I)
        if function:
            end = _close_paren(value, index + len(function.group(0)) - 1)
            out.append(_map_function(value[index:end + 1], role))
            index = end + 1
            continue
        if role == "text":
            variable = re.match(r"var\(\s*--([\w-]+)\s*\)", rest)
            if variable and variable.group(1) in TEXT_VARIABLE_ALIASES:
                name = variable.group(1)
                out.append(f"var(--{name}-text, var(--{name}))")
                index += len(variable.group(0))
                continue
        hex_color = re.match(r"#([0-9a-fA-F]{3,8})(?![0-9a-zA-Z])", rest)
        if hex_color:
            mapped = _map_hex(hex_color.group(1), role)
            out.append(mapped or hex_color.group(0))
            index += len(hex_color.group(0))
            continue
        word = re.match(r"[A-Za-z][\w-]*", rest)
        if word:
            token = word.group(0)
            if token.lower() in NAMED_COLORS and (index == 0 or not value[index - 1].isalnum()):
                mapped = map_rgb(NAMED_COLORS[token.lower()], 1.0, role)
                out.append(_format(mapped, 1.0, None) if mapped else token)
            else:
                out.append(token)
            index += len(token)
            continue
        out.append(value[index])
        index += 1
    return "".join(out)


def _split_space(value: str) -> list[str]:
    tokens, depth, current = [], 0, ""
    for char in value:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        if char.isspace() and depth == 0:
            if current:
                tokens.append(current)
            current = ""
        else:
            current += char
    if current:
        tokens.append(current)
    return tokens


def _is_width(token: str) -> bool:
    return bool(re.fullmatch(r"-?[\d.]+(px|em|rem|%|vw|vh|ch|ex|pt)?|thin|medium|thick|calc\(.*\)", token, re.I))


def _color_token(value: str) -> str | None:
    for token in _split_space(value):
        if token.lower() in BORDER_STYLES or _is_width(token):
            continue
        return token
    return None


IMAGE_FUNCTION = re.compile(r"(?:repeating-)?(?:linear|radial|conic)-gradient\(|url\(|image-set\(|-webkit-image-set\(", re.I)


def _background_parts(value: str) -> tuple[str, str]:
    """(image layers, colour) of a background shorthand."""
    images, colour = [], None
    for layer in split_top_level(value, ","):
        rest, layer_images = layer, []
        while True:
            match = IMAGE_FUNCTION.search(rest)
            if not match:
                break
            end = _close_paren(rest, match.end() - 1)
            layer_images.append(rest[match.start():end + 1])
            rest = rest[:match.start()] + " " + rest[end + 1:]
        images.append(layer_images[0] if layer_images else "none")
        for token in _split_space(rest):
            low = token.lower()
            if (low.startswith(("#", "rgb", "hsl", "var(")) or low in NAMED_COLORS
                    or low in ("transparent", "currentcolor", "inherit", "initial", "unset")):
                colour = token
    if all(image == "none" for image in images):
        image_text = "none"
    else:
        image_text = ", ".join(images)
    return image_text, colour or "transparent"


def twin_declarations(declarations, keep_colours: bool) -> list[str]:
    """Colour-only twin declarations for one rule."""
    def mapped(value: str, role: str) -> str:
        return value if keep_colours else map_value(value, role)

    out = []
    for prop, value, important in declarations:
        suffix = " !important" if important else ""
        if prop.startswith("--"):
            continue
        if prop in TEXT_PROPS:
            out.append(f"{prop}:{mapped(value, 'text')}{suffix}")
        elif prop == "background-color":
            out.append(f"{prop}:{mapped(value, 'background')}{suffix}")
        elif prop == "background-image":
            out.append(f"{prop}:{mapped(value, 'background')}{suffix}")
        elif prop == "background":
            if value.lower() in ("inherit", "initial", "unset", "revert"):
                out.append(f"background-color:{value}{suffix}")
                out.append(f"background-image:{value}{suffix}")
                continue
            image, colour = _background_parts(value)
            out.append(f"background-image:{mapped(image, 'background')}{suffix}")
            out.append(f"background-color:{mapped(colour, 'background')}{suffix}")
        elif prop in BORDER_COLOR_PROPS:
            out.append(f"{prop}:{mapped(value, 'border')}{suffix}")
        elif prop in BORDER_SHORTHANDS:
            colour = _color_token(value) or "currentcolor"
            out.append(f"{prop}-color:{mapped(colour, 'border')}{suffix}")
        elif prop == "outline":
            colour = _color_token(value)
            if colour:
                out.append(f"outline-color:{mapped(colour, 'border')}{suffix}")
        elif prop == "text-decoration":
            colour = _color_token(value)
            if colour and not re.fullmatch(r"none|underline|overline|line-through|blink|wavy|solid|double|dotted|dashed", colour, re.I):
                out.append(f"text-decoration-color:{mapped(colour, 'text')}{suffix}")
        elif prop in GRAPHIC_PROPS:
            out.append(f"{prop}:{mapped(value, 'graphic')}{suffix}")
        elif prop in SHADOW_PROPS:
            out.append(f"{prop}:{mapped(value, 'shadow')}{suffix}")
    return out


def prefix_selector(selector: str) -> str | None:
    selector = selector.strip()
    low = selector.lower()
    if not selector or "[data-theme" in low:
        return None
    if low.startswith(":root"):
        return DARK + selector[5:]
    if re.match(r"html(?![\w-])", low):
        return DARK + selector[4:]
    return f"{DARK} {selector}"


def build(nodes) -> list[str]:
    out = []
    for node in nodes:
        if node[0] == "group":
            prelude = node[1]
            if re.search(r"\bprint\b", prelude, re.I) and not re.search(r"\bscreen\b", prelude, re.I):
                continue
            inner = build(node[2])
            if inner:
                out.append(prelude + "{\n" + "\n".join(inner) + "\n}")
            continue
        _, selector_text, body = node
        selectors = [prefix_selector(part) for part in split_top_level(selector_text, ",")]
        if any(selector is None for selector in selectors):
            continue
        keep = any(paper in selector_text for paper in PAPER_SELECTORS)
        declarations = twin_declarations(parse_declarations(body), keep)
        if declarations:
            selector_list = ",".join(re.sub(r"\s+", " ", selector) for selector in selectors)
            out.append(selector_list + "{" + ";".join(declarations) + "}")
    return out


def dark_css(*sources: str) -> str:
    rules = []
    for source in sources:
        rules.extend(build(parse_blocks(strip_comments(source))))
    return "@media screen{\n" + "\n".join(rules) + "\n}"


# ---------------------------------------------------------------- files

def remove_generated_css(css: str) -> str:
    start, end = css.find(CSS_START), css.find(CSS_END)
    if start < 0 or end < 0:
        return css
    return css[:start] + css[end + len(CSS_END):]


def update_shared_css() -> int:
    original = SHARED_CSS.read_text(encoding="utf-8")
    light = remove_generated_css(original)
    block = CSS_START + "\n" + dark_css(TAILWIND.read_text(encoding="utf-8"), light) + "\n" + CSS_END
    start, end = original.find(CSS_START), original.find(CSS_END)
    if start >= 0 and end >= 0:
        updated = original[:start] + block + original[end + len(CSS_END):]
    else:
        updated = original.rstrip("\n") + "\n\n" + block + "\n"
    write_if_changed(SHARED_CSS, original, updated)
    return len(block)


def write_if_changed(path: Path, original: str, updated: str) -> None:
    """Leave unchanged files alone, so Git on Windows does not show line-ending-only edits."""
    if updated != original:
        path.write_text(updated, encoding="utf-8", newline="")


def update_page(path: Path) -> int:
    html = original = path.read_text(encoding="utf-8")
    match = re.search(r"<style>(.*?)</style>", html, re.S)
    if not match:
        raise SystemExit(f"{path.name}: no <style> block")
    block = f'<style id="{PAGE_STYLE_ID}">\n{dark_css(match.group(1))}\n</style>'
    existing = re.search(rf'<style id="{PAGE_STYLE_ID}">.*?</style>', html, re.S)
    if existing:
        html = html[:existing.start()] + block + html[existing.end():]
    else:
        html = html[:match.end()] + "\n" + block + html[match.end():]
    write_if_changed(path, original, html)
    return len(block)


def main() -> None:
    print(f"account_workspace.css: {update_shared_css():,} characters of dark rules")
    for page in PAGES:
        print(f"{page}: {update_page(FRONTEND / page):,} characters of dark rules")


if __name__ == "__main__":
    main()
