from __future__ import annotations

import csv
import hashlib
import json
import posixpath
import re
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
REL = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def write_csv(path, rows, fields=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    fields = fields or (list(rows[0]) if rows else ['status'])
    with path.open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def q(identifier):
    return '"' + identifier.replace('"', '""') + '"'


def timestamp(value):
    """Canonical microseconds; aware instants -> UTC, naive remain naive.

    Never invent a timezone or equate a naive time with an aware time.
    Reject fractions beyond microseconds instead of silently truncating keys.
    """
    if value is None or str(value).strip() == '':
        return None
    text = str(value).strip()
    fraction = re.search(r'\.(\d+)', text)
    if fraction and len(fraction[1]) > 6:
        if any(c != '0' for c in fraction[1][6:]):
            return None
        text = text[:fraction.start(1)] + fraction[1][:6] + text[fraction.end(1):]
    try:
        date = datetime.fromisoformat(text.replace('Z', '+00:00'))
    except ValueError:
        return None
    if date.tzinfo is not None:
        date = date.astimezone(timezone.utc)
    return date.isoformat(timespec='microseconds')


def identity(value):
    return None if value is None or str(value).strip() == '' else str(value).strip()


def digest(values):
    return hashlib.sha256(json.dumps(values, ensure_ascii=False, separators=(',', ':')).encode()).digest()


def is_identity(column):
    return bool(re.search(r'(^id_|_id$|^index|^kode_|^nik|^no_|^nib$|kbli|^code_|^nomor_|^assignment|_value$|provinsi|kabupaten|kecamatan|desa|subsls|sls|negara|telepon|whatsapp)', column))


def sheets(path):
    with ZipFile(path) as archive:
        rels = {r.attrib['Id']: r.attrib['Target'] for r in ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))}
        result = []
        for s in ET.fromstring(archive.read('xl/workbook.xml')).find(NS + 'sheets'):
            target = rels[s.attrib[REL + 'id']]
            target = target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join('xl', target))
            result.append((s.attrib['name'], target))
        return result


def xlsx_rows(path, sheet_path):
    """Stream OOXML cells, preserving numeric lexemes, NULL, types and formulas.

    Dates stored as Excel serial numbers remain original numeric lexemes in RAW;
    original workbook preserves styles. No cached formula is mistaken for source.
    """
    with ZipFile(path) as archive:
        shared = []
        if 'xl/sharedStrings.xml' in archive.namelist():
            with archive.open('xl/sharedStrings.xml') as stream:
                for _, e in ET.iterparse(stream, events=('end',)):
                    if e.tag == NS + 'si':
                        shared.append(''.join(t.text or '' for t in e.iter(NS + 't')))
                        e.clear()
        with archive.open(sheet_path) as stream:
            context = ET.iterparse(stream, events=('start', 'end'))
            _, root = next(context)
            data = None
            for event, element in context:
                if event == 'start' and element.tag == NS + 'sheetData':
                    data = element
                if event != 'end' or element.tag != NS + 'row':
                    continue
                values, types = [], []
                for cell in element:
                    reference = re.match(r'([A-Z]+)', cell.attrib['r'])[1]
                    column = 0
                    for letter in reference:
                        column = column * 26 + ord(letter) - 64
                    while len(values) < column:
                        values.append(None)
                        types.append('null')
                    kind = cell.attrib.get('t', 'n')
                    formula, value = cell.find(NS + 'f'), cell.find(NS + 'v')
                    if formula is not None:
                        value, kind = '=' + (formula.text or ''), 'formula'
                    elif kind == 'inlineStr':
                        value, kind = ''.join(t.text or '' for t in cell.iter(NS + 't')), 'text'
                    elif kind == 's':
                        value, kind = shared[int(value.text)], 'text'
                    else:
                        value = value.text if value is not None else None
                        kind = {'n': 'number', 'b': 'boolean', 'd': 'date', 'str': 'text', 'e': 'error'}.get(kind, kind)
                    values[column - 1], types[column - 1] = value, kind if value is not None else 'null'
                row_number = int(element.attrib['r'])
                yield row_number, values, types
                element.clear()
                if data is not None:
                    data.clear()


def records(path, sheet_path, width):
    rows = xlsx_rows(path, sheet_path)
    next(rows, None)
    for number, values, types in rows:
        if len(values) > width and any(v is not None for v in values[width:]):
            raise ValueError('ROW_WIDER_THAN_HEADER')
        yield number, (values + [None] * width)[:width], (types + ['null'] * width)[:width]
