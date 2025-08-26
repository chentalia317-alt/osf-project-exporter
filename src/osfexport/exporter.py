from collections import deque
import json
import os
import datetime
import urllib.request as webhelper

API_HOST_TEST = os.getenv('API_HOST_TEST', 'https://api.test.osf.io/v2')
API_HOST_PROD = os.getenv('API_HOST_PROD', 'https://api.osf.io/v2')

STUBS_DIR = os.path.join(
    os.path.dirname(__file__), 'stubs'
)

# Reduce response size by applying filters on fields
URL_FILTERS = {
    'identifiers': {
        'category': 'doi'
    }
}


class MockAPIResponse:
    """Simulate OSF API response for testing purposes."""

    JSON_FILES = {
        'nodes': os.path.join(
            STUBS_DIR, 'nodestubs.json'),
        'nodes2': os.path.join(
            STUBS_DIR, 'nodestubs2.json'),
        'x': os.path.join(
            STUBS_DIR, 'singlenode.json'),
        'a': os.path.join(
            STUBS_DIR, 'asingle.json'),
        'affiliated_institutions': os.path.join(
            STUBS_DIR, 'institutionstubs.json'),
        'contributors': os.path.join(
            STUBS_DIR, 'contributorstubs.json'),
        'identifiers': os.path.join(
            STUBS_DIR, 'doistubs.json'),
        'custom_metadata': os.path.join(
            STUBS_DIR, 'custommetadatastub.json'),
        'root_folder': os.path.join(
            STUBS_DIR, 'files', 'rootfolders.json'),
        'root_files': os.path.join(
            STUBS_DIR, 'files', 'rootfiles.json'),
        'tf1_folder': os.path.join(
            STUBS_DIR, 'files', 'tf1folders.json'),
        'tf1-2_folder': os.path.join(
            STUBS_DIR, 'files', 'tf1folders-2.json'),
        'tf1-2_files': os.path.join(
            STUBS_DIR, 'files', 'tf2-second-folders.json'),
        'tf1_files': os.path.join(
            STUBS_DIR, 'files', 'tf1files.json'),
        'tf2_folder': os.path.join(
            STUBS_DIR, 'files', 'tf2folders.json'),
        'tf2-second_folder': os.path.join(
            STUBS_DIR, 'files', 'tf2-second-folders.json'),
        'tf2_files': os.path.join(
            STUBS_DIR, 'files', 'tf2files.json'),
        'tf2-second_files': os.path.join(
            STUBS_DIR, 'files', 'tf2-second-files.json'),
        'tf2-second-2_files': os.path.join(
            STUBS_DIR, 'files', 'tf2-second-files-2.json'),
        'license': os.path.join(
            STUBS_DIR, 'licensestub.json'),
        'subjects': os.path.join(
            STUBS_DIR, 'subjectsstub.json'),
        'wikis': os.path.join(
            STUBS_DIR, 'wikis', 'wikistubs.json'),
        'wikis2': os.path.join(
            STUBS_DIR, 'wikis', 'wikis2stubs.json'),
        'x-child-1': os.path.join(
            STUBS_DIR, 'components', 'x-child-1.json'),
        'x-child-2': os.path.join(
            STUBS_DIR, 'components', 'x-child-2.json'),
        'empty-children': os.path.join(
            STUBS_DIR, 'components', 'empty-children.json'),
    }

    MARKDOWN_FILES = {
        'helloworld': os.path.join(
            STUBS_DIR, 'wikis', 'helloworld.md'),
        'home': os.path.join(
            STUBS_DIR, 'wikis', 'home.md'),
        'anotherone': os.path.join(
            STUBS_DIR, 'wikis', 'anotherone.md'),
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

    project_id = url.strip("/").split("/")[-1]
    return project_id


def get_host(is_test):
    """Get API host based on flag.

    Parameters
    ----------
    is_test: bool
        If True, return test API host, otherwise return production host.

    Returns
    -------
    str
        API host URL for the test site or production site.
    """

    return API_HOST_TEST if is_test else API_HOST_PROD


def is_public(url):
    """Return boolean to indicate if a URL is public (True) or not (False).

    Parameters
    ------------
    url: str
        The URL to test.
    """

    request = webhelper.Request(url, method='GET')
    try:
        result = webhelper.urlopen(request).status
    except webhelper.HTTPError as e:
        result = e
    return result == 200


def call_api(url, pat, method='GET', per_page=100, filters={}, is_json=True):
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


def paginate_json_result(start, action, **kwargs):
    """Loop through paginated JSON responses and perform action on each.

    Parameters
    -------------
    start: str
        Link to start looping from
    action: func
        Takes in found JSON page and returns a result
    per_page: int
        How many items to include on one page. Default is 100.
        Valid range is from 1-1000.
    filters: dict
        Optional key-value dict to filter queries by.
    is_json:
        If JSON response expected, add header to specify JSON format.
    pat: str
        Personal Access Token to authorise a user.
    dryrun: bool
        Flag for whether mock JSON or real API will be used.
    **kwargs
        Extra keyword args to pass down to action and call_api.

    Returns
    ------------------
    results: deque
        Queue of results per page
    """

    next_link = start
    is_last_page = False
    results = deque()
    per_page = kwargs.pop('per_page', 100)
    filters = kwargs.pop('filters', {})
    is_json = kwargs.pop('is_json', True)
    pat = kwargs.get('pat', '')
    dryrun = kwargs.get('dryrun', False)
    while not is_last_page:
        if not dryrun:
            curr_page = call_api(
                next_link, pat, per_page=per_page, filters=filters,
                is_json=is_json)
            # Catch error if call_api is replaced with mock in tests
            try:
                curr_page = curr_page.read()
                if is_json:
                    curr_page = json.loads(curr_page)
            except AttributeError:
                pass
        else:
            curr_page = MockAPIResponse.read(next_link)
        results.append(action(curr_page, **kwargs))
        # Stop if no next link found
        try:
            next_link = curr_page['links']['next']
            is_last_page = not next_link
        except KeyError:
            is_last_page = True
    return results


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
        files_found: list[str]
            List of file paths found in the project."""

    FILE_FILTER = {
        'kind': 'file'
    }
    FOLDER_FILTER = {
        'kind': 'folder'
    }
    per_page = 100

    files_found = []

    is_last_page_folders = False
    while not is_last_page_folders:
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
                files_found += explore_file_tree(link, pat, dryrun=dryrun)
        except KeyError:
            pass

        # For each folder, loop through pages for its files
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
                    size = file['attributes']['size']
                    size_mb = size / (1024 ** 2)  # Convert bytes to MB
                    data = (
                        file['attributes']['materialized_path'],
                        str(round(size_mb, 2)),
                        file['links']['download']
                    )
                    files_found.append(data)
            except KeyError:
                pass
            curr_link = files['links']['next']
            if curr_link is None:
                is_last_page_files = True

        curr_link = folders['links']['next']
        if curr_link is None:
            is_last_page_folders = True

    return files_found


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


def get_nodes(pat, page_size=100, dryrun=False, project_id='', usetest=False):
    """Pull and list projects for a user from the OSF.

    Parameters
    ----------
    pat: str
        Personal Access Token to authorise a user with.
    page_size: int
        How many nodes to put onto a page. Default is 100.
        Possible range is 1-1000
    dryrun: bool
        If True, use test data from JSON stubs to mock API calls.
    project_id: str
        Optional ID for a specific OSF project to export.
    usetest: bool
        If True, use test API host, otherwise use production host.

    Returns
    ----------
        projects: list[dict]
            List of all project objects found
        root_nodes: list[int]
            List of indexes for root nodes in projects list.
            These are the nodes to make PDFs for and start from in PDFs.
    """

    # Set start link and page size filter based on flags
    api_host = get_host(usetest)
    node_filter = {}
    if not dryrun:
        if project_id:
            start = f'{api_host}/nodes/{project_id}/'
        else:
            start = f'{api_host}/users/me/nodes/'
            node_filter = {
                'parent': ''
            }
    else:
        page_size = 4  # Nodes found are hardcoded for --dryrun
        if project_id:
            start = project_id
        else:
            start = 'nodes'

    results = paginate_json_result(
        start, get_project_data, dryrun=dryrun, usetest=usetest,
        pat=pat, filters=node_filter, project_id=project_id, per_page=page_size
    )
    l1, l2 = zip(*list(results))
    projects = [item for sublist in l1 for item in sublist]

    # After pagination we get indexes of root nodes local to each page
    # We need to convert these to global indexes before merging the list
    page_idx = -1
    for page in l2:
        page_idx += 1
        for idx, n in enumerate(page):
            global_node_idx = page_size*page_idx + n
            page[idx] = global_node_idx
    root_nodes = [item for sublist in l2 for item in sublist]

    return projects, root_nodes


def get_project_data(nodes, **kwargs):
    """Pull and list projects for a user from the OSF.

    Parameters
    ----------
    pat: str
        Personal Access Token to authorise a user with.
    dryrun: bool
        If True, use test data from JSON stubs to mock API calls.
    project_id: str
        Optional ID for a specific OSF project to export.
    usetest: bool
        If True, use test API host, otherwise use production host.

    Returns
    ----------
        projects: list[dict]
            List of dictionaries representing projects.
    """

    pat = kwargs.pop('pat', '')
    dryrun = kwargs.pop('dryrun', False)
    usetest = kwargs.pop('usetest', False)
    project_id = kwargs.pop('project_id', '')

    api_host = get_host(usetest)

    if not dryrun and project_id:
        nodes = {'data': [nodes['data']]}
    elif project_id:
        # Put data into same format as if multiple nodes found
        nodes = {'data': [MockAPIResponse.read(project_id)['data']]}

    projects = []
    root_nodes = []  # Track indexes of start nodes for PDFs
    added_node_ids = set()  # Track added node IDs to avoid duplicates

    # Dispatch table used to define how to process JSON
    # Add new field by giving name and function
    fields = {
        'metadata': {
            'title': lambda project, **kwargs: project['attributes']['title'],
            'id': lambda project, **kwargs: project['id'],
            'url': lambda project, **kwargs: project['links']['html'],
            'description': lambda project, **kwargs: project['attributes']['description'],
            'date_created': lambda project, **kwargs: datetime.datetime.fromisoformat(
                    project['attributes']['date_created']
                ).astimezone().strftime('%Y-%m-%d'),
            'date_modified': lambda project, **kwargs: datetime.datetime.fromisoformat(
                    project['attributes']['date_modified']
                ).astimezone().strftime('%Y-%m-%d'),
            'public': lambda project, **kwargs: project['attributes']['public'],
            'category': get_category,
            'tags': get_tags,
            'resource_type': lambda project, **kwargs: 'NA',
            'resource_lang': lambda project, **kwargs: 'NA',
            'affiliated_institutions': get_affiliated_institutions,
            'identifiers': get_identifiers,
            'license': get_license,
            'subjects': get_subjects,
            'funders': lambda project, **kwargs: [],
        },
        'contributors': get_contributors
    }

    for idx, project in enumerate(nodes['data']):
        if project['id'] in added_node_ids:
            continue
        else:
            added_node_ids.add(project['id'])

        project_data = {
            'metadata': {}
        }
        for field in fields['metadata']:
            project_data['metadata'][field] = fields['metadata'][field](
                project, dryrun=dryrun, key=field, pat=pat
            )
        project_data['contributors'] = fields['contributors'](
            project, dryrun=dryrun, key='contributors', pat=pat
        )

        # TODO: split into function
        # Resource type/lang/funding info share specific endpoint
        # that isn't linked to in user nodes' responses
        if dryrun:
            metadata = MockAPIResponse.read('custom_metadata')
        else:
            metadata = json.loads(call_api(
                f"{api_host}/custom_item_metadata_records/{project['id']}/",
                pat
            ).read())
        metadata = metadata['data']['attributes']
        resource_type = metadata['resource_type_general']
        resource_lang = metadata['language']
        project_data['metadata']['resource_type'] = resource_type
        project_data['metadata']['resource_lang'] = resource_lang
        for funder in metadata['funders']:
            project_data['metadata']['funders'].append(funder)
        # =========

        relations = project['relationships']

        # Get list of files in project
        if dryrun:
            link = 'root'
            use_mocks = True
        else:
            link = relations['files']['links']['related']['href']
            link += 'osfstorage/'  # ID for OSF Storage
            use_mocks = False
        project_data['files'] = explore_file_tree(link, pat, dryrun=use_mocks)

        project_data['wikis'] = explore_wikis(
            f'{api_host}/nodes/{project['id']}/wikis/',
            pat=pat, dryrun=dryrun
        )

        # In general, start nodes for PDFs have no parents
        if 'links' in project['relationships']['parent']:
            project_data['parent'] = project['relationships']['parent'][
                'links']['related']['href']
        else:
            project_data['parent'] = None
            root_nodes.append(idx)

        # Projects specified by ID to export also count as start nodes for PDFs
        # This will be the first node in list of root nodes
        if project_data['metadata']['id'] == project_id and 0 not in root_nodes:
            root_nodes.append(idx)

        def get_children(json_page, **kwargs):
            children = []
            for child in json_page['data']:
                children.append(child['id'])
                nodes['data'].append(child)  # Add to list of nodes to search
            return children
        children_link = relations['children']['links']['related']['href']
        children = list(paginate_json_result(
            children_link, dryrun=dryrun, pat=pat, action=get_children
        ))
        newlist = [item for sublist in children for item in sublist]
        project_data['children'] = newlist

        projects.append(project_data)

    return projects, root_nodes


def get_category(project, **kwargs):
    # Define nice representations of categories if needed
    CATEGORY_STRS = {
        '': 'Uncategorized',
        'methods and measures': 'Methods and Measures'
    }
    if project['attributes']['category'] in CATEGORY_STRS:
        return CATEGORY_STRS[project['attributes']['category']]
    else:
        return project['attributes']['category'].title()


def get_tags(project, **kwargs):
    if project['attributes']['tags']:
        return ', '.join(project['attributes']['tags'])
    else:
        return 'NA'


def get_contributors(project, **kwargs):
    dryrun = kwargs.pop('dryrun', True)
    key = kwargs.pop('key', 'contributors')
    pat = kwargs.pop('pat', '')
    if not dryrun:
        # Check relationship exists and can get link to linked data
        # Otherwise just pass a placeholder dict
        try:
            link = project['relationships'][key]['links']['related']['href']
            json_data = json.loads(
                call_api(
                    link, pat,
                    filters=URL_FILTERS.get(key, {})
                ).read()
            )
        except KeyError:
            json_data = {'data': None}
    else:
        json_data = MockAPIResponse.read(key)
    values = []
    for item in json_data['data']:
        values.append((
            item['embeds']['users']['data']
            ['attributes']['full_name'],
            item['attributes']['bibliographic'],
            item['embeds']['users']['data']['links']['html']
        ))
    return values


def get_affiliated_institutions(project, **kwargs):
    dryrun = kwargs.pop('dryrun', True)
    key = kwargs.pop('key', 'affiliated_institutions')
    pat = kwargs.pop('pat', '')
    if not dryrun:
        # Check relationship exists and can get link to linked data
        # Otherwise just pass a placeholder dict
        try:
            link = project['relationships'][key]['links']['related']['href']
            json_data = json.loads(
                call_api(
                    link, pat,
                    filters=URL_FILTERS.get(key, {})
                ).read()
            )
        except KeyError:
            json_data = {'data': None}
    else:
        json_data = MockAPIResponse.read(key)
    values = []
    for item in json_data['data']:
        values.append(item['attributes']['name'])
    values = ', '.join(values)
    return values


def get_identifiers(project, **kwargs):
    dryrun = kwargs.pop('dryrun', True)
    key = kwargs.pop('key', 'identifiers')
    pat = kwargs.pop('pat', '')
    if not dryrun:
        # Check relationship exists and can get link to linked data
        # Otherwise just pass a placeholder dict
        try:
            link = project['relationships'][key]['links']['related']['href']
            json_data = json.loads(
                call_api(
                    link, pat,
                    filters=URL_FILTERS.get(key, {})
                ).read()
            )
        except KeyError:
            json_data = {'data': None}
    else:
        json_data = MockAPIResponse.read(key)
    values = []
    for item in json_data['data']:
        values.append(item['attributes']['value'])
    values = ', '.join(values)
    return values


def get_license(project, **kwargs):
    dryrun = kwargs.pop('dryrun', True)
    key = kwargs.pop('key', 'license')
    pat = kwargs.pop('pat', '')
    if not dryrun:
        # Check relationship exists and can get link to linked data
        # Otherwise just pass a placeholder dict
        try:
            link = project['relationships'][key]['links']['related']['href']
            json_data = json.loads(
                call_api(
                    link, pat,
                    filters=URL_FILTERS.get(key, {})
                ).read()
            )
        except KeyError:
            json_data = {'data': None}
    else:
        json_data = MockAPIResponse.read(key)
    if json_data['data'] is not None:
        return json_data['data']['attributes']['name']
    else:
        return None


def get_subjects(project, **kwargs):
    dryrun = kwargs.pop('dryrun', True)
    key = kwargs.pop('key', 'subjects')
    pat = kwargs.pop('pat', '')
    if not dryrun:
        # Check relationship exists and can get link to linked data
        # Otherwise just pass a placeholder dict
        try:
            link = project['relationships'][key]['links']['related']['href']
            json_data = json.loads(
                call_api(
                    link, pat,
                    filters=URL_FILTERS.get(key, {})
                ).read()
            )
        except KeyError:
            raise KeyError()  # Subjects should have a href link
    else:
        json_data = MockAPIResponse.read(key)
    values = []
    for item in json_data['data']:
        values.append(item['attributes']['text'])
    values = ', '.join(values)
    return values
