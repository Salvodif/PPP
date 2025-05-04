from pathlib import Path
from typing import Optional
from textual.app import ComposeResult
from textual.widgets import Input, Button, TextArea, DirectoryTree, Label
from textual.containers import Vertical, Horizontal, VerticalScroll
from datetime import datetime


class BookForm:
    def __init__(self, book=None, start_directory: str = ".", show_file_browser: bool = True):
        self.title_input = Input(placeholder="Titolo", value=book.title if book else "")
        self.author_input = Input(placeholder="Autore", value=book.author if book else "")
        self.tags_input = Input(placeholder="Tags (separati da virgola)", value=", ".join(book.tags) if book else "")
        self.series_input = Input(placeholder="Serie", value=book.series if book and book.series else "")
        self.num_series_input = Input(placeholder="Numero serie", value=str(book.num_series) if book and book.num_series else "")
        self.read_input = Input(placeholder="Data lettura (YYYY-MM-DD)", value=book.read if book and book.read else "")
        self.description_input = TextArea(book.description if book and book.description else "", language="markdown")
        self.save_button = Button("Salva", id="save", variant="primary")

        # Conditionally create file browser widgets
        self.file_tree: Optional[DirectoryTree] = None
        self.selected_file_label: Optional[Label] = None

        self.show_file_browser = show_file_browser

        if self.show_file_browser:
            self.file_tree = DirectoryTree(f"{start_directory}", id="file-browser")
            self.file_tree.show_hidden = False
            self.file_tree.filter_dirs = True
            self.file_tree.valid_extensions = {".pdf", ".epub", ".docx", }
            self.selected_file_label = Label("Nessun file selezionato")

            if book and book.filename:
                 # You might want to show the current filename or path here
                 # For simplicity, we keep "Nessun file selezionato" until user clicks
                 pass

        # --- Dynamic layout creation ---
        form_elements = []

        # Add file browser only if enabled
        if self.show_file_browser and self.file_tree and self.selected_file_label:
            form_elements.extend([
                Label("Seleziona file:"),
                self.file_tree,
                self.selected_file_label,
            ])

        # Add common fields
        form_elements.extend([
            Horizontal(Label("Titolo:", classes="fixed-width-label"), self.title_input), # Consider adding CSS classes for alignment
            Horizontal(Label("Autore:", classes="fixed-width-label"), self.author_input),
            Horizontal(Label("Tags:", classes="fixed-width-label"), self.tags_input),
            Horizontal(Label("Serie:", classes="fixed-width-label"), self.series_input),
            Horizontal(Label("Numero:", classes="fixed-width-label"), self.num_series_input), # Shortened label
            # Note: The Checkbox and read_input are handled in EditScreen directly for now
            # Horizontal(Label("Data lettura:", classes="fixed-width-label"), self.read_input), # We'll add this back if needed universally
            Label("Descrizione:"), # Label takes full width here
            self.description_input,
        ])

        self.form_container = VerticalScroll(
            Vertical(*form_elements, id="form-content"),
            id="form-container"
        )
        # --- End Dynamic layout ---

    def compose_form(self) -> ComposeResult:
        return self.form_container

    def get_values(self):
        filename_path = None

        try:
            if self.show_file_browser and self.selected_file_label and self.selected_file_label.renderable != "Nessun file selezionato":
                filename_path = Path(str(self.selected_file_label.renderable))
            elif not self.show_file_browser and self.book_data:
                filename_path = Path(self.book_data.filename) if self.book_data.filename else None
        except Exception:
                filename_path = None

        # Attempt to parse num_series safely
        num_series_value = None
        try:
            if self.num_series_input.value.strip():
                num_series_value = float(self.num_series_input.value)
        except (ValueError, TypeError):
            num_series_value = None # Handle invalid input

        # The 'read' value is now directly taken from input, validation happens elsewhere
        read_value = self.read_input.value.strip() if self.read_input.value else None

        return {
            'title': self.title_input.value,
            'author': self.author_input.value,
            'tags': [tag.strip() for tag in self.tags_input.value.split(",") if tag.strip()],
            'series': self.series_input.value if self.series_input.value else None,
            'num_series': num_series_value,
            'read': read_value,
            'description': self.description_input.text if self.description_input.text else None,
            'filename': filename_path
        }

    def validate(self):
        if not self.title_input.value.strip():
            return "Il titolo è obbligatorio"
        if not self.author_input.value.strip():
            return "L'autore è obbligatorio"

        # Validate num_series input if present
        if self.num_series_input.value.strip():
            try:
                float(self.num_series_input.value)
            except ValueError:
                 return "Numero serie deve essere un numero valido (es. 1 o 2.5)"

        # Validate read date format if present - USE THE CORRECT FORMAT
        if self.read_input.value.strip():
            try:
                datetime.strptime(self.read_input.value.strip(), "%Y-%m-%d %H:%M") # Check YYYY-MM-DD HH:MM format
            except ValueError:
                return "Formato data lettura non valido (usare YYYY-MM-DD HH:MM)"

        # Validate file selection only if the browser is shown
        if self.show_file_browser:
             if not self.selected_file_label or self.selected_file_label.renderable == "Nessun file selezionato":
                 # Is a file mandatory for adding? If so:
                 # return "È obbligatorio selezionare un file"
                 pass # If file is optional, do nothing

        return None # No errors
