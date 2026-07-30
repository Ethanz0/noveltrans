"""Unit tests for noveltrans CheckpointManager (run resumption and state persistence)."""

from pathlib import Path

import pytest

from noveltrans.state.checkpoint import CheckpointManager
from noveltrans.state.models import CheckpointData


@pytest.fixture
def checkpoint_path(tmp_path: Path) -> Path:
    return tmp_path / "state" / "checkpoint.json"


@pytest.fixture
def manager(checkpoint_path: Path) -> CheckpointManager:
    return CheckpointManager(checkpoint_path)


# ============================================================================
# Tier 1: Unit Tests (Load/Save/Skip basic operations)
# ============================================================================


def test_checkpoint_load_non_existent(manager: CheckpointManager) -> None:
    """Tier 1: Test loading non-existent checkpoint returns default CheckpointData."""
    data = manager.load_checkpoint()
    assert data.last_completed_chapter == 0
    assert data.current_batch == []
    assert data.batch_start_time is None


def test_checkpoint_save_and_load_roundtrip(
    manager: CheckpointManager, sample_checkpoint: CheckpointData
) -> None:
    """Tier 1: Test save and load round-trip preserves all CheckpointData fields."""
    manager.save_checkpoint(sample_checkpoint)

    loaded = manager.load_checkpoint()
    assert loaded.last_completed_chapter == sample_checkpoint.last_completed_chapter
    assert loaded.current_batch == sample_checkpoint.current_batch
    assert loaded.batch_start_time is not None


def test_update_completed_chapter(manager: CheckpointManager) -> None:
    """Tier 1: Test updating completed chapter saves and updates last_completed_chapter."""
    manager.update_completed(1)
    assert manager.load_checkpoint().last_completed_chapter == 1

    manager.update_completed(5)
    assert manager.load_checkpoint().last_completed_chapter == 5


def test_set_batch_state(manager: CheckpointManager) -> None:
    """Tier 1: Test setting current batch updates batch list and start timestamp."""
    batch = [1, 2, 3, 4, 5]
    manager.set_batch(batch)

    loaded = manager.load_checkpoint()
    assert loaded.current_batch == batch
    assert loaded.batch_start_time is not None


def test_should_skip_logic(manager: CheckpointManager) -> None:
    """Tier 1: Test should_skip logic based on last completed chapter."""
    manager.update_completed(3)

    assert manager.should_skip(1) is True
    assert manager.should_skip(2) is True
    assert manager.should_skip(3) is True
    assert manager.should_skip(4) is False
    assert manager.should_skip(5) is False


def test_should_skip_with_force_flag(manager: CheckpointManager) -> None:
    """Tier 1: Test force flag overrides completion state and forces execution (returns False)."""
    manager.update_completed(3)

    assert manager.should_skip(1, force=True) is False
    assert manager.should_skip(3, force=True) is False


# ============================================================================
# Tier 2: Component Integration Tests (File persistence & error handling)
# ============================================================================


def test_checkpoint_persistence_across_instances(checkpoint_path: Path) -> None:
    """Tier 2: Test state persistence across distinct CheckpointManager instances."""
    mgr1 = CheckpointManager(checkpoint_path)
    mgr1.update_completed(4)

    mgr2 = CheckpointManager(checkpoint_path)
    assert mgr2.load_checkpoint().last_completed_chapter == 4


def test_batch_resume_workflow(manager: CheckpointManager) -> None:
    """Tier 2: Simulates partial batch execution and resuming remaining chapters."""
    batch = [10, 11, 12, 13, 14]
    manager.set_batch(batch)

    # Chapters 10 and 11 complete
    manager.update_completed(10)
    manager.update_completed(11)

    # Inspect remaining batch chapters to execute
    loaded = manager.load_checkpoint()
    remaining = [c for c in loaded.current_batch if not manager.should_skip(c)]
    assert remaining == [12, 13, 14]


def test_checkpoint_directory_auto_creation(tmp_path: Path) -> None:
    """Tier 2: Verify saving checkpoint automatically creates parent directories."""
    deep_path = tmp_path / "deep" / "nested" / "state" / "checkpoint.json"
    mgr = CheckpointManager(deep_path)

    mgr.update_completed(1)
    assert deep_path.exists()


def test_corrupt_checkpoint_file_fallback(checkpoint_path: Path) -> None:
    """Tier 2: Verify corrupt JSON checkpoint file falls back to default empty state."""
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_path.write_text("INVALID { { JSON CORRUPTED", encoding="utf-8")

    mgr = CheckpointManager(checkpoint_path)
    data = mgr.load_checkpoint()
    assert data.last_completed_chapter == 0


def test_out_of_order_chapter_completion(manager: CheckpointManager) -> None:
    """Tier 2: Completing lower chapter after higher chapter keeps max completed chapter."""
    manager.update_completed(5)
    manager.update_completed(2)  # Should not lower last_completed_chapter

    assert manager.load_checkpoint().last_completed_chapter == 5


# ============================================================================
# Tier 3: Edge Cases & Boundary Tests
# ============================================================================


def test_empty_batch_reset(manager: CheckpointManager) -> None:
    """Tier 3: Test setting empty batch resets batch list."""
    manager.set_batch([1, 2, 3])
    manager.set_batch([])
    assert manager.load_checkpoint().current_batch == []


# ============================================================================
# Tier 4: Real-world Application Scenarios (Interrupted run simulation)
# ============================================================================


def test_multi_chapter_run_interruption_and_resume(checkpoint_path: Path) -> None:
    """Tier 4: Simulate multi-chapter run crash at Ch3 and resume to finish Ch5."""
    mgr = CheckpointManager(checkpoint_path)
    batch = [1, 2, 3, 4, 5]
    mgr.set_batch(batch)

    # Run chapters 1 and 2
    mgr.update_completed(1)
    mgr.update_completed(2)
    # Crash on Ch3!

    # Restart pipeline
    resumed_mgr = CheckpointManager(checkpoint_path)
    current_state = resumed_mgr.load_checkpoint()
    assert current_state.last_completed_chapter == 2

    # Resume remaining chapters
    to_run = [c for c in current_state.current_batch if not resumed_mgr.should_skip(c)]
    assert to_run == [3, 4, 5]

    for chap in to_run:
        resumed_mgr.update_completed(chap)

    final_state = resumed_mgr.load_checkpoint()
    assert final_state.last_completed_chapter == 5
