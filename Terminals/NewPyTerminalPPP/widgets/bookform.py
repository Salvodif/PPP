from pathlib import Path
from textual.app import ComposeResult
from textual.widgets import Input, Button, TextArea, DirectoryTree, Label
from textual.containers import Vertical, Horizontal, VerticalScroll
from datetime import datetime

from models import BookManager

class BookForm:
    def __init__(self, book=None, start_directory: str = "."):
        self.title_input = Input(placeholder="Titolo", value=book.title if book else "")
        self.author_input = Input(placeholder="Autore", value=book.author if book else "")
        self.tags_input = Input(placeholder="Tags (separati da virgola)", 
                               value=", ".join(book.tags) if book else "")
        self.series_input = Input(placeholder="Serie", value=book.series if book and book.series else "")
        self.num_series_input = Input(placeholder="Numero serie", 
                                    value=str(book.num_series) if book and book.num_series else "")
        self.read_input = Input(placeholder="Data lettura (YYYY-MM-DD)", 
                              value=book.read if book and book.read else "")
        self.description_input = TextArea(book.description if book and book.description else "", 
                                        language="markdown")
        self.save_button = Button("Salva", variant="primary")
        self.file_tree = DirectoryTree(f"{start_directory}", id="file-selector")
        self.file_tree.show_hidden = False
        self.file_tree.filter_dirs = True
        self.file_tree.valid_extensions = {".pdf", ".epub", ".docx"}
        self.selected_file_label = Label("Nessun file selezionato")

        self.form_container = VerticalScroll(
            Vertical(
                Horizontal(Label("Titolo:"), self.title_input),
                Horizontal(Label("Autore:"), self.author_input),
                Horizontal(Label("Tags:"), self.tags_input),
                Horizontal(Label("Serie:"), self.series_input),
                Horizontal(Label("Numero serie:"), self.num_series_input),
                Horizontal(Label("Data lettura:"), self.read_input),
                Label("Descrizione:"),
                self.description_input,
                Label("Seleziona file:"),
                self.file_tree,
                self.selected_file_label,
                id="form-content"
            ),
            id="form-container"
        )

    def compose_form(self) -> ComposeResult:
        return self.form_container

    def get_values(self):
        filename_path = None

        if self.selected_file_label.renderable != "Nessun file selezionato":
            filename_path = Path(self.selected_file_label.renderable)
        else:
            filename_path = None

        return {
            'title': self.title_input.value,
            'author': self.author_input.value,
            'tags': [tag.strip() for tag in self.tags_input.value.split(",") if tag.strip()],
            'series': self.series_input.value if self.series_input.value else None,
            'num_series': float(self.num_series_input.value) if self.num_series_input.value else None,
            'read': self.read_input.value if self.read_input.value else None,
            'description': self.description_input.text if self.description_input.text else None,
            'filename': filename_path
        }

    def validate(self):
        if not self.title_input.value:
            return "Il titolo è obbligatorio"
        if not self.author_input.value:
            fs_name = BookManager.author_to_fsname(self.author_input.value)
            if not BookManager.is_author_fsname_consistent(self.author_input.value, fs_name):
                return (f"Il nome filesystem non corrisponde all'autore.\n"
                        f"Atteso: '{fs_name}'\n"
                        f"Modifica il nome nella directory o l'autore nel form.")
            return None
        if self.read_input.value:
            try:
                datetime.strptime(self.read_input.value, "%Y-%m-%d")
            except ValueError:
                return "Formato data lettura non valido (usare YYYY-MM-DD)"
        return None