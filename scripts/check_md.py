"""Validate the documentation's internal references.

Three editing rounds over a 1,600-line report need this to be trustworthy, and
the ad-hoc checker it replaces was wrong in both directions at once.

It missed a whole class of bug: four references in `report.md` read `§8` while
meaning section 8 of a *different* document, and section 8 of the report is
Limitations. A bare `§8` is not a link, so no link checker could see it. That is
what `--sections` is for.

And it reported two false positives, because it slugged headings by collapsing
whitespace runs and stripping underscores. GitHub does neither: it drops
punctuation in place, leaving the hyphens behind, so
`## 5.6 The corpus axis: f' = +22.09 points` anchors at `...axis-f--2209-points`
with *two* hyphens, and `top_p` keeps its underscore. A checker that is wrong
about the rule is worse than none, because it is believed.

Run: PYTHONPATH=src:. python scripts/check_md.py
Exit status is 1 if anything is broken, so CI or a driver can gate on it.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import click

ROOT = Path(__file__).resolve().parent.parent

# Working documents that are deliberately not part of the published docs.
SKIP_NAMES = {"draft-blog-post.md"}

# Directories of verbatim records *about* another document. Every "§n" in a
# review of report.md refers to report.md, and the reviews are kept word for
# word, so neither the section convention nor their internal links are this
# repo's to enforce. Checking them produced 180 false positives.
SUBJECT_IS_ELSEWHERE = ("docs/reviews",)


def about_another_document(path: Path) -> bool:
    try:
        rel = path.relative_to(ROOT).as_posix()
    except ValueError:
        return False
    return rel.startswith(SUBJECT_IS_ELSEWHERE)


HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
# "§5.13", "§3.9", "§8" -- the project's own cross-reference convention.
SECTION_REF = re.compile(r"§(\d+(?:\.\d+[a-z]?)?)")
# A heading's leading number: "## 1. Summary" -> "1", "### 5.13 The run" -> "5.13".
# The trailing period is optional because this project's top-level headings carry
# one ("1. Summary") and its subsections do not ("5.13 The final run").
HEADING_NUMBER = re.compile(r"^(\d+(?:\.\d+[a-z]?)?)\.?\s")
# Any mention of another markdown document, which makes a nearby §n unambiguous.
MD_FILENAME = re.compile(r"[\w.-]+\.md")


def slug(text: str) -> str:
    """GitHub's heading anchor, which is not the obvious algorithm.

    Strip inline markdown, lowercase, delete every character that is not a
    letter, digit, underscore, hyphen or space -- *in place*, without
    collapsing what is left -- then turn spaces into hyphens.
    """
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    # Strip emphasis markers, but never a lone underscore: GitHub keeps the one
    # in `top_p`, and stripping it is precisely the bug that made the previous
    # checker call a correct anchor broken.
    text = re.sub(r"(\*\*|__|\*)", "", text)
    text = text.lower()
    text = re.sub(r"[^a-z0-9_\- ]", "", text)
    return text.strip().replace(" ", "-")


def headings(path: Path) -> list[tuple[int, str]]:
    out = []
    fenced = False
    for i, line in enumerate(path.read_text().splitlines(), 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        m = HEADING.match(line)
        if m:
            out.append((i, m.group(2).strip()))
    return out


def anchors(path: Path) -> set[str]:
    return {slug(text) for _, text in headings(path)}


def section_numbers(path: Path) -> set[str]:
    """The numbered sections a `§n` in this document could legitimately mean."""
    out = set()
    for _, text in headings(path):
        m = HEADING_NUMBER.match(text)
        if m:
            out.add(m.group(1))
    return out


def show(path: Path) -> str:
    """Repo-relative where possible, absolute otherwise -- tmp paths in tests."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def docs(root: Path) -> list[Path]:
    return sorted(
        p
        for p in root.rglob("*.md")
        if ".git" not in p.parts and p.name not in SKIP_NAMES and "node_modules" not in p.parts
    )


def check_links(files: list[Path]) -> list[str]:
    cache: dict[Path, set[str]] = {}
    problems = []
    for path in files:
        if about_another_document(path):
            continue
        for i, line in enumerate(path.read_text().splitlines(), 1):
            for m in LINK.finditer(line):
                target = m.group(1)
                if target.startswith(("http://", "https://", "mailto:", "#!")):
                    continue
                file_part, _, frag = target.partition("#")
                dest = ((path.parent / file_part) if file_part else path).resolve()
                rel = show(path)
                if not dest.exists():
                    problems.append(f"{rel}:{i}: link to a missing file -- {target}")
                    continue
                if frag and dest.suffix == ".md":
                    if dest not in cache:
                        cache[dest] = anchors(dest)
                    if frag not in cache[dest]:
                        problems.append(f"{rel}:{i}: link to a missing anchor -- {target}")
    return problems


def check_sections(files: list[Path]) -> list[str]:
    """`§n` always means a section of the document it appears in.

    The bug this exists for: a report whose own section 8 is Limitations, using
    `§8` four times to mean section 8 of its plan document.
    """
    problems = []
    for path in files:
        if about_another_document(path):
            continue
        own = section_numbers(path)
        if not own:
            continue
        lines = path.read_text().splitlines()
        fenced = False
        for i, line in enumerate(lines, 1):
            if line.lstrip().startswith("```"):
                fenced = not fenced
                continue
            if fenced:
                continue
            for m in SECTION_REF.finditer(line):
                if m.group(1) in own:
                    continue
                # A reference that names its document is fine: "`results.md`
                # §2.1", "§8 of [methodology.md](...)". Prose here is wrapped at
                # 80 columns, so the filename is often on the next line -- hence
                # a three-line window rather than the one line. It will
                # occasionally suppress a real problem whose line happens to
                # mention some other document; that is the right trade, because
                # a lint with seven false positives is a lint nobody reads.
                window = "\n".join(lines[max(0, i - 2) : i + 1])
                if MD_FILENAME.search(window):
                    continue
                problems.append(
                    f"{show(path)}:{i}: §{m.group(1)} is not a section of "
                    f"this document, and no document is named near it"
                )
    return problems


@click.command()
@click.option("--root", type=click.Path(exists=True, file_okay=False), default=str(ROOT))
@click.option("--links/--no-links", default=True, help="Check relative links and #anchors.")
@click.option(
    "--sections/--no-sections",
    default=True,
    help="Check that every §n names a section of its own document.",
)
def main(root: str, links: bool, sections: bool) -> None:
    files = docs(Path(root).resolve())
    problems: list[str] = []
    if links:
        problems += check_links(files)
    if sections:
        problems += check_sections(files)

    print(f"{len(files)} markdown files checked")
    for p in problems:
        print(f"  {p}")
    if problems:
        print(f"\n{len(problems)} problem(s)")
        sys.exit(1)
    print("no broken links, anchors or section references")


if __name__ == "__main__":
    main()
