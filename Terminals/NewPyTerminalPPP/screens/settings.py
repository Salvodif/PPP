from textual import on
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Input, Button, Header, Footer

from configmanager import ConfigManager

class Settings(Screen):
    BINDINGS = [
        ("escape", "back", "Torna indietro"),  # Aggiungi questa riga
    ]

    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager
        self._configpaths = config_manager.paths

    def compose(self) -> ComposeResult:
        yield Header()

        yield Input(value=self._configpaths['db'], id="db-path", placeholder="Percorso database")
        yield Input(value=self._configpaths['library'], id="library-path", placeholder="Percorso libreria")
        yield Input(value=self._configpaths['main_upload_dir'], id="main-upload-dir", placeholder="Percorso upload")
        yield Input(value=self._configpaths['exiftool_path'], id="exiftool-path", placeholder="Percorso ExIfTool")

        yield Button("Salva", id="save-button")

        yield Footer()

    @on(Button.Pressed, "#save-button")
    def handle_save(self, event: Button.Pressed):
        db_path = self.query_one("#db-path", Input).value
        library_path = self.query_one("#library-path", Input).value
        main_upload_dir = self.query_one("#main-upload-dir", Input).value
        exiftool_path = self.query_one("#exiftool-path", Input).value

        self.config_manager.update_paths({
            'db': db_path,
            'library': library_path,
            'main_upload_dir': main_upload_dir,
            'exiftool_path': exiftool_path
        })

        self.notify("Percorsi aggiornati con successo!")
        self.dismiss()

    @on(Button.Pressed, "#cancel-button")  # Aggiunto gestore per il pulsante Annulla
    def handle_cancel(self, event: Button.Pressed):
        self.dismiss()

    def action_back(self):
        """Torna alla schermata principale senza salvare"""
        self.dismiss()
