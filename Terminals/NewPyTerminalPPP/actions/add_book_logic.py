# --- START OF FILE actions/add_book_logic.py ---

import os
import shutil
from pathlib import Path
from datetime import datetime
import traceback # Import traceback

from tinydb import TinyDB, Query
from normalize import normalize_author_for_path # Assuming normalize.py is accessible

ALLOWED_EXTENSIONS = {".pdf", ".epub", ".docx", ".pptx"}

def process_add_book(
    source_file_path_str: str,
    author: str,
    title: str,
    tags_str: str,
    db_path: str,
    library_base_path: Path
) -> dict:
    """
    Validates input, renames/moves the file, and adds the entry to TinyDB.

    Returns:
        A dictionary containing:
        - 'success': True or False
        - 'message': A status message for the user.
        - 'new_file_path': The path to the file after moving (if successful).
    """
    # --- 1. Input Validation ---
    if not all([source_file_path_str, author, title]):
        return {"success": False, "message": "Error: File path, Author, and Title are required.", "new_file_path": None}

    source_path = Path(source_file_path_str)
    if not source_path.is_file():
        return {"success": False, "message": f"Error: Source file not found at '{source_file_path_str}'", "new_file_path": None}

    if source_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        return {"success": False, "message": f"Error: Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}", "new_file_path": None}

    # --- 2. Prepare Paths and Filename ---
    try:
        normalized_author = normalize_author_for_path(author)
        target_author_dir = library_base_path / normalized_author
        new_filename = f"{title} - {author}{source_path.suffix}"
        target_path = target_author_dir / new_filename

        # Prevent overwriting accidentally (optional but recommended)
        if target_path.exists():
             return {"success": False, "message": f"Error: Target file already exists: '{target_path}'", "new_file_path": None}

    except Exception as e:
        traceback.print_exc() # Log the full error
        return {"success": False, "message": f"Error preparing paths: {e}", "new_file_path": None}


    # --- 3. Create Directory and Move File ---
    try:
        target_author_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source_path), str(target_path)) # shutil works well with strings
    except OSError as e:
        traceback.print_exc() # Log the full error
        return {"success": False, "message": f"Error moving file: {e}", "new_file_path": None}
    except Exception as e: # Catch other potential errors
         traceback.print_exc()
         return {"success": False, "message": f"Unexpected error during file move: {e}", "new_file_path": None}


    # --- 4. Update TinyDB ---
    try:
        db = TinyDB(db_path)
        # Split tags, remove whitespace, filter empty strings
        tags_list = [tag.strip() for tag in tags_str.split(',') if tag.strip()]

        new_entry = {
            "author": author,
            "title": title,
            "filename": new_filename, # Store the NEW filename
            "tags": tags_list,
            "added": datetime.now().isoformat() # Use ISO format timestamp
        }
        db.insert(new_entry)
        db.close() # Ensure data is written

    except Exception as e:
        traceback.print_exc() # Log the full error
        # Attempt to move the file back if DB insert fails (optional rollback)
        try:
            shutil.move(str(target_path), str(source_path))
            message = f"Error adding to database: {e}. File move reverted."
        except Exception as move_back_e:
            message = f"CRITICAL Error adding to DB: {e}. FAILED TO REVERT FILE MOVE: {move_back_e}"
        return {"success": False, "message": message, "new_file_path": None}

    # --- 5. Success ---
    success_message = f"Book added successfully!\nAuthor: {author}\nTitle: {title}\nFile saved to: {target_path}"
    return {"success": True, "message": success_message, "new_file_path": str(target_path)}

# --- END OF FILE actions/add_book_logic.py ---