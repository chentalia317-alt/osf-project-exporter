import os
import urllib.request as webhelper

import click
from fpdf import FPDF
from mistletoe import markdown

import exporter as exporter

API_HOST_TEST = os.getenv('API_HOST_TEST', 'https://api.test.osf.io/v2')
API_HOST_PROD = os.getenv('API_HOST_PROD', 'https://api.osf.io/v2')

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

    project_id = ''
    if url:
        try:
            project_id = extract_project_id(url)
        except ValueError as e:
            click.echo(str(e))
            return

    projects = exporter.get_project_data(pat, dryrun, project_id=project_id)
    click.echo(f'Found {len(projects)} projects.')
    click.echo('Generating PDF...')
    exporter.generate_pdf(projects, filename)


@click.command()
@click.option('--pat', type=str, default='',
              prompt=True, hide_input=True,
              help='Personal Access Token to authorise OSF account access.')
@click.option('--usetest', is_flag=True, default=False,
              help="""Use this to connect to the test API environment.
              Otherwise, the production environment will be used.""")
def show_welcome(pat, usetest):
    """Get a welcome message from the OSF site.
    This is for testing if we can connect to the API."""

    if usetest:
        api_host = API_HOST_TEST
    else:
        api_host = API_HOST_PROD

    request = webhelper.Request(f'{api_host}/', method='GET')
    request.add_header('Authorization', f'Bearer {pat}')
    result = webhelper.urlopen(request)
    click.echo(result.read())
    click.echo(result.status)


# Group will be used as entry point for CLI
@click.group()
def cli():
    pass


cli.add_command(pull_projects)
cli.add_command(show_welcome)
