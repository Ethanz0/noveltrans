"""Checkpoint manager for translation run persistence and resume capability."""

from datetime import UTC, datetime
from pathlib import Path

from noveltrans.state.models import CheckpointData


class CheckpointManager:
    """Manages reading and writing execution state checkpoints."""

    def __init__(self, checkpoint_path: Path | str) -> None:
        self.checkpoint_path = Path(checkpoint_path)

    def load_checkpoint(self) -> CheckpointData:
        """Load checkpoint from file, returning default CheckpointData if missing/corrupt."""
        if not self.checkpoint_path.exists():
            return CheckpointData()
        try:
            content = self.checkpoint_path.read_text(encoding="utf-8")
            return CheckpointData.model_validate_json(content)
        except Exception:
            return CheckpointData()

    def save_checkpoint(self, checkpoint: CheckpointData) -> None:
        """Save checkpoint data atomically to disk."""
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        content = checkpoint.model_dump_json(indent=2)
        self.checkpoint_path.write_text(content, encoding="utf-8")

    def update_completed(self, chapter_number: int) -> CheckpointData:
        """Update last completed chapter and save to disk."""
        checkpoint = self.load_checkpoint()
        if chapter_number > checkpoint.last_completed_chapter:
            checkpoint.last_completed_chapter = chapter_number
        self.save_checkpoint(checkpoint)
        return checkpoint

    def set_batch(self, chapters: list[int]) -> CheckpointData:
        """Set current batch of chapters and start timestamp, then save."""
        checkpoint = self.load_checkpoint()
        checkpoint.current_batch = chapters
        checkpoint.batch_start_time = datetime.now(UTC)
        self.save_checkpoint(checkpoint)
        return checkpoint

    def should_skip(self, chapter_number: int, force: bool = False) -> bool:
        """Check if chapter should be skipped based on checkpoint and force flag."""
        if force:
            return False
        checkpoint = self.load_checkpoint()
        return chapter_number <= checkpoint.last_completed_chapter
