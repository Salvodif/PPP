from pathlib import Path
import shutil
import subprocess
from typing import Optional
from uuid import uuid4
from datetime import datetime
from textual.app import ComposeResult
from textual.screen import Screen
from textual import on
from textual.containers import Vertical, Horizontal
from textual.markup import escape
from textual.widgets import Header, Footer, Button, Label, DirectoryTree

from formvalidators import FormValidators
from messages import BookAdded
from widgets.bookform import BookForm
from models import BookManager, Book


class AddScreen(Screen):
    BINDINGS = [("escape", "back", "Torna indietro")]

    def __init__(self, bookmanager: BookManager, start_directory: str = "."):
        super().__init__()
        self.bookmanager = bookmanager
        self.form = BookForm(start_directory=start_directory)
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Label("Aggiungi nuovo libro", classes="title"),
            self.form.compose_form(),
            Horizontal(
                Button("Annulla", id="cancel"),
                self.form.save_button,
            ),
            id="add-container"
        )
        yield Footer()

    def on_mount(self):
        self.query_one(DirectoryTree).focus()

    @on(DirectoryTree.FileSelected)
    def handle_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """Gestisce la selezione di un file"""
        self.form.selected_file_label.update(str(event.path))

    def action_back(self):
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "cancel":
            self.app.pop_screen()
        elif event.button is self.form.save_button:
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
                author_dir = self.bookmanager.ensure_author_directory(values['author'])

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
                f'-Author="{values["author"]}"',
                f'-Title="{values["title"]}"',
                f'-Keywords="{", ".join(values["tags"])}"',
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