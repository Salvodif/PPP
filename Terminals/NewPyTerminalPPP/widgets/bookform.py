from pathlib import Path
from typing import Optional, List, Iterable, Sequence # Added Sequence
from textual.app import ComposeResult
from textual.widgets import Input, Button, TextArea, DirectoryTree, Label
from textual.containers import Vertical, Horizontal, VerticalScroll
from datetime import datetime

# Imports for textual-autocomplete version 4.x
from textual_autocomplete import AutoComplete, DropdownItem, TargetState
# Note: 'Completion' is not used as a class name for the items anymore, DropdownItem is used.
# 'AutoCompleter' base class is also not used; we subclass AutoComplete itself.


# --- Custom AutoComplete Subclasses ---

class AuthorAutoComplete(AutoComplete):
    def __init__(self,
                 target: Input | str,
                 all_authors: List[str],
                 **kwargs):
        super().__init__(target, candidates=None, **kwargs) # Pass None to candidates, we use get_candidates
        self.all_authors = sorted(list(set(all_authors if all_authors else [])))

    def get_candidates(self, target_state: TargetState) -> list[DropdownItem]:
        """
        Called by the AutoComplete widget to get the list of dropdown items.
        """
        prefix = self.get_search_string(target_state) # Get what the user has typed
        if not prefix:
            # Optionally return all authors or an empty list if prefix is empty
            # For now, let's return matching authors only if there's a prefix
            return []

        matches: list[DropdownItem] = []
        for author_name in self.all_authors:
            if author_name.lower().startswith(prefix.lower()):
                # The `match` method (which you can also override for custom scoring)
                # will be called internally if you don't override get_matches.
                # Here, we are essentially pre-filtering.
                # The DropdownItem's 'main' attribute is what's used for matching by default.
                matches.append(DropdownItem(main=author_name)) # prefix can be an icon etc.
        return matches

    # You might need to override get_search_string if the default isn't what you want.
    # The default get_search_string returns text[:cursor_position].
    # def get_search_string(self, target_state: TargetState) -> str:
    #     return super().get_search_string(target_state)

    # You can also override `get_matches` for more control over scoring and highlighting,
    # but the default fuzzy matching might be good enough.


class TagAutoComplete(AutoComplete):
    def __init__(self,
                 target: Input | str,
                 all_tags: List[str],
                 **kwargs):
        super().__init__(target, candidates=None, **kwargs)
        self.all_tags = sorted(list(set(all_tags if all_tags else [])))

    def get_candidates(self, target_state: TargetState) -> list[DropdownItem]:
        prefix = self.get_search_string(target_state)
        
        # For tags, we need to handle comma-separated values.
        # The AutoComplete widget itself doesn't inherently split by comma.
        # get_search_string will return the whole input up to the cursor.
        # We need the *current tag part* the user is typing.
        
        current_tag_prefix = prefix
        if ',' in prefix:
            parts = prefix.split(',')
            current_tag_prefix = parts[-1].lstrip() # Get the last part, remove leading space

        if not current_tag_prefix:
            return []

        matches: list[DropdownItem] = []
        for tag_name in self.all_tags:
            if tag_name.lower().startswith(current_tag_prefix.lower()):
                matches.append(DropdownItem(main=tag_name))
        return matches

    def apply_completion(self, value: str, state: TargetState) -> None:
        """
        Override to correctly insert the completed tag in a comma-separated list.
        """
        target_input_widget = self.target # Get the actual Input widget

        current_text = state.text
        cursor_pos = state.cursor_position

        # Find the start of the current tag part
        start_of_current_tag = 0
        last_comma_before_cursor = current_text.rfind(',', 0, cursor_pos)
        if last_comma_before_cursor != -1:
            start_of_current_tag = last_comma_before_cursor + 1
            # Skip leading spaces after comma
            while start_of_current_tag < cursor_pos and current_text[start_of_current_tag].isspace():
                start_of_current_tag += 1
        
        # Text before the current tag part (including the last comma and space if any)
        prefix_text = current_text[:start_of_current_tag]
        # Text after the cursor (if any)
        suffix_text = current_text[cursor_pos:]

        # Construct the new value
        # Ensure there's a comma and space if other tags precede this one,
        # and add a comma and space after the new tag if it's not the last one (or if more might be added).
        
        new_text_parts = []
        if prefix_text.strip().endswith(','): # if there was already a comma
             new_text_parts.append(prefix_text)
             new_text_parts.append(value)
        elif prefix_text.strip(): # if there was text before, but no comma
            new_text_parts.append(prefix_text)
            if not prefix_text.endswith(" "): new_text_parts.append(" ") # ensure space
            new_text_parts.append(value)
        else: # first tag
            new_text_parts.append(value)

        # Add a comma and space for the next tag, then the suffix
        new_text_parts.append(", ") 
        
        # Reconstruct the full text
        final_text = "".join(new_text_parts) + suffix_text.lstrip(", ") # Avoid double commas from suffix
        
        # More refined reconstruction:
        existing_tags_before = [t.strip() for t in current_text[:start_of_current_tag].split(',') if t.strip()]
        all_tags_list = existing_tags_before + [value]
        
        # Get tags that were after the cursor originally
        tags_after_cursor = [t.strip() for t in suffix_text.split(',') if t.strip()]
        all_tags_list.extend(tags_after_cursor)
        
        # Join them back, ensuring uniqueness if desired (not doing it here for simplicity)
        final_reconstructed_text = ", ".join(tag for tag in all_tags_list if tag)


        with self.prevent(Input.Changed): # Prevent feedback loop
            target_input_widget.value = final_reconstructed_text
            # Try to place cursor after the inserted tag + ", "
            # Calculate new cursor position: length of prefix + new tag + ", "
            new_cursor_pos = len(", ".join(existing_tags_before + [value])) + 2 if existing_tags_before else len(value) + 2
            target_input_widget.cursor_position = new_cursor_pos
        
        # This will trigger a rebuild of options via _handle_target_update
        # self.post_completion() # Default hides, which is fine


class BookForm:
    def __init__(self,
                 book=None,
                 start_directory: str = ".",
                 show_file_browser: bool = True,
                 all_authors: Optional[List[str]] = None,
                 all_tags: Optional[List[str]] = None):

        _authors = all_authors if all_authors is not None else []
        _tags = all_tags if all_tags is not None else []
        self.book_data = book

        # The actual Input widgets that will be targeted by AutoComplete
        self.author_target_input = Input(placeholder="Autore", value=book.author if book else "", classes="form-input", id="author_input_target")
        self.tags_target_input = Input(placeholder="Tags (separati da virgola)", value=", ".join(book.tags) if book and book.tags else "", classes="form-input", id="tags_input_target")

        # The AutoComplete widgets, now separate and configured to target the Inputs
        # We instantiate our custom subclasses here.
        # The AutoComplete widgets themselves are not directly added to the layout in place of Inputs,
        # but are composed by the Screen/Container that holds the form elements, and they position themselves.
        # For now, let's keep them as attributes to be composed later.
        self.author_autocomplete = AuthorAutoComplete(
            target=f"#{self.author_target_input.id}", # Target by ID
            all_authors=_authors,
            prevent_default_tab=False, # Allow tabbing out after selection
            prevent_default_enter=True # Prevent form submission on enter if dropdown open
        )
        self.tags_autocomplete = TagAutoComplete(
            target=f"#{self.tags_target_input.id}", # Target by ID
            all_tags=_tags,
            prevent_default_tab=False,
            prevent_default_enter=True
        )


        self.title_input = Input(placeholder="Titolo", value=book.title if book else "", classes="form-input")
        # Series, Num Series, Read Date, Description, Save Button remain the same
        self.series_input = Input(placeholder="Serie", value=book.series if book and book.series else "", classes="form-input")
        self.num_series_input = Input(placeholder="Numero serie", value=str(book.num_series) if book and book.num_series is not None else "", classes="form-input")
        self.read_input = Input(placeholder="Data lettura (YYYY-MM-DD HH:MM)", value=book.read if book and book.read else "", classes="form-input")
        self.description_input = TextArea(book.description if book and book.description else "", language="markdown", classes="form-input")
        self.save_button = Button("Salva", id="save", variant="primary", classes="button-primary")


        self.file_tree: Optional[DirectoryTree] = None
        self.selected_file_label: Optional[Label] = None
        self.show_file_browser = show_file_browser

        if self.show_file_browser:
            self.file_tree = DirectoryTree(f"{start_directory}", id="file-browser")
            self.file_tree.show_hidden = False
            self.file_tree.filter_dirs = True
            self.file_tree.valid_extensions = {".pdf", ".epub", ".docx", }
            self.selected_file_label = Label("Nessun file selezionato", id="selected-file")
            if book and book.filename:
                 pass

        form_elements = []
        if self.show_file_browser and self.file_tree and self.selected_file_label:
            form_elements.extend([
                Label("Seleziona file:", classes="form-label-heading"),
                Horizontal(self.file_tree),
                self.selected_file_label,
            ])

        # Use the target_input widgets in the form layout
        form_elements.extend([
            Horizontal(Label("Titolo:", classes="form-label"), self.title_input, classes="form-row"),
            Horizontal(Label("Autore:", classes="form-label"), self.author_target_input, classes="form-row"), # Use target
            Horizontal(Label("Tags:", classes="form-label"), self.tags_target_input, classes="form-row"),       # Use target
            Horizontal(Label("Serie:", classes="form-label"), self.series_input, classes="form-row"),
            Horizontal(Label("Numero:", classes="form-label"), self.num_series_input,classes="form-row"),
            Horizontal(Label("Data lettura:", classes="form-label"), self.read_input, classes="form-row"),
            Horizontal(
                 Label("Descrizione:", classes="form-label"),
                 self.description_input,
                 classes="form-row"
            )
        ])

        self.form_container = VerticalScroll(
            Vertical(*form_elements, id="form-content"),
            # The AutoComplete widgets are typically added at the top level of the screen
            # or a high-level container, not nested deep within the form structure itself.
            # They will position themselves absolutely over the target Input.
            # So, they are not directly part of form_elements here.
            # The Screen (e.g., AddScreen) will compose them.
            id="form-container"
        )

    def compose_form(self) -> ComposeResult:
        """
        This method now just returns the main form container.
        The AutoComplete widgets will be composed by the parent screen.
        """
        yield self.form_container
        # Yield the AutoComplete widgets so they get composed into the DOM
        # The Screen using BookForm will call a method like this, or BookForm
        # can compose them if it becomes a Widget itself.
        # For now, let's assume the Screen will handle their composition.

    def get_autocomplete_widgets(self) -> List[AutoComplete]:
        """Helper to get the autocomplete widgets for the parent screen to compose."""
        return [self.author_autocomplete, self.tags_autocomplete]


    def get_values(self):
        filename_path = None
        # ... (rest of get_values remains similar, but uses self.author_target_input.value etc.) ...
        try:
            if self.show_file_browser and self.selected_file_label:
                label_content = str(self.selected_file_label.renderable)
                if label_content != "Nessun file selezionato" and label_content.strip() != "Errore nella selezione":
                    candidate_path = Path(label_content)
                    if candidate_path.is_file():
                        filename_path = candidate_path
            elif not self.show_file_browser and self.book_data and self.book_data.filename:
                if self.book_data.filename:
                    filename_path = Path(self.book_data.filename)
        except Exception:
            filename_path = None

        num_series_value = None
        try:
            if self.num_series_input.value.strip():
                num_series_value = float(self.num_series_input.value)
        except (ValueError, TypeError):
            num_series_value = None

        read_value = self.read_input.value.strip() if self.read_input.value else None

        return {
            'title': self.title_input.value,
            'author': self.author_target_input.value, # Use value from target input
            'tags': [tag.strip() for tag in self.tags_target_input.value.split(",") if tag.strip()], # Use value from target input
            'series': self.series_input.value if self.series_input.value else None,
            'num_series': num_series_value,
            'read': read_value,
            'description': self.description_input.text if self.description_input.text else None,
            'filename': filename_path
        }

    def validate(self):
        # ... (validation remains similar, but uses self.author_target_input.value etc.) ...
        if not self.title_input.value.strip():
            return "Il titolo è obbligatorio"
        if not self.author_target_input.value.strip(): # Use value from target input
            return "L'autore è obbligatorio"

        if self.num_series_input.value.strip():
            try:
                float(self.num_series_input.value)
            except ValueError:
                 return "Numero serie deve essere un numero valido (es. 1 o 2.5)"

        if self.read_input.value.strip():
            try:
                datetime.strptime(self.read_input.value.strip(), "%Y-%m-%d %H:%M")
            except ValueError:
                return "Formato data lettura non valido (usare YYYY-MM-DD HH:MM)"

        if self.show_file_browser:
            if not self.selected_file_label or \
               str(self.selected_file_label.renderable) == "Nessun file selezionato" or \
               str(self.selected_file_label.renderable).strip() == "Errore nella selezione":
                pass
        return None