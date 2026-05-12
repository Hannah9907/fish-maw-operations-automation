import re


HEAD_PATTERN = re.compile(
    r"^(?P<heads>\d+(?:\.\d+)?)头"
    r"(?P<product>[^/【\[\]]+?)"
    r"/(?P<weight>\d+(?:\.\d+)?)g"
    r"(?:/(?P<qty>\d+(?:\.\d+)?)个)?"
    r"(?:[【\[](?P<amount>\d+(?:\.\d+)?)[】\]])?"
    r"(?:\s*(?P<extra>.+))?$"
)

NO_HEAD_PATTERN = re.compile(
    r"^(?P<product>[^/【\[\]]+?)"
    r"/(?P<weight>\d+(?:\.\d+)?)g"
    r"(?:/(?P<qty>\d+(?:\.\d+)?)个)?"
    r"(?:[【\[](?P<amount>\d+(?:\.\d+)?)[】\]])?"
    r"(?:\s*(?P<extra>.+))?$"
)


def clean_text(text: str) -> str:
    """Clean order remark text before parsing."""
    if not text:
        return ""

    text = text.replace("\r", "")
    text = text.replace("\n", "")
    text = text.replace("｜", "|")
    text = text.replace("／", "/")
    text = text.replace("【 ", "【").replace(" 】", "】")
    text = re.sub(r"\s*/\s*", "/", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def to_number(value):
    if value is None or value == "":
        return None
    number = float(value)
    if number.is_integer():
        return int(number)
    return number


def parse_line(line: str, item_no: int) -> dict:
    """Parse one product line."""
    raw_line = line.strip()

    match = HEAD_PATTERN.match(raw_line)
    has_head = True

    if not match:
        match = NO_HEAD_PATTERN.match(raw_line)
        has_head = False

    if not match:
        return {
            "item_no": item_no,
            "raw_line_text": raw_line,
            "display_name": None,
            "product_name": None,
            "spec_qty_per_500g": None,
            "sold_weight_g": None,
            "sold_qty": None,
            "marked_line_amount": None,
            "extra_note": None,
            "parse_status": "失败",
        }

    data = match.groupdict()
    product_name = data.get("product", "").strip()
    heads = to_number(data.get("heads")) if has_head else None
    sold_weight_g = to_number(data.get("weight"))
    sold_qty = to_number(data.get("qty"))
    amount = to_number(data.get("amount"))
    extra = data.get("extra")

    if extra:
        extra = extra.strip()
    else:
        extra = None

    if has_head:
        display_name = f"{heads}头{product_name}"
    else:
        display_name = product_name

    return {
        "item_no": item_no,
        "raw_line_text": raw_line,
        "display_name": display_name,
        "product_name": product_name,
        "spec_qty_per_500g": heads,
        "sold_weight_g": sold_weight_g,
        "sold_qty": sold_qty,
        "marked_line_amount": amount,
        "extra_note": extra,
        "parse_status": "成功",
    }


def parse_remark(remark: str) -> list[dict]:
    """Parse a full order remark into product lines."""
    cleaned = clean_text(remark)

    if not cleaned:
        return []

    parts = [part.strip() for part in cleaned.split("|") if part.strip()]
    return [parse_line(part, index) for index, part in enumerate(parts, start=1)]
