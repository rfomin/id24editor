# id24editor

Unfinished ID24 SBARDEF editor.

## Setup and Building

1.  **Create a virtual environment:**

    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
    ```

2.  **Install dependencies:**

    You can install the project and its dependencies from `pyproject.toml` using `pip`:

    ```bash
    pip install .
    ```
    If you are using `uv`, you can use the following command:
    ```bash
    uv pip install .
    ```

3.  **Build the project:**

    This project uses `pyside6-project` to compile Qt UI files (`.ui`) into Python code. Run the following command to build the project:

    ```bash
    pyside6-project build
    ```

## Running the Application

After the build process is complete, you can run the editor with the following command:

```bash
python src/main.py
```
