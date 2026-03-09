"""Invoice-to-PDF generator using only the Python standard library.

Produces a clean, professional invoice PDF from billing tracker invoices.
No external dependencies required — uses a minimal PDF writer.

Usage:
    from billing.invoice_pdf import generate_invoice_pdf

    pdf_path = generate_invoice_pdf("acme-corp", days=30)

CLI:
    python -m billing.invoice_pdf acme-corp --days 30
"""

import json
import struct
import sys
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ── Minimal PDF Writer ─────────────────────────────────────────

class _PDFWriter:
    """Bare-bones PDF 1.4 writer — text only, no images."""

    def __init__(self):
        self._objects: list[bytes] = []
        self._pages: list[int] = []
        self._offsets: list[int] = []

    def _add_obj(self, data: bytes) -> int:
        self._objects.append(data)
        return len(self._objects)

    def add_page(self, lines: list[tuple[float, float, str, float]]):
        """Add a page. lines = [(x, y, text, font_size), ...]"""
        stream_parts = ["BT"]
        for x, y, text, size in lines:
            # Replace non-latin-1 chars for PDF compatibility
            text = text.replace("\u2014", "--").replace("\u2013", "-")
            safe = (
                text.replace("\\", "\\\\")
                .replace("(", "\\(")
                .replace(")", "\\)")
            )
            stream_parts.append(f"/F1 {size:.0f} Tf")
            stream_parts.append(f"{x:.1f} {y:.1f} Td")
            stream_parts.append(f"({safe}) Tj")
            stream_parts.append(f"{-x:.1f} {-y:.1f} Td")
        stream_parts.append("ET")
        stream = "\n".join(stream_parts).encode("latin-1")
        compressed = zlib.compress(stream)

        stream_obj_num = self._add_obj(
            b"<< /Length " + str(len(compressed)).encode()
            + b" /Filter /FlateDecode >>\nstream\n"
            + compressed + b"\nendstream"
        )
        page_obj_num = self._add_obj(
            b"<< /Type /Page /Parent 2 0 R "
            b"/MediaBox [0 0 612 792] "
            b"/Contents " + str(stream_obj_num).encode() + b" 0 R "
            b"/Resources << /Font << /F1 4 0 R >> >> >>"
        )
        self._pages.append(page_obj_num)

    def build(self) -> bytes:
        # Object 1: Catalog
        # Object 2: Pages (placeholder — fixed up below)
        # Object 3: (reserved for pages, filled below)
        # Object 4: Font

        objs: list[bytes] = []

        # 1 — Catalog
        objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")

        # 2 — Pages (placeholder)
        objs.append(b"PLACEHOLDER")

        # 3 — (not used, we'll reindex)
        # 4 — Font
        objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

        # Re-add stream + page objects
        page_refs: list[int] = []
        for obj_data in self._objects:
            objs.append(obj_data)
            # Track page objects
        # Page refs are the page objects we added
        for pg in self._pages:
            # pg was 1-based index into self._objects
            # In objs, self._objects start at index 3 (0=catalog, 1=pages, 2=font)
            page_refs.append(pg + 3)

        # Fix pages object
        kids = " ".join(f"{r} 0 R" for r in page_refs)
        objs[1] = (
            f"<< /Type /Pages /Kids [{kids}] /Count {len(page_refs)} >>".encode()
        )

        # Also fix parent refs in page objects
        for i in range(3, len(objs)):
            if b"/Type /Page /Parent 2 0 R" in objs[i]:
                pass  # Already correct

        # Build PDF bytes
        buf = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
        offsets = []
        for idx, obj in enumerate(objs):
            offsets.append(len(buf))
            obj_num = idx + 1
            buf += f"{obj_num} 0 obj\n".encode() + obj + b"\nendobj\n"

        xref_pos = len(buf)
        buf += b"xref\n"
        buf += f"0 {len(objs) + 1}\n".encode()
        buf += b"0000000000 65535 f \n"
        for off in offsets:
            buf += f"{off:010d} 00000 n \n".encode()

        buf += b"trailer\n"
        buf += f"<< /Size {len(objs) + 1} /Root 1 0 R >>\n".encode()
        buf += b"startxref\n"
        buf += f"{xref_pos}\n".encode()
        buf += b"%%EOF\n"
        return buf


# ── Invoice PDF Generator ──────────────────────────────────────

def _draw_invoice(invoice: dict) -> bytes:
    """Render an invoice dict to PDF bytes."""
    pdf = _PDFWriter()
    lines: list[tuple[float, float, str, float]] = []

    W = 612  # Letter width
    y = 740

    def add(x: float, text: str, size: float = 11):
        nonlocal y
        lines.append((x, y, text, size))

    def nl(gap: float = 16):
        nonlocal y
        y -= gap

    # Header
    add(50, "DIGITAL LABOUR", 22)
    nl(18)
    add(50, "AI Workforce — Invoice", 10)
    nl(30)

    # Separator
    add(50, "_" * 75, 8)
    nl(20)

    # Client info
    add(50, f"Client:  {invoice.get('client', 'N/A')}", 11)
    add(350, f"Date:  {datetime.now(timezone.utc).strftime('%Y-%m-%d')}", 11)
    nl()
    add(50, f"Period:  {invoice.get('period', 'N/A')}", 11)
    nl(24)

    # Table header
    add(50, "Description", 10)
    add(280, "Qty", 10)
    add(360, "Rate", 10)
    add(450, "Amount", 10)
    nl(6)
    add(50, "_" * 75, 8)
    nl(16)

    # Line items
    retainer = invoice.get("retainer", "")
    if retainer and "base_price" in invoice:
        from billing.tracker import RETAINER_TIERS
        tier = RETAINER_TIERS.get(retainer, {})
        tier_label = retainer.replace("_", " ").title()
        add(50, f"Retainer: {tier_label}", 11)
        add(280, "1", 11)
        add(360, f"${invoice['base_price']:.2f}", 11)
        add(450, f"${invoice['base_price']:.2f}", 11)
        nl()

        if invoice.get("overage_count", 0) > 0:
            add(50, f"Overage tasks", 11)
            add(280, str(invoice["overage_count"]), 11)
            add(360, f"${tier.get('overage', 0):.2f}", 11)
            add(450, f"${invoice['overage_charge']:.2f}", 11)
            nl()
    else:
        # Per-task breakdown
        from billing.tracker import PRICING, BillingTracker
        bt = BillingTracker()
        summary = bt.client_summary(invoice["client"], days=30)
        by_type = summary.get("by_type", {})
        for task_type, count in by_type.items():
            rate = PRICING.get(task_type, {}).get("per_task", 0)
            label = task_type.replace("_", " ").title()
            add(50, label, 11)
            add(280, str(count), 11)
            add(360, f"${rate:.2f}", 11)
            add(450, f"${count * rate:.2f}", 11)
            nl()

    nl(8)
    add(50, "_" * 75, 8)
    nl(20)

    # Totals
    total = invoice.get("total_charge", 0)
    add(360, "Total:", 12)
    add(450, f"${total:.2f}", 12)
    nl(30)

    # Footer
    add(50, "Payment: Stripe checkout link sent to client email.", 9)
    nl()
    add(50, "Terms: Due upon receipt. Net 14 days.", 9)
    nl(30)
    add(50, "Thank you for choosing Digital Labour.", 10)

    pdf.add_page(lines)
    return pdf.build()


def generate_invoice_pdf(client: str, days: int = 30) -> str:
    """Generate an invoice and render it as PDF. Returns the PDF file path."""
    from billing.tracker import BillingTracker

    bt = BillingTracker()
    invoice = bt.generate_invoice(client, days=days)

    pdf_bytes = _draw_invoice(invoice)

    output_dir = PROJECT_ROOT / "output" / "invoices"
    output_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y%m%d")
    pdf_path = output_dir / f"invoice_{client}_{now}.pdf"
    pdf_path.write_bytes(pdf_bytes)

    return str(pdf_path)


# ── CLI ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate invoice PDF")
    parser.add_argument("client", help="Client ID")
    parser.add_argument("--days", type=int, default=30, help="Billing period in days")
    args = parser.parse_args()

    path = generate_invoice_pdf(args.client, days=args.days)
    print(f"Invoice PDF generated: {path}")
