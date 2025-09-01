from collections import deque
import datetime
from unittest import TestCase
import os
import shutil
import json
import traceback
import urllib.error
from unittest.mock import patch, MagicMock, call
import importlib.metadata

import PIL
from click.testing import CliRunner
from pypdf import PdfReader
from mistletoe import markdown

from osfexport.exporter import (
    MockAPIResponse,
    call_api,
    get_project_data,
    get_nodes,
    explore_file_tree,
    explore_wikis,
    is_public,
    extract_project_id,
    paginate_json_result
)
from osfexport.cli import (
    cli, prompt_pat
)
from osfexport.formatter import (
    HTMLImageSizeCapRenderer,
    write_pdf
)
# from mistletoe import markdown

TEST_PDF_FOLDER = 'good-pdfs'
TEST_INPUT = 'test_pdf.pdf'
FOLDER_OUT = os.path.join('tests', 'outfolder')

# Run tests in docker container
# with 'python -m unittest <tests.test_clitool.TESTCLASS>'


class TestAPI(TestCase):
    """Tests for interacting with the OSF API."""

    API_HOST = 'https://api.test.osf.io/v2'

    def test_basic_api_call_works(self):
        """Test for if JSON for user's projects are loaded correctly"""

        data = call_api(
            f'{TestAPI.API_HOST}/',
            pat=''
        )
        assert data.status == 200

        data = json.loads(data.read())
        assert isinstance(data, dict)
        # All mocked data assumes API version 2.20 is used
        assert data['meta']['version'] == '2.20', (
            'Expected API version 2.20, actual version: ',
            data['meta']['version']
        )

    def test_get_public_status_on_code(self):
        assert not is_public(f'{TestAPI.API_HOST}/users/me')
        assert is_public(f'{TestAPI.API_HOST}')

    def test_get_public_projects_if_no_pat(self):
        public_node_id = json.loads(
            call_api(
                f'{TestAPI.API_HOST}/nodes', pat='',
                per_page=1,
                filters={
                    'parent': ''
                }
            ).read()
        )['data'][0]['id']

        result = call_api(
            f'{TestAPI.API_HOST}/nodes/{public_node_id}/', pat='',
        )
        assert result.status == 200

    def test_parse_single_project_json_as_expected(self):
        # Use first public project available for this test
        # TODO: allow choosing individual components to start export from
        # Currently using a component will cause a fail
        data = call_api(
            f'{TestAPI.API_HOST}/nodes/',
            pat='',
            per_page=1,
            filters={
                'parent': ''
            }
        )
        node = json.loads(data.read())['data'][0]
        id = extract_project_id(node['links']['html'])
        projects, root_projects = get_nodes(
            pat='', dryrun=False,
            usetest=True, project_id=id
        )

        expected_child_count = len(
            json.loads(
                call_api(
                    f'{TestAPI.API_HOST}/nodes/{node["id"]}/children/',
                    pat=''
                ).read()
            )['data']
        )
        assert len(projects) == expected_child_count + 1
        assert len(root_projects) == 1, (root_projects)
        assert projects[0]['metadata']['title'] == node['attributes']['title']
        assert isinstance(projects[0]['files'], list)

    def test_write_image_html_with_new_size(self):
        url = 'https://osf.io/download/x/'
        text = f"""This has an image in the wiki page.
![Someone taking a pic on their phone camera][1]This is an image above this text.
Another paragraph.

  [1]: {url}"""

        # Mock requests to simulate errors when trying to download images
        with patch('urllib.request.urlopen') as mock_get:
            mock_get.side_effect = urllib.error.HTTPError(
                url='https://osf.io/download/x/',
                code=401,
                msg='Unauthorized',
                hdrs={},
                fp=None
            )
            html = markdown(text, renderer=HTMLImageSizeCapRenderer)
            assert f'<a href="{url}">{url}</a>' in html, (
                f'<a href="{url}">{url}</a>',
                html
            )
        with patch('urllib.request.urlopen') as mock_get:
            mock_get.side_effect = PIL.UnidentifiedImageError()
            html = markdown(text, renderer=HTMLImageSizeCapRenderer)
            assert f'<a href="{url}">{url}</a>' in html, (
                f'<a href="{url}">{url}</a>',
                html
            )


class TestExporter(TestCase):
    """Tests for the exporter without real API usage."""

    @patch('osfexport.exporter.get_affiliated_institutions')
    def test_get_project_data_handles_HTTP_errors(self, mock_get_inst):
        mock_get_inst.side_effect = urllib.error.HTTPError(
            url='https://test.osf.io',
            code=401,
            msg=' HTTP Error 401: Unauthorized',
            hdrs={},
            fp=None
        )
        nodes = MockAPIResponse.read('nodes')
        projects, root_nodes = get_project_data(
            nodes,
            pat='',
            dryrun=False,
            usetest=True
        )
        assert isinstance(projects, list)
        assert isinstance(root_nodes, list)
        # There are 4 real nodes in the mock JSON data
        assert mock_get_inst.call_count == 4, (
            f'Wrong num of calls: {mock_get_inst.call_count}'
        )

    @patch('osfexport.exporter.get_project_data')
    def test_paginate_json_result_gets_next_page_despite_function_errors(self, mock_get_data):
        mock_get_data.side_effect = urllib.error.HTTPError(
            url='https://test.osf.io',
            code=401,
            msg=' HTTP Error 401: Unauthorized',
            hdrs={},
            fp=None
        )
        results = paginate_json_result(
            start='nodes', action=mock_get_data, dryrun=True, usetest=False,
            pat='', filters={}, project_id='', per_page=20, fail_on_first=False
        )
        # There are 2 pages of nodes to read in the mock JSON data
        assert mock_get_data.call_count == 2, (
            f'Wrong num of calls: {mock_get_data.call_count}'
        )
        assert results is not None

        # Raise error on first error
        with self.assertRaises(urllib.error.HTTPError):
            results = paginate_json_result(
                start='nodes', action=mock_get_data, dryrun=True, usetest=False,
                pat='', filters={}, project_id='', per_page=20
            )

    @patch('urllib.request.urlopen')
    @patch('urllib.request.Request')
    def test_call_api_add_headers(self, mock_request_class, mock_urlopen):
        # Mock Request instances to check headers
        # Mock urlopen to avoid real HTTP calls
        mock_request_instance = MagicMock()
        mock_request_class.return_value = mock_request_instance
        call_api('https://test.osf.io', pat='pat', is_json=True)
        version = importlib.metadata.version("osfexport")
        expected_calls = [
            call().add_header('Authorization', 'Bearer pat'),
            call().add_header('User-Agent', f'osfexport/{version} (Python)'),
            call().add_header('Accept', 'application/vnd.api+json;version=2.20')
        ]
        mock_request_class.assert_has_calls(expected_calls, any_order=False)

    def test_get_public_status(self):
        # Public url
        mock_response = MagicMock()
        mock_response.status = 200
        with patch('osfexport.exporter.call_api') as mock_call_api:
            mock_call_api.return_value = mock_response
            result = is_public('url')
            mock_call_api.assert_called_once_with(
                'url', pat='', method='GET'
            )
            assert result is True

        # Private url
        mock_response = MagicMock()
        mock_response.status = 401
        with patch('osfexport.exporter.call_api') as mock_call_api:
            mock_call_api.return_value = mock_response
            result = is_public('url')
            mock_call_api.assert_called_once_with(
                'url', pat='', method='GET'
            )
            assert result is False

    def test_explore_mock_file_tree(self):
        files = explore_file_tree(
            'root', pat='', dryrun=True
        )

        assert '/helloworld.txt.txt' == files[4][0]
        assert '/tf1/helloworld.txt.txt' == files[1][0]
        assert '/tf1/tf2/file.txt' == files[0][0]
        assert '/tf1/tf2-second/secondpage.txt' == files[2][0]
        assert '/tf1/tf2-second/thirdpage.txt' == files[3][0]
        assert files[0][1] == "2.1", (files[0][1])
        assert isinstance(files[0][2], str)

    def test_get_latest_mock_wiki_version(self):
        link = 'wiki'
        wikis = explore_wikis(
            link, pat='', dryrun=True
            )
        assert len(wikis) == 3
        assert 'helloworld' in wikis.keys(), (
            'Missing wiki IDs'
        )
        assert 'home' in wikis.keys(), (
            'Missing wiki IDs'
        )
        assert 'anotherone' in wikis.keys(), (
            'Missing wiki IDs'
        )

        assert 'hello world' in wikis['helloworld'], (
            wikis['helloworld']
        )
        assert '~~strikethrough~~' in wikis['home'], (
            wikis['home']
        )

    def test_get_project_data_for_json_mocks(self):
        nodes = MockAPIResponse.read('nodes')
        projects, root_nodes = get_project_data(
            nodes,
            pat='',
            dryrun=True,
            usetest=True
        )

        assert len(projects) == 4, (
            f'Expected 4 projects in the stub data, got {len(projects)}'
        )
        assert len(root_nodes) == 2, (
            f'Expected 2 root nodes in the stub data, got {len(root_nodes)}'
        )
        assert root_nodes[0] == 0
        assert root_nodes[1] == 1
        assert projects[root_nodes[0]]['metadata']['id'] == 'x', (
            'Expected ID x, got: ',
            projects[root_nodes[0]]['metadata']['id']
        )
        assert projects[root_nodes[1]]['metadata']['id'] == 'y', (
            'Expected ID y, got: ',
            projects[root_nodes[1]]['metadata']['id']
        )

        assert projects[0]['metadata']['title'] == 'Test1', (
            'Expected title Test1, got: ',
            projects[0]['metadata']['title']
        )
        assert projects[0]['metadata']['id'] == 'x', (
            'Expected ID x, got: ',
            projects[0]['metadata']['id']
        )
        assert projects[1]['metadata']['title'] == 'Test2', (
            'Expected title Test2, got: ',
            projects[1]['metadata']['title']
        )
        assert projects[0]['metadata']['license'] == 'mynewlicense', (
            'Expected mynewlicense, got: ',
            projects[0]['metadata']['license']
        )
        assert projects[0]['metadata']['description'] == 'Test1 Description', (
            'Expected description Test1 Description, got: ',
            projects[0]['metadata']['description']
        )
        assert projects[1]['metadata']['description'] == 'Test2 Description', (
            'Expected description Test2 Description, got: ',
            projects[1]['description']
        )
        expected_date = '2000-01-01'
        assert str(
            projects[0]['metadata']['date_created']
        ) == expected_date, (
            f'Expected date_created {expected_date}, got: ',
            projects[0]['metadata']['date_created']
        )
        assert str(
            projects[0]['metadata']['date_modified']
        ) == expected_date, (
            f'Expected date_modified {expected_date}, got: ',
            projects[0]['metadata']['date_modified']
        )
        assert projects[0]['metadata']['tags'] == 'test1, test2, test3', (
            'Expected tags test1, test2, test3, got: ',
            projects[0]['metadata']['tags']
        )
        assert projects[1]['metadata']['tags'] == 'NA', (
            'Expected tags NA, got: ',
            projects[1]['metadata']['tags']
        )

        assert projects[0]['contributors'][0][0] == 'Test User 1', (
            "Expected contributor Test User 1, got: ",
            projects[0]['contributors'][0][0]
        )
        assert not projects[0]['contributors'][0][1], (
            "Expected contributor status False, got: ",
            projects[0]['contributors'][0][1]
        )
        link = 'https://test.osf.io/userid/'
        link_two = 'https://test.osf.io/userid2/'
        assert projects[0]['contributors'][0][2] == link, (
            f"Expected contributor link {link}, got: ",
            projects[0]['contributors'][0][2]
        )
        assert projects[0]['contributors'][1][0] == 'Test User 2', (
            "Expected contributor Test User 2, got: ",
            projects[0]['contributors'][1][0]
        )
        assert projects[0]['contributors'][1][1], (
            "Expected contributor status True, got: ",
            projects[0]['contributors'][1][1]
        )
        assert projects[0]['contributors'][1][2] == link_two, (
            f"Expected contributor link {link_two}, got: ",
            projects[0]['contributors'][1][2]
        )

        doi = projects[0]['metadata']['identifiers']
        assert doi == '10.4-2-6-25/OSF.IO/74PAD', (
            'Expected identifiers 10.4-2-6-25/OSF.IO/74PAD, got: ',
            doi
        )
        assert projects[0]['metadata']['resource_type'] == 'Other', (
            'Expected resource_type Other, got: ',
            projects[0]['metadata']['resource_type']
        )
        assert projects[0]['metadata']['resource_lang'] == 'eng', (
            'Expected resource_lang eng, got: ',
            projects[0]['metadata']['resource_lang']
        )
        assert len(projects[0]['files']) == 5
        assert '/helloworld.txt.txt' == projects[0]['files'][4][0], (
            projects[0]['files'][4][0]
        )
        assert '/tf1/helloworld.txt.txt' == projects[0]['files'][1][0], (
            projects[0]['files'][1][0]
        )
        assert '/tf1/tf2/file.txt' == projects[0]['files'][0][0], (
            projects[0]['files'][0][0]
        )
        subjects = projects[0]['metadata']['subjects']
        assert subjects == 'Education, Literature, Geography', (
            'Expected Education, Literature, Geography, got: ',
            subjects
        )
        assert len(projects[0]['wikis']) == 3
        assert projects[0]['metadata']['url'] == 'https://test.osf.io/x/', (
            'Expected URL https://test.osf.io/x/, got: ',
            projects[0]['metadata']['url']
        )
        assert projects[1]['metadata']['url'] != 'https://test.osf.io/x/', (
            'Repeated project URL'
        )

        assert projects[0]['parent'] is None, (
            'Expected no parent, got: ',
            projects[0]['parent']
        )
        assert 'a' in projects[0]['children']
        assert 'b' in projects[0]['children']

        assert projects[0]['metadata']['public']
        assert not projects[1]['metadata']['public']

        assert projects[0]['metadata']['category'] == 'Methods and Measures', (
            projects[0]['metadata']['category']
        )
        assert projects[1]['metadata']['category'] == 'Uncategorized', (
            projects[1]['metadata']['category']
        )

        assert projects[3]['parent'][0] == projects[2]['metadata']['title'], (
            projects[3]['parent'][0],
            f'Expected: {projects[2]['metadata']['title']}'
        )
        assert projects[3]['parent'][1] == projects[2]['metadata']['url'], (
            projects[3]['parent'][1],
            f'Expected: {projects[2]['metadata']['url']}'
        )

    def test_get_paginated_projects(self):
        projects, root_nodes = get_nodes(
            pat='',
            dryrun=True,
            usetest=True,
            page_size=4
        )
        assert len(projects) == 5, (
            f'Expected 5 projects in the stub data, got {len(projects)}',
            projects
        )
        assert len(root_nodes) == 3, (
            f'Expected 3 root nodes in the stub data, got {len(root_nodes)}'
        )
        assert root_nodes[0] == 0
        assert root_nodes[1] == 1
        assert root_nodes[2] == 4

    def test_get_single_mock_project(self):
        projects, roots = get_nodes(
            pat='', dryrun=True, usetest=True,
            project_id='x'
        )
        assert len(roots) == 1, (
            roots
        )
        assert len(projects) == 3, (
            print(projects)
        )
        assert projects[0]['metadata']['id'] == 'x'
        assert projects[0]['children'] == ['a', 'b'], (
            projects[0]['children']
        )

    def test_use_dryrun_in_user_default_dir(self):
        cwd = os.getcwd()
        try:
            # Go to user's home directory in cross-platform way
            os.chdir(os.path.expanduser("~"))
            projects, roots = get_nodes('', dryrun=True, usetest=True)
        except Exception as e:
            raise e
        finally:
            # Reverse state changes for reproducibility
            os.chdir(cwd)
            assert os.getcwd() == cwd

    def test_extract_project_id_from_strings(self):
        url = 'https://osf.io/x/'
        project_id = extract_project_id(url)
        assert project_id == 'x', f'Expected "x", got {project_id}'

        url = 'https://api.test.osf.io/v2/nodes/x/'
        project_id = extract_project_id(url)
        assert project_id == 'x', f'Expected "x", got {project_id}'

        # TODO: add test for passing a URL for test site when
        # we are using production site, and vice versa

        url = 'x'
        project_id = extract_project_id(url)
        assert project_id == 'x', f'Expected "x", got {project_id}'

        # Should just run normally
        url = ''
        project_id = extract_project_id(url)

    @patch('osfexport.exporter.call_api')
    def test_add_on_paginated_results(self, mock_get):
        # Mock JSON responses
        page1 = {'data': 1, 'links': {'next': 'http://api.example.com/page2'}}
        page2 = {'data': 3, 'links': {'next': 'http://api.example.com/page3'}}
        page3 = {'data': 5, 'links': {'next': None}}
        # Configure mock to return these responses in sequence
        mock_get.side_effect = [
            page1,
            page2,
            page3
        ]

        def add_x(json, **kwargs):
            x = kwargs.get('x', 0)
            return json['data'] + x

        results = paginate_json_result(
            start='http://api.example.com/page1', action=add_x, x=5
        )
        assert isinstance(results, deque)
        self.assertEqual(results.popleft(), 1+5)
        self.assertEqual(results.popleft(), 3+5)
        self.assertEqual(results.popleft(), 5+5)

    def test_get_single_component_mock_project(self):
        projects, roots = get_nodes(
            pat='', dryrun=True, usetest=True,
            project_id='a'
        )
        assert len(roots) == 1, (
            roots
        )
        assert len(projects) == 1, (
            projects
        )
        assert projects[0]['metadata']['id'] == 'a'
        assert projects[0]['parent'][0] == 'Test1', (
            projects[0]['parent'][0],
            'Expected: Test1'
        )
        assert projects[0]['parent'][1] == 'https://test.osf.io/x/', (
            projects[0]['parent'][1],
            'Expected: https://test.osf.io/x/'
        )


class TestFormatter(TestCase):
    """Tests for the PDF formatter."""

    def test_write_pdf_no_folder_given(self):
        projects = [
            {
                'metadata': {
                    'title': 'My Project Title',
                    'id': 'id',
                    'url': 'https://test.osf.io/x',
                    'category': 'Uncategorized',
                    'description': 'This is a description of the project',
                    'date_created': datetime.datetime.fromisoformat(
                        '2025-06-12T15:54:42.105112Z'
                    ),
                    'date_modified': datetime.datetime.fromisoformat(
                        '2001-01-01T01:01:01.105112Z'
                    ),
                    'tags': 'tag1, tag2, tag3',
                    'resource_type': 'na',
                    'resource_lang': 'english',
                    'affiliated_institutions': 'University of Manchester',
                    'identifiers': 'N/A',
                    'license': 'Apache 2.0',
                    'subjects': 'sub1, sub2, sub3',
                },
                'contributors': [
                    ('Pineapple Pizza', False, 'https://test.osf.io/userid/'),
                    ('Margarita', True, 'https://test.osf.io/userid/'),
                    ('Margarine', True, 'https://test.osf.io/userid/')
                ],
                'files': [
                    ('file1.txt', None, 'https://test.osf.io/userid/'),
                    ('file2.txt', None, None),
                ],
                'funders': [],
                'wikis': {
                    'Home': 'hello world',
                    'Page2': 'another page'
                },
                "parent": None,
                'children': ['a']
            }
        ]
        root_nodes = [0]
        is_filename_match = False  # Flag for if exported PDF has expected name
        try:
            pdf_one, path_one = write_pdf(projects, root_nodes[0], '')

            title_one = projects[0]['metadata']['title'].replace(' ', '-')
            date_one = pdf_one.date_printed.strftime(
                '%Y-%m-%d %H-%M-%S %Z'
            ).replace(' ', '-')
            expected_filename = f'{title_one}-{date_one}.pdf'

            is_filename_match = expected_filename in os.listdir(os.getcwd())
            assert 'Component of:' not in PdfReader(path_one).pages[0].extract_text(), (
                'Did not expect parent URL in PDF, got: ',
                PdfReader(path_one).pages[0].extract_text()
            )
        except Exception as e:
            if isinstance(e, AssertionError):
                raise e
            print(e)
        finally:
            if os.path.exists(path_one):
                os.remove(path_one)

        assert is_filename_match, (
            'Unable to create file in current directory.'
        )

    def test_write_component_pdf_with_one_off_parent(self):
        projects = [
            {
                'metadata': {
                    'title': 'Component1',
                    'id': 'id',
                    'url': 'https://test.osf.io/x',
                    'category': 'Uncategorized',
                    'description': 'This is a description of the project',
                    'date_created': datetime.datetime.fromisoformat(
                        '2025-06-12T15:54:42.105112Z'
                    ),
                    'date_modified': datetime.datetime.fromisoformat(
                        '2001-01-01T01:01:01.105112Z'
                    ),
                    'tags': 'tag1, tag2, tag3',
                    'resource_type': 'na',
                    'resource_lang': 'english',
                    'affiliated_institutions': 'University of Manchester',
                    'identifiers': 'N/A',
                    'license': 'Apache 2.0',
                    'subjects': 'sub1, sub2, sub3',
                },
                'contributors': [
                    ('Pineapple Pizza', False, 'https://test.osf.io/userid/'),
                    ('Margarita', True, 'https://test.osf.io/userid/'),
                    ('Margarine', True, 'https://test.osf.io/userid/')
                ],
                'files': [
                    ('file1.txt', None, 'https://test.osf.io/userid/'),
                    ('file2.txt', None, None),
                ],
                'funders': [],
                'wikis': {
                    'Home': 'hello world',
                    'Page2': 'another page'
                },
                "parent": ['apple', 'https://test.osf.io/parent-id'],
                'children': ['a']
            }
        ]
        root_nodes = [0]
        is_filename_match = False  # Flag for if exported PDF has expected name
        try:
            pdf_one, path_one = write_pdf(projects, root_nodes[0], '')

            title_one = projects[0]['metadata']['title'].replace(' ', '-')
            date_one = pdf_one.date_printed.strftime(
                '%Y-%m-%d %H-%M-%S %Z'
            ).replace(' ', '-')
            expected_filename = f'{title_one}-{date_one}.pdf'

            is_filename_match = expected_filename in os.listdir(os.getcwd())

            page_one = PdfReader(path_one)
            text = page_one.pages[0].extract_text()
            assert f'Parent: {projects[0]['parent'][0]}' in text
            assert f'Parent URL: {projects[0]['parent'][1]}' in text, (
                'Expected parent URL in PDF, got: ',
                text
            )
        except Exception as e:
            if isinstance(e, AssertionError):
                raise e
            print(e)
        finally:
            if os.path.exists(path_one):
                os.remove(path_one)

        assert is_filename_match, (
            'Unable to create file in current directory.'
        )

    def test_write_unicode_pdfs_from_mock_projects(self):
        # Put PDFs in a folder to keep things tidy
        if os.path.exists(FOLDER_OUT):
            shutil.rmtree(FOLDER_OUT)
        os.mkdir(FOLDER_OUT)

        projects = [
            {
                'metadata': {
                    'title': 'My Project Title',
                    'id': 'id',
                    'url': 'https://test.osf.io/x',
                    'category': 'Uncategorized',
                    'description': 'This is a description of the project ג',
                    'date_created': datetime.datetime.fromisoformat(
                        '2025-06-12T15:54:42.105112Z'
                    ),
                    'date_modified': datetime.datetime.fromisoformat(
                        '2001-01-01T01:01:01.105112Z'
                    ),
                    'tags': 'tag1, tag2, tag3',
                    'resource_type': 'na',
                    'resource_lang': 'english',
                    # Below uses em-dash at end
                    'affiliated_institutions': 'University of Manchester — Test',
                    'identifiers': 'N/A',
                    'license': 'Apache 2.0',
                    'subjects': 'sub1, sub2, sub3',
                },
                'contributors': [
                    ('Pineapple Pizza', False, 'https://test.osf.io/userid/'),
                    ('Margarita', True, 'https://test.osf.io/userid/'),
                    ('Margarine', True, 'https://test.osf.io/userid/')
                ],
                'files': [
                    ('file1.txt', None, 'https://test.osf.io/userid/'),
                    ('file2.txt', None, None),
                ],
                'funders': [],
                'wikis': {
                    'Home': 'hello world',
                    'Page2': 'another page'
                },
                "parent": None,
                'children': ['a']
            },
            {
                'metadata': {
                    "title": "child1",
                    "id": "a",
                    'url': 'https://test.osf.io/a',
                },
                'contributors': [
                    (
                        'Long Double-Barrelled Name and Surname',
                        False, 'https://test.osf.io/userid/'
                    ),
                    (
                        'name2', True, 'https://test.osf.io/userid/'
                    ),
                    (
                        'name3', True, 'https://test.osf.io/userid/'
                    )
                ],
                'files': [
                    ('file1.txt', None, None),
                    ('file2.txt', None, None),
                ],
                'wikis': {},
                "parent": ('My Project Title', 'https://test.osf.io/x'),
                'children': ['b']
            },
            {
                'metadata': {
                    "title": "Second Project in new PDF ♡",
                    "id": "c",
                    'url': 'lol',
                    'category': 'Methods and Measures'
                },
                'contributors': [
                    (
                        'Long Double-Barrelled Name and Surname',
                        False, 'https://test.osf.io/userid/'
                    ),
                    (
                        'name2', True, 'https://test.osf.io/userid/'
                    ),
                    (
                        'name3', True, 'https://test.osf.io/userid/'
                    )
                ],
                'files': [
                    ('file1.txt', None, None),
                    ('file2.txt', None, None),
                ],
                'wikis': {},
                "parent": None,
                'children': []
            },
            {
                'metadata': {
                    "title": "child2",
                    "id": "b",
                    'url': 'dan'
                },
                'contributors': [
                    (
                        'Long Double-Barrelled Name and Surname',
                        False, 'https://test.osf.io/userid/'
                    ),
                    (
                        'name2', True, 'https://test.osf.io/userid/'
                    ),
                    (
                        'name3', True, 'https://test.osf.io/userid/'
                    )
                ],
                'files': [
                    ('file1.txt', None, None),
                    ('file2.txt', None, None),
                ],
                'wikis': {},
                "parent": ['child1', 'https://test.osf.io/a'],
                'children': []
            },
        ]

        root_nodes = [0, 2]  # Indices of root nodes in projects list

        # Get URL now as it will be removed later
        url = projects[0]['metadata']['url']
        url_comp = projects[1]['metadata']['url']

        # Can we specify where to write PDFs?
        pdf_one, path_one = write_pdf(projects, root_nodes[0], FOLDER_OUT)
        pdf_two, path_two = write_pdf(projects, root_nodes[1], FOLDER_OUT)
        files = os.listdir(FOLDER_OUT)
        assert len(files) == 2

        title_one = projects[0]['metadata']['title'].replace(' ', '-')
        title_two = projects[2]['metadata']['title'].replace(' ', '-')
        date_one = pdf_one.date_printed.strftime(
            '%Y-%m-%d %H-%M-%S %Z'
        ).replace(' ', '-')
        date_two = pdf_two.date_printed.strftime(
            '%Y-%m-%d %H-%M-%S %Z'
        ).replace(' ', '-')
        path_one_real = os.path.join(
            os.getcwd(), FOLDER_OUT,
            f'{title_one}-{date_one}.pdf'
        )
        path_two_real = os.path.join(
            os.getcwd(), FOLDER_OUT,
            f'{title_two}-{date_two}.pdf'
        )
        assert path_one == path_one_real, (
            path_one,
            path_one_real
        )
        assert path_two == path_two_real, (
            path_two,
            path_two_real
        )

        import_one = PdfReader(os.path.join(
            FOLDER_OUT, f'{title_one}-{date_one}.pdf'
        ))
        import_two = PdfReader(os.path.join(
            FOLDER_OUT, f'{title_two}-{date_two}.pdf'
        ))
        assert len(import_one.pages) == 5, (
            'Expected 5 pages in the first PDF, got: ',
            len(import_one.pages)
        )

        content_first_page = import_one.pages[0].extract_text(
            extraction_mode='layout'
        )
        assert f'{projects[0]['metadata']['title']}' in content_first_page, (
            content_first_page
        )

        content_second_page = import_two.pages[0].extract_text(
            extraction_mode='layout'
        )
        assert 'Category: Methods and Measures' in content_second_page, (
            content_second_page
        )

        content_third_page = import_one.pages[3].extract_text(
            extraction_mode='layout'
        )
        assert f'{projects[0]['metadata']['title']}' in content_third_page, (
            content_third_page
        )
        assert f'{url}' in content_third_page, (
            content_third_page
        )
        assert f'{projects[1]['metadata']['title']}' in content_third_page
        assert f'{url_comp}' in content_third_page

        assert f'{url}' in content_first_page, (
            content_third_page
        )
        assert 'Category: Uncategorized' in content_first_page, (
            content_first_page
        )
        timestamp = pdf_one.date_printed.strftime(
            '%Y-%m-%d %H:%M:%S %Z')
        assert f'Exported: {timestamp}' in content_first_page, (
            'Actual content:',
            content_first_page
        )

        # This way of string formatting compresses line lengths used
        # End of headers and table rows marked by \n\n
        contributors_table = (
            '2. Contributors\n\n'
            'Name'
            'Bibliographic?'
            'Profile Link\n\n'
            'Pineapple Pizza'
            'No'
            'https://test.osf.io/userid/\n\n'
            'Margarita'
            'Yes'
            'https://test.osf.io/userid/\n\n'
            'Margarine'
            'Yes'
            'https://test.osf.io/userid/\n\n'
        ).replace(' ', '')
        assert contributors_table in content_first_page.replace(' ', ''), (
            'Table: ',
            contributors_table,
            'Actual: ',
            content_first_page.replace(' ', '')
        )

        # This way of string formatting compresses line lengths used
        # End of headers and table rows marked by \n\n
        files_table = (
            '3. Files in Main Project\n\n'
            'OSF Storage\n\n'
            'File Name'
            'Size (MB)'
            'Download Link\n\n'
            'file1.txt'
            'N/A'
            'https://test.osf.io/userid/\n\n'
            'file2.txt'
            'N/A'
            'N/A\n\n'
        ).replace(' ', '')
        assert files_table in content_first_page.replace(' ', ''), (
            'Table: ',
            files_table,
            'Actual: ',
            content_first_page.replace(' ', '')
        )

        content_fourth_page = import_one.pages[4].extract_text(
            extraction_mode='layout'
        )
        assert f'{projects[0]['metadata']['title']}' not in content_fourth_page, (
            'Incorrect parent title for component'
        )
        assert f'{projects[3]['metadata']['title']}' in content_fourth_page
        assert f'Parent: {projects[3]['parent'][0]}' in content_fourth_page
        assert f'Parent URL:   {projects[3]['parent'][1]}' in content_fourth_page, (
            projects[3]['parent'][1], content_fourth_page
        )

        # Remove files only if all good - keep for debugging otherwise
        if os.path.exists(FOLDER_OUT):
            shutil.rmtree(FOLDER_OUT)


class TestCLI(TestCase):
    @patch('osfexport.exporter.is_public', lambda x: True)
    def test_prompt_pat_if_public_project_id_given(self):
        pat = prompt_pat('x')
        assert pat == '', (
            pat
        )

    @patch('osfexport.exporter.is_public', lambda x: False)
    @patch('click.prompt', return_value='strinput')
    def test_prompt_pat_if_private_project_id_given(self, mock_obj):
        pat = prompt_pat('x')
        assert pat == 'strinput'

    @patch('click.prompt', return_value='strinput')
    def test_prompt_pat_if_exporting_all_projects(self, mock_obj):
        pat = prompt_pat()
        assert pat == 'strinput'

    @patch('osfexport.cli.prompt_pat')
    @patch('osfexport.exporter.get_nodes')
    def test_export_projects_handles_http_errors(self, mock_func, mock_prompt):
        codes = [401, 402, 403, 404, 500]
        for code in codes:
            mock_prompt.return_value = '-'
            mock_func.side_effect = urllib.error.HTTPError(
                url='https://test.osf.io',
                code=code,
                msg='HTTP Error',
                hdrs={},
                fp=None
            )
            runner = CliRunner()
            result = runner.invoke(
                cli, [
                    'export-projects',
                    '--usetest'
                ],
                terminal_width=60
            )
            assert "Exporting failed as an error occurred:" in result.output

    def test_pull_projects_command_on_mocks(self):
        """Test generating a PDF from parsed project data.
        This assumes the JSON parsing works correctly."""

        if os.path.exists(FOLDER_OUT):
            shutil.rmtree(FOLDER_OUT)
        os.mkdir(FOLDER_OUT)

        runner = CliRunner()
        result = runner.invoke(
            cli, [
                'export-projects', '--dryrun',
                '--folder', FOLDER_OUT,
                '--url', '',
                '--pat', ''
            ],
            terminal_width=60
        )
        assert not result.exception, (
            result.exc_info,
            traceback.format_tb(result.exc_info[2])
        )

        if os.path.exists(FOLDER_OUT):
            shutil.rmtree(FOLDER_OUT)
