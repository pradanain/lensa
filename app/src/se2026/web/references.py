import csv
import re

from .kbli import KbliHierarchy


class References:
    def __init__(self, root):
        folder = root / "app/config/references"

        def rows(name):
            with (folder / name).open(encoding="utf-8-sig", newline="") as stream:
                return list(csv.DictReader(stream, delimiter=";"))

        self.kbli = {
            r["Kode"].strip(): dict(
                code=r["Kode"].strip(),
                category=r["Kategori"].strip(),
                category_label="Kategori " + r["Kategori"].strip(),
                title=r["Judul"].strip(),
                description=r["Deskripsi"].strip(),
                outside_se=r["Bukan cakupan SE"].strip() == "1",
            )
            for r in rows("master-kbli-2025.csv")
        }
        if not self.kbli or any(not re.fullmatch(r"[0-9]{5}", code) for code in self.kbli):
            raise ValueError("REFERENCE_KBLI_INVALID")
        self.hierarchy = KbliHierarchy(folder / "kbli2025-hierarchy.json", self.kbli)
        self.categories = self.hierarchy.categories
        for row in self.kbli.values():
            row["category_label"] = self.categories[row["category"]]
        self.professions = {
            r["kode"].strip().zfill(3): r["nama@1"].strip() for r in rows("master-profesi.csv")
        }
        self.profession_aliases = rows("master-profesi-alias-long.csv")
        self.country_rows = [
            dict(code=r["kode_negara"].strip().zfill(3), title=r["negara"].strip())
            for r in rows("master-kode-negara.csv")
        ]
        labels = {}
        for row in self.country_rows:
            labels.setdefault(row["code"], set()).add(row["title"])
        self.countries = {code: next(iter(values)) for code, values in labels.items() if len(values) == 1}
        self.country_conflicts = {code: sorted(values) for code, values in labels.items() if len(values) > 1}

    def kbli_state(self, value):
        text = str(value or "").strip()
        if not text:
            return "MISSING"
        if not re.fullmatch(r"[0-9]{5}", text):
            return "INVALID_FORMAT"
        return "VALID" if text in self.kbli else "UNKNOWN_REFERENCE"

    def tree(self, category=None, prefix="", level=2, text=""):
        return self.hierarchy.tree(category, prefix, level, text)

    def summary(self):
        return dict(
            kbli_codes=len(self.kbli),
            categories=len(self.categories),
            outside_se_codes=sum(r["outside_se"] for r in self.kbli.values()),
            professions=len(self.professions),
            countries=len(self.country_rows),
            country_code_conflicts=len(self.country_conflicts),
            category_codes=sorted(self.categories),
            category_labels=self.categories,
            hierarchy_counts={
                "categories": 22,
                "divisions": 87,
                "groups": 257,
                "classes": 519,
                "subclasses": 1559,
            },
            prefix_labels="Kategori huruf dan kode 2–5 digit mengikuti referensi lokal KBLI 2025; awalan angka 1 digit adalah penyaring tambahan.",
        )

    def search(self, kind, text="", limit=50):
        term = text.casefold().strip()
        if kind == "countries":
            entries = self.country_rows
        elif kind == "professions":
            alias_codes = {
                r["kode"].strip().zfill(3)
                for r in self.profession_aliases
                if term and term in r["alias"].casefold()
            }
            entries = [
                dict(code=k, title=v)
                for k, v in self.professions.items()
                if not term or term in k.casefold() or term in v.casefold() or k in alias_codes
            ]
            return entries if limit is None else entries[:limit]
        else:
            entries = list(self.kbli.values())
        filtered = [r for r in entries if not term or term in str(r).casefold()]
        return filtered if limit is None else filtered[:limit]
