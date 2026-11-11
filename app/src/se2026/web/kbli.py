"""KBLI 2025 local hierarchy; numeric single digits are search prefixes only."""

import json
import re
from collections import Counter

LEVELS = {1: "Awalan 1 digit", 2: "Golongan pokok", 3: "Golongan", 4: "Subgolongan", 5: "Kelompok"}


class KbliHierarchy:
    def __init__(self, path, leaves):
        records = json.loads(path.read_text(encoding="utf-8-sig"))
        if Counter(r["digit"] for r in records) != {1: 22, 2: 87, 3: 257, 4: 519, 5: 1559}:
            raise ValueError("KBLI_HIERARCHY_LEVEL_COUNTS_INVALID")
        self.leaves = leaves
        self.nodes = {}
        for row in records:
            level, code, category = row["digit"], row["kode"], row["kategori"]
            if not isinstance(code, str) or not re.fullmatch(
                "[A-V]" if level == 1 else f"[0-9]{{{level}}}", code
            ):
                raise ValueError("KBLI_HIERARCHY_CODE_INVALID")
            if code in self.nodes:
                raise ValueError("KBLI_HIERARCHY_DUPLICATE_CODE")
            self.nodes[code] = dict(
                code=code,
                prefix=code,
                category=category,
                level=level,
                level_name="Kategori" if level == 1 else LEVELS[level],
                title=row["judul"].strip(),
                description=row["deskripsi"].strip(),
                description_status="SOURCE_TEXT" if row["deskripsi"].strip() else "CHILD_TITLES_ONLY",
                parent_code=None if level == 1 else category if level == 2 else code[:-1],
                is_official=True,
            )
        found = {code for code, row in self.nodes.items() if row["level"] == 5}
        if found != set(leaves):
            raise ValueError("KBLI_HIERARCHY_LEAF_SET_MISMATCH")
        for node in self.nodes.values():
            parent = self.nodes.get(node["parent_code"]) if node["parent_code"] else None
            if node["parent_code"] and (not parent or parent["category"] != node["category"]):
                raise ValueError("KBLI_HIERARCHY_PARENT_MISMATCH")
            if node["level"] == 5:
                leaf = leaves[node["code"]]
                if leaf["category"] != node["category"]:
                    raise ValueError("KBLI_HIERARCHY_CATEGORY_MISMATCH")
                node.update(
                    title=leaf["title"],
                    description=leaf["description"],
                    description_status="WORKSPACE_MASTER",
                )
        for node in self.nodes.values():
            if not node["description"]:
                children = [r for r in self.nodes.values() if r["parent_code"] == node["code"]]
                node["description"] = (
                    "Uraian kategori belum tersedia pada referensi lokal. Cakupan menurut golongan pokok: "
                    + "; ".join(r["code"] + " - " + r["title"] for r in children)
                    + "."
                )
        self.categories = {code: r["title"] for code, r in self.nodes.items() if r["level"] == 1}

    def technical_prefix(self, prefix, category=None):
        divisions = [
            r
            for r in self.nodes.values()
            if r["level"] == 2
            and r["code"].startswith(prefix)
            and (not category or r["category"] == category)
        ]
        categories = sorted({r["category"] for r in divisions})
        return dict(
            code=prefix,
            prefix=prefix,
            level=1,
            level_name=LEVELS[1],
            category=category or (categories[0] if len(categories) == 1 else ""),
            categories=categories,
            title="Awalan kode " + prefix,
            description="Angka "
            + prefix
            + " merupakan awalan pencarian, bukan tingkatan resmi KBLI. Pada pilihan ini mencakup golongan pokok: "
            + "; ".join(r["code"] + " - " + r["title"] for r in divisions)
            + ".",
            description_status="TECHNICAL_PREFIX_EXPLANATION",
            parent_code=category,
            is_official=False,
        )

    def catalog(self):
        keys = ("code", "category", "title", "level", "level_name", "parent_code")
        return [dict((k, node[k]) for k in keys) for node in self.nodes.values()]

    def selection(self, category, prefix):
        result = [dict(self.nodes[category])] if category in self.categories else []
        if prefix:
            if not category and len(prefix) >= 2 and prefix[:2] in self.nodes:
                result = [dict(self.nodes[self.nodes[prefix[:2]]["category"]])]
            result.append(self.technical_prefix(prefix[0], category))
            for length in range(2, len(prefix) + 1):
                node = self.nodes.get(prefix[:length])
                if node and (not category or node["category"] == category):
                    result.append(dict(node))
        return result

    def tree(self, category=None, prefix="", level=2, text=""):
        if level == 1:
            prefixes = sorted(
                {code[0] for code, row in self.leaves.items() if not category or row["category"] == category}
            )
            nodes = [self.technical_prefix(code, category) for code in prefixes]
        else:
            nodes = [dict(r) for r in self.nodes.values() if r["level"] == level]
        output = []
        terms = text.casefold().split()
        for node in nodes:
            if category and node["category"] != category or not node["code"].startswith(prefix):
                continue
            content = (node["code"] + " " + node["title"] + " " + node["description"]).casefold()
            if any(term not in content for term in terms):
                continue
            children = [
                r
                for code, r in self.leaves.items()
                if code.startswith(node["code"]) and (not category or r["category"] == category)
            ]
            output.append(
                {
                    **node,
                    "category_label": self.categories.get(node["category"], "Lintas kategori"),
                    "reference_codes": len(children),
                    "outside_se_codes": sum(r["outside_se"] for r in children),
                }
            )
        return sorted(output, key=lambda r: r["code"])
