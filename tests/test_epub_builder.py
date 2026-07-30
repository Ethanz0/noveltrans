"""Unit tests for noveltrans EPUBBuilder (EPUB3 compilation using ebooklib)."""

from pathlib import Path

from ebooklib import epub

from noveltrans.epub.builder import EPUBBuilder

# ============================================================================
# Tier 1: Unit Tests (HTML conversion, single chapter adding, building)
# ============================================================================


def test_epub_builder_init() -> None:
    """Tier 1: Verify EPUBBuilder initialization with title, author, and language."""
    builder = EPUBBuilder(title="Solo Leveling Vol 1", author="Chugong", language="en")
    assert builder.title == "Solo Leveling Vol 1"
    assert builder.author == "Chugong"
    assert builder.language == "en"
    assert builder.chapters == []


def test_add_chapter_and_markdown_conversion() -> None:
    """Tier 1: Test markdown text conversion to HTML elements (h1, h2, p)."""
    builder = EPUBBuilder(title="Test")
    md_content = "# Main Header\n\nParagraph text line 1.\n\n## Subheader\n\nParagraph text line 2."
    builder.add_chapter(1, md_content)

    assert len(builder.chapters) == 1
    ch = builder.chapters[0]
    assert ch["number"] == 1
    assert ch["title"] == "Chapter 1"

    html = builder._markdown_to_html("Chapter 1", md_content)
    assert "<h1>Chapter 1</h1>" in html
    assert "<p>Paragraph text line 1.</p>" in html
    assert "<h2>Subheader</h2>" in html


def test_build_epub_file_creation(tmp_path: Path) -> None:
    """Tier 1: Test build() generates a valid .epub binary file on disk."""
    builder = EPUBBuilder(title="Test Volume", author="Author Name")
    builder.add_chapter(1, "First chapter markdown text.")

    out_file = tmp_path / "output.epub"
    res_path = builder.build(out_file)

    assert res_path.exists()
    assert res_path.stat().st_size > 0


def test_generic_chapter_title_default() -> None:
    """Tier 1: Test omitting explicit chapter title defaults to 'Chapter X'."""
    builder = EPUBBuilder(title="Test")
    builder.add_chapter(5, "Chapter 5 text")
    assert builder.chapters[0]["title"] == "Chapter 5"


def test_custom_chapter_title() -> None:
    """Tier 1: Test passing explicit custom title overrides default generic title."""
    builder = EPUBBuilder(title="Test")
    builder.add_chapter(1, "Chapter text", title="The Awakening")
    assert builder.chapters[0]["title"] == "The Awakening"


# ============================================================================
# Tier 2: Component Integration Tests (Partial builds, CSS, TOC)
# ============================================================================


def test_partial_chapter_build(tmp_path: Path) -> None:
    """Tier 2: Verify partial chapter build (compiling selected range e.g. Ch 1 to 3)."""
    builder = EPUBBuilder(title="Volume 1 Partial", author="Author")
    for i in range(1, 4):  # Chapters 1..3
        builder.add_chapter(i, f"Content for chapter {i}")

    epub_path = tmp_path / "partial.epub"
    builder.build(epub_path)

    assert epub_path.exists()

    # Read back epub with ebooklib to verify chapter items count
    book = epub.read_epub(str(epub_path))
    html_items = [item for item in book.get_items() if item.get_type() == 9]  # ITEM_DOCUMENT = 9
    # Includes nav document + 3 chapter XHTML files = 4 HTML documents
    assert len(html_items) >= 3


def test_css_stylesheet_embedding(tmp_path: Path) -> None:
    """Tier 2: Test custom CSS stylesheet embedding into generated EPUB."""
    custom_css = "body { color: #333333; font-family: Arial, sans-serif; }"
    builder = EPUBBuilder(title="Styled Book")
    builder.add_chapter(1, "Text content")

    epub_path = tmp_path / "styled.epub"
    builder.build(epub_path, css_style=custom_css)

    book = epub.read_epub(str(epub_path))
    css_items = [
        item
        for item in book.get_items()
        if item.file_name.endswith(".css")
        or getattr(item, "media_type", "") == "text/css"
    ]
    assert len(css_items) >= 1
    content_str = css_items[0].get_content().decode("utf-8")
    assert "Arial" in content_str


def test_multi_chapter_sorting(tmp_path: Path) -> None:
    """Tier 2: Verify chapters added out of order are sorted by chapter number in EPUB."""
    builder = EPUBBuilder(title="Unordered Build")
    builder.add_chapter(3, "Ch 3 text")
    builder.add_chapter(1, "Ch 1 text")
    builder.add_chapter(2, "Ch 2 text")

    epub_path = tmp_path / "ordered.epub"
    builder.build(epub_path)

    book = epub.read_epub(str(epub_path))
    # TOC order check
    toc_titles = [item.title for item in book.toc if hasattr(item, "title")]
    assert toc_titles == ["Chapter 1", "Chapter 2", "Chapter 3"]


def test_table_of_contents_structure(tmp_path: Path) -> None:
    """Tier 2: Test table of contents structure contains expected chapter titles."""
    builder = EPUBBuilder(title="TOC Test")
    builder.add_chapter(1, "Text 1", title="Prologue")
    builder.add_chapter(2, "Text 2", title="The Beginning")

    epub_path = tmp_path / "toc.epub"
    builder.build(epub_path)

    book = epub.read_epub(str(epub_path))
    toc_titles = [item.title for item in book.toc if hasattr(item, "title")]
    assert "Prologue" in toc_titles
    assert "The Beginning" in toc_titles


# ============================================================================
# Tier 3: Edge Cases & Boundary Tests
# ============================================================================


def test_empty_chapter_content(tmp_path: Path) -> None:
    """Tier 3: Test adding chapter with empty content string builds valid EPUB."""
    builder = EPUBBuilder(title="Empty Content Test")
    builder.add_chapter(1, "")

    out_file = tmp_path / "empty_chap.epub"
    res = builder.build(out_file)
    assert res.exists()


# ============================================================================
# Tier 4: Real-world Application Scenarios
# ============================================================================


def test_full_epub_generation_and_reading_verification(
    temp_project_dir: Path, tmp_path: Path
) -> None:
    """Tier 4: End-to-end scenario compiling translated txt output files into an EPUB file."""
    # Write translated chapter files to output/txt/
    output_txt = temp_project_dir / "output" / "txt"
    (output_txt / "ch001.md").write_text(
        "# Chapter 1: Awakening\n\nSung Jinwoo held his dagger tightly in the dungeon.",
        encoding="utf-8",
    )
    (output_txt / "ch002.md").write_text(
        "# Chapter 2: The Shadows\n\nCha Hae-in arrived at the raid site.",
        encoding="utf-8",
    )

    builder = EPUBBuilder(title="Solo Leveling", author="Chugong")
    for ch_num, filename in [(1, "ch001.md"), (2, "ch002.md")]:
        file_path = output_txt / filename
        content = file_path.read_text(encoding="utf-8")
        builder.add_chapter(ch_num, content)

    out_epub = temp_project_dir / "output" / "epub" / "Solo Leveling.epub"
    final_path = builder.build(out_epub)

    assert final_path.exists()
    assert final_path.name == "Solo Leveling.epub"

    # Verify EPUB content can be parsed by ebooklib
    book = epub.read_epub(str(final_path))
    assert book.get_metadata("DC", "title")[0][0] == "Solo Leveling"
    assert book.get_metadata("DC", "creator")[0][0] == "Chugong"
