from datetime import date
from io import BytesIO

import pandas as pd
import streamlit as st

from parser import parse_remark
from inventory import calculate_inventory_cost


ORDER_COLUMNS = [
    "订单号",
    "序号",
    "原始备注",
    "展示名称",
    "商品名称",
    "规格头数",
    "销售总重(g)",
    "销售个数",
    "备注金额(¥)",
    "附加说明",
    "解析状态",
    "买家实付金额(¥)",
    "平台补贴金额(¥)",
    "商家初始到手金额(¥)",
]

AFTERSALE_COLUMNS = [
    "计算时间",
    "订单号",
    "退款商品",
    "销售总重(g)",
    "实际退回重量(g)",
    "买家退款金额(¥)",
    "平台补贴冲回(¥)",
    "商家净留存(¥)",
]

INVENTORY_COLUMNS = [
    "批次号",
    "展示名称",
    "进货日期",
    "进货总重(g)",
    "初始个数",
    "初始成本(¥/500g)",
    "当前个数",
    "最近复称重量(g)",
    "损耗重量(g)",
    "损耗率",
    "当前折算头数",
    "当前真实成本(¥/500g)",
    "批次状态",
]


def init_session_state():
    if "order_items_df" not in st.session_state:
        st.session_state["order_items_df"] = pd.DataFrame(columns=ORDER_COLUMNS)

    if "aftersale_df" not in st.session_state:
        st.session_state["aftersale_df"] = pd.DataFrame(columns=AFTERSALE_COLUMNS)

    if "inventory_df" not in st.session_state:
        st.session_state["inventory_df"] = pd.DataFrame(columns=INVENTORY_COLUMNS)

    if "batch_counter" not in st.session_state:
        st.session_state["batch_counter"] = 1


def to_excel_bytes(df: pd.DataFrame, sheet_name: str) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()


def parse_order_to_rows(
    order_id,
    remark_text,
    buyer_paid_amount=None,
    platform_subsidy_amount=None,
    merchant_receivable_amount=None,
) -> pd.DataFrame:
    if pd.isna(remark_text):
        remark_text = ""

    parsed_lines = parse_remark(str(remark_text))
    rows = []

    if not parsed_lines:
        rows.append(
            {
                "订单号": order_id,
                "序号": None,
                "原始备注": remark_text,
                "展示名称": None,
                "商品名称": None,
                "规格头数": None,
                "销售总重(g)": None,
                "销售个数": None,
                "备注金额(¥)": None,
                "附加说明": None,
                "解析状态": "失败",
                "买家实付金额(¥)": buyer_paid_amount,
                "平台补贴金额(¥)": platform_subsidy_amount,
                "商家初始到手金额(¥)": merchant_receivable_amount,
            }
        )
    else:
        for line in parsed_lines:
            rows.append(
                {
                    "订单号": order_id,
                    "序号": line.get("item_no"),
                    "原始备注": line.get("raw_line_text"),
                    "展示名称": line.get("display_name"),
                    "商品名称": line.get("product_name"),
                    "规格头数": line.get("spec_qty_per_500g"),
                    "销售总重(g)": line.get("sold_weight_g"),
                    "销售个数": line.get("sold_qty"),
                    "备注金额(¥)": line.get("marked_line_amount"),
                    "附加说明": line.get("extra_note"),
                    "解析状态": line.get("parse_status"),
                    "买家实付金额(¥)": buyer_paid_amount,
                    "平台补贴金额(¥)": platform_subsidy_amount,
                    "商家初始到手金额(¥)": merchant_receivable_amount,
                }
            )

    return pd.DataFrame(rows, columns=ORDER_COLUMNS)


def append_order_rows(new_rows: pd.DataFrame):
    if new_rows.empty:
        return

    current_df = st.session_state["order_items_df"]
    st.session_state["order_items_df"] = pd.concat(
        [current_df, new_rows],
        ignore_index=True,
    )


def order_row_to_line(row: pd.Series) -> dict:
    return {
        "item_no": row.get("序号"),
        "raw_line_text": row.get("原始备注"),
        "display_name": row.get("展示名称"),
        "product_name": row.get("商品名称"),
        "spec_qty_per_500g": row.get("规格头数"),
        "sold_weight_g": row.get("销售总重(g)"),
        "sold_qty": row.get("销售个数"),
        "marked_line_amount": row.get("备注金额(¥)"),
        "extra_note": row.get("附加说明"),
        "parse_status": row.get("解析状态"),
    }


def order_group_to_lines(order_df: pd.DataFrame) -> list[dict]:
    return [order_row_to_line(row) for _, row in order_df.iterrows()]


def generate_batch_id(purchase_date_value=None):
    if purchase_date_value:
        date_part = str(purchase_date_value).replace("-", "")[:8]
    else:
        date_part = date.today().strftime("%Y%m%d")

    batch_id = f"B{date_part}-{st.session_state['batch_counter']:04d}"
    st.session_state["batch_counter"] += 1
    return batch_id


def recalculate_inventory_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=INVENTORY_COLUMNS)

    df = df.copy()

    for column in INVENTORY_COLUMNS:
        if column not in df.columns:
            df[column] = None

    for idx, row in df.iterrows():
        try:
            result = calculate_inventory_cost(
                display_name=str(row.get("展示名称") or ""),
                purchase_weight_g=float(row.get("进货总重(g)") or 0),
                initial_piece_qty=float(row.get("初始个数") or 0),
                initial_cost_per_500g=float(row.get("初始成本(¥/500g)") or 0),
                current_piece_qty=float(row.get("当前个数") or 0),
                latest_measured_weight_g=float(row.get("最近复称重量(g)") or 0),
            )

            if result.get("can_calculate"):
                df.at[idx, "损耗重量(g)"] = round(result["shrinkage_loss_g"], 2)
                df.at[idx, "损耗率"] = round(result["shrinkage_rate"] * 100, 2)
                df.at[idx, "当前折算头数"] = round(result["current_equiv_heads"], 1)
                df.at[idx, "当前真实成本(¥/500g)"] = round(result["current_real_cost_per_500g"], 2)
            else:
                df.at[idx, "损耗重量(g)"] = None
                df.at[idx, "损耗率"] = None
                df.at[idx, "当前折算头数"] = None
                df.at[idx, "当前真实成本(¥/500g)"] = None
        except Exception:
            df.at[idx, "损耗重量(g)"] = None
            df.at[idx, "损耗率"] = None
            df.at[idx, "当前折算头数"] = None
            df.at[idx, "当前真实成本(¥/500g)"] = None

    return df[INVENTORY_COLUMNS]
