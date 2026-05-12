def calculate_inventory_cost(
    display_name: str,
    purchase_weight_g: float,
    initial_piece_qty: float,
    initial_cost_per_500g: float,
    current_piece_qty: float,
    latest_measured_weight_g: float,
) -> dict:
    """Calculate shrinkage-adjusted real cost for one inventory batch."""
    errors = []
    warnings = []

    if purchase_weight_g <= 0:
        errors.append("进货总重必须大于 0。")
    if initial_piece_qty <= 0:
        errors.append("初始个数必须大于 0。")
    if initial_cost_per_500g <= 0:
        errors.append("初始成本必须大于 0。")
    if current_piece_qty <= 0:
        errors.append("当前个数必须大于 0。")
    if latest_measured_weight_g <= 0:
        errors.append("最近复称重量必须大于 0。")

    if errors:
        return {"can_calculate": False, "errors": errors, "warnings": warnings}

    if current_piece_qty > initial_piece_qty:
        warnings.append("当前个数高于初始个数，请检查是否存在录入误差或回库未单独记录。")

    initial_cost_per_g = initial_cost_per_500g / 500
    initial_total_cost = purchase_weight_g * initial_cost_per_g

    theoretical_remaining_weight_g = purchase_weight_g * (current_piece_qty / initial_piece_qty)
    current_remaining_cost = theoretical_remaining_weight_g * initial_cost_per_g

    shrinkage_loss_g = theoretical_remaining_weight_g - latest_measured_weight_g
    shrinkage_rate = shrinkage_loss_g / theoretical_remaining_weight_g

    current_equiv_heads = current_piece_qty / latest_measured_weight_g * 500

    current_real_cost_per_g = current_remaining_cost / latest_measured_weight_g
    current_real_cost_per_500g = current_real_cost_per_g * 500

    if latest_measured_weight_g > theoretical_remaining_weight_g:
        warnings.append("实测重量高于理论剩余重量，可能存在称重误差、录入误差或盘盈。")

    return {
        "can_calculate": True,
        "display_name": display_name,
        "initial_cost_per_g": initial_cost_per_g,
        "initial_total_cost": initial_total_cost,
        "theoretical_remaining_weight_g": theoretical_remaining_weight_g,
        "current_remaining_cost": current_remaining_cost,
        "shrinkage_loss_g": shrinkage_loss_g,
        "shrinkage_rate": shrinkage_rate,
        "current_equiv_heads": current_equiv_heads,
        "current_real_cost_per_g": current_real_cost_per_g,
        "current_real_cost_per_500g": current_real_cost_per_500g,
        "warnings": warnings,
    }
