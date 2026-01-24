PDF Destination Testing Runbook

Purpose
Document the repeatable steps to add temporary named destinations and outline
entries to a PDF for validating exact jump targets. This preserves existing
TOC destinations while adding new test-only anchors.

Prereqs (one-time)
- Install pyenv + build deps (if system python lacks pip):
  - curl https://pyenv.run | bash
  - sudo apt-get update
  - sudo apt-get install -y build-essential libssl-dev zlib1g-dev libbz2-dev \
    libreadline-dev libsqlite3-dev libffi-dev liblzma-dev tk-dev xz-utils curl
- Install Python + venv:
  - export PYENV_ROOT="$HOME/.pyenv"
  - export PATH="$PYENV_ROOT/bin:$PATH"
  - eval "$(pyenv init -)"
  - pyenv install 3.12.3
  - pyenv virtualenv 3.12.3 pdfcoords
- Install tools in the venv:
  - /home/john/.pyenv/versions/3.12.3/envs/pdfcoords/bin/python -m pip install pymupdf pikepdf

How the mapping is derived
1) Read existing PDF destinations to avoid name collisions:
   - qpdf --show-object=22 winston-hills-ccrs-and-amendments-complete-searchable-toc.pdf
   - The /Dests dictionary lives in the catalog (object 22 in this PDF).
2) Find exact text coordinates with PyMuPDF:
   - PyMuPDF returns rectangles in a top-left origin.
   - Convert to PDF /XYZ coordinates using:
     - pdf_y = page.rect.height - rect.y0
3) Add named destinations + outline entries with pikepdf:
   - Do not modify existing /Dests in the catalog.
   - Add a new /Names -> /Dests name tree if missing, then add the new dests.
   - Create outline entries pointing to the new /XYZ destinations.

Template script (creates a temp PDF for testing)
Save or run this directly from the repo root:

```python
import pikepdf
from pathlib import Path

src = Path('winston-hills-ccrs-and-amendments-complete-searchable-toc.pdf')
out = Path('tmp/winston-hills-ccrs-and-amendments-complete-searchable-toc-test.pdf')

entries = [
    # (name, page_num_1_based, x, y) y is from bottom of page
    ('amend1-p7', 78, 143.543, 201.641),
    # ...
]

pdf = pikepdf.open(src)

if '/Names' not in pdf.Root:
    pdf.Root.Names = pikepdf.Dictionary()
if '/Dests' not in pdf.Root.Names:
    pdf.Root.Names.Dests = pikepdf.NameTree.new(pdf).obj

name_tree = pikepdf.NameTree(pdf.Root.Names.Dests)

for name, page_num, x, y in entries:
    page = pdf.pages[page_num - 1].obj
    dest = pikepdf.Array([page, pikepdf.Name('/XYZ'), x, y, 0])
    name_tree[name] = dest

with pdf.open_outline() as outline:
    for name, page_num, x, y in entries:
        page = pdf.pages[page_num - 1].obj
        dest = pikepdf.Array([page, pikepdf.Name('/XYZ'), x, y, 0])
        outline.add(f'TEST DEST {name}', dest)

pdf.save(out)
print('wrote', out)
```

How to test
- Open the temp PDF: tmp/winston-hills-ccrs-and-amendments-complete-searchable-toc-test.pdf
- Use the outline panel; entries labeled TEST DEST <name> should jump to the
  exact target text.

Gotchas
- PyMuPDF set_toc does not reliably accept X/Y; pikepdf does.
- Use page.obj when creating destination arrays; pikepdf does not accept
  ObjectHelper instances.
- This PDF uses catalog /Dests already; we only add a Names/Dests name tree
  to avoid touching existing TOC anchors.
