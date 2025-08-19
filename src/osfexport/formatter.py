import datetime
import os
import io

from fpdf import FPDF, Align
from fpdf.fonts import FontFace
from mistletoe import markdown
import qrcode

# Global styles for PDF
BLUE = (173, 216, 230)
HEADINGS_STYLE = FontFace(emphasis="BOLD", fill_color=BLUE)
FONT_SIZES = {
    'h1': 18,  # Project titles
    'h2': 16,  # Section titles
    'h3': 14,  # Section sub-titles
    'h4': 12,  # Body
    'h5': 10  # Footer
}
LINE_PADDING = 0.5  # Gaps between liness


class PDF(FPDF):
    """Custom PDF class to implement extra customisation.
    Attributes:
        date_printed: datetime
            Date and time when the project was exported.
        url: str
            Current URL to include in QR codes.
        parent_url: str
            URL of root project to use in component sections.
        parent_title: str
            Title of root project to use in component sections.
    """

    def __init__(self, url='', parent_url='', parent_title=''):
        super().__init__()
        self.date_printed = datetime.datetime.now().astimezone()
        self.parent_url = parent_url
        self.parent_title = parent_title
        self.url = url
        # Setup unicode font for use. Can have 4 styles
        self.font = 'dejavu-sans'
        self.add_font(self.font, style="", fname=os.path.join(
            os.path.dirname(__file__), 'font', 'DejaVuSans.ttf'))
        self.add_font(self.font, style="b", fname=os.path.join(
            os.path.dirname(__file__), 'font', 'DejaVuSans-Bold.ttf'))
        self.add_font(self.font, style="i", fname=os.path.join(
            os.path.dirname(__file__), 'font', 'DejaVuSans-Oblique.ttf'))
        self.add_font(self.font, style="bi", fname=os.path.join(
            os.path.dirname(__file__), 'font', 'DejaVuSans-BoldOblique.ttf'))

    def generate_qr_code(self):
        qr = qrcode.make(self.url)
        img_byte_arr = io.BytesIO()
        qr.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        return img_byte_arr

    def footer(self):
        self.set_y(-15)
        self.set_x(-30)
        self.set_font(self.font, size=FONT_SIZES['h5'])
        self.cell(0, 10, f"Page: {self.page_no()}", align="C")
        self.set_x(10)
        timestamp = self.date_printed.strftime(
            '%Y-%m-%d %H:%M:%S %Z'
        )
        self.cell(0, 10, f"Exported: {timestamp}", align="L")
        self.set_x(10)
        self.set_y(-25)
        qr_img = self.generate_qr_code()
        self.image(qr_img, w=15, h=15, x=Align.C)


def write_pdf(projects, root_idx, folder=''):
    """Make PDF for each project.

    Parameters
    ------------
        projects: dict[str, str|tuple]
            Projects found to export into the PDF.
        root_idx: int
            Position of root node (no parent) in the projects list.
            This is used for accessing root projects without sorting the list.
        folder: str
            The path to the folder to output the project PDFs in.
            Default is the current working directory.

    Returns
    ------------
        pdfs: list
            List of created PDF files.
    """

    def write_list_section(key, fielddict, pdf):
        """Handle writing fields based on their type to PDF.
        Possible types are lists or strings.

        Parameters
        -----------
            key: str
                Name of the field to write.
            fielddict: dict
                Dictionary containing the field data.
            pdf: PDF
                PDF object to write to."""

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
            # Create separate paragraphs for more complex attributes
            pdf.write(0, '\n')
            pdf.set_font(pdf.font, size=FONT_SIZES['h3'])
            pdf.multi_cell(
                0, h=0,
                text=f'**{field_name}**\n\n',
                align='L', markdown=True, padding=LINE_PADDING
            )
            pdf.set_font(pdf.font, size=FONT_SIZES['h4'])
            for item in fielddict[key]:
                for subkey in item.keys():
                    if subkey in pdf_display_names:
                        field_name = pdf_display_names[subkey]
                    else:
                        field_name = subkey.replace('_', ' ').title()

                    pdf.multi_cell(
                        0, h=0,
                        text=f'**{field_name}:** {item[subkey]}\n\n',
                        align='L', markdown=True, padding=LINE_PADDING
                    )
                pdf.write(0, '\n')
        else:
            # Simple key-value attributes can go on one-line
            pdf.multi_cell(
                0,
                h=0,
                text=f'**{field_name}:** {fielddict[key]}\n\n',
                align='L',
                markdown=True,
                padding=LINE_PADDING
            )

    def write_project_body(pdf, project):
        """Write the body of a project to the PDF.

        Parameters
        -----------
            pdf: PDF
                PDF object to write to.
            project: dict
                Dictionary containing project data to write.
            parent_title: str
                Title of the parent project.
        Returns
        -----------
            pdf: PDF"""
        pdf.add_page()
        pdf.set_line_width(0.05)
        pdf.set_left_margin(10)
        pdf.set_right_margin(10)
        pdf.set_font(pdf.font, size=FONT_SIZES['h4'])
        wikis = project['wikis']

        # Write header section
        # Write parent header and title first
        if pdf.parent_title:
            pdf.set_font(pdf.font, size=FONT_SIZES['h1'], style='B')
            pdf.multi_cell(0, h=0, text=f'{pdf.parent_title}\n', align='L')
        if pdf.parent_url:
            pdf.set_font(pdf.font, size=FONT_SIZES['h4'])
            pdf.cell(
                text='Main Project URL:', align='L'
            )
            pdf.cell(
                text=f'{pdf.parent_url}\n', align='L', link=pdf.parent_url
            )
            pdf.write(0, '\n\n')

        # Check if title, url is of parent's to avoid duplication
        title = project['metadata']['title']
        if pdf.parent_title != title:
            pdf.set_font(pdf.font, size=FONT_SIZES['h1'], style='B')
            pdf.multi_cell(
                0, h=0, text=f'{title}\n',
                align='L', padding=LINE_PADDING
            )

        # Pop URL field to avoid printing it out in Metadata section
        url = project['metadata'].pop('url', '')

        pdf.url = url  # Set current URL to use in QR codes
        qr_img = pdf.generate_qr_code()
        pdf.image(qr_img, w=30, x=Align.R, y=5)

        pdf.set_font(pdf.font, size=FONT_SIZES['h4'])
        if url and pdf.parent_url != url:
            pdf.cell(
                text='Component URL:',
                align='L'
            )
            pdf.cell(
                text=f'{url}',
                align='L',
                link=url
            )
            pdf.write(0, '\n\n')

        pdf.ln()
        pdf.ln()

        # Write title for metadata section, then actual fields
        pdf.set_font(pdf.font, size=FONT_SIZES['h2'], style='B')
        pdf.multi_cell(
            0, h=0, text='1. Project Metadata\n',
            align='L', padding=LINE_PADDING)
        pdf.set_font(pdf.font, size=FONT_SIZES['h4'])
        for key in project['metadata']:
            write_list_section(key, project['metadata'], pdf)
        pdf.write(0, '\n')
        pdf.write(0, '\n')

        # Write Contributors in table
        pdf.set_font(pdf.font, size=FONT_SIZES['h2'], style='B')
        pdf.multi_cell(0, h=0, text='2. Contributors\n', align='L')
        pdf.set_font(pdf.font, size=FONT_SIZES['h4'])
        with pdf.table(
            headings_style=HEADINGS_STYLE,
            col_widths=(1, 0.5, 1)
        ) as table:
            row = table.row()
            row.cell('Name')
            row.cell('Bibliographic?')
            row.cell('Profile Link')
            for data_row in project['contributors']:
                row = table.row()
                for idx, datum in enumerate(data_row):
                    if datum is True:
                        datum = 'Yes'
                    if datum is False:
                        datum = 'No'
                    if idx == 2:
                        row.cell(text=datum, link=datum)
                    else:
                        row.cell(datum)
        pdf.write(0, '\n')
        pdf.write(0, '\n')

        # List files stored in storage providers
        # For now only OSF Storage is involved
        pdf.set_font(pdf.font, size=FONT_SIZES['h2'], style='B')
        pdf.multi_cell(0, h=0, text='3. Files in Main Project\n', align='L')
        pdf.write(0, '\n')
        pdf.set_font(pdf.font, size=FONT_SIZES['h3'], style='B')
        pdf.multi_cell(0, h=0, text='OSF Storage\n', align='L')
        pdf.set_font(pdf.font, size=FONT_SIZES['h4'])
        if len(project['files']) > 0:
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
                    for idx, datum in enumerate(data_row):
                        if datum is True:
                            datum = 'Yes'
                        if datum is False or datum is None:
                            datum = 'N/A'
                        if idx == 2:
                            row.cell(text=datum, link=datum)
                        else:
                            row.cell(datum)
        else:
            pdf.write(0, '\n')
            pdf.multi_cell(
                0, h=0, text='No files found for this project.\n', align='L'
            )
            pdf.write(0, '\n')

        # Write wikis separately to more easily handle Markdown parsing
        pdf.ln()
        pdf.set_font(pdf.font, size=FONT_SIZES['h1'], style='B')
        pdf.multi_cell(0, h=0, text='4. Wiki\n', align='L')
        pdf.ln()
        for i, wiki in enumerate(wikis.keys()):
            pdf.set_font(pdf.font, size=FONT_SIZES['h2'], style='B')
            pdf.multi_cell(0, h=0, text=f'{wiki}\n')
            pdf.set_font(pdf.font, size=FONT_SIZES['h4'])
            html = markdown(wikis[wiki])
            pdf.write_html(html)
            if i < len(wikis.keys())-1:
                pdf.add_page()

        return pdf

    def explore_project_tree(project, projects, pdf=None):
        """Recursively find child projects and write them to the PDF.

        Parameters
        -----------
            project: dict
                Dictionary containing project data to write.
            projects: list[dict]
                List of all projects to explore.
            pdf: PDF
                PDF object to write to. If None, a new PDF will be created.
            parent_title: str
                Title of the parent project.

        Returns
        -----------
            pdf: PDF
                PDF object with the project and its children written to it."""

        # Start with no PDF at root projects
        if not pdf:
            pdf = PDF(
                parent_title=project['metadata']['title'],
                parent_url=project['metadata']['url']
            )

        # Add current project to PDF
        pdf = write_project_body(pdf, project)

        # Do children last so that come at end of the PDF
        children = project['children']
        for child_id in children:
            child_project = next(
                (p for p in projects if p['metadata']['id'] == child_id), None
            )
            if child_project:
                pdf = explore_project_tree(
                    child_project, projects, pdf=pdf
                )

        return pdf

    curr_project = projects[root_idx]
    title = curr_project['metadata']['title']
    pdf = explore_project_tree(curr_project, projects)

    # Remove spaces in file name for better behaviour on Linux
    # Add timestamp to allow distinguishing between PDFs at a glance
    timestamp = pdf.date_printed.strftime(
        '%Y-%m-%d %H:%M:%S %Z'
    ).replace(' ', '-')
    filename = f'{title.replace(' ', '-')}-{timestamp}.pdf'

    if folder:
        if not os.path.exists(folder):
            os.mkdir(folder)
        path = os.path.join(os.getcwd(), folder, filename)
    else:
        path = os.path.join(os.getcwd(), filename)
    pdf.output(path)

    return pdf, path
