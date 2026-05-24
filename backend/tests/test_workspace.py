import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.workspace import assert_inside, ensure_project_workspace, list_file_tree


class WorkspaceTests(unittest.TestCase):
    def test_workspace_creation_and_tree(self):
        root = Path.cwd() / ".testdata" / "workspace-test"
        workspace = ensure_project_workspace(root, "proj_test")
        target = workspace / "src" / "app.py"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("print('ok')", encoding="utf-8")
        files = list_file_tree(workspace)
        self.assertEqual(files[0]["path"], "src/app.py")

    def test_assert_inside_blocks_escape(self):
        root = (Path.cwd() / ".testdata" / "workspace-safe").resolve()
        root.mkdir(parents=True, exist_ok=True)
        with self.assertRaises(ValueError):
            assert_inside(root, (root / ".." / "escape.txt").resolve())


if __name__ == "__main__":
    unittest.main()
