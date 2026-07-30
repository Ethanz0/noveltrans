"""Main Typer CLI application for noveltrans."""

import typer

from noveltrans.cli.epub_cmd import epub_app
from noveltrans.cli.glossary_cmd import glossary_app
from noveltrans.cli.init_cmd import init_cmd
from noveltrans.cli.status_cmd import status_cmd
from noveltrans.cli.style_cmd import style_app
from noveltrans.cli.summary_cmd import arc_app, story_app, summary_app
from noveltrans.cli.translate_cmd import translate_app

app = typer.Typer(
    name="noveltrans",
    help="AI-powered web novel translation CLI tool (Korean, Japanese, Chinese)",
    add_completion=False,
)

# Register top-level commands and subcommand groups
app.command("init")(init_cmd)
app.command("status")(status_cmd)
app.add_typer(translate_app, name="translate")
app.add_typer(glossary_app, name="glossary")
app.add_typer(epub_app, name="epub")
app.add_typer(style_app, name="style")
app.add_typer(summary_app, name="summary")
app.add_typer(arc_app, name="arc")
app.add_typer(story_app, name="story")


@app.callback()
def main() -> None:
    """noveltrans CLI entrypoint."""


if __name__ == "__main__":
    app()
