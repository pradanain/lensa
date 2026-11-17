"""Conservative display rules: compile an allowlisted expression subset; never execute JS."""

import ast
import re
from decimal import Decimal, InvalidOperation

UNKNOWN = object()


def compile_condition(source):
    if not source or not source.strip():
        return {"literal": True}
    if "===" in source or "!==" in source:
        return {"unknown": "STRICT_TYPE_CONDITION_NOT_TRANSLATED"}
    text = re.sub(r"/\*.*?\*/|//[^\n]*", "", source, flags=re.S).strip()
    # Pure IIFEs with declarations and one return can be treated as expressions.
    if re.match(r"^\(\s*(?:function\s*\(\)|\(\)\s*=>)\s*\{", text):
        text = text[text.index("{") + 1 :]
        text = re.sub(r"\}\s*\)\s*\(\s*\)\s*;?\s*$", "", text).strip()
    text = re.sub(
        r"(?<=[\w\)'\"\]])[ \t]*\r?\n\s*(?=(?:let|const|var|return)\s|(?:getValue|Number)\(|\[)", ";\n", text
    )
    aliases = {}

    def expression(value):
        value = re.sub(r"\??\.?\[0\]\??\.value", "", value)
        value = value.replace("?.", ".")
        value = re.sub(r"\s*\?\?\s*(?:'0'|\"0\"|''|\"\"|0)", "", value)
        value = re.sub(r"/([0-9|()^$]+)/(?:\.test)\(([^()]+)\)", r"matches('\1',\2)", value)
        parts = re.split(r"('(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\")", value)
        for i in range(0, len(parts), 2):
            parts[i] = parts[i].replace("&&", " and ").replace("||", " or ")
            parts[i] = re.sub(r"!(?!=)", " not ", parts[i])
            parts[i] = re.sub(r"\btrue\b", "True", parts[i])
            parts[i] = re.sub(r"\bfalse\b", "False", parts[i])
        value = "".join(parts)
        return convert(ast.parse(value.strip(), mode="eval").body)

    def convert(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (str, int, float, bool)):
            return {"literal": node.value}
        if isinstance(node, ast.Name) and node.id in aliases:
            return aliases[node.id]
        if isinstance(node, (ast.List, ast.Tuple)):
            return {"op": "list", "args": [convert(x) for x in node.elts]}
        if isinstance(node, ast.BoolOp):
            return {
                "op": "all" if isinstance(node.op, ast.And) else "any",
                "args": [convert(v) for v in node.values],
            }
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return {"op": "not", "args": [convert(node.operand)]}
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = {
                ast.Eq: "eq",
                ast.NotEq: "ne",
                ast.Lt: "lt",
                ast.LtE: "le",
                ast.Gt: "gt",
                ast.GtE: "ge",
            }.get(type(node.ops[0]))
            if op:
                return {"op": op, "args": [convert(node.left), convert(node.comparators[0])]}
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if (
                node.func.id == "getValue"
                and len(node.args) == 1
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                return {"ref": node.args[0].value}
            op = {"Number": "number", "String": "string", "matches": "matches"}.get(node.func.id)
            if op:
                return {"op": op, "args": [convert(v) for v in node.args]}
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            op = {"includes": "contains", "toLowerCase": "lower"}.get(node.func.attr)
            if op:
                return {"op": op, "args": [convert(node.func.value), *[convert(v) for v in node.args]]}
        if isinstance(node, ast.Attribute) and node.attr == "length":
            return {"op": "length", "args": [convert(node.value)]}
        raise ValueError("UNSUPPORTED_TEMPLATE_EXPRESSION")

    try:
        parts = [p.strip() for p in text.split(";") if p.strip()]
        for part in parts[:-1]:
            declaration = re.fullmatch(r"(?:let|const|var)\s+(\w+)\s*=\s*(.+)", part, re.S)
            if not declaration:
                return {"unknown": "UNSUPPORTED_TEMPLATE_PROGRAM"}
            aliases[declaration[1]] = expression(declaration[2])
        return expression(re.sub(r"^return\s+", "", parts[-1]))
    except (ValueError, SyntaxError, IndexError, re.error):
        return {"unknown": "UNSUPPORTED_TEMPLATE_EXPRESSION"}


def truth(value):
    return UNKNOWN if value is UNKNOWN else True if isinstance(value, (list, dict)) else bool(value)


def number(value):
    if value is UNKNOWN:
        return UNKNOWN
    try:
        parsed = Decimal(str(value))
        return parsed if parsed.is_finite() else UNKNOWN
    except (InvalidOperation, ValueError):
        return UNKNOWN


def evaluate(node, resolve, depth=0):
    if depth > 40 or "unknown" in node:
        return UNKNOWN
    if "literal" in node:
        return node["literal"]
    if "ref" in node:
        return resolve(node["ref"])
    op = node.get("op")
    args = [evaluate(n, resolve, depth + 1) for n in node.get("args", [])]
    if op == "all":
        return (
            False
            if any(truth(v) is False for v in args)
            else UNKNOWN
            if any(v is UNKNOWN for v in args)
            else True
        )
    if op == "any":
        return (
            True
            if any(truth(v) is True for v in args)
            else UNKNOWN
            if any(v is UNKNOWN for v in args)
            else False
        )
    if any(v is UNKNOWN for v in args):
        return UNKNOWN
    try:
        if op == "list":
            return args
        if op == "not":
            return not truth(args[0])
        if op == "number":
            return number(args[0])
        if op == "string":
            return str(args[0])
        if op == "lower":
            return args[0].lower() if isinstance(args[0], str) else UNKNOWN
        if op == "length":
            return len(args[0]) if isinstance(args[0], (str, list)) else UNKNOWN
        if op == "contains":
            return args[1] in args[0] if isinstance(args[0], (str, list)) else UNKNOWN
        if op == "matches":
            return (
                bool(re.search(args[0], str(args[1]))) if re.fullmatch(r"[0-9|()^$]+", args[0]) else UNKNOWN
            )
        if op in {"eq", "ne", "lt", "le", "gt", "ge"}:
            a, b = args
            if not (isinstance(a, str) and isinstance(b, str)):
                a, b = number(a), number(b)
                if a is UNKNOWN or b is UNKNOWN:
                    return UNKNOWN
            return {
                "eq": lambda: a == b,
                "ne": lambda: a != b,
                "lt": lambda: a < b,
                "le": lambda: a <= b,
                "gt": lambda: a > b,
                "ge": lambda: a >= b,
            }[op]()
    except (TypeError, ValueError, IndexError):
        pass
    return UNKNOWN


def apply_display_rules(form, rendered):
    schemas = {f["question_id"]: f for s in form["sections"] for f in s["questions"]}
    facts = {scope: {} for scope in ("root", "businesses", "members", "meters", "offices")}
    blocked, conflicts = set(), set()
    for section in rendered:
        for field in section["questions"]:
            schema = schemas[field["question_id"]]
            key = schema.get("template_key")
            if not key:
                continue
            if schema.get("source_version_scope") == "assignment":
                continue  # Operational geography is not a questionnaire control answer.
            scope = schema.get("roster") or "root"
            if field["status"] == "RESTRICTED":
                blocked.add((scope, key))
            value = field.get("value")
            if field["status"] != "ANSWERED" or value is None or str(value).strip() == "":
                value = UNKNOWN
            elif schema.get("template_type") in {20, 24} or (schema.get("source_field") or "").startswith(
                "umur"
            ):
                value = number(value)
                if (
                    value is not UNKNOWN
                    and (schema.get("source_field") or "").startswith("umur")
                    and value < 0
                ):
                    value = UNKNOWN
            else:
                choices = schema.get("choices", {})
                if choices and value not in choices:

                    def normalize(label):
                        return re.sub(r"^\s*\d+(?:\.[a-z])?[.)]?\s+", "", str(label)).strip().casefold()

                    labels = [
                        k
                        for k, label in choices.items()
                        if normalize(value) == normalize(label)
                        or (field.get("label") and normalize(field["label"]) == normalize(label))
                    ]
                    if len(labels) == 1:
                        value = labels[0]
                    else:
                        value = UNKNOWN
            existing = facts[scope].get(key, UNKNOWN)
            if existing is not UNKNOWN and value is not UNKNOWN and existing != value:
                conflicts.add((scope, key))
            facts[scope][key] = value if existing is UNKNOWN or existing == value else existing

    variables = form.get("display_variables", {})
    cache, visiting = {}, set()

    def resolve(key, scope):
        row = "@$ROW$" in key
        key = key.replace("@$ROW$", "")
        token = (key, scope)
        fact_scope = scope if row else "root"
        if (fact_scope, key) in blocked or (fact_scope, key) in conflicts:
            return UNKNOWN
        fact = facts[fact_scope].get(key, UNKNOWN)
        if fact is not UNKNOWN:
            return fact
        if key in variables:
            if token in visiting:
                return UNKNOWN
            if token not in cache:
                visiting.add(token)
                cache[token] = evaluate(variables[key], lambda ref: resolve(ref, scope))
                visiting.remove(token)
            return cache[token]
        return facts[scope if row else "root"].get(key, UNKNOWN)

    for section in rendered:
        scope = (
            "businesses"
            if section["section_id"] == "blokl"
            else "members"
            if section["section_id"] in {"b_ak", "b_ak_lanjutan"}
            else "meters"
            if section["section_id"] == "b_perumahan"
            else "root"
        )
        for field in section["questions"]:
            schema = schemas[field["question_id"]]
            rules = schema.get("display_rules", [])
            row_scope = schema.get("roster") or scope
            result = evaluate(
                {"op": "all", "args": rules},
                lambda key, row_scope=row_scope: resolve(key, row_scope),
            )
            field["display_state"] = (
                "HIDDEN"
                if field.get("applicability") == "NOT_APPLICABLE" or result is False
                else "UNKNOWN"
                if result is UNKNOWN
                else "VISIBLE"
            )
    return rendered
