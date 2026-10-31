"""The documentation reference checker.

The thing worth testing hardest is `slug`, because the checker it replaces was
*wrong about GitHub's rule* and therefore reported two correct anchors as
broken. A validator that is wrong about its own rule is worse than no validator,
since its passes are believed. The cases below are the two real headings it got
wrong, pinned.

`check_sections` is tested because it catches a class of bug no link checker
can see: a bare `§8` that means section 8 of another document.
"""

from __future__ import annotations

from scripts.check_md import anchors, check_links, check_sections, section_numbers, slug


class TestSlug:
    """GitHub drops punctuation in place; it does not collapse what is left."""

    def test_plain_heading(self):
        assert slug("1. Summary") == "1-summary"

    def test_dropped_punctuation_leaves_its_hyphen(self):
        # The real case: "f′ = +22.09" loses three characters and keeps the
        # spaces around them, so the anchor has a double hyphen.
        assert slug("5.6 The corpus axis: f′ = +22.09 points per doubling, flat") == (
            "56-the-corpus-axis-f--2209-points-per-doubling-flat"
        )

    def test_underscores_survive(self):
        # `top_p` must not become `topp`.
        assert slug("5.10 Decoding: T=0.6, top_p 1.0, everywhere") == (
            "510-decoding-t06-top_p-10-everywhere"
        )

    def test_backticks_and_bold_are_stripped_not_slugged(self):
        assert slug("3.7 Two `recovery` conventions, and **why**") == (
            "37-two-recovery-conventions-and-why"
        )

    def test_a_link_in_a_heading_keeps_only_its_text(self):
        assert slug("See [the plan](final-run-plan.md) now") == "see-the-plan-now"

    def test_unicode_punctuation_is_dropped(self):
        assert slug("The cliff — what it is") == "the-cliff--what-it-is"


class TestHeadingExtraction:
    def test_anchors_and_section_numbers(self, tmp_path):
        p = tmp_path / "d.md"
        p.write_text("# Title\n\n## 1. Summary\n\ntext\n\n### 2.9a A sub\n")
        assert anchors(p) == {"title", "1-summary", "29a-a-sub"}
        # "1." carries a trailing period and "2.9a" does not; both must resolve.
        assert section_numbers(p) == {"1", "2.9a"}

    def test_an_unnumbered_heading_contributes_no_section_number(self, tmp_path):
        p = tmp_path / "d.md"
        p.write_text("## Glossary\n\n## 3 Methods\n")
        assert section_numbers(p) == {"3"}

    def test_a_hash_inside_a_fence_is_not_a_heading(self, tmp_path):
        p = tmp_path / "d.md"
        p.write_text("# Real\n\n```bash\n# just a comment\n```\n\n## 2 Also real\n")
        assert anchors(p) == {"real", "2-also-real"}


class TestCheckLinks:
    def test_a_good_anchor_passes(self, tmp_path):
        a = tmp_path / "a.md"
        b = tmp_path / "b.md"
        b.write_text("## 5.6 The axis: f′ = +22.09 flat\n")
        a.write_text("see [it](b.md#56-the-axis-f--2209-flat)\n")
        assert check_links([a, b]) == []

    def test_a_missing_file_is_reported(self, tmp_path):
        a = tmp_path / "a.md"
        a.write_text("see [it](nope.md)\n")
        problems = check_links([a])
        assert len(problems) == 1 and "missing file" in problems[0]

    def test_a_missing_anchor_is_reported(self, tmp_path):
        a = tmp_path / "a.md"
        b = tmp_path / "b.md"
        b.write_text("## Something else\n")
        a.write_text("see [it](b.md#not-there)\n")
        problems = check_links([a])
        assert len(problems) == 1 and "missing anchor" in problems[0]

    def test_external_urls_are_skipped(self, tmp_path):
        a = tmp_path / "a.md"
        a.write_text("[x](https://example.com/page#frag) [y](mailto:a@b.c)\n")
        assert check_links([a]) == []


class TestCheckSections:
    """The bug a link checker cannot see."""

    def test_a_reference_to_an_own_section_passes(self, tmp_path):
        p = tmp_path / "r.md"
        p.write_text("## 8 Limitations\n\nas §8 says\n")
        assert check_sections([p]) == []

    def test_a_reference_to_another_documents_section_is_flagged(self, tmp_path):
        # The real case: the report's §8 is Limitations, but four references
        # read "§8" meaning §8 of the plan.
        p = tmp_path / "r.md"
        p.write_text("## 1 Summary\n\nregistered in §8 of the plan\n")
        problems = check_sections([p])
        assert len(problems) == 1
        assert "§8 is not a section of this document" in problems[0]

    def test_subsection_references_resolve(self, tmp_path):
        p = tmp_path / "r.md"
        p.write_text("## 5 F\n\n### 5.13 The run\n\nsee §5.13 and §5\n")
        assert check_sections([p]) == []

    def test_a_document_with_no_numbered_headings_is_skipped(self, tmp_path):
        p = tmp_path / "r.md"
        p.write_text("# Notes\n\nsee §4 of the other thing\n")
        assert check_sections([p]) == []

    def test_a_reference_inside_a_code_fence_is_ignored(self, tmp_path):
        p = tmp_path / "r.md"
        p.write_text("## 1 A\n\n```\nprint('§9')\n```\n")
        assert check_sections([p]) == []

    def test_naming_the_document_on_the_same_line_suppresses_it(self, tmp_path):
        p = tmp_path / "r.md"
        p.write_text("## 1 A\n\nthe range in `results.md` §2.1 holds\n")
        assert check_sections([p]) == []

    def test_naming_the_document_on_the_next_line_suppresses_it(self, tmp_path):
        # Prose wrapped at 80 columns routinely splits "§8 of" from the link
        # that follows it, which a line-scoped check reports as a false
        # positive. This was 6 of the first 8 hits against the real docs.
        p = tmp_path / "r.md"
        p.write_text("## 1 A\n\nwhich is why §8 of\n[final-run-plan.md](final-run-plan.md) says\n")
        assert check_sections([p]) == []

    def test_an_unnamed_reference_is_still_flagged(self, tmp_path):
        p = tmp_path / "r.md"
        p.write_text("## 1 A\n\nwhich the additive law of §2.9 assumes it does not\n")
        assert len(check_sections([p])) == 1
