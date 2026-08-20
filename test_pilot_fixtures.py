from pathlib import Path

from docx import Document
from pypdf import PdfReader

FIXTURES = Path(__file__).parent / "pilot_fixtures"


def test_real_pilot_fixture_files_exist_and_are_readable():
    contract = FIXTURES / "pilot_contract.pdf"
    amendment = FIXTURES / "pilot_amendment.pdf"
    invoice = FIXTURES / "pilot_invoice.docx"

    contract_text = "\n".join(page.extract_text() or "" for page in PdfReader(contract).pages)
    amendment_text = "\n".join(page.extract_text() or "" for page in PdfReader(amendment).pages)
    invoice_text = "\n".join(p.text for p in Document(invoice).paragraphs)

    assert "100 hours at USD 150 per hour" in contract_text
    assert "20 hours at USD 150 per hour" in amendment_text
    assert "USD 15,000" in invoice_text



def test_pilot_fixture_render_qa_recorded():
    qa = FIXTURES / "RENDER_QA.txt"
    assert qa.exists()
    text = qa.read_text(encoding="utf-8")
    assert "contract: PASS" in text
    assert "amendment: PASS" in text
    assert "invoice: PASS" in text
