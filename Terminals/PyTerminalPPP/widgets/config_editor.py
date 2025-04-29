import yaml
from pathlib import Path

from textual.widgets import Input, Button, Label
from textual.containers import Vertical, Horizontal, Grid
from textual.widget import Widget
from textual.message import Message

from tool.config_reader import ConfigReader


class ConfigEditor(Vertical):
    class SaveRequested(Message):
        def __init__(self, sender: Widget, new_config: dict) -> None:
            super().__init__(sender)
            self.new_config = new_config


    def __init__(self, id=None):
        super().__init__(id=id)
        self._config = ConfigReader()


    def compose(self):
        with Grid(id="grid_container"):
            yield Label("Database: ")
            yield Input(id="config_db", placeholder="DB Path...")
            yield Label("Library: ")
            yield Input(id="config_library", placeholder="Library Path...")
            yield Label("Upload directory: ")
            yield Input(id="upload_dir", placeholder="Upload default directory...")
            yield Label("ExIfTool: ")
            yield Input(id="exiftool_path", placeholder="ExIfTool exe...")


    def on_mount(self):
        self.query_one("#config_db", Input).value = self._config.DB
        self.query_one("#config_library", Input).value = self._config.LIBRARY
        self.query_one("#upload_dir", Input).value = self._config.MAIN_UPLOAD_DIR
        self.query_one("#exiftool_path", Input).value = self._config.EXIFTOOL_PATH


    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id != "save_config":
            return

        # Prepara i nuovi dati da salvare
        new_config = {"paths": {}}

        for key, widget in self._fields.items():
            new_config["paths"][key] = widget.value

        # Mantieni le sezioni esistenti (tags, tag_icons, ecc.)
        if self._config_path.exists():
            try:
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    existing_config = yaml.safe_load(f) or {}
                    if 'tags' in existing_config:
                        new_config['tags'] = existing_config['tags']
                    if 'tag_icons' in existing_config:
                        new_config['tag_icons'] = existing_config['tag_icons']
            except Exception as e:
                self.notify(f"Errore nel leggere il file YAML esistente: {e}", severity="error")

        # Salva i nuovi dati nel file YAML
        try:
            with open(self._config_path, 'w', encoding='utf-8') as f:
                yaml.dump(new_config, f, allow_unicode=True, sort_keys=False)
            self.post_message(self.SaveRequested(self, new_config))
            self.notify("Configurazione salvata con successo!", severity="information")
        except Exception as e:
            self.notify(f"Errore nel salvataggio del file YAML: {e}", severity="error")

        # Animazione del pulsante di salvataggio
        save_button = self.query_one("#save_config", Button)
        original_label = save_button.label
        save_button.label = "✅ Configurazione salvata!"
        save_button.refresh()
        await self.sleep(1)
        save_button.label = original_label
        save_button.refresh()
