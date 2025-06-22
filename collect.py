import os
import pyperclip
# import pathlib # Path is imported directly
import fnmatch
# import subprocess # Not used
from pathlib import Path

def get_gitignore_patterns(directory):
    """Parse .gitignore file if exists and return patterns to be ignored."""
    gitignore_path = os.path.join(directory, '.gitignore')
    patterns = []
    
    if os.path.exists(gitignore_path):
        try:
            with open(gitignore_path, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if line and not line.startswith('#'):
                        patterns.append(line)
        except IOError as e:
            # Inform about errors reading .gitignore, but don't stop everything.
            print(f"Warning: Could not read .gitignore file at {gitignore_path}: {e}")
            # patterns will remain empty, so nothing will be ignored by .gitignore rules from this file.
    
    return patterns

def should_ignore(path_str, patterns, base_directory_str):
    """Check if a path should be ignored based on gitignore patterns.
    Uses fnmatch, which is OS-dependent for case-sensitivity. This often aligns with
    git's core.ignorecase setting (e.g. case-insensitive on Windows by default).
    """
    if not patterns:
        return False
    
    abs_path = os.path.abspath(path_str)
    abs_base_directory = os.path.abspath(base_directory_str)

    if not abs_path.startswith(abs_base_directory):
        # Path is outside the scope of this .gitignore (e.g. symlink pointing out)
        # This function assumes patterns are relative to base_directory_str.
        return False 

    try:
        relative_path = os.path.relpath(abs_path, abs_base_directory)
    except ValueError:
        # Should not happen if abs_path.startswith(abs_base_directory) is true
        # and paths are on the same drive (Windows).
        return False 

    # Normalize path separators to '/' for matching, as gitignore patterns use this.
    # If abs_path is abs_base_directory itself, relative_path will be ".".
    # We generally check contents *within* base_directory, so relative_path won't be ".".
    if relative_path == ".": 
        # The base directory itself is not typically ignored by its own patterns.
        # If it were, should_ignore would be called with base_dir as path_str.
        # For simplicity, assume the root of traversal isn't ignored by its own .gitignore.
        return False
    else:
        relative_path = relative_path.replace(os.sep, '/')
    
    path_is_dir = os.path.isdir(abs_path)

    for p_raw in patterns:
        pattern = p_raw.strip()

        if not pattern or pattern.startswith('#'): # Should be pre-filtered by get_gitignore_patterns
            continue
        
        if pattern.startswith('!'):
            # Negation patterns are skipped for simplicity, maintaining original behavior.
            # A full implementation would track matches and apply negations last.
            continue
        
        is_dir_only_pattern = pattern.endswith('/')
        if is_dir_only_pattern:
            pattern = pattern[:-1] # Remove trailing slash for matching
        
        # Patterns starting with / are anchored to the base_directory
        if pattern.startswith('/'):
            anchored_p = pattern[1:]
            # Check if the relative_path itself matches the anchored pattern
            if fnmatch.fnmatch(relative_path, anchored_p):
                if is_dir_only_pattern and not path_is_dir: # e.g. `/foo/` should not match file `foo`
                    continue # This rule doesn't apply; try next pattern
                return True
            # Check if relative_path is a child of an anchored directory pattern
            # e.g., pattern `/logs/`, relative_path `logs/today.txt`
            if relative_path.startswith(anchored_p + '/'):
                return True
        # Patterns containing / (but not starting with /) are relative to .gitignore dir.
        # Git: "foo/bar" matches "foo/bar" at the current .gitignore level. Does not match "a/foo/bar".
        # fnmatch needs to match the whole relative_path for this.
        elif '/' in pattern:
            if fnmatch.fnmatch(relative_path, pattern):
                if is_dir_only_pattern and not path_is_dir and relative_path == pattern: # e.g. `foo/bar/` vs file `foo/bar`
                    continue
                return True
            # Check if relative_path is a child of such a pattern
            # e.g. pattern `some/dir`, relative_path `some/dir/file.txt`
            if relative_path.startswith(pattern + '/'):
                # Similar to anchored case, pattern implies a directory.
                return True
        # Simple patterns (no slashes): match basename, or any directory component.
        else:
            # Match basename of the path/file
            if fnmatch.fnmatch(os.path.basename(abs_path), pattern):
                if is_dir_only_pattern and not path_is_dir: # e.g. `build/` vs file `build`
                    continue
                return True
            
            # Match if any directory component of the path matches the pattern
            # e.g., pattern `build` should ignore `src/build/index.html`
            if relative_path: # Ensure not empty string (root case, though unlikely here)
                # Path(relative_path).parent gives the directory part of relative_path
                # Path(relative_path).parent.parts gives ('src', 'build') for 'src/build/index.html'
                path_dir_components = Path(relative_path).parent.parts
                for part in path_dir_components:
                    if fnmatch.fnmatch(part, pattern):
                        # If `pattern` came from `patt/` (is_dir_only_pattern=True), this is fine,
                        # because `part` refers to a directory component.
                        return True
    return False

def get_directory_tree(directory, gitignore_patterns, base_directory_for_ignore):
    """Generate a tree representation of the directory structure, respecting .gitignore."""
    # First check if the provided path is actually a directory
    if not os.path.isdir(directory):
        return f"Error: {directory} is not a directory"
    
    result = []
    
    def print_tree(current_dir_path, prefix=""):
        # Ensure current_dir_path is a directory before proceeding
        if not os.path.isdir(current_dir_path): # Should not happen if called correctly
            return
            
        # Get items in directory
        try:
            items_in_dir = sorted(os.listdir(current_dir_path))
        except PermissionError:
            result.append(f"{prefix}(Permission denied)")
            return
        except Exception as e: # Catch other potential OS errors
            result.append(f"{prefix}(Error listing directory: {str(e)})")
            return
        
        # Filter items based on .gitignore and other rules before determining tree structure
        valid_items_for_tree = []
        for item_name in items_in_dir:
            item_path = os.path.join(current_dir_path, item_name)
            
            # Apply .gitignore rules first
            if should_ignore(item_path, gitignore_patterns, base_directory_for_ignore):
                continue
            
            # If item is a hidden file (e.g. .myconfig), it's kept at this stage.
            # Recursion into hidden directories is handled later.
            valid_items_for_tree.append(item_name)
        
        # Process each valid entry
        for i, item_name in enumerate(valid_items_for_tree):
            is_last = i == len(valid_items_for_tree) - 1
            item_path = os.path.join(current_dir_path, item_name) # Reconstruct item_path for this item
            
            # Choose the appropriate prefix characters
            if is_last:
                branch = "└── "
                new_prefix = prefix + "    "
            else:
                branch = "├── "
                new_prefix = prefix + "│   "
            
            # Add the entry to our result
            result.append(f"{prefix}{branch}{item_name}")
            
            # Recursively process directories
            if os.path.isdir(item_path):
                # Original behavior: hidden directories are not traversed for tree display.
                # This means if `.git` is not in .gitignore (or un-ignored by `!`),
                # it would be listed if `valid_items_for_tree` includes it,
                # but `print_tree` won't recurse into it due to `not item_name.startswith('.')`.
                if not item_name.startswith('.'): 
                    print_tree(item_path, new_prefix)
    
    # Start the recursive process
    result.append(os.path.basename(os.path.abspath(directory))) # Root directory name
    print_tree(directory) # Initial call for the root directory itself
    
    return '\n'.join(result)

def process_directory(directory_path):
    """Process all files in a directory, respecting .gitignore rules."""
    abs_directory_path = os.path.abspath(directory_path) # Standardize to absolute path
    
    # Check if the path is a directory
    if not os.path.isdir(abs_directory_path):
        if os.path.isfile(abs_directory_path):
            # If it's a single file, process just that file
            output = f"Processing single file: {os.path.basename(abs_directory_path)}\n\n"
            
            try:
                with open(abs_directory_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                    
                output += f"{'=' * 80}\n"
                output += f"File: {os.path.basename(abs_directory_path)}\n"
                output += f"{'=' * 80}\n"
                output += content + "\n"
            except Exception as e:
                output += f"Error reading file: {str(e)}\n"
                
            return output
        else:
            return f"Error: {abs_directory_path} is neither a file nor a directory"
    
    # Get gitignore patterns from the root of the processing directory
    gitignore_patterns = get_gitignore_patterns(abs_directory_path)
    
    # Generate directory tree, passing patterns and the base path for ignore checks
    # The base_directory for ignore rules is the directory_path itself.
    tree_structure = get_directory_tree(abs_directory_path, gitignore_patterns, abs_directory_path)
    
    # Initialize output string with the tree structure
    output = f"Directory Structure:\n{tree_structure}\n\n"
    output += "File Contents:\n"
    
    # Walk through the directory
    for root, dirs, files in os.walk(abs_directory_path, topdown=True):
        # Filter directories to prevent descending into ignored ones (dirs[:] modifies os.walk's list)
        # Also respect original hidden directory rule
        
        # Create a copy of dirs to iterate over, as we're modifying dirs itself
        original_dirs = list(dirs) 
        dirs[:] = [] # Clear dirs to selectively re-add non-ignored ones

        for d_name in original_dirs:
            dir_path = os.path.join(root, d_name)
            if should_ignore(dir_path, gitignore_patterns, abs_directory_path):
                continue
            # Original behavior: skip traversing hidden directories for content processing
            if d_name.startswith('.'):
                continue
            dirs.append(d_name) # Add back to dirs if not ignored
        
        for file_name in files:
            file_path = os.path.join(root, file_name)
            
            # Check if the file should be ignored by .gitignore rules first
            if should_ignore(file_path, gitignore_patterns, abs_directory_path):
                continue
            
            # Original filters: Skip binary files and hidden files
            if file_name.startswith('.') or is_binary_file(file_path):
                continue
                
            # Read file content
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                
                # Skip empty files
                if not content.strip():
                    continue
                
                # Get relative path for display
                rel_path = os.path.relpath(file_path, abs_directory_path)
                
                # Add file content to output
                output += f"\n{'=' * 80}\n"
                output += f"File: {rel_path}\n"
                output += f"{'=' * 80}\n"
                output += content + "\n"
            except Exception as e: # Catch errors reading individual files
                rel_path = os.path.relpath(file_path, abs_directory_path) # Try to get rel_path for error msg
                output += f"\n{'=' * 80}\n"
                output += f"File: {rel_path}\n"
                output += f"{'=' * 80}\n"
                output += f"Error reading file: {str(e)}\n"
    
    return output

def is_binary_file(file_path):
    """Check if a file is binary."""
    try:
        # Open in binary read mode to avoid encoding issues during check
        with open(file_path, 'rb') as f:
            # Read a chunk of the file
            chunk = f.read(1024)
            # Check for null bytes, a common indicator of binary files
            # More sophisticated checks exist, but this is a common heuristic.
            if b'\0' in chunk:
                return True
            # Attempt to decode as UTF-8; if it fails, it's likely binary or non-UTF-8 text.
            # For this tool's purpose (text processing), non-UTF-8 text might as well be binary.
            try:
                chunk.decode('utf-8')
            except UnicodeDecodeError:
                return True
        return False # No null bytes and decodable as UTF-8 (or empty)
    except IOError: # File might not be readable
        return True # Treat as binary/inaccessible if error


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Copy directory or file contents to clipboard and save to context.txt, respecting .gitignore')
    parser.add_argument('path', help='Path to the directory or file to process')
    parser.add_argument('-o', '--output', default='context.txt', help='Output file name (default: context.txt)')
    
    args = parser.parse_args()
    
    # Process the path (either directory or file)
    output = process_directory(args.path)
    
    # Save to file
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
    except IOError as e:
        print(f"Error saving output to file {args.output}: {e}")
        # Optionally, still try to copy to clipboard
    
    # Copy to clipboard
    try:
        pyperclip.copy(output)
    except pyperclip.PyperclipException as e:
        print(f"Error copying to clipboard: {e}")
        print("You might need to install a copy/paste mechanism for your system.")
        print("For example, on Linux: sudo apt-get install xclip or sudo apt-get install xsel")
    
    processed_path_type = "Directory" if os.path.isdir(args.path) else "File"
    if os.path.exists(args.path): # Check if path was valid at all
        print(f"{processed_path_type} contents processed.")
        if os.path.exists(args.output):
             print(f"Output saved to {args.output}")
        if 'pyperclip' in globals() and pyperclip.is_available(): # Check if clipboard op likely succeeded
             print(f"Output copied to clipboard.")
        print(f"Total size: {len(output)} characters")
    else:
        # Error message would have been printed by process_directory or shown in output string
        if not output.startswith("Error:"): # if process_directory itself didn't return an error string
            print(f"Path {args.path} not found.")


if __name__ == "__main__":
    main()