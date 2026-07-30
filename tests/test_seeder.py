"""Unit tests for noveltrans GlossarySeeder."""

from pathlib import Path
from typing import Any

import pytest

from noveltrans.core.seeder import GlossarySeeder
from noveltrans.glossary.manager import GlossaryManager
from noveltrans.llm.protocols import SeedResult


@pytest.mark.asyncio
async def test_seeder_async(temp_project_dir: Path, mock_llm_client: Any) -> None:
    """Test asynchronous seeding call and project state persistence."""
    seeder = GlossarySeeder(llm_client=mock_llm_client, project_dir=temp_project_dir)

    result: SeedResult = await seeder.seed(["성진우는 그림자 군주로 각성했다."])
    assert isinstance(result, SeedResult)
    assert len(result.characters) > 0

    # Verify project state persistence
    manager = GlossaryManager(project_dir=temp_project_dir)
    glossary = manager.load_glossary()
    assert len(glossary.characters) > 0

    story_sum_path = temp_project_dir / "state" / "story_summary.json"
    assert story_sum_path.exists()
    arc_sum_path = temp_project_dir / "state" / "arc_summary.json"
    assert arc_sum_path.exists()


def test_seeder_sync_and_file(temp_project_dir: Path, mock_llm_client: Any) -> None:
    """Test synchronous seeding and file-based seeding."""
    ch1_file = temp_project_dir / "source" / "ch001.txt"
    seeder = GlossarySeeder(llm_client=mock_llm_client, project_dir=temp_project_dir)

    result = seeder.seed_from_files([ch1_file])
    assert len(result.characters) > 0
