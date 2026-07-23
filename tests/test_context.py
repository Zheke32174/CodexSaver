from __future__ import annotations

import os
import tempfile
from pathlib import Path

from codexsaver.context import ContextPacker


class TestContextPacker:
    def test_load_single_workspace_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir, "example.py")
            file_path.write_text("def foo(): return 42\n", encoding="utf-8")
            contexts = ContextPacker(workspace=tmpdir).load(["example.py"])
            assert len(contexts) == 1
            assert "def foo" in contexts[0].content
            assert contexts[0].path == "example.py"

    def test_load_nonexistent_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            contexts = ContextPacker(workspace=tmpdir).load(["nonexistent/file.py"])
            assert len(contexts) == 1
            assert "not found" in contexts[0].content

    def test_load_respects_max_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(5):
                Path(tmpdir, f"f{i}.txt").write_text(f"content {i}", encoding="utf-8")
            contexts = ContextPacker(max_files=2, workspace=tmpdir).load(
                [f"f{i}.txt" for i in range(5)]
            )
            assert len(contexts) == 2

    def test_load_truncates_large_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "large.py").write_text("x" * 200, encoding="utf-8")
            contexts = ContextPacker(max_chars_per_file=50, workspace=tmpdir).load(["large.py"])
            assert len(contexts[0].content) < 200
            assert "truncated" in contexts[0].content

    def test_load_respects_total_chars(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(3):
                Path(tmpdir, f"f{i}.txt").write_text("x" * 60, encoding="utf-8")
            contexts = ContextPacker(max_total_chars=100, workspace=tmpdir).load(
                [f"f{i}.txt" for i in range(3)]
            )
            assert sum(len(c.content) for c in contexts) <= 160

    def test_load_empty_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            assert ContextPacker(workspace=tmpdir).load([]) == []

    def test_load_resolves_relative_path_from_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = Path(tmpdir, "src")
            nested.mkdir()
            nested.joinpath("example.py").write_text("print('ok')\n", encoding="utf-8")
            contexts = ContextPacker(workspace=tmpdir).load(["src/example.py"])
            assert contexts[0].path == "src/example.py"
            assert "print('ok')" in contexts[0].content

    def test_absolute_path_is_refused_without_reading(self):
        with tempfile.TemporaryDirectory() as workspace, tempfile.NamedTemporaryFile(
            mode="w", delete=False
        ) as outside:
            outside.write("TOP SECRET")
            outside_path = outside.name
        try:
            contexts = ContextPacker(workspace=workspace).load([outside_path])
            assert "refused context path" in contexts[0].content
            assert "TOP SECRET" not in contexts[0].content
        finally:
            os.unlink(outside_path)

    def test_parent_traversal_is_refused_without_reading(self):
        with tempfile.TemporaryDirectory() as parent:
            workspace = Path(parent, "workspace")
            workspace.mkdir()
            Path(parent, "outside.txt").write_text("TOP SECRET", encoding="utf-8")
            contexts = ContextPacker(workspace=str(workspace)).load(["../outside.txt"])
            assert "refused context path" in contexts[0].content
            assert "TOP SECRET" not in contexts[0].content

    def test_outward_symlink_is_refused_without_reading(self):
        with tempfile.TemporaryDirectory() as parent:
            workspace = Path(parent, "workspace")
            workspace.mkdir()
            outside = Path(parent, "outside.txt")
            outside.write_text("TOP SECRET", encoding="utf-8")
            link = workspace / "linked.txt"
            try:
                link.symlink_to(outside)
            except (OSError, NotImplementedError):
                return
            contexts = ContextPacker(workspace=str(workspace)).load(["linked.txt"])
            assert "refused context path" in contexts[0].content
            assert "TOP SECRET" not in contexts[0].content
