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

SAMPLE_ORDER_INPUTS = [
    {
        "订单号": "DEMO-001",
        "订单备注": "10头赤嘴母胶/350g/7个【2030】\n特选珍珠川贝/50g【470】",
        "买家实付金额(¥)": 2500,
        "平台补贴金额(¥)": 120,
        "商家初始到手金额(¥)": 2380,
    },
    {
        "订单号": "DEMO-002",
        "订单备注": "10.8头土鳘公胶/510g/11个【3880】 纸皮筒",
        "买家实付金额(¥)": 3880,
        "平台补贴金额(¥)": 180,
        "商家初始到手金额(¥)": 3700,
    },
    {
        "订单号": "DEMO-003",
        "订单备注": "12头北海公胶/420克/10个【2680】|特选珍珠川贝/80G【720】",
        "买家实付金额(¥)": 3400,
        "平台补贴金额(¥)": 160,
        "商家初始到手金额(¥)": 3240,
    },
]

SAMPLE_INVENTORY_INPUTS = [
    {
        "批次号": "DEMO-B20260501-0001",
        "展示名称": "10头赤嘴母胶",
        "进货日期": "2026-05-01",
        "进货总重(g)": 2500,
        "初始个数": 50,
        "初始成本(¥/500g)": 1680,
        "当前个数": 38,
        "最近复称重量(g)": 1840,
        "批次状态": "在库",
    },
    {
        "批次号": "DEMO-B20260503-0002",
        "展示名称": "10.8头土鳘公胶",
        "进货日期": "2026-05-03",
        "进货总重(g)": 5100,
        "初始个数": 110,
        "初始成本(¥/500g)": 3050,
        "当前个数": 82,
        "最近复称重量(g)": 3715,
        "批次状态": "在库",
    },
    {
        "批次号": "DEMO-B20260508-0003",
        "展示名称": "12头北海公胶",
        "进货日期": "2026-05-08",
        "进货总重(g)": 4200,
        "初始个数": 100,
        "初始成本(¥/500g)": 2180,
        "当前个数": 24,
        "最近复称重量(g)": 995,
        "批次状态": "在库",
    },
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


def get_sample_orders_upload_df() -> pd.DataFrame:
    return pd.DataFrame(SAMPLE_ORDER_INPUTS)


def build_sample_order_rows() -> pd.DataFrame:
    sample_rows = []

    for order in SAMPLE_ORDER_INPUTS:
        sample_rows.append(
            parse_order_to_rows(
                order_id=order["订单号"],
                remark_text=order["订单备注"],
                buyer_paid_amount=order["买家实付金额(¥)"],
                platform_subsidy_amount=order["平台补贴金额(¥)"],
                merchant_receivable_amount=order["商家初始到手金额(¥)"],
            )
        )

    return pd.concat(sample_rows, ignore_index=True)


def load_sample_orders():
    sample_df = build_sample_order_rows()
    current_df = st.session_state["order_items_df"]
    current_ids = set(current_df["订单号"].astype(str)) if not current_df.empty else set()
    new_rows = sample_df[~sample_df["订单号"].astype(str).isin(current_ids)]

    if new_rows.empty:
        return 0

    append_order_rows(new_rows)
    return len(new_rows)


def build_sample_inventory_df() -> pd.DataFrame:
    inventory_df = pd.DataFrame(SAMPLE_INVENTORY_INPUTS)

    for column in INVENTORY_COLUMNS:
        if column not in inventory_df.columns:
            inventory_df[column] = None

    return recalculate_inventory_df(inventory_df[INVENTORY_COLUMNS])


def get_sample_inventory_upload_df() -> pd.DataFrame:
    return build_sample_inventory_df()


def load_sample_inventory():
    sample_df = build_sample_inventory_df()
    current_df = st.session_state["inventory_df"]
    current_ids = set(current_df["批次号"].astype(str)) if not current_df.empty else set()
    new_rows = sample_df[~sample_df["批次号"].astype(str).isin(current_ids)]

    if new_rows.empty:
        return 0

    st.session_state["inventory_df"] = recalculate_inventory_df(
        pd.concat([current_df, new_rows], ignore_index=True)
    )
    return len(new_rows)


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
            values = [
                row.get("进货总重(g)"),
                row.get("初始个数"),
                row.get("初始成本(¥/500g)"),
                row.get("当前个数"),
                row.get("最近复称重量(g)"),
            ]

            if any(pd.isna(value) for value in values):
                raise ValueError("missing inventory value")

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
