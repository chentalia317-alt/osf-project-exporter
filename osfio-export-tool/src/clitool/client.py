import json
import os
import datetime
import urllib.request as webhelper

import click
from fpdf import FPDF
from fpdf.fonts import FontFace
from mistletoe import markdown

API_HOST = os.getenv('API_HOST', 'https://api.test.osf.io/v2')

# Global styles for PDF
BLUE = (173, 216, 230)
HEADINGS_STYLE = FontFace(emphasis="BOLD", fill_color=BLUE)


class MockAPIResponse:
    """Simulate OSF API response for testing purposes."""

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
        'wikis': os.path.join(
            'tests', 'stubs', 'wikis', 'wikistubs.json'),
        'wikis2': os.path.join(
            'tests', 'stubs', 'wikis', 'wikis2stubs.json')
    }

    MARKDOWN_FILES = {
        'helloworld': os.path.join(
            'tests', 'stubs', 'wikis', 'helloworld.md'),
        'home': os.path.join(
            'tests', 'stubs', 'wikis', 'home.md'),
        'anotherone': os.path.join(
            'tests', 'stubs', 'wikis', 'anotherone.md'),
    }

    @staticmethod
    def read(field):
        """Get mock response for a field.

        Parameters
        -----------
            field: str
                ID associated to a JSON or Markdown mock file.
                Available fields to mock are listed in class-level
                JSON_FILES and MARKDOWN_FILES attributes.

        Returns
        ------------
            Parsed JSON dictionary or Markdown."""

        if field in MockAPIResponse.JSON_FILES.keys():
            with open(MockAPIResponse.JSON_FILES[field], 'r') as file:
                return json.load(file)
        elif field in MockAPIResponse.MARKDOWN_FILES.keys():
            with open(MockAPIResponse.MARKDOWN_FILES[field], 'r') as file:
                return file.read()
        else:
            return {}


class PDF(FPDF):
    
    def __init__(self):
        super().__init__()
        self.date_printed = datetime.datetime.now()

    def footer(self):
        self.set_y(-15)
        self.set_x(-30)
        self.set_font('Times', size=8)
        self.cell(0, 10, f"Page: {self.page_no()}", align="C")
        self.set_x(10)
        self.cell(0, 10, f"Printed: {self.date_printed.strftime(
            '%Y-%m-%d %H:%M:%S'
        )}", align="L")


# Reduce response size by applying filters on fields
URL_FILTERS = {
    'identifiers': {
        'category': 'doi'
    }
}


def call_api(url, pat, method='GET', per_page=None, filters={}, is_json=True):
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
    is_json: bool
        If true, set API version to get correct API responses.

    Returns
    ----------
        result: HTTPResponse
            Response to the request from the API.
    """
    if (filters or per_page) and method == 'GET':
        query_string = '&'.join([f'filter[{key}]={value}'
                                 for key, value in filters.items()
                                 if not isinstance(value, dict)])
        if per_page:
            query_string += f'&page[size]={per_page}'
        url = f'{url}?{query_string}'

    request = webhelper.Request(url, method=method)
    request.add_header('Authorization', f'Bearer {pat}')

    # Pin API version so that JSON has correct format
    API_VERSION = '2.20'
    if is_json:
        request.add_header(
            'Accept',
            f'application/vnd.api+json;version={API_VERSION}'
        )
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
            folders = MockAPIResponse.read(f"{curr_link}_folder")
        else:
            folders = json.loads(
                call_api(
                    curr_link, pat,
                    per_page=per_page, filters=FOLDER_FILTER
                ).read()
            )

        # Find deepest subfolders first to avoid missing files
        try:
            for folder in folders['data']:
                links = folder['relationships']['files']['links']
                link = links['related']['href']
                filenames += explore_file_tree(link, pat, dryrun=dryrun)
        except KeyError:
            pass

        # Now find files in current folder
        is_last_page_files = False
        while not is_last_page_files:
            if dryrun:
                files = MockAPIResponse.read(f"{curr_link}_files")
            else:
                files = json.loads(
                    call_api(
                        curr_link, pat,
                        per_page=per_page, filters=FILE_FILTER
                    ).read()
                )
            try:
                for file in files['data']:
                    filenames.append(file['attributes']['materialized_path'])
            except KeyError:
                pass
            # Need to go to next page of files if response paginated
            curr_link = files['links']['next']
            if curr_link is None:
                is_last_page_files = True

        # Need to go to next page of folders if response paginated
        curr_link = folders['links']['next']
        if curr_link is None:
            is_last_page_folders = True

    return filenames


def explore_wikis(link, pat, dryrun=True):
    """Get wiki contents for a particular project.

    Parameters:
    -------------
    link: str
        URL to project wikis or name of wikis field to access mock JSON.
    pat: str
        Personal Access Token to authenticate a user with.
    dryrun: bool
        Flag to indicate whether to use mock JSON files or real API calls.

    Returns
    ---------------
    wikis: List of JSON representing wikis for a project."""

    wiki_content = {}
    is_last_page = False
    if dryrun:
        wikis = MockAPIResponse.read('wikis')
    else:
        wikis = json.loads(
            call_api(link, pat).read()
        )

    while not is_last_page:
        for wiki in wikis['data']:
            if dryrun:
                content = MockAPIResponse.read(wiki['attributes']['name'])
            else:
                # Decode Markdown content to allow parsing later on
                content = call_api(
                    wiki['links']['download'], pat=pat, is_json=False
                ).read().decode('utf-8')
            wiki_content[wiki['attributes']['name']] = content

        # Go to next page of wikis if pagination applied
        # so that we don't miss wikis
        link = wikis['links']['next']
        if not link:
            is_last_page = True
        else:
            if dryrun:
                wikis = MockAPIResponse.read(link)
            else:
                wikis = json.loads(
                    call_api(link, pat).read()
                )

    return wiki_content


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
        except Exception:
            click.echo("Project URL is invalid! PLease try another")
            return []

    if not dryrun:
        if project_id:
            result = call_api(
                f'{API_HOST}/nodes/{project_id}/', pat
            )
            # Put data into same format as if multiple nodes found
            nodes = {'data': [json.loads(result.read())['data']]}
        else:
            result = call_api(
                f'{API_HOST}/users/me/nodes/', pat
            )
            nodes = json.loads(result.read())
    else:
        if project_id:
            # Put data into same format as if multiple nodes found
            nodes = {'data': [MockAPIResponse.read(project_id)['data']]}
        else:
            nodes = MockAPIResponse.read('nodes')

    projects = []
    for project in nodes['data']:
        if project['attributes']['category'] != 'project':
            continue
        project_data = {
            'metadata': {
                'title': project['attributes']['title'],
                'id': project['id'],
                'url': project['links']['html'],
                'description': project['attributes']['description'],
                'date_created': datetime.datetime.fromisoformat(
                    project['attributes']['date_created']),
                'date_modified': datetime.datetime.fromisoformat(
                    project['attributes']['date_modified']),
                'tags': ', '.join(project['attributes']['tags'])
                if project['attributes']['tags'] else 'NA',
                'resource_type': 'NA',
                'resource_lang': 'NA',
                'funders': []
            },
            'files': [],
            'wikis': {}
        }

        # Resource type/lang/funding info share specific endpoint
        # that isn't linked to in user nodes' responses
        if dryrun:
            metadata = MockAPIResponse.read('custom_metadata')
        else:
            metadata = json.loads(call_api(
                f"{API_HOST}/custom_item_metadata_records/{project['id']}/",
                pat
            ).read())
        metadata = metadata['data']['attributes']
        resource_type = metadata['resource_type_general']
        resource_lang = metadata['language']
        project_data['metadata']['resource_type'] = resource_type
        project_data['metadata']['resource_lang'] = resource_lang
        for funder in metadata['funders']:
            project_data['metadata']['funders'].append(funder)

        relations = project['relationships']

        # Get list of files in project
        if dryrun:
            files = explore_file_tree('root', pat, dryrun=True)
            for f in files:
                project_data['files'].append((f, None, None))
        else:
            # Get files hosted on OSF storage
            link = relations['files']['links']['related']['href']
            link += 'osfstorage/'
            project_data['files'] = ', '.join(
                explore_file_tree(link, pat, dryrun=False)
            )

        # These attributes need link traversal to get their data
        # Most should be part of the project metadata
        METADATA_RELATIONS = [
            'affiliated_institutions',
            'identifiers',
            'license',
            'subjects',
        ]
        RELATION_KEYS = METADATA_RELATIONS + ['contributors']
        for key in RELATION_KEYS:
            if not dryrun:
                # Check relationship exists and can get link to linked data
                # Otherwise just pass a placeholder dict
                try:
                    link = relations[key]['links']['related']['href']
                    json_data = json.loads(
                        call_api(
                            link, pat,
                            filters=URL_FILTERS.get(key, {})
                        ).read()
                    )
                except KeyError:
                    if key == 'subjects':
                        raise KeyError()  # Subjects should have a href link
                    json_data = {'data': None}
            else:
                json_data = MockAPIResponse.read(key)

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

            if isinstance(json_data['data'], dict):  # e.g. license field
                values.append(json_data['data']['attributes']['name'])

            if isinstance(values, list):
                if key != 'contributors':
                    values = ', '.join(values)
                else:
                    contributors = []
                    for c in values:
                        contributors.append((c, False, 'N/A'))
                    values = contributors

            if key in METADATA_RELATIONS:
                project_data['metadata'][key] = values
            else:
                project_data[key] = values

        project_data['wikis'] = explore_wikis(
            f'{API_HOST}/nodes/{project['id']}/wikis/',
            pat=pat, dryrun=dryrun
        )

        projects.append(project_data)

    return projects


def write_pdfs(projects, folder=''):
    """Make PDF for each project.

    Parameters
    ------------
        projects: dict[str, str|tuple]
            Projects found to export into the PDF.
        folder: str
            The path to the folder to output the project PDFs in.
            Default is the current working directory.

    Returns
    ------------
        pdfs: list
            List of created PDF files.
    """

    def write_list_section(key, fielddict):
        """Handle writing fields based on their type to PDF.
        Possible types are lists or strings."""

        # Set nicer display names for certain PDF fields
        pdf_display_names = {
            'identifiers': 'DOI',
            'funders': 'Support/Funding Information'
        }
        if key in pdf_display_names:
            field_name = pdf_display_names[key]
        else:
            field_name = key.replace('_', ' ').title()
        if isinstance(fielddict[key], list):
            pdf.write(0, '\n')
            pdf.set_font('Times', size=14)
            pdf.multi_cell(
                0, h=0,
                text=f'**{field_name}**\n\n',
                align='L', markdown=True
            )
            pdf.set_font('Times', size=12)
            for item in fielddict[key]:
                for subkey in item.keys():
                    if subkey in pdf_display_names:
                        field_name = pdf_display_names[subkey]
                    else:
                        field_name = subkey.replace('_', ' ').title()

                    pdf.multi_cell(
                        0, h=0,
                        text=f'**{field_name}:** {item[subkey]}\n\n',
                        align='L', markdown=True
                    )
                pdf.write(0, '\n')
        else:
            pdf.multi_cell(
                0,
                h=0,
                text=f'**{field_name}:** {fielddict[key]}\n\n',
                align='L',
                markdown=True
            )

    pdfs = []
    for project in projects:
        pdf = PDF()
        pdf.add_page()
        pdf.set_line_width(0.05)
        pdf.set_left_margin(10)
        pdf.set_right_margin(10)
        pdf.set_font('Times', size=12)
        wikis = project.pop('wikis')

        # Write header section
        title = project['metadata']['title']
        pdf.set_font('Times', size=18, style='B')
        pdf.multi_cell(0, h=0, text=f'{title}\n', align='L')
        pdf.set_font('Times', size=12)
        url = project['metadata'].pop('url', '')
        if url:
            pdf.multi_cell(
                0, h=0,
                text=f'Project URL: {url}\n',
                align='L'
            )
        pdf.ln()

        # Write title for metadata section, then actual fields
        pdf.set_font('Times', size=16, style='B')
        pdf.multi_cell(0, h=0, text='1. Project Metadata\n', align='L')
        pdf.set_font('Times', size=12)
        for key in project['metadata']:
            write_list_section(key, project['metadata'])
        pdf.write(0, '\n')
        pdf.write(0, '\n')

        # Write Contributors in table
        pdf.set_font('Times', size=16, style='B')
        pdf.multi_cell(0, h=0, text='2. Contributors\n', align='L')
        pdf.set_font('Times', size=12)
        with pdf.table(
            headings_style=HEADINGS_STYLE,
            col_widths=(1, 0.5, 1)
        ) as table:
            row = table.row()
            row.cell('Name')
            row.cell('Bibliographic?')
            row.cell('Email (if available)')
            for data_row in project['contributors']:
                row = table.row()
                for datum in data_row:
                    if datum is True:
                        datum = 'Yes'
                    if datum is False:
                        datum = 'N/A'
                    row.cell(datum)
        pdf.write(0, '\n')
        pdf.write(0, '\n')

        # List files stored in storage providers
        # For now only OSF Storage is involved
        pdf.set_font('Times', size=16, style='B')
        pdf.multi_cell(0, h=0, text='3. Files in Main Project\n', align='L')
        pdf.write(0, '\n')
        pdf.set_font('Times', size=14, style='B')
        pdf.multi_cell(0, h=0, text='OSF Storage\n', align='L')
        pdf.set_font('Times', size=12)
        with pdf.table(
            headings_style=HEADINGS_STYLE,
            col_widths=(1, 0.5, 1)
        ) as table:
            row = table.row()
            row.cell('File Name')
            row.cell('Size (MB)')
            row.cell('Download Link')
            for data_row in project['files']:
                row = table.row()
                for datum in data_row:
                    if datum is True:
                        datum = 'Yes'
                    if datum is False or datum is None:
                        datum = 'N/A'
                    row.cell(datum)

        # Write wikis separately to more easily handle Markdown parsing
        pdf.ln()
        pdf.set_font('Times', size=18, style='B')
        pdf.multi_cell(0, h=0, text='4. Wiki\n', align='L')
        pdf.ln()
        for i, wiki in enumerate(wikis.keys()):
            pdf.set_font('Times', size=16, style='B')
            pdf.multi_cell(0, h=0, text=f'{wiki}\n')
            pdf.set_font('Times', size=12)
            html = markdown(wikis[wiki])
            pdf.write_html(html)
            if i < len(wikis.keys())-1:
                pdf.add_page()

        filename = f'{title}_export.pdf'
        pdf.output(os.path.join(folder, filename))
        pdfs.append(pdf)

    return pdfs


@click.command()
@click.option('--pat', type=str, default='',
              prompt=True, hide_input=True,
              help='Personal Access Token to authorise OSF account access.')
@click.option('--dryrun', is_flag=True, default=False,
              help='If enabled, use mock responses in place of the API.')
@click.option('--folder', type=str, default='',
              help='Name of the PDF file to export to.')
@click.option('--url', type=str, default='',
              help="""A link to one project you want to export.

              For example: https://osf.io/dry9j/

              Leave blank to export all projects you have access to.""")
def pull_projects(pat, dryrun, folder, url=''):
    """Pull and export OSF projects to a PDF file.
    You can export all projects you have access to, or one specific one
    with the --url option."""

    projects = get_project_data(pat, dryrun, project_url=url)
    click.echo(f'Found {len(projects)} projects.')
    click.echo('Generating PDF...')
    write_pdfs(projects, folder)


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
