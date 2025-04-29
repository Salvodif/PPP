import os
import stat # For checking hidden attribute on Windows
from pathlib import Path
from typing import Iterable # Use Iterable for type hint

# Import from Textual
from textual.widgets import DirectoryTree


class FilteredDirectoryTree(DirectoryTree):
    """
    A DirectoryTree that filters its contents using filter_paths.

    - Hides hidden files/directories (dotfiles on Linux/macOS, hidden attribute on Windows).
    *   Shows only directories and files with specific allowed extensions.
    """
    # Define allowed extensions as a class attribute or pass via __init__
    # Using class attribute as in your example:
    ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".epub"} # <<< Ensure all needed extensions are here

    def __init__(
        self,
        path: str | Path,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ):
        super().__init__(path, name=name, id=id, classes=classes, disabled=disabled)
        # Normalize extensions to lowercase for case-insensitive comparison
        self.allowed_extensions = {ext.lower() for ext in (self.ALLOWED_EXTENSIONS or set())}

    def _is_hidden(self, path: Path) -> bool:
        """
        Checks if a file or directory should be considered hidden.

        - On POSIX (Linux, macOS): Checks if the name starts with a dot '.'.
        - On Windows: Checks if the FILE_ATTRIBUTE_HIDDEN is set.
        - Returns True if hidden or if an error occurs accessing attributes.
        """
        try:
            if os.name != 'nt' and path.name.startswith('.'):
                return True

            if os.name == 'nt':
                file_attrs = path.stat().st_file_attributes
                if file_attrs & stat.FILE_ATTRIBUTE_HIDDEN or path.name.startswith('.'):
                    return True

        except (OSError, FileNotFoundError) as e:
            return True

        return False


    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        """Filters the paths yielded by the base DirectoryTree."""
        count_before = 0
        count_after = 0
        for path in paths:
            count_before += 1
            if self._is_hidden(path):
                continue # Salta questo path e vai al prossimo

            count_after += 1
            if path.is_dir():
                yield path
            elif path.is_file():
                if self.allowed_extensions and path.suffix.lower() in self.allowed_extensions:
                    yield path
