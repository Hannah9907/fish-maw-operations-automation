from datetime import datetime

import pandas as pd
import streamlit as st

from calculator import calculate_refund
from state_utils import (
    AFTERSALE_COLUMNS,
    init_session_state,
    load_sample_orders,
    order_group_to_lines,
    order_row_to_line,
    to_excel_bytes,
)


st.set_page_config(page_title="售后退款计算", page_icon="↩️", layout="wide")
init_session_state()


def safe_number(value, default=0.0):
    if value is None or value == "":
        return default

    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


st.title("↩️ 售后退款计算")
st.caption("从订单数据表中搜索并选择退款商品，计算买家退款、平台补贴冲回和商家净留存。")

order_df = st.session_state["order_items_df"].copy()

if order_df.empty:
    st.info("当前还没有订单数据。请先进入“订单汇总”页面录入或上传订单数据。")
    col_load_sample, col_go_orders = st.columns([1, 5])

    with col_load_sample:
        if st.button("加载示例订单", type="primary"):
            load_sample_orders()
            st.rerun()

    with col_go_orders:
        st.page_link("pages/1_订单汇总.py", label="前往订单汇总", icon="🧾")
else:
    search_keyword = st.text_input(
        "搜索退款商品",
        placeholder="可按订单号、商品名称、头数或重量搜索，例如：DD001、赤嘴、10头、350g",
    )

    searchable_df = order_df[order_df["解析状态"] == "成功"].copy()

    if search_keyword:
        mask = searchable_df.astype(str).apply(
            lambda row: search_keyword.lower() in " ".join(row.values).lower(),
            axis=1,
        )
        searchable_df = searchable_df[mask]

    if searchable_df.empty:
        st.warning("没有找到匹配的商品。")
    else:
        option_map = {
            f"{idx}｜订单 {row.get('订单号')}｜{row.get('展示名称')}｜{row.get('销售总重(g)')}g": idx
            for idx, row in searchable_df.iterrows()
        }

        selected_label = st.selectbox("选择要退款的商品", options=list(option_map.keys()))
        selected_index = option_map[selected_label]
        selected_row = order_df.loc[selected_index]
        selected_key = f"{selected_row.get('订单号')}::{selected_row.get('序号')}::{selected_row.get('展示名称')}"

        same_order_df = order_df[
            (order_df["订单号"].astype(str) == str(selected_row.get("订单号")))
            & (order_df["解析状态"] == "成功")
        ]

        parsed_lines = order_group_to_lines(same_order_df)
        selected_line = order_row_to_line(selected_row)

        st.markdown("#### 订单金额")

        col1, col2, col3 = st.columns(3)

        default_buyer_paid = safe_number(selected_row.get("买家实付金额(¥)"))
        default_platform_subsidy = safe_number(selected_row.get("平台补贴金额(¥)"))
        default_merchant_receivable = safe_number(selected_row.get("商家初始到手金额(¥)"))

        with col1:
            buyer_paid_amount = st.number_input("买家实付金额(¥)", min_value=0.0, value=default_buyer_paid, step=1.0)

        with col2:
            platform_subsidy_amount = st.number_input("平台补贴金额(¥)", min_value=0.0, value=default_platform_subsidy, step=1.0)

        with col3:
            merchant_receivable_amount = st.number_input("商家初始到手金额(¥)", min_value=0.0, value=default_merchant_receivable, step=1.0)

        actual_return_weight_g = st.number_input(
            "实际退回重量(g)",
            min_value=0.0,
            value=safe_number(selected_row.get("销售总重(g)")) / 2,
            step=1.0,
        )

        if st.button("计算退款", type="primary"):
            result = calculate_refund(
                selected_line=selected_line,
                parsed_lines=parsed_lines,
                buyer_paid_amount=buyer_paid_amount,
                platform_subsidy_amount=platform_subsidy_amount,
                merchant_receivable_amount=merchant_receivable_amount,
                actual_return_weight_g=actual_return_weight_g,
            )

            if not result.get("can_calculate"):
                st.error(result.get("error", "无法计算退款。"))
            else:
                st.session_state["latest_refund_result"] = {
                    "selected_key": selected_key,
                    "selected_row": selected_row.to_dict(),
                    "actual_return_weight_g": actual_return_weight_g,
                    "result": result,
                }

        if (
            "latest_refund_result" in st.session_state
            and st.session_state["latest_refund_result"].get("selected_key") == selected_key
        ):
            latest = st.session_state["latest_refund_result"]
            result = latest["result"]
            selected_row_dict = latest["selected_row"]

            st.subheader("退款计算结果")

            metric1, metric2, metric3 = st.columns(3)

            with metric1:
                st.metric("买家退款金额", f"¥{result['buyer_refund_amount']:,.2f}")

            with metric2:
                st.metric("平台补贴冲回", f"¥{result['platform_subsidy_reversed_amount']:,.2f}")

            with metric3:
                st.metric("商家净留存", f"¥{result['merchant_net_kept_amount']:,.2f}")

            detail_df = pd.DataFrame(
                [
                    {"项目": "金额分摊方式", "结果": result["allocation_method"]},
                    {"项目": "退货比例", "结果": f"{result['return_ratio'] * 100:.2f}%"},
                    {"项目": "退款克价", "结果": f"¥{result['refund_price_per_g']:,.2f}/g"},
                ]
            )
            st.dataframe(detail_df, use_container_width=True, hide_index=True)

            if st.button("保存为售后记录"):
                record = {
                    "计算时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "订单号": selected_row_dict.get("订单号"),
                    "退款商品": selected_row_dict.get("展示名称"),
                    "销售总重(g)": selected_row_dict.get("销售总重(g)"),
                    "实际退回重量(g)": latest["actual_return_weight_g"],
                    "买家退款金额(¥)": round(result["buyer_refund_amount"], 2),
                    "平台补贴冲回(¥)": round(result["platform_subsidy_reversed_amount"], 2),
                    "商家净留存(¥)": round(result["merchant_net_kept_amount"], 2),
                }

                new_record_df = pd.DataFrame([record], columns=AFTERSALE_COLUMNS)
                st.session_state["aftersale_df"] = pd.concat(
                    [st.session_state["aftersale_df"], new_record_df],
                    ignore_index=True,
                )
                st.success("已保存售后记录。")

st.divider()

st.subheader("售后记录")

aftersale_df = st.session_state["aftersale_df"].copy()

if aftersale_df.empty:
    st.info("当前还没有售后记录。")
else:
    edited_aftersale_df = st.data_editor(
        aftersale_df,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
    )
    st.session_state["aftersale_df"] = edited_aftersale_df

    excel_data = to_excel_bytes(edited_aftersale_df, sheet_name="aftersales")
    st.download_button(
        label="下载售后记录 Excel",
        data=excel_data,
        file_name="fish_maw_aftersales.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
