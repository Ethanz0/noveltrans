"""Unit tests for StyleAnalyzer."""

from pathlib import Path
from unittest.mock import MagicMock

from noveltrans.core.style_analyzer import StyleAnalyzer


def test_analyze_style_basic(temp_project_dir: Path, mock_llm_client: MagicMock) -> None:
    mock_llm_client.complete.return_value = "# Generated Style Guide\n- Maintain action tone."
    analyzer = StyleAnalyzer(
        llm_client=mock_llm_client,
        project_dir=temp_project_dir,
    )

    style_guide = analyzer.analyze_style_sync("Sample Korean novel chapter text.")
    assert "# Generated Style Guide" in style_guide

    style_file = temp_project_dir / "style_guide.md"
    assert style_file.exists()
    assert "# Generated Style Guide" in style_file.read_text(encoding="utf-8")


def test_analyze_style_no_file_update(temp_project_dir: Path, mock_llm_client: MagicMock) -> None:
    mock_llm_client.complete.return_value = "# Temporary Style"
    analyzer = StyleAnalyzer(
        llm_client=mock_llm_client,
        project_dir=temp_project_dir,
    )

    res = analyzer.analyze_style_sync("Sample text", update_file=False)
    assert res == "# Temporary Style"
