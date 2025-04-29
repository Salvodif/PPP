# --- START OF FILE config_manager.py ---

import json
import os
from pathlib import Path
import traceback
from typing import Any, Dict, List, Optional

DEFAULT_CONFIG_FILENAME = "config.json"

class ConfigManagerLogic:
    """Handles loading, accessing, and saving application configuration."""

    def __init__(self, config_path: str = DEFAULT_CONFIG_FILENAME):
        self.config_path = Path(config_path)
        self.config_data: Dict[str, Any] = {}
        self.load_config()

    def load_config(self) -> bool:
        """Loads configuration from the JSON file."""
        if not self.config_path.exists():
            print(f"Error: Configuration file not found at '{self.config_path}'")
            self.config_data = self._get_default_config()
            self.save_config()

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f)
            print(f"Configuration loaded successfully from '{self.config_path}'")
            self.config_data.setdefault("paths", {})
            self.config_data.setdefault("tags", {"hierarchy": {}, "flat_tags": []})
            self.config_data.setdefault("tag_icons", {"default": "📄"})
            return True
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from '{self.config_path}': {e}")
            traceback.print_exc()
            self.config_data = self._get_default_config() # Load default on error
            return False
        except Exception as e:
            print(f"Error loading configuration file '{self.config_path}': {e}")
            traceback.print_exc()
            self.config_data = self._get_default_config() # Load default on error
            return False


    def _get_default_config(self) -> Dict[str, Any]:
         """Returns a dictionary with the default configuration structure."""
         return {
             "paths": {
                 "db": "library.json",
                 "library": "MyLibrary",
                 "main_upload_dir": str(Path.home()),
                 "exiftool_path": ""
             },
             "tags": {
                 "hierarchy": {},
                 "flat_tags": ["ExampleTag", "AnotherTag"]
             },
             "tag_icons": {
                 "ExampleTag": "⭐",
                 "default": "📄"
             }
         }


    def save_config(self) -> bool:
        """Saves the current configuration data back to the JSON file."""
        try:
            # Create parent directory if it doesn't exist
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            print(f"Configuration saved successfully to '{self.config_path}'")
            return True
        except Exception as e:
            print(f"Error saving configuration file '{self.config_path}': {e}")
            traceback.print_exc()
            return False


    def _get_nested(self, keys: List[str], default: Any = None) -> Any:
        """Helper to safely get nested dictionary values."""
        data = self.config_data
        try:
            for key in keys:
                data = data[key]
            return data
        except (KeyError, TypeError):
            return default


    # --- Path Accessors ---
    @property
    def db_path(self) -> Optional[str]:
        return self._get_nested(["paths", "db"])

    @property
    def library_path(self) -> Optional[Path]:
        path_str = self._get_nested(["paths", "library"])
        return Path(path_str) if path_str else None

    @property
    def upload_dir(self) -> Optional[Path]:
        path_str = self._get_nested(["paths", "main_upload_dir"])
        return Path(path_str) if path_str else None

    @property
    def exiftool_path(self) -> Optional[str]:
         return self._get_nested(["paths", "exiftool_path"])

    def update_paths(self, new_paths: Dict[str, str]) -> None:
        """Updates the 'paths' section in the configuration data."""
        if "paths" not in self.config_data:
            self.config_data["paths"] = {} # Create if missing

        # Update only the keys present in new_paths
        for key, value in new_paths.items():
            if key in ["db", "library", "main_upload_dir", "exiftool_path"]:
                 self.config_data["paths"][key] = value
            else:
                 print(f"Warning: Unknown path key '{key}' ignored during update.")

    # --- Tag Accessors/Mutators ---
    @property
    def tag_hierarchy(self) -> Dict:
        # Ensure tags and hierarchy keys exist
        self.config_data.setdefault("tags", {}).setdefault("hierarchy", {})
        return self.config_data["tags"]["hierarchy"]

    @property
    def flat_tags(self) -> List[str]:
        # Ensure tags and flat_tags keys exist
        self.config_data.setdefault("tags", {}).setdefault("flat_tags", [])
        return self.config_data["tags"]["flat_tags"]

    def update_flat_tags(self, new_flat_tags: List[str]) -> None:
        """Updates the 'flat_tags' list in the configuration data."""
        # Ensure tags key exists
        self.config_data.setdefault("tags", {})
        self.config_data["tags"]["flat_tags"] = sorted(list(set(new_flat_tags))) # Ensure unique and sorted

    @property
    def tag_icons(self) -> Dict[str, str]:
        # Ensure tag_icons key exists
        self.config_data.setdefault("tag_icons", {"default": "📄"})
        return self.config_data["tag_icons"]

    def update_tag_icons(self, new_tag_icons: Dict[str, str]) -> None:
         """Updates the 'tag_icons' dictionary in the configuration data."""
         # Ensure default icon exists
         new_tag_icons.setdefault("default", "📄")
         self.config_data["tag_icons"] = new_tag_icons

    def get_icon_for_tag(self, tag: str) -> str:
        """Gets the icon for a specific tag, falling back to default."""
        icons = self.tag_icons
        return icons.get(tag, icons.get("default", "❓"))

# --- END OF MODIFIED config_manager_logic.py ---