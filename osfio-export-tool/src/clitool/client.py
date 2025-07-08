import json
import os
import datetime
import urllib.request as webhelper

import click
from fpdf import FPDF

API_HOST = 'https://api.test.osf.io/v2'


class MockAPIResponse:
    """Simulate OSF API response for testing purposes.

    :param field: String for the field name to mock.
    """

    JSON_FILES = {
        'nodes': os.path.join(
            'tests', 'stubs', 'nodestubs.json'),
        'affiliated_institutions': os.path.join(
            'tests', 'stubs', 'institutionstubs.json'),
        'contributors': os.path.join(
            'tests', 'stubs', 'contributorstubs.json'),
        'identifiers': os.path.join(
            'tests', 'stubs', 'doistubs.json'),
        'custom_metadata': os.path.join(
            'tests', 'stubs', 'custommetadatastub.json'),
        'root_folder': os.path.join(
            'tests', 'stubs', 'files', 'rootfolders.json'),
        'root_files': os.path.join(
            'tests', 'stubs', 'files', 'rootfiles.json'),
        'tf1_folder': os.path.join(
            'tests', 'stubs', 'files', 'tf1folders.json'),
        'tf1_files': os.path.join(
            'tests', 'stubs', 'files', 'tf1files.json'),
        'tf2_folder': os.path.join(
            'tests', 'stubs', 'files', 'tf2folders.json'),
        'tf2_files': os.path.join(
            'tests', 'stubs', 'files', 'tf2files.json'),
        'license': os.path.join(
            'tests', 'stubs', 'licensestub.json'),
    }

    def __init__(self, field):
        self.field = field

    def read(self):
        """Get mock response for a field."""

        if self.field in MockAPIResponse.JSON_FILES.keys():
            with open(MockAPIResponse.JSON_FILES[self.field], 'r') as file:
                return json.load(file)
        else:
            return {}


# Reduce response size by applying filters on fields
URL_FILTERS = {
    'identifiers': {
        'category': 'doi'
    }
}


def call_api(url, method, pat, filters={}):
    """Call OSF v2 API methods.

    Parameters
    ----------
    url: str
        URL to API method/resource/query.
    method: str
        HTTP method for the request.
    pat: str
        Personal Access Token to authorise a user with.
    filters: dict
        Dictionary of query parameters to filter results with.

        Example Input: {'category': 'project', 'title': 'ttt'}
        Example Query String: ?filter[category]=project&filter[title]=ttt

    Returns
    ----------
        result: HTTPResponse
            Response to the request from the API.
    """
    if filters and method == 'GET':
        query_string = '&'.join([f'filter[{key}]={value}'
                                 for key, value in filters.items()])
        url = f'{url}?{query_string}'
    request = webhelper.Request(url, method=method)
    request.add_header('Authorization', f'Bearer {pat}')
    result = webhelper.urlopen(request)
    return result


def explore_file_tree(curr_link, pat, dryrun=True):
    """Explore and get names of files stored in OSF"""

    FILE_FILTER = {
        'kind': 'file'
    }
    FOLDER_FILTER = {
        'kind': 'folder'
    }
    filenames = []

    # Get files and folders
    # # From Mock API if testing, otherwise use query params
    if dryrun:
        files = MockAPIResponse(f"{curr_link}_files").read()
        folders = MockAPIResponse(f"{curr_link}_folder").read()
    else:
        files = json.loads(
            call_api(curr_link, 'GET', pat, filters=FILE_FILTER).read()
        )
        folders = json.loads(
            call_api(curr_link, 'GET', pat, filters=FOLDER_FILTER).read()
        )

    # Reach current deepest child for folders before adding filenames
    try:
        for folder in folders['data']:
            link = folder['relationships']['files']['links']['related']['href']
            filenames += explore_file_tree(link, pat, dryrun=dryrun)
    except KeyError:
        pass
    for file in files['data']:
        filenames.append(file['attributes']['materialized_path'])

    return filenames


def get_project_data(pat, dryrun):
    """Pull and list projects for a user from the OSF.

    Parameters
    ----------
    pat: str
        Personal Access Token to authorise a user with.
    dryrun: bool
        If True, use test data from JSON stubs to mock API calls.

    Returns
    ----------
        projects: list[dict]
            List of dictionaries representing projects.
    """

    if not dryrun:
        result = call_api(
            f'{API_HOST}/users/me/nodes/', 'GET', pat
        )
        nodes = json.loads(result.read())
    else:
        nodes = MockAPIResponse('nodes').read()

    projects = []
    for project in nodes['data']:
        if project['attributes']['category'] != 'project':
            continue
        project_data = {
            'title': project['attributes']['title'],
            'id': project['id'],
            'description': project['attributes']['description'],
            'date_created': datetime.datetime.fromisoformat(
                project['attributes']['date_created']),
            'date_modified': datetime.datetime.fromisoformat(
                project['attributes']['date_modified']),
            'tags': ', '.join(project['attributes']['tags'])
            if project['attributes']['tags'] else 'NA',
        }

        # Resource type/lang/funding info share specific endpoint
        # that isn't linked to in user nodes' responses
        if dryrun:
            metadata = MockAPIResponse('custom_metadata').read()
        else:
            metadata = json.loads(call_api(
                f"{API_HOST}/custom_item_metadata_records/{project['id']}/",
                'GET', pat
            ).read())
        metadata = metadata['data']['attributes']
        project_data['resource_type'] = metadata['resource_type_general']
        project_data['resource_lang'] = metadata['language']
        project_data['funders'] = []
        for funder in metadata['funders']:
            project_data['funders'].append(funder)

        relations = project['relationships']

        # Get list of files in project
        if dryrun:
            project_data['files'] = ', '.join(
                explore_file_tree('root', pat, dryrun=True)
            )
        else:
            # Get files hosted on OSF storage
            link = relations['files']['links']['related']['href']
            link += 'osfstorage/'
            project_data['files'] = ', '.join(
                explore_file_tree(link, pat, dryrun=False)
            )

        relation_keys = [
            'affiliated_institutions',
            'contributors',
            'identifiers',
            'license'
        ]
        for key in relation_keys:
            if not dryrun:
                link = relations[key]['links']['related']['href']
                json_data = json.loads(
                    call_api(
                        link, 'GET', pat,
                        filters=URL_FILTERS.get(key, {})
                    ).read()
                )
            else:
                json_data = MockAPIResponse(key).read()
            
            values = []

            if isinstance(json_data['data'], list):
                for item in json_data['data']:
                    # Required data can either be embedded or in attributes
                    if 'embeds' in item:
                        if 'users' in item['embeds']:
                            values.append(item['embeds']['users']['data']
                                        ['attributes']['full_name'])
                        else:
                            values.append(item['embeds']['attributes']['name'])
                    else:
                        if key == 'identifiers':
                            values.append(item['attributes']['value'])
                        else:
                            values.append(item['attributes']['name'])
            
            if isinstance(json_data['data'], dict):
                values.append(json_data['data']['attributes']['name'])

            if isinstance(values, list):
                values = ', '.join(values)
            project_data[key] = values

        projects.append(project_data)

    return projects


@click.command()
@click.option('--pat', type=str, default='',
              prompt=True, hide_input=True,
              help='Personal Access Token to authorise OSF account access.')
@click.option('--dryrun', is_flag=True, default=False,
              help='If enabled, use mock responses in place of the API.')
@click.option('--filename', type=str, default='osf_projects.pdf',
              help='Name of the PDF file to export to.')
def pull_projects(pat, dryrun, filename):
    """Pull and export OSF projects to a PDF file."""

    projects = get_project_data(pat, dryrun)
    click.echo(f'Found {len(projects)} projects.')
    click.echo('Generating PDF...')

    # Set nicer display names for certian PDF fields
    pdf_display_names = {
        'identifiers': 'DOI',
        'funders': 'Support/Funding Information'
    }

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('helvetica', size=12)
    pdf.cell(text='Exported OSF Projects', ln=True, align='C')
    pdf.write(0, '\n')
    for project in projects:
        for key in projects[0].keys():
            if key in pdf_display_names:
                field_name = pdf_display_names[key]
            else:
                field_name = key.replace('_', ' ').title()
            if isinstance(project[key], list):
                pdf.write(0, '\n')
                pdf.cell(text=f'{field_name}', ln=True, align='C')
                for item in project[key]:
                    for subkey in item.keys():
                        if subkey in pdf_display_names:
                            field_name = pdf_display_names[subkey]
                        else:
                            field_name = subkey.replace('_', ' ').title()
                        pdf.cell(
                            text=f'{field_name}: {item[subkey]}',
                            ln=True, align='C'
                        )
                pdf.write(0, '\n')
            else:
                pdf.cell(
                    text=f'{field_name}: {project[key]}',
                    ln=True, align='C'
                )
        pdf.cell(text='=======', ln=True, align='C')
    pdf.output(filename)


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
