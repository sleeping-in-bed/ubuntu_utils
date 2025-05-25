#!/usr/bin/env python3
import os
from pathlib import Path

import click
from bs4 import BeautifulSoup


@click.command()
@click.option(
    "--dir", "htmlcov_dir", default="htmlcov", help="Coverage HTML output directory."
)
def main(htmlcov_dir):
    """Generate an index.html that links to sub coverage reports."""
    links = []
    if not os.path.exists(htmlcov_dir):
        click.echo(f"Directory '{htmlcov_dir}' does not exist.", err=True)
        raise SystemExit(1)

    for name in sorted(os.listdir(htmlcov_dir)):
        path = os.path.join(htmlcov_dir, name)
        index_file = os.path.join(path, "index.html")
        if os.path.isdir(path) and os.path.exists(index_file):
            soup = BeautifulSoup(
                Path(index_file).read_text(encoding="utf-8"), "html.parser"
            )
            coverage_span = soup.find("span", class_="pc_cov")
            content = (
                f'<li><a href="{name}/index.html">{name} Coverage Report</a><br/>'
                f"<p>Coverage report: {coverage_span.text}</p></li>"
            )
            links.append(content)

    links_html = "\n".join(links)
    content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Coverage Reports</title>
</head>
<body>
    <h1>Coverage Reports</h1>
    <ul>
        {links_html}
    </ul>
</body>
</html>"""

    index_path = os.path.join(htmlcov_dir, "index.html")
    Path(index_path).write_text(content, encoding="utf-8")
