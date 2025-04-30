from pathlib import Path
from textual.app import App
from models import BookManager

from screens.main import MainScreen

class LibriManagerApp(App):
    CSS_PATH = "styles.css"
    
    def __init__(self, library: BookManager):
        super().__init__()
        self.library = library
    
    def on_mount(self):
        self.push_screen(MainScreen(self.library))

def run_app(json_path):
    library = BookManager(json_path)
    app = LibriManagerApp(library)
    app.run()

if __name__ == "__main__":
    script_dir = Path(__file__).parent
    file_path = script_dir / "test_library.json"
    run_app(file_path)
