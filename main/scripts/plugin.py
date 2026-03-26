from pathlib import Path

from mkdocs.config import Config
from mkdocs.structure.files import File, Files
from mkdocs.structure.pages import Page

ADD_TO_DOCS = [
    "changelog.md",
]
VIRTUAL_FILES = dict[str, str]()


def on_files(files: Files, config: Config):
    """
    Add virtual files.
    """

    all_files = [file for file in files]

    for path in ADD_TO_DOCS:
        content = Path(path).read_text()
        VIRTUAL_FILES[path] = content

        file = File(
            path,
            config["docs_dir"],
            config["site_dir"],
            config["use_directory_urls"],
        )
        all_files.append(file)

    return Files(all_files)


def on_page_read_source(page: Page, config: Config) -> str | None:
    if page.file.src_path in VIRTUAL_FILES:
        return VIRTUAL_FILES[page.file.src_path]
    return None
