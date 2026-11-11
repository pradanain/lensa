"""Local XLSX responses: explicit text cells, no formulas or respondent files on disk."""

import io
import re
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import HTTPException, Response


def workbook_response(headers, rows, filename):
    def column(index):
        name = ""
        while index:
            index, remainder = divmod(index - 1, 26)
            name = chr(65 + remainder) + name
        return name

    buffer = io.BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>',
        )
        archive.writestr(
            "_rels/.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        )
        archive.writestr(
            "xl/workbook.xml",
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Hasil" sheetId="1" r:id="rId1"/></sheets></workbook>',
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>',
        )
        archive.writestr(
            "xl/styles.xml",
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF217346"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf/></cellStyleXfs><cellXfs count="2"><xf fontId="0" fillId="0" borderId="0" xfId="0"/><xf fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>',
        )
        with archive.open("xl/worksheets/sheet1.xml", "w") as stream:

            def write(text):
                stream.write(text.encode("utf-8"))

            write(
                '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><cols>'
            )
            for index in range(1, len(headers) + 1):
                write(f'<col min="{index}" max="{index}" width="24" customWidth="1"/>')
            write("</cols><sheetData>")
            count = 0
            for count, row in enumerate(_with_header(headers, rows), 1):
                if count > 1048576:
                    raise HTTPException(422, "EXPORT_EXCEL_ROW_LIMIT")
                write(f'<row r="{count}">')
                for index, value in enumerate(row, 1):
                    address = column(index) + str(count)
                    style = ' s="1"' if count == 1 else ""
                    if isinstance(value, int) and not isinstance(value, bool):
                        write(f'<c r="{address}"{style} t="n"><v>{value}</v></c>')
                    else:
                        text = "" if value is None else str(value)
                        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]", "", text)
                        if len(text) > 32767:
                            raise HTTPException(422, "EXPORT_EXCEL_CELL_LIMIT")
                        write(
                            f'<c r="{address}"{style} t="inlineStr"><is><t xml:space="preserve">{escape(text)}</t></is></c>'
                        )
                write("</row>")
            write(f'</sheetData><autoFilter ref="A1:{column(len(headers))}{count}"/></worksheet>')
    return Response(
        buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}.xlsx"',
            "Cache-Control": "no-store, private",
        },
    )


def _with_header(headers, rows):
    yield headers
    yield from rows


def directory_workbook(directory, scope, payload, role):
    result = directory.search(scope, payload, role, all_rows=True)
    fields = [
        ("Sumber", "source"),
        ("Assignment ID", "assignment_id"),
        ("Versi", "version"),
        ("Roster", "index1"),
        ("Nama", "title"),
        ("Kecamatan", "kecamatan_label"),
        ("Desa", "desa_label"),
        ("SLS", "sls_label"),
        ("SUB-SLS", "subsls_label"),
        ("Kode SLS", "sls"),
        ("Kode SUB-SLS", "subsls"),
        ("Status", "status_label"),
    ]
    if scope == "businesses":
        fields += [
            ("Penanggung Jawab", "person_in_charge"),
            ("Nama KK", "family_head"),
            ("Kategori", "kategori"),
            ("KBLI 2025", "kbli"),
        ]
    headers = [title for title, _ in fields]
    if scope == "businesses":
        headers += ["Judul KBLI"]
        if role == "admin":
            headers += ["Latitude", "Longitude"]

    def rows():
        for item in result["rows"]:
            row = [item.get(field) for _, field in fields]
            row[0] = "UB" if item["source"] == "ub" else "UMKM"
            row[11] = re.sub(
                r"^\s*\d+\s*[.)\-:]\s*", "", str(item.get("status_label") or item.get("status") or "")
            )
            if scope == "businesses":
                row.append(directory.references.kbli.get(item.get("kbli"), {}).get("title"))
                if role == "admin":
                    coordinates = item.get("map_coordinates") or {}
                    row.extend([coordinates.get("latitude"), coordinates.get("longitude")])
            yield row

    return workbook_response(headers, rows(), "lensa-" + scope)
