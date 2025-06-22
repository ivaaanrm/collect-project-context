# Directory Content Aggregator (Context Copier)

This Python script processes a specified directory or a single file. It generates a directory tree structure (for directories) and aggregates the content of relevant text files into a single string. This output is then saved to a specified file (default: `context.txt`) and copied to the system clipboard.

It's particularly useful for quickly gathering context from a project to paste into Large Language Models (LLMs), for creating documentation snippets, or for sharing code context.

## Features

*   **Directory Tree Generation**: Displays a visual tree of the directory structure.
*   **File Content Aggregation**: Includes the content of non-binary, non-hidden text files.
*   **.gitignore Aware**: Respects ignore patterns found in a `.gitignore` file located at the root of the processed directory.
    *   Filters both the directory tree and the files included for content aggregation.
    *   Supports common `.gitignore` patterns (e.g., `*.log`, `build/`, `/docs`, `src/*.tmp`).
    *   *Note*: Complex negation patterns (e.g., `!important.log`) are currently skipped for simplicity in the ignore logic.
*   **Single File Processing**: Can also process a single file directly if a file path is provided.
*   **Clipboard Integration**: Copies the aggregated output to the clipboard for easy pasting.
*   **File Output**: Saves the complete output to a text file.

## Requirements

*   Python 3.6+
*   `pyperclip` library

## Installation

1.  Ensure you have Python 3.6 or newer installed.
2.  Save the script (e.g., as `context_copier.py`).
3.  Install the required Python package using pip:
    ```bash
    pip install -r requirements.txt
    ```
    (This will install `pyperclip`.)

## Usage

Run the script from your terminal:

```bash
python collect.py <path_to_directory_or_file> [options]