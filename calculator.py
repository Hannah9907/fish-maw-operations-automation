def to_float(value, default=0.0):
    """Safely convert value to float."""
    if value is None or value == "":
        return default

    try:
        if value != value:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def get_total_marked_amount(parsed_lines: list[dict]) -> float:
    """Calculate the total amount written in remark brackets."""
    return sum(to_float(line.get("marked_line_amount")) for line in parsed_lines)


def calculate_line_amounts(
    selected_line: dict,
    parsed_lines: list[dict],
    buyer_paid_amount: float,
    platform_subsidy_amount: float,
    merchant_receivable_amount: float,
) -> dict:
    """Allocate order-level amounts to a selected product."""
    total_lines = len(parsed_lines)
    marked_line_amount = to_float(selected_line.get("marked_line_amount"))
    total_marked_amount = get_total_marked_amount(parsed_lines)

    if marked_line_amount > 0 and total_marked_amount > 0:
        allocation_ratio = marked_line_amount / total_marked_amount
        allocation_method = "按备注金额比例分摊"
    elif total_lines == 1:
        allocation_ratio = 1.0
        allocation_method = "单商品订单，默认整单金额归属于该商品"
    else:
        return {
            "can_calculate": False,
            "allocation_method": "无法自动分摊：多商品订单缺少备注金额",
        }

    return {
        "can_calculate": True,
        "allocation_method": allocation_method,
        "allocation_ratio": allocation_ratio,
        "refund_basis_line_amount": buyer_paid_amount * allocation_ratio,
        "platform_subsidy_line_amount": platform_subsidy_amount * allocation_ratio,
        "merchant_receivable_line_amount": merchant_receivable_amount * allocation_ratio,
    }


def calculate_refund(
    selected_line: dict,
    parsed_lines: list[dict],
    buyer_paid_amount: float,
    platform_subsidy_amount: float,
    merchant_receivable_amount: float,
    actual_return_weight_g: float,
) -> dict:
    """Calculate partial refund based on actual returned weight."""
    sold_weight_g = to_float(selected_line.get("sold_weight_g"))

    if sold_weight_g <= 0:
        return {"can_calculate": False, "error": "销售总重必须大于 0，无法计算退款。"}

    if actual_return_weight_g <= 0:
        return {"can_calculate": False, "error": "实际退回重量必须大于 0。"}

    if actual_return_weight_g > sold_weight_g:
        return {"can_calculate": False, "error": "实际退回重量不能大于该商品销售总重。"}

    line_amounts = calculate_line_amounts(
        selected_line=selected_line,
        parsed_lines=parsed_lines,
        buyer_paid_amount=buyer_paid_amount,
        platform_subsidy_amount=platform_subsidy_amount,
        merchant_receivable_amount=merchant_receivable_amount,
    )

    if not line_amounts.get("can_calculate"):
        return {"can_calculate": False, "error": line_amounts.get("allocation_method")}

    return_ratio = actual_return_weight_g / sold_weight_g

    refund_basis_line_amount = line_amounts["refund_basis_line_amount"]
    platform_subsidy_line_amount = line_amounts["platform_subsidy_line_amount"]
    merchant_receivable_line_amount = line_amounts["merchant_receivable_line_amount"]

    buyer_refund_amount = refund_basis_line_amount * return_ratio
    platform_subsidy_reversed_amount = platform_subsidy_line_amount * return_ratio

    merchant_net_kept_amount = (
        merchant_receivable_line_amount
        - buyer_refund_amount
        - platform_subsidy_reversed_amount
    )

    refund_price_per_g = refund_basis_line_amount / sold_weight_g

    return {
        "can_calculate": True,
        "allocation_method": line_amounts["allocation_method"],
        "return_ratio": return_ratio,
        "refund_basis_line_amount": refund_basis_line_amount,
        "platform_subsidy_line_amount": platform_subsidy_line_amount,
        "merchant_receivable_line_amount": merchant_receivable_line_amount,
        "refund_price_per_g": refund_price_per_g,
        "buyer_refund_amount": buyer_refund_amount,
        "platform_subsidy_reversed_amount": platform_subsidy_reversed_amount,
        "merchant_net_kept_amount": merchant_net_kept_amount,
    }
