"""Tests for gemtext content generation."""

from pathlib import Path

import pytest

from nauyaca.content.gemtext import generate_directory_listing


class TestDirectoryListing:
    """Test directory listing generation."""

    def test_generate_listing_basic(self, tmp_path):
        """Test basic directory listing generation."""
        # Create some test files
        (tmp_path / "file1.gmi").write_text("Test")
        (tmp_path / "file2.txt").write_text("Test")

        listing = generate_directory_listing(tmp_path, "/")

        assert "# Index of /" in listing
        assert "file1.gmi" in listing
        assert "file2.txt" in listing

    def test_generate_listing_with_subdirectories(self, tmp_path):
        """Test listing with subdirectories."""
        # Create subdirectories
        (tmp_path / "subdir1").mkdir()
        (tmp_path / "subdir2").mkdir()
        (tmp_path / "file.txt").write_text("Test")

        listing = generate_directory_listing(tmp_path, "/test/")

        assert "# Index of /test/" in listing
        assert "subdir1/" in listing
        assert "subdir2/" in listing
        assert "file.txt" in listing

    def test_generate_listing_empty_directory(self, tmp_path):
        """Test listing of empty directory."""
        listing = generate_directory_listing(tmp_path, "/empty/")

        assert "# Index of /empty/" in listing
        assert "empty directory" in listing.lower()

    def test_generate_listing_with_parent_link(self, tmp_path):
        """Test that non-root directories include parent link."""
        listing = generate_directory_listing(tmp_path, "/docs/guide/")

        assert "# Index of /docs/guide/" in listing
        assert "=> /docs/" in listing  # Parent directory link
        assert ".." in listing

    def test_generate_listing_root_no_parent(self, tmp_path):
        """Test that root directory doesn't include parent link."""
        listing = generate_directory_listing(tmp_path, "/")

        # Should not have ".." link for root
        lines = listing.split("\n")
        parent_links = [line for line in lines if ".." in line and "=>" in line]
        assert len(parent_links) == 0

    def test_generate_listing_sorts_directories_first(self, tmp_path):
        """Test that directories are listed before files."""
        # Create mixed content
        (tmp_path / "zebra.txt").write_text("Test")
        (tmp_path / "alpha").mkdir()
        (tmp_path / "beta.gmi").write_text("Test")
        (tmp_path / "gamma").mkdir()

        listing = generate_directory_listing(tmp_path, "/")

        # Extract just the link lines
        lines = listing.split("\n")
        link_lines = [line for line in lines if line.startswith("=>")]

        # Directories should come first
        dir_lines = [line for line in link_lines if "/" in line.split()[-1]]
        file_lines = [line for line in link_lines if "/" not in line.split()[-1]]

        # All directories should appear before any files
        if dir_lines and file_lines:
            last_dir_index = lines.index(dir_lines[-1])
            first_file_index = lines.index(file_lines[0])
            assert last_dir_index < first_file_index

    def test_generate_listing_includes_file_sizes(self, tmp_path):
        """Test that file listings include file sizes."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World")

        listing = generate_directory_listing(tmp_path, "/")

        assert "test.txt" in listing
        # Should have size in parentheses
        assert "(" in listing and ")" in listing
        assert "B" in listing  # Bytes indicator

    def test_generate_listing_formats_link_paths(self, tmp_path):
        """Test that link paths are properly formatted."""
        (tmp_path / "file.gmi").write_text("Test")
        (tmp_path / "subdir").mkdir()

        listing = generate_directory_listing(tmp_path, "/docs/")

        # Files should be linked without trailing slash
        assert "=> /docs/file.gmi" in listing
        # Directories should be linked with trailing slash
        assert "=> /docs/subdir/" in listing

    def test_generate_listing_not_a_directory(self, tmp_path):
        """Test that generating listing for a file raises ValueError."""
        test_file = tmp_path / "notadir.txt"
        test_file.write_text("Test")

        with pytest.raises(ValueError, match="Not a directory"):
            generate_directory_listing(test_file, "/")

    def test_generate_listing_normalizes_base_path(self, tmp_path):
        """Test that base path without trailing slash gets normalized."""
        listing = generate_directory_listing(tmp_path, "/docs")

        # Should add trailing slash
        assert "# Index of /docs/" in listing

    def test_file_size_formatting_bytes(self, tmp_path):
        """Test file size formatting for small files."""
        test_file = tmp_path / "small.txt"
        test_file.write_text("Hi")  # 2 bytes

        listing = generate_directory_listing(tmp_path, "/")

        assert "2 B" in listing

    def test_file_size_formatting_kilobytes(self, tmp_path):
        """Test file size formatting for KB files."""
        test_file = tmp_path / "medium.txt"
        test_file.write_text("a" * 2048)  # 2 KB

        listing = generate_directory_listing(tmp_path, "/")

        assert "KB" in listing

    def test_directory_listing_is_valid_gemtext(self, tmp_path):
        """Test that directory listing is valid gemtext format."""
        (tmp_path / "file.gmi").write_text("Test")

        listing = generate_directory_listing(tmp_path, "/")

        lines = listing.split("\n")
        # Should start with heading
        assert lines[0].startswith("#")
        # Links should start with =>
        link_lines = [line for line in lines if "file.gmi" in line]
        assert any(line.startswith("=>") for line in link_lines)
