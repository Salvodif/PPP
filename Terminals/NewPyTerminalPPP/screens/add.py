import shutil
import subprocess


from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4
from textual import on
from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.markup import escape
from textual.widgets import Header, Footer, Label, DirectoryTree, Button

from messages import BookAdded
from models import Book, BookManager
from formvalidators import FormValidators
from widgets.bookform import BookForm


class AddScreen(Screen):
    BINDINGS = [("escape", "back", "Torna indietro")]

    def __init__(self, bookmanager: BookManager, start_directory: str = "."):
        super().__init__()
        self.bookmanager = bookmanager
        self.form = BookForm(start_directory=start_directory, show_file_browser=True)
        self.start_directory = start_directory

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Label("Aggiungi nuovo libro", classes="title"),
            self.form.compose_form(),
            self.form.save_button,
            id="add-container"
        )
        yield Footer()

    def on_mount(self):
        """Focus sul tree dopo il mount, if it exists"""
        # Check if the file_tree was actually created
        if self.form.file_tree:
            self.form.file_tree.focus()
        else:
            # Fallback focus if no file tree (shouldn't happen with show_file_browser=True)
             self.form.title_input.focus()

    def action_back(self):
        self.app.pop_screen()

    # --- Event handler for file selection ---
    # This needs to be in the Screen that CONTAINS the BookForm
    # if BookForm itself doesn't handle the event bubbling.
    # Let's move the handler from BookForm to here for clarity.
    @on(DirectoryTree.FileSelected)
    def handle_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        event.stop()

        if self.form.selected_file_label: # Check if the label exists in the form
            try:
                # Update the label *within the form*
                self.form.selected_file_label.update(str(event.path))
            except Exception as e:
                self.notify(f"Errore selezione file: {e}", severity="error")
                if self.form.selected_file_label:
                    self.form.selected_file_label.update("Errore nella selezione")

    @on(Button.Pressed, "#save")
    def on_button_pressed(self, event: Button.Pressed):
        error = self.form.validate()
        if error:
            self.notify(escape(error), severity="error", timeout=5)
            return

        try:
            values = self.form.get_values()
            if not values['filename']:
                self.notify(escape("Seleziona un file!"), severity="error", timeout=5)
                return

            # 1. Validazione nome autore e titolo
            fs_author = FormValidators.author_to_fsname(values['author'])
            fs_title = FormValidators.title_to_fsname(values['title'])

            # 2. Creazione nuovo nome file
            original_path = values['filename']
            new_filename = f"{fs_title} - {fs_author}{original_path.suffix}"

            # 3. Creazione directory autore se non esiste
            author_dir = self.bookmanager.ensure_directory(values['author'])

            # 4. Copia file nella directory autore
            dest_path = Path(author_dir) / new_filename
            shutil.copy2(original_path, dest_path)

            # 5. Modifica metadati con exiftool (se supportato)
            if dest_path.suffix.lower() in ['.pdf', '.docx', '.epub']:
                self.update_file_metadata(dest_path, values)

            # 6. Creazione oggetto Book con il nuovo percorso
            book = Book(
                uuid=str(uuid4()),
                author=values['author'],
                title=values['title'],
                added=datetime.now(),
                tags=values['tags'],
                series=values['series'],
                num_series=values['num_series'],
                read=values['read'],
                description=values['description'],
                filename=new_filename  # Usa il nuovo nome file
            )

            # 7. Salvataggio nel database
            self.bookmanager.add_book(book)
            self.app.post_message(BookAdded(book))
            self.app.pop_screen()
            self.notify("Libro aggiunto con successo!", severity="success")

        except Exception as e:
            error_message = str(e).replace("[", "[").replace("]", "]")
            self.notify(error_message, severity="error", timeout=5)

    def update_file_metadata(self, file_path: Path, values: dict) -> Optional[bool]:
        """Modifica i metadati del file usando exiftool"""
        try:
            exiftool_path = self.app.config_manager.paths.get('exiftool_path', 'exiftool')
            
            commands = [
                exiftool_path,
                '-overwrite_original',
                f'-Author={values["author"]}',
                f'-Title={values["title"]}',
                f'-Keywords={", ".join(values["tags"])}',
                str(file_path)
            ]
            
            if values['description']:
                commands.insert(-1, f'-Description="{values["description"]}"')
            
            result = subprocess.run(commands, capture_output=True, text=True)
            
            if result.returncode != 0:
                error_msg = escape(f"Exiftool error: {result.stderr}")
                self.notify(error_msg, severity="error", timeout=5)
                return False
            return True
            
        except Exception as e:
            error_msg = escape(f"Metadata update failed: {str(e)}")
            self.notify(error_msg, severity="error", timeout=5)
            return None
