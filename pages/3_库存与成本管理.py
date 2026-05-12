from datetime import date

import pandas as pd
import streamlit as st

from state_utils import (
    INVENTORY_COLUMNS,
    generate_batch_id,
    init_session_state,
    recalculate_inventory_df,
    to_excel_bytes,
)


st.set_page_config(page_title="库存与成本管理", page_icon="📦", layout="wide")
init_session_state()

st.title("📦 库存与成本管理")
st.caption("维护库存批次，并在可编辑表格中实时更新损耗率、当前折算头数和当前真实成本。")

st.divider()

st.subheader("新增库存批次")

with st.form("new_inventory_batch_form", enter_to_submit=False):
    col1, col2, col3 = st.columns(3)

    with col1:
        display_name = st.text_input("展示名称", placeholder="例如：11头马来斗湖胶")
        purchase_date = st.date_input("进货日期", value=date.today())

    with col2:
        purchase_weight_g = st.number_input("进货总重(g)", min_value=0.0, value=0.0, step=1.0)
        initial_piece_qty = st.number_input("初始个数", min_value=0.0, value=0.0, step=1.0)

    with col3:
        initial_cost_per_500g = st.number_input("初始成本(¥/500g)", min_value=0.0, value=0.0, step=1.0)
        batch_status = st.selectbox("批次状态", options=["在库", "售罄", "异常"])

    submitted = st.form_submit_button("新增批次", type="primary")

if submitted:
    if not display_name.strip():
        st.warning("请填写展示名称。")
    elif purchase_weight_g <= 0 or initial_piece_qty <= 0 or initial_cost_per_500g <= 0:
        st.warning("进货总重、初始个数和初始成本都必须大于 0。")
    else:
        batch_id = generate_batch_id(purchase_date)

        new_batch = pd.DataFrame(
            [
                {
                    "批次号": batch_id,
                    "展示名称": display_name,
                    "进货日期": str(purchase_date),
                    "进货总重(g)": purchase_weight_g,
                    "初始个数": initial_piece_qty,
                    "初始成本(¥/500g)": initial_cost_per_500g,
                    "当前个数": initial_piece_qty,
                    "最近复称重量(g)": purchase_weight_g,
                    "损耗重量(g)": None,
                    "损耗率": None,
                    "当前折算头数": None,
                    "当前真实成本(¥/500g)": None,
                    "批次状态": batch_status,
                }
            ],
            columns=INVENTORY_COLUMNS,
        )

        inventory_df = pd.concat(
            [st.session_state["inventory_df"], new_batch],
            ignore_index=True,
        )
        st.session_state["inventory_df"] = recalculate_inventory_df(inventory_df)
        st.success(f"已新增批次：{batch_id}")

st.divider()

st.subheader("库存数据表")

inventory_df = recalculate_inventory_df(st.session_state["inventory_df"])

if inventory_df.empty:
    st.info("当前还没有库存数据。请先新增一个库存批次。")
else:
    edited_inventory_df = st.data_editor(
        inventory_df,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_order=INVENTORY_COLUMNS,
        disabled=[
            "批次号",
            "损耗重量(g)",
            "损耗率",
            "当前折算头数",
            "当前真实成本(¥/500g)",
        ],
        column_config={
            "损耗率": st.column_config.NumberColumn("损耗率", format="%.2f%%"),
            "当前折算头数": st.column_config.NumberColumn("当前折算头数", format="%.1f"),
            "当前真实成本(¥/500g)": st.column_config.NumberColumn("当前真实成本(¥/500g)", format="¥%.2f"),
            "批次状态": st.column_config.SelectboxColumn(
                "批次状态",
                options=["在库", "售罄", "异常"],
            ),
        },
    )

    st.session_state["inventory_df"] = recalculate_inventory_df(edited_inventory_df)

    st.caption("提示：你可以直接在表格里修改“当前个数”和“最近复称重量(g)”，系统会自动更新损耗率、当前折算头数和真实成本。")

    col_download, col_clear = st.columns([1, 5])

    with col_download:
        excel_data = to_excel_bytes(st.session_state["inventory_df"], sheet_name="inventory")
        st.download_button(
            label="下载库存数据 Excel",
            data=excel_data,
            file_name="fish_maw_inventory.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    with col_clear:
        if st.button("清空库存数据"):
            st.session_state["inventory_df"] = pd.DataFrame(columns=INVENTORY_COLUMNS)
            st.rerun()
