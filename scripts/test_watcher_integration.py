"""
Test Watcher Integration — Validates BaseWatcher and task lifecycle.
Tests:
1. Task creation in Inbox with correct YAML format
2. Moving task to Needs_Action with error metadata
3. Moving task to Done
4. Moving task to Pending_Approval
"""

import sys
from pathlib import Path

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import FOLDERS, ensure_folders
from logger_setup import logger
from scripts.base_watcher import BaseWatcher


class TestWatcher(BaseWatcher):
    """Concrete test implementation of BaseWatcher."""

    def __init__(self):
        super().__init__(name="test", poll_interval=60)

    def check_for_events(self) -> int:
        """No-op for testing."""
        return 0


def test_task_creation():
    """Test 1: Create task in Inbox with correct YAML frontmatter."""
    print("\n" + "=" * 60)
    print("TEST 1: Task Creation in Inbox")
    print("=" * 60)

    watcher = TestWatcher()
    task_id = watcher.generate_task_id("TEST", "test_email_001")

    metadata = {
        "from": "test@example.com",
        "subject": "Test Email",
        "priority": "high",
    }

    content = """# Task: Test Email

**Source:** Test Watcher
**From:** test@example.com

## Action Required
> [!TODO] This is a test task
"""

    task_path = watcher.create_task_file(
        task_id=task_id,
        metadata=metadata,
        content=content,
        destination="inbox",
    )

    print(f"✅ Task created: {task_path}")

    # Verify file exists and has correct format
    path = Path(task_path)
    assert path.exists(), "Task file should exist"

    file_content = path.read_text(encoding="utf-8")
    assert file_content.startswith("---"), "File should start with YAML frontmatter"
    assert "task_id:" in file_content, "File should contain task_id"
    assert "source:" in file_content, "File should contain source"
    assert "created:" in file_content, "File should contain created timestamp"
    assert "status:" in file_content, "File should contain status"

    print("✅ YAML frontmatter format validated")
    print(f"\nFile content preview:")
    print("-" * 60)
    print(file_content[:500])
    print("-" * 60)

    return task_id, task_path


def test_move_to_needs_action(task_id: str):
    """Test 2: Move task to Needs_Action with error metadata."""
    print("\n" + "=" * 60)
    print("TEST 2: Move Task to Needs_Action")
    print("=" * 60)

    watcher = TestWatcher()

    metadata = {
        "from": "test@example.com",
        "subject": "Test Email",
        "source": "test_watcher",
        "priority": "high",
    }

    content = """# Task: Test Email

**Source:** Test Watcher
**From:** test@example.com

## Action Required
> [!TODO] This is a test task
"""

    needs_action_path = watcher.move_to_needs_action(
        task_id=task_id,
        metadata=metadata,
        content=content,
        error_reason="AI reasoning failed: could not parse intent",
        retry_count=0,
    )

    print(f"✅ Task moved to Needs_Action: {needs_action_path}")

    # Verify file exists in Needs_Action folder
    path = Path(needs_action_path)
    assert path.exists(), "Needs_Action file should exist"
    assert "Needs_Action" in str(path), "File should be in Needs_Action folder"

    file_content = path.read_text(encoding="utf-8")
    assert "status: needs_action" in file_content, "Status should be needs_action"
    assert "error_reason:" in file_content, "Should contain error_reason"
    assert "retry_count:" in file_content, "Should contain retry_count"
    assert "[!ERROR]" in file_content, "Should contain error callout"

    print("✅ Needs_Action format validated")
    print(f"\nFile content preview:")
    print("-" * 60)
    print(file_content[:600])
    print("-" * 60)

    return needs_action_path


def test_move_to_approval(task_id: str):
    """Test 3: Move task to Pending_Approval."""
    print("\n" + "=" * 60)
    print("TEST 3: Move Task to Pending_Approval")
    print("=" * 60)

    watcher = TestWatcher()

    metadata = {
        "from": "test@example.com",
        "subject": "Test Email",
        "source": "test_watcher",
    }

    content = """# Task: Test Email

**Action:** Send reply to test@example.com
"""

    approval_path = watcher.move_to_approval(
        task_id=task_id,
        metadata=metadata,
        content=content,
        approval_reason="Email response requires human review before sending",
    )

    print(f"✅ Task sent to Pending_Approval: {approval_path}")

    # Verify file exists in Pending_Approval folder
    path = Path(approval_path)
    assert path.exists(), "Approval file should exist"
    assert "Pending_Approval" in str(path), "File should be in Pending_Approval folder"

    file_content = path.read_text(encoding="utf-8")
    assert "approval_status: pending" in file_content, "Should have pending approval status"
    assert "[!APPROVAL]" in file_content, "Should contain approval callout"

    print("✅ Pending_Approval format validated")

    return approval_path


def test_vault_structure():
    """Test 4: Validate vault folder structure."""
    print("\n" + "=" * 60)
    print("TEST 4: Vault Folder Structure")
    print("=" * 60)

    ensure_folders()

    required_folders = [
        "inbox", "plans", "needs_action", "pending_approval",
        "approved", "rejected", "done", "review_required", "logs",
    ]

    for folder_name in required_folders:
        folder = FOLDERS[folder_name]
        exists = folder.exists()
        print(f"  {'✅' if exists else '❌'} {folder_name}: {folder}")
        assert exists, f"Folder {folder_name} should exist"

    print("\n✅ All required vault folders present")


def run_all_tests():
    """Run all integration tests."""
    print("\n" + "=" * 60)
    print("🧪 Personal AI Employee — Watcher Integration Tests")
    print("=" * 60)

    try:
        # Test vault structure
        test_vault_structure()

        # Test task creation
        task_id, task_path = test_task_creation()

        # Test move to Needs_Action
        needs_action_path = test_move_to_needs_action(task_id)

        # Test move to Pending_Approval
        approval_path = test_move_to_approval(f"{task_id}_approval")

        # Summary
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print(f"\nGenerated files:")
        print(f"  Inbox:          {task_path}")
        print(f"  Needs_Action:   {needs_action_path}")
        print(f"  Pending_Approval: {approval_path}")
        print("\nWatcher system is fully operational ✅")
        print("=" * 60 + "\n")

        return True

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
