import os
import urllib.request as webhelper

import click
from fpdf import FPDF
from mistletoe import markdown

import exporter as exporter

API_HOST = os.getenv('API_HOST', 'https://api.test.osf.io/v2')

def extract_project_id(url):
    """Extract project ID from a given OSF project URL.

    Parameters
    ----------
    url: str
        URL of the OSF project.

    Returns
    -------
    str
        Project ID extracted from the URL.
    """
    try:
        project_id = url.split(".io/")[1].strip("/")
        if '/' in project_id:
            # Need extra processing for API links
            project_id = project_id.split('/')[-1]
        return project_id
    except Exception:
        raise ValueError(
            """
            Invalid OSF project URL.
            Please provide a valid URL in the format:
            https://osf.io/<project_id>/")
            """
        )

@click.command()
@click.option('--pat', type=str, default='',
              prompt=True, hide_input=True,
              help='Personal Access Token to authorise OSF account access.')
@click.option('--dryrun', is_flag=True, default=False,
              help='If enabled, use mock responses in place of the API.')
@click.option('--filename', type=str, default='osf_projects.pdf',
              help='Name of the PDF file to export to.')
@click.option('--url', type=str, default='',
              help="""A link to one project you want to export.

              For example: https://osf.io/dry9j/

              Leave blank to export all projects you have access to.""")
def pull_projects(pat, dryrun, filename, url=''):
    """Pull and export OSF projects to a PDF file.
    You can export all projects you have access to, or one specific one
    with the --url option."""

    try:
        project_id = extract_project_id(url)
    except ValueError as e:
        click.echo(str(e))
        return

    projects = exporter.get_project_data(pat, dryrun, project_url=url)
    click.echo(f'Found {len(projects)} projects.')
    click.echo('Generating PDF...')
    exporter.generate_pdf(projects, filename)


@click.command()
@click.option('--pat', type=str, default='',
              prompt=True, hide_input=True,
              help='Personal Access Token to authorise OSF account access.')
def get_user_details(pat):
    """Get details for a specific OSF user."""

    request = webhelper.Request(f'{API_HOST}/', method='GET')
    request.add_header('Authorization', f'Bearer {pat}')
    result = webhelper.urlopen(request)
    click.echo(result.read())
    click.echo(result.status)


# Group will be used as entry point for CLI
@click.group()
def cli():
    pass


cli.add_command(pull_projects)
cli.add_command(get_user_details)
