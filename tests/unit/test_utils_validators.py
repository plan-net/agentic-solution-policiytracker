"""Tests for utility validation functions."""

import os

import pytest

from src.utils.exceptions import ConfigurationError
from src.utils.validators import (
    get_supported_extensions,
    sanitize_filename,
    validate_context_file,
    validate_directory_exists,
    validate_file_extension,
    validate_file_size,
    validate_path_security,
)


class TestValidatePathSecurity:
    """Test path security validation."""

    def test_safe_paths(self):
        """Test that safe paths are accepted."""
        safe_paths = [
            "/home/user/documents/file.txt",
            "documents/subfolder/file.pdf",
            "./local/file.md",
            "simple_filename.txt",
            "/var/log/app.log",
        ]

        for path in safe_paths:
            assert validate_path_security(path), f"Safe path rejected: {path}"

    def test_dangerous_path_traversal(self):
        """Test that path traversal attempts are blocked."""
        dangerous_paths = [
            "../etc/passwd",
            "../../sensitive/file.txt",
            "./documents/../../../etc/hosts",
            "folder/../../../private/data",
            "~/.ssh/id_rsa",
            "~/sensitive_data",
        ]

        for path in dangerous_paths:
            assert not validate_path_security(path), f"Dangerous path accepted: {path}"

    def test_system_directories(self):
        """Test that system directories are blocked."""
        system_paths = [
            "/etc/passwd",
            "/proc/version",
            "/sys/kernel/version",
            "/etc/shadow",
            "/proc/cpuinfo",
        ]

        for path in system_paths:
            assert not validate_path_security(path), f"System path accepted: {path}"

    def test_additional_traversal_patterns(self):
        """Test various path traversal patterns."""
        traversal_patterns = [
            "documents/../config",
            "files/../../secret",
            "data/../../../etc",
            "../../../etc/passwd",
            "folder/./../../private",
        ]

        for path in traversal_patterns:
            assert not validate_path_security(path), f"Traversal pattern accepted: {path}"

    def test_edge_cases(self):
        """Test edge cases for path validation."""
        edge_cases = [
            "",  # Empty path - should be safe
            "/",  # Root path - should be safe
            ".",  # Current directory - should be safe
        ]

        for path in edge_cases:
            # Empty and root paths should be considered safe by this function
            result = validate_path_security(path)
            assert isinstance(result, bool), f"Non-boolean result for: {path}"


class TestValidateFileExtension:
    """Test file extension validation."""

    def test_allowed_extensions(self):
        """Test that allowed extensions are accepted."""
        allowed_extensions = [".pdf", ".docx", ".txt", ".md"]

        test_cases = [
            ("document.pdf", True),
            ("report.docx", True),
            ("readme.txt", True),
            ("notes.md", True),
            ("Document.PDF", True),  # Case insensitive
            ("REPORT.DOCX", True),
        ]

        for filename, expected in test_cases:
            result = validate_file_extension(filename, allowed_extensions)
            assert result == expected, f"Extension validation failed for {filename}"

    def test_disallowed_extensions(self):
        """Test that disallowed extensions are rejected."""
        allowed_extensions = [".pdf", ".docx", ".txt"]

        disallowed_files = [
            "script.exe",
            "malware.bat",
            "code.py",
            "data.json",
            "config.xml",
            "image.jpg",
        ]

        for filename in disallowed_files:
            result = validate_file_extension(filename, allowed_extensions)
            assert not result, f"Disallowed extension accepted: {filename}"

    def test_no_extension(self):
        """Test files without extensions."""
        allowed_extensions = [".pdf", ".txt"]

        files_without_ext = [
            "README",
            "LICENCE",
            "Makefile",
            "dockerfile",
        ]

        for filename in files_without_ext:
            result = validate_file_extension(filename, allowed_extensions)
            assert not result, f"File without extension accepted: {filename}"

    def test_empty_extension_list(self):
        """Test with empty allowed extensions list."""
        result = validate_file_extension("document.pdf", [])
        assert not result, "File accepted with empty allowed extensions"

    def test_case_insensitivity(self):
        """Test that extension checking is case insensitive."""
        allowed_extensions = [".PDF", ".TXT"]

        test_cases = [
            ("file.pdf", True),
            ("file.PDF", True),
            ("file.txt", True),
            ("file.TXT", True),
            ("file.Pdf", True),
            ("file.Txt", True),
        ]

        for filename, expected in test_cases:
            result = validate_file_extension(filename, allowed_extensions)
            assert result == expected, f"Case insensitive test failed for {filename}"


class TestValidateFileSize:
    """Test file size validation."""

    def test_file_within_size_limit(self, temp_directory):
        """Test that files within size limit are accepted."""
        # Create a small test file
        test_file = os.path.join(temp_directory, "small_file.txt")
        with open(test_file, "w") as f:
            f.write("This is a small test file.")

        # Should be well under 1 MB
        assert validate_file_size(test_file, 1), "Small file rejected"
        assert validate_file_size(test_file, 10), "Small file rejected with large limit"

    def test_large_file_exceeds_limit(self, temp_directory):
        """Test that large files are rejected."""
        # Create a file larger than 1MB
        test_file = os.path.join(temp_directory, "large_file.txt")
        with open(test_file, "w") as f:
            # Write approximately 2MB of data
            content = "x" * (1024 * 1024 * 2)  # 2MB
            f.write(content)

        # Should exceed 1 MB limit
        assert not validate_file_size(test_file, 1), "Large file accepted"
        # But should be under 5 MB limit
        assert validate_file_size(test_file, 5), "File under larger limit rejected"

    def test_nonexistent_file(self):
        """Test that nonexistent files are rejected."""
        nonexistent_file = "/path/that/does/not/exist.txt"
        assert not validate_file_size(nonexistent_file, 10), "Nonexistent file accepted"

    def test_zero_size_limit(self, temp_directory):
        """Test with zero size limit."""
        test_file = os.path.join(temp_directory, "any_file.txt")
        with open(test_file, "w") as f:
            f.write("content")

        assert not validate_file_size(test_file, 0), "File accepted with zero size limit"

    def test_exact_size_limit(self, temp_directory):
        """Test file exactly at size limit."""
        test_file = os.path.join(temp_directory, "exact_size.txt")
        # Create file of exactly 1MB
        with open(test_file, "w") as f:
            content = "x" * (1024 * 1024)  # Exactly 1MB
            f.write(content)

        # Should be accepted at exactly 1MB limit
        assert validate_file_size(test_file, 1), "File at exact limit rejected"


class TestValidateDirectoryExists:
    """Test directory existence validation."""

    def test_existing_directory(self, temp_directory):
        """Test that existing directory is validated."""
        assert validate_directory_exists(temp_directory), "Existing directory rejected"

    def test_nonexistent_directory(self):
        """Test that nonexistent directory is rejected."""
        nonexistent_dir = "/path/that/does/not/exist"
        assert not validate_directory_exists(nonexistent_dir), "Nonexistent directory accepted"

    def test_file_instead_of_directory(self, temp_directory):
        """Test that a file path is rejected when directory expected."""
        # Create a file
        test_file = os.path.join(temp_directory, "test_file.txt")
        with open(test_file, "w") as f:
            f.write("content")

        assert not validate_directory_exists(test_file), "File accepted as directory"

    def test_relative_path_resolution(self):
        """Test that relative paths are resolved correctly."""
        # Current directory should exist
        assert validate_directory_exists("."), "Current directory rejected"
        assert validate_directory_exists("./"), "Current directory with ./ rejected"

    def test_home_directory(self):
        """Test home directory validation."""
        home_dir = os.path.expanduser("~")
        if os.path.exists(home_dir):
            assert validate_directory_exists(home_dir), "Home directory rejected"


class TestValidateContextFile:
    """Test context file validation."""

    def test_valid_context_file(self, temp_directory):
        """Test that valid context file is accepted."""
        context_file = os.path.join(temp_directory, "context.yaml")
        with open(context_file, "w") as f:
            f.write("company_terms: ['test']\ncore_industries: ['tech']")

        # Should not raise exception
        validate_context_file(context_file)

    def test_nonexistent_context_file(self):
        """Test that nonexistent context file raises error."""
        nonexistent_file = "/path/that/does/not/exist.yaml"

        with pytest.raises(ConfigurationError) as exc_info:
            validate_context_file(nonexistent_file)

        assert exc_info.value.setting_name == "context_file"
        assert "not found" in exc_info.value.message.lower()

    def test_unsafe_context_file_path(self):
        """Test that unsafe context file path raises error."""
        # Use path that fails security validation
        unsafe_path = "../../../etc/passwd"

        with pytest.raises(ConfigurationError) as exc_info:
            validate_context_file(unsafe_path)

        assert exc_info.value.setting_name == "context_file"
        # Check for either "invalid path" or "not found" error messages
        message_lower = exc_info.value.message.lower()
        assert "invalid path" in message_lower or "not found" in message_lower


class TestGetSupportedExtensions:
    """Test supported extensions function."""

    def test_returns_list(self):
        """Test that function returns a list."""
        extensions = get_supported_extensions()
        assert isinstance(extensions, list), "Function should return a list"

    def test_contains_expected_extensions(self):
        """Test that common extensions are included."""
        extensions = get_supported_extensions()

        expected_extensions = [".md", ".pdf", ".docx", ".txt", ".html"]

        for ext in expected_extensions:
            assert ext in extensions, f"Expected extension {ext} not found"

    def test_all_extensions_start_with_dot(self):
        """Test that all extensions start with a dot."""
        extensions = get_supported_extensions()

        for ext in extensions:
            assert ext.startswith("."), f"Extension {ext} does not start with dot"

    def test_no_empty_extensions(self):
        """Test that no empty extensions are returned."""
        extensions = get_supported_extensions()

        for ext in extensions:
            assert len(ext) > 1, f"Extension {ext} is too short"


class TestSanitizeFilename:
    """Test filename sanitization."""

    def test_clean_filename_unchanged(self):
        """Test that clean filenames remain unchanged."""
        clean_names = [
            "document.pdf",
            "report_2024.docx",
            "analysis-results.txt",
            "file_name_123.md",
        ]

        for name in clean_names:
            result = sanitize_filename(name)
            assert result == name, f"Clean filename was changed: {name} -> {result}"

    def test_dangerous_characters_replaced(self):
        """Test that dangerous characters are replaced."""
        dangerous_names = [
            "file<with>brackets.txt",
            'file"with"quotes.pdf',
            "file:with:colons.docx",
            "file/with/slashes.md",
            "file\\with\\backslashes.txt",
            "file|with|pipes.pdf",
            "file?with?questions.txt",
            "file*with*asterisks.md",
        ]

        for name in dangerous_names:
            result = sanitize_filename(name)
            # Should not contain any of the dangerous characters
            dangerous_chars = '<>:"/\\|?*'
            for char in dangerous_chars:
                assert char not in result, f"Dangerous character {char} not removed from {name}"

    def test_long_filename_truncated(self):
        """Test that very long filenames are truncated."""
        # Create a filename longer than 255 characters
        long_name = "very_long_filename_" * 20 + ".txt"  # Much longer than 255

        result = sanitize_filename(long_name)

        assert len(result) <= 255, f"Filename not truncated: length {len(result)}"
        assert result.endswith(".txt"), "Extension lost during truncation"

    def test_extension_preserved_in_truncation(self):
        """Test that file extension is preserved when truncating."""
        long_name = "a" * 300 + ".docx"

        result = sanitize_filename(long_name)

        assert len(result) <= 255, "Filename not truncated"
        assert result.endswith(".docx"), "Extension not preserved"

    def test_empty_filename(self):
        """Test handling of empty filename."""
        result = sanitize_filename("")
        assert result == "", "Empty filename should remain empty"

    def test_filename_with_only_extension(self):
        """Test filename that is only an extension."""
        result = sanitize_filename(".gitignore")
        assert result == ".gitignore", "Extension-only filename changed"

    def test_multiple_dangerous_characters(self):
        """Test filename with multiple dangerous characters."""
        dangerous_name = 'file<>:"/\\|?*.txt'
        result = sanitize_filename(dangerous_name)

        # All dangerous characters should be replaced with underscores
        expected = "file_________.txt"
        assert result == expected, f"Expected {expected}, got {result}"

    def test_unicode_filename(self):
        """Test that unicode characters are preserved."""
        unicode_name = "файл_документ_测试.pdf"
        result = sanitize_filename(unicode_name)
        assert result == unicode_name, "Unicode filename was modified"
