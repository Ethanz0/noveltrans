"""EPUB3 builder module for packaging translated markdown chapters into EPUB files."""

import html
import re
import uuid
from pathlib import Path
from typing import Any

from ebooklib import epub

from noveltrans.config.settings import ProjectConfig


class EPUBBuilder:
    """Builder class for assembling translated markdown chapters into EPUB3 files."""

    DEFAULT_CSS = """\
@namespace url('http://www.w3.org/1999/xhtml');

body {
    font-family: Georgia, serif;
    margin: 5%;
    line-height: 1.6;
    color: #111111;
    background-color: #ffffff;
}

h1, h2, h3, h4, h5, h6 {
    font-family: sans-serif;
    text-align: center;
    margin-top: 1.5em;
    margin-bottom: 1em;
    font-weight: bold;
}

h2 {
    font-size: 1.5em;
}

p {
    text-indent: 1.5em;
    margin-top: 0;
    margin-bottom: 0.5em;
    text-align: justify;
}

hr {
    border: none;
    border-top: 1px solid #cccccc;
    margin: 2em auto;
    width: 30%;
}
"""

    def __init__(
        self,
        title: str | None = None,
        author: str | None = None,
        language: str = "en",
        project_dir: Path | str | None = None,
        identifier: str | None = None,
        css_content: str | None = None,
    ) -> None:
        """Initialize EPUBBuilder with project path or explicit metadata."""
        self.project_dir = Path(project_dir) if project_dir else None

        config: ProjectConfig | None = None
        if self.project_dir and (self.project_dir / "project.json").exists():
            try:
                content = (self.project_dir / "project.json").read_text(encoding="utf-8")
                config = ProjectConfig.model_validate_json(content)
            except Exception:
                config = None

        self.title = title or (config.title if config else "Untitled")
        self.author = author or (config.author if config else "")
        self.language = language or (config.target_language if config else "en")
        self.identifier = identifier or f"urn:uuid:{uuid.uuid4()}"
        self.css_content = css_content or self.DEFAULT_CSS
        self.chapters: list[dict[str, Any]] = []

        # Determine default input (txt) and output (epub) directories
        if self.project_dir:
            out_base = config.output_dir if config else "output"
            self.input_dir = self.project_dir / out_base / "txt"
            self.output_dir = self.project_dir / out_base / "epub"
        else:
            self.input_dir = Path("output/txt")
            self.output_dir = Path("output/epub")

    def add_chapter(self, number: int, content: str, title: str | None = None) -> None:
        """Add a chapter with chapter number, content, and optional custom title."""
        ch_title = title if title is not None else f"Chapter {number}"
        self.chapters.append({
            "number": number,
            "title": ch_title,
            "content": content,
        })

    @staticmethod
    def parse_chapter_range(
        chapters: list[int] | range | set[int] | tuple[int, int] | str | None,
    ) -> set[int] | None:
        """Parse various representations of chapter ranges into a set of integers.

        Returns None if all chapters should be built.
        """
        if chapters is None:
            return None
        if isinstance(chapters, str):
            cleaned = chapters.strip()
            if not cleaned or cleaned.lower() == "all":
                return None

            selected: set[int] = set()
            parts = cleaned.split(",")
            for part in parts:
                part = part.strip()
                if ".." in part:
                    start_str, end_str = part.split("..", 1)
                    selected.update(range(int(start_str.strip()), int(end_str.strip()) + 1))
                elif "-" in part and not part.startswith("-"):
                    start_str, end_str = part.split("-", 1)
                    selected.update(range(int(start_str.strip()), int(end_str.strip()) + 1))
                elif part.isdigit():
                    selected.add(int(part))
            return selected

        if isinstance(chapters, tuple) and len(chapters) == 2:
            return set(range(chapters[0], chapters[1] + 1))
        if isinstance(chapters, (list, range, set)):
            return set(chapters)

        return None

    @staticmethod
    def extract_chapter_number(filepath: Path) -> int | None:
        """Extract numeric chapter identifier from a file stem."""
        stem = filepath.stem
        match = re.search(r"(?:ch|chapter)?[_\s-]*(\d+)", stem, re.IGNORECASE)
        if match:
            return int(match.group(1))
        digit_match = re.search(r"\d+", stem)
        if digit_match:
            return int(digit_match.group(0))
        return None

    def _markdown_to_html(self, title: str, content: str) -> str:
        """Convert chapter title and markdown text into XHTML content."""
        paragraphs = re.split(r"\n\s*\n", content.strip())

        body_elements: list[str] = [f"<h1>{html.escape(title)}</h1>"]

        for p in paragraphs:
            p_clean = p.strip()
            if not p_clean:
                continue

            if match := re.match(r"^#\s+(.+)$", p_clean):
                h_text = html.escape(match.group(1))
                body_elements.append(f"<h1>{h_text}</h1>")
                continue
            if match := re.match(r"^##\s+(.+)$", p_clean):
                h_text = html.escape(match.group(1))
                body_elements.append(f"<h2>{h_text}</h2>")
                continue
            if match := re.match(r"^###\s+(.+)$", p_clean):
                h_text = html.escape(match.group(1))
                body_elements.append(f"<h3>{h_text}</h3>")
                continue
            if match := re.match(r"^####\s+(.+)$", p_clean):
                h_text = html.escape(match.group(1))
                body_elements.append(f"<h4>{h_text}</h4>")
                continue

            if re.match(r"^[-*_]{3,}$", p_clean):
                body_elements.append("<hr/>")
                continue

            is_blockquote = False
            if p_clean.startswith(">"):
                is_blockquote = True
                p_clean = re.sub(r"^>\s?", "", p_clean, flags=re.MULTILINE)

            escaped = html.escape(p_clean)

            escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
            escaped = re.sub(r"__(.+?)__", r"<strong>\1</strong>", escaped)

            escaped = re.sub(r"\*(.+?)\*", r"<em>\1</em>", escaped)
            escaped = re.sub(r"_(.+?)_", r"<em>\1</em>", escaped)

            escaped = re.sub(r"`(.+?)`", r"<code>\1</code>", escaped)

            # Web novels treat single newlines as hard breaks
            escaped = escaped.replace("\n", "<br/>\n")

            if is_blockquote:
                body_elements.append(f"<blockquote>{escaped}</blockquote>")
            else:
                body_elements.append(f"<p>{escaped}</p>")

        inner_html = "\n".join(body_elements)
        return (
            "<!DOCTYPE html>\n"
            '<html xmlns="http://www.w3.org/1999/xhtml">\n'
            "<head>\n"
            f"  <title>{html.escape(title)}</title>\n"
            '  <link rel="stylesheet" href="style/nav.css" type="text/css"/>\n'
            "</head>\n"
            "<body>\n"
            '  <section>\n'
            f"{inner_html}\n"
            "  </section>\n"
            "</body>\n"
            "</html>"
        )

    def build(
        self,
        output_path: Path | str | None = None,
        css_style: str | None = None,
        chapters: list[int] | range | set[int] | tuple[int, int] | str | None = None,
        input_dir: Path | str | None = None,
    ) -> Path:
        """Package translated markdown chapters into an EPUB3 file."""
        target_set = self.parse_chapter_range(chapters)

        chapters_to_build: list[dict[str, Any]] = []

        if self.chapters:
            for ch in self.chapters:
                num = int(ch["number"])
                if target_set is None or num in target_set:
                    chapters_to_build.append(ch)
        else:
            source_dir = Path(input_dir) if input_dir else self.input_dir
            if not source_dir.exists():
                raise FileNotFoundError(f"Input directory does not exist: {source_dir}")

            discovered: list[tuple[int, Path]] = []
            for file in source_dir.iterdir():
                if file.is_file() and file.suffix.lower() in (".txt", ".md"):
                    ch_num = self.extract_chapter_number(file)
                    if ch_num is not None and (target_set is None or ch_num in target_set):
                        discovered.append((ch_num, file))

            if not discovered:
                raise ValueError(f"No matching chapter files found in {source_dir}")

            discovered.sort(key=lambda item: item[0])
            for num, file_path in discovered:
                content = file_path.read_text(encoding="utf-8")
                chapters_to_build.append({
                    "number": num,
                    "title": f"Chapter {num}",
                    "content": content,
                })

        if not chapters_to_build:
            raise ValueError("No chapters available to build EPUB.")

        chapters_to_build.sort(key=lambda ch: int(ch["number"]))

        book = epub.EpubBook()
        book.set_identifier(self.identifier)
        book.set_title(self.title)
        book.set_language(self.language)
        if self.author:
            book.add_author(self.author)

        css_item = epub.EpubItem(
            uid="style_nav",
            file_name="style/nav.css",
            media_type="text/css",
            content=css_style or self.css_content,
        )
        book.add_item(css_item)

        epub_chapters: list[epub.EpubHtml] = []
        for ch in chapters_to_build:
            ch_num = int(ch["number"])
            ch_title = str(ch["title"])
            ch_content = str(ch["content"])

            html_content = self._markdown_to_html(ch_title, ch_content)

            ch_item = epub.EpubHtml(
                title=ch_title,
                file_name=f"chapter_{ch_num:04d}.xhtml",
                lang=self.language,
            )
            ch_item.content = html_content
            ch_item.add_item(css_item)
            book.add_item(ch_item)
            epub_chapters.append(ch_item)

        book.toc = tuple(epub_chapters)  # pyright: ignore[reportAttributeAccessIssue]
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        spine_list: list[Any] = ["nav"] + epub_chapters
        book.spine = spine_list

        if output_path:
            out_file = Path(output_path)
        else:
            sanitized_title = re.sub(r"[^\w\s-]", "", self.title).strip().replace(" ", "_")
            if not sanitized_title:
                sanitized_title = "novel"
            out_file = self.output_dir / f"{sanitized_title}.epub"

        out_file.parent.mkdir(parents=True, exist_ok=True)
        epub.write_epub(str(out_file), book, {})

        return out_file
