import os
import subprocess
import tempfile
import contextlib
from pathlib import Path


@contextlib.contextmanager
def temp_file_with_content(content, suffix=".txt"):
    """Context manager that creates a temporary file with content and cleans up after use.

    Args:
        content: The content to write to the temporary file
        suffix: File suffix to use (default: '.txt')

    Yields:
        Path object for the temporary file
    """
    # Create a temporary file that isn't auto-deleted when closed
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        # Write the content to the file
        with os.fdopen(fd, "w") as f:
            f.write(content)

        # Yield the path as a Path object for easier manipulation
        yield Path(path)
    finally:
        if os.environ.get("LLM_GIT_KEEP_TEMP_FILES", "0") == "0":
            try:
                os.unlink(path)
            except OSError:
                pass


def edit_with_editor(text):
    """Edit text using the system editor"""
    editor = os.environ.get("EDITOR", "vim")

    with temp_file_with_content(text) as temp_file:
        subprocess.run([editor, temp_file], check=True)
        return temp_file.read_text()
