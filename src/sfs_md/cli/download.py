"""
CLI för nedladdning av SFS-dokument.
"""

import click
from pathlib import Path
from typing import List, Optional


@click.command()
@click.option(
    "--ids",
    default="all",
    help="Kommaseparerad lista med dokument-ID:n eller 'all' för alla dokument",
)
@click.option(
    "--out",
    default="sfs_docs",
    type=click.Path(),
    help="Katalog att spara nedladdade dokument i",
)
@click.option(
    "--source",
    type=click.Choice(["riksdagen", "rkrattsbaser"]),
    default="riksdagen",
    help="Källa för nedladdning",
)
@click.option(
    "--year",
    type=int,
    help="Filtrera för specifikt årtal (fungerar med --ids all och --source riksdagen)",
)
@click.option("--verbose", "-v", is_flag=True, help="Visa detaljerad utskrift")
def download(
    ids: str, out: str, source: str, year: Optional[int], verbose: bool
) -> None:
    """Ladda ner SFS-dokument från Riksdagen eller Regeringskansliet."""
    
    click.echo(f"🔄 Laddar ner SFS-dokument från {source}")
    
    if verbose:
        click.echo(f"Parametrar:")
        click.echo(f"  IDs: {ids}")
        click.echo(f"  Output: {out}")
        click.echo(f"  Källa: {source}")
        if year:
            click.echo(f"  År: {year}")
    
    # Här skulle du importera och använda din befintliga nedladdningslogik
    # from ..downloaders.riksdagen import RiksdagenDownloader
    # from ..downloaders.rkrattsbaser import RkrattbaserDownloader
    
    click.echo("⚠️  Implementation needed: Flytta logik från download_sfs_docs.py")


def main() -> None:
    """Entry point för CLI-kommando."""
    download()


if __name__ == "__main__":
    main()
