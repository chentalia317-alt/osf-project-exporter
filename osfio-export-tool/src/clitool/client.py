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
        'x': os.path.join(
            'tests', 'stubs', 'singlenode.json'),
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
        'tf1-2_folder': os.path.join(
            'tests', 'stubs', 'files', 'tf1folders-2.json'),
        'tf1-2_files': os.path.join(
            'tests', 'stubs', 'files', 'tf2-second-folders.json'),
        'tf1_files': os.path.join(
            'tests', 'stubs', 'files', 'tf1files.json'),
        'tf2_folder': os.path.join(
            'tests', 'stubs', 'files', 'tf2folders.json'),
        'tf2-second_folder': os.path.join(
            'tests', 'stubs', 'files', 'tf2-second-folders.json'),
        'tf2_files': os.path.join(
            'tests', 'stubs', 'files', 'tf2files.json'),
        'tf2-second_files': os.path.join(
            'tests', 'stubs', 'files', 'tf2-second-files.json'),
        'tf2-second-2_files': os.path.join(
            'tests', 'stubs', 'files', 'tf2-second-files-2.json'),
        'license': os.path.join(
            'tests', 'stubs', 'licensestub.json'),
        'subjects': os.path.join(
            'tests', 'stubs', 'subjectsstub.json'),
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


def call_api(url, method, pat, per_page=None, filters={}):
    """Call OSF v2 API methods.

    Parameters
    ----------
    url: str
        URL to API method/resource/query.
    method: str
        HTTP method for the request.
    pat: str
        Personal Access Token to authorise a user with.
    per_page: int
        Number of items to include in a JSON page for API responses.
        The maximum is 100.
    filters: dict
        Dictionary of query parameters to filter results with.

        Example Input: {'category': 'project', 'title': 'ttt'}
        Example Query String: ?filter[category]=project&filter[title]=ttt

    Returns
    ----------
        result: HTTPResponse
            Response to the request from the API.
    """
    if (filters or per_page) and method == 'GET':
        query_string = '&'.join([f'filter[{key}]={value}'
                                 for key, value in filters.items() if not isinstance(value, dict)])
        if per_page:
            query_string += f'&page[size]={per_page}'
        url = f'{url}?{query_string}'
    
    API_VERSION = '2.20'
    request = webhelper.Request(url, method=method)
    request.add_header('Authorization', f'Bearer {pat}')
    # Pin API version so that responses have correct format
    request.add_header('Accept', f'application/vnd.api+json;version={API_VERSION}')
    result = webhelper.urlopen(request)
    return result


def explore_file_tree(curr_link, pat, dryrun=True):
    """Explore and get names of files stored in OSF.
    
    Parameters
    ----------
    curr_link: string
        URL/name to use to get real/mock files and folders.
    pat: string
        Personal Access Token to authorise a user.
    dryrun: bool
        Flag to indicate whether to use mock JSON files or real API calls.

    Returns
    ----------
        filenames: list[str]
            List of file paths found in the project."""

    FILE_FILTER = {
        'kind': 'file'
    }
    FOLDER_FILTER = {
        'kind': 'folder'
    }
    per_page = 100

    filenames = []

    is_last_page_folders = False
    while not is_last_page_folders:
        # Use Mock JSON if unit/integration testing
        if dryrun:
            folders = MockAPIResponse(f"{curr_link}_folder").read()
        else:
            folders = json.loads(
                call_api(
                    curr_link, 'GET', pat,
                    per_page=per_page, filters=FOLDER_FILTER
                ).read()
            )
        
        # Find deepest subfolders first to avoid missing files
        try:
            for folder in folders['data']:
                link = folder['relationships']['files']['links']['related']['href']
                filenames += explore_file_tree(link, pat, dryrun=dryrun)
        except KeyError:
            pass

        # Now find files in current folder to complete current page
        is_last_page_files = False
        while not is_last_page_files:
            if dryrun:
                files = MockAPIResponse(f"{curr_link}_files").read()
            else:
                files = json.loads(
                    call_api(
                        curr_link, 'GET', pat,
                        per_page=per_page, filters=FILE_FILTER
                    ).read()
                )
            try:
                for file in files['data']:
                    filenames.append(file['attributes']['materialized_path'])
            except KeyError:
                pass
            # Files could be split into multiple pages - loop until no more pages
            curr_link = files['links']['next']
            if curr_link == None:
                is_last_page_files = True
        
        # Folders could be split across pages - loop until no more pages
        curr_link = folders['links']['next']
        if curr_link == None:
            is_last_page_folders = True

    return filenames


def get_project_data(pat, dryrun, project_url=''):
    """Pull and list projects for a user from the OSF.

    Parameters
    ----------
    pat: str
        Personal Access Token to authorise a user with.
    dryrun: bool
        If True, use test data from JSON stubs to mock API calls.
    project_url: str
        Optional URL to a specific OSF project, of form <URL>.io/<project_id>/

    Returns
    ----------
        projects: list[dict]
            List of dictionaries representing projects.
    """

    # Don't get other projects if user gives valid/invalid URL to save time
    project_id = None
    if project_url != '':
        try:
            project_id = project_url.split(".io/")[1].strip("/")
            if '/' in project_id:
                # Need extra processing for API links
                project_id = project_id.split('/')[-1]
        except Exception as e:
            click.echo("Project URL is invalid! PLease try another")
            return []
    
    if not dryrun:
        if project_id:
            result = call_api(
                f'{API_HOST}/nodes/{project_id}/', 'GET', pat
            )
            # Put data into same format as if multiple nodes found
            nodes = {'data': [json.loads(result.read())['data']]}
        else:
            result = call_api(
                f'{API_HOST}/users/me/nodes/', 'GET', pat
            )
            nodes = json.loads(result.read())
    else:
        if project_id:
            # Put data into same format as if multiple nodes found
            nodes = {'data': [MockAPIResponse(project_id).read()['data']]}
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

        # Get links for data for these keys and extract
        # certain attributes for each one
        RELATION_KEYS = [
            'affiliated_institutions',
            'contributors',
            'identifiers',
            'license',
            'subjects'
        ]
        for key in RELATION_KEYS:
            if not dryrun:
                # Check relationship exists and can get link to linked data
                # Otherwise just pass a placeholder dict
                try:
                    link = relations[key]['links']['related']['href']
                    json_data = json.loads(
                        call_api(
                            link, 'GET', pat,
                            filters=URL_FILTERS.get(key, {})
                        ).read()
                    )
                except KeyError:
                    if key == 'subjects':
                        raise KeyError() # Subjects should have a href link
                    json_data = {'data': None}
            else:
                json_data = MockAPIResponse(key).read()

            values = []
            if isinstance(json_data['data'], list):
                for item in json_data['data']:
                    # Required data can either be embedded or in attributes
                    if 'embeds' in item and key != "subjects":
                        if 'users' in item['embeds']:
                            values.append(
                                item['embeds']['users']['data']
                                ['attributes']['full_name']
                            )
                        else:
                            values.append(item['embeds']['attributes']['name'])
                    else:
                        if key == 'identifiers':
                            values.append(item['attributes']['value'])
                        elif key == 'subjects':
                            values.append(item['attributes']['text'])
                        else:
                            values.append(item['attributes']['name'])
            
            if isinstance(json_data['data'], dict): # e.g. license field
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
@click.option('--url', type=str, default='',
              help='Give a link to a project to export just that one.')
def pull_projects(pat, dryrun, filename, url=''):
    """Pull and export OSF projects to a PDF file."""

    projects = get_project_data(pat, dryrun, project_url=url)
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
