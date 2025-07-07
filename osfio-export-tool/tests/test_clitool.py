from unittest import TestCase
import os
import json

from click.testing import CliRunner
from pypdf import PdfReader

from clitool import cli, call_api, get_project_data, explore_file_tree

API_HOST = 'https://api.test.osf.io/v2'

TEST_PDF_FOLDER = 'good-pdfs'
TEST_INPUT = 'test_pdf.pdf'
input_path = os.path.join('tests', TEST_PDF_FOLDER, TEST_INPUT)
test_data = os.path.join('tests', 'myprojects.txt')

# Run tests in docker container
# with 'python -m unittest <tests.test_clitool.TESTCLASS>'


class TestAPI(TestCase):
    """Tests for interacting with the OSF API."""

    def test_get_projects_api(self):
        """Test for if JSON for user's projects are loaded correctly"""

        data = call_api(
            f'{API_HOST}/users/me/nodes/',
            'GET', os.getenv('PAT')
        )
        assert data.status == 200
        data = json.loads(data.read())
        assert isinstance(data, dict)

    def test_filter_by_api(self):
        """Test if we use query params in API calls."""

        filters = {
            'category': '',
            'title': 'ttt'
        }
        data = call_api(
            f'{API_HOST}/nodes/',
            'GET', os.getenv('PAT'), filters=filters
        )
        assert data.status == 200

    def test_explore_api_file_tree(self):
        """Test using API to filter and search file links."""

        data = call_api(
            f'{API_HOST}/users/me/nodes/',
            'GET', os.getenv('PAT')
        )
        nodes = json.loads(data.read())['data']
        if len(nodes) > 0:
            link = f'{API_HOST}/nodes/{nodes[0]['id']}/files/osfstorage/'
            files = explore_file_tree(link, os.getenv('PAT'), dryrun=False)
            assert isinstance(files, list)
        else:
            print("No nodes available, consider making a test project.")

    def test_pull_projects_command(self):
        """Test we can successfully pull projects using the OSF API"""

        if os.path.exists(input_path):
            os.remove(input_path)

        runner = CliRunner()

        # No PAT given - exception
        result = runner.invoke(
            cli, ['pull-projects'], input='', terminal_width=60
        )
        assert result.exception
        assert not os.path.exists(input_path)

        # Use PAT to find user projects
        result = runner.invoke(
            cli, ['pull-projects', '--filename', input_path],
            input=os.getenv('PAT', ''),
            terminal_width=60
        )
        assert not result.exception, result.exception
        assert os.path.exists(input_path)

        if os.path.exists(input_path):
            os.remove(input_path)


class TestClient(TestCase):
    """Tests for the internal CLI parts without real API usage."""

    def test_explore_mock_file_tree(self):
        """Test exploration of mock file tree."""

        files = explore_file_tree('root', os.getenv('PAT', ''), dryrun=True)
        assert '/helloworld.txt.txt' in files
        assert '/tf1/helloworld.txt.txt' in files
        assert '/tf1/tf2/file.txt' in files

    def test_parse_api_responses(self):
        """Using JSON stubs to simulate API responses,
        test we can parse them correctly"""

        projects = get_project_data(os.getenv('PAT', ''), True)

        assert len(projects) == 2, (
            'Expected 2 projects in the stub data'
        )
        assert projects[0]['title'] == 'Test1', (
            'Expected title Test1, got: ',
            projects[0]['title']
        )
        assert projects[0]['id'] == 'x', (
            'Expected ID x, got: ',
            projects[0]['id']
        )
        assert projects[1]['title'] == 'Test2', (
            'Expected title Test2, got: ',
            projects[1]['title']
        )
        assert projects[0]['description'] == 'Test1 Description', (
            'Expected description Test1 Description, got: ',
            projects[0]['description']
        )
        assert projects[1]['description'] == 'Test2 Description', (
            'Expected description Test2 Description, got: ',
            projects[1]['description']
        )
        expected_date = '2000-01-01 14:18:00.376705+00:00'
        assert str(projects[0]['date_created']) == expected_date, (
            f'Expected date_created {expected_date}, got: ',
            projects[0]['date_created']
        )
        assert str(projects[0]['date_modified']) == expected_date, (
            f'Expected date_modified {expected_date}, got: ',
            projects[0]['date_modified']
        )
        assert projects[0]['tags'] == 'test1, test2, test3', (
            'Expected tags test1, test2, test3, got: ',
            projects[0]['tags']
        )
        assert projects[1]['tags'] == 'NA', (
            'Expected tags NA, got: ',
            projects[1]['tags']
        )
        assert projects[0]['contributors'] == 'Test User 1, Test User 2', (
            'Expected contributors Test User 1, Test User 2, got: ',
            projects[0]['contributors']
        )
        assert projects[0]['identifiers'] == '10.4-2-6-25/OSF.IO/74PAD', (
            'Expected identifiers 10.4-2-6-25/OSF.IO/74PAD, got: ',
            projects[0]['identifiers']
        )
        assert projects[0]['resource_type'] == 'Other', (
            'Expected resource_type Other, got: ',
            projects[0]['resource_type']
        )
        assert projects[0]['resource_lang'] == 'eng', (
            'Expected resource_lang eng, got: ',
            projects[0]['resource_lang']
        )
        assert '/helloworld.txt.txt' in projects[0]['files']
        assert '/tf1/helloworld.txt.txt' in projects[0]['files']
        assert '/tf1/tf2/file.txt' in projects[0]['files']

    def test_generate_pdf(self):
        """Test generating a PDF from parsed project data.
        This assumes the JSON parsing works correctly."""

        if os.path.exists(input_path):
            os.remove(input_path)

        runner = CliRunner()
        result = runner.invoke(
            cli, ['pull-projects', '--dryrun', '--filename', input_path],
            input=os.getenv('PAT', ''),
            terminal_width=60
        )
        assert not result.exception, result.exception
        assert os.path.exists(input_path)

        # Compare content of created PDF with reference PDF
        reader_created = PdfReader(input_path)
        reader_reference = PdfReader(os.path.join(
            'tests', TEST_PDF_FOLDER, 'osf_projects_stub.pdf'
        ))
        for p1, p2 in zip(reader_created.pages, reader_reference.pages):
            text_generated = p1.extract_text(extraction_mode='layout')
            text_reference = p2.extract_text(extraction_mode='layout')
            assert text_generated == text_reference, (
                f'Generated text does not match reference text:\n'
                f'Generated: {text_generated}\n'
                f'Reference: {text_reference}'
            )
            assert all(x == y for x, y in zip(p1.images, p2.images))

        if os.path.exists(input_path):
            os.remove(input_path)
