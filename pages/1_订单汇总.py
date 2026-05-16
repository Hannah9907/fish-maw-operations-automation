import pandas as pd
import streamlit as st

from state_utils import (
    ORDER_COLUMNS,
    get_sample_orders_upload_df,
    append_order_rows,
    init_session_state,
    load_sample_orders,
    parse_order_to_rows,
    to_excel_bytes,
)


st.set_page_config(page_title="订单汇总", page_icon="🧾", layout="wide")
init_session_state()

# 页面样式微调：
# 1. 放大 Tab 标题：手动录入 / 批量上传
# 2. 缩小 Tab 内部小标题：复制粘贴订单备注 / 上传订单文件
st.markdown(
    """
    <style>
    button[data-baseweb="tab"] p {
        font-size: 20px !important;
        font-weight: 600 !important;
    }

    .section-small-title {
        font-size: 18px;
        font-weight: 600;
        margin-top: 0.75rem;
        margin-bottom: 1rem;
        color: #31333F;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🧾 订单汇总")
st.caption("将订单备注解析为结构化订单数据，并统一保存到订单数据表。")

st.divider()

st.subheader("快速体验")
st.write("第一次打开网站时，可以先加载一组示例订单，直接测试订单解析和售后退款流程。")

col_sample_load, col_sample_download = st.columns([1, 5])

with col_sample_load:
    if st.button("加载示例订单", type="primary"):
        inserted_count = load_sample_orders()
        if inserted_count:
            st.success(f"已加载 {inserted_count} 条示例商品记录。")
        else:
            st.info("示例订单已经在数据表里了。")

with col_sample_download:
    sample_orders_df = get_sample_orders_upload_df()
    sample_excel_data = to_excel_bytes(sample_orders_df, sheet_name="sample_orders")
    st.download_button(
        label="下载示例订单 Excel",
        data=sample_excel_data,
        file_name="fish_maw_sample_orders.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

st.divider()

tab_manual, tab_upload = st.tabs(["手动录入", "批量上传"])

with tab_manual:
    st.markdown(
        '<div class="section-small-title">复制粘贴订单备注</div>',
        unsafe_allow_html=True,
    )

    with st.form("manual_order_form", enter_to_submit=False):
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            order_id = st.text_input("订单号", placeholder="例如：DD001")

        with col2:
            buyer_paid_amount = st.number_input("买家实付金额(¥)", min_value=0.0, value=0.0, step=1.0)

        with col3:
            platform_subsidy_amount = st.number_input("平台补贴金额(¥)", min_value=0.0, value=0.0, step=1.0)

        with col4:
            merchant_receivable_amount = st.number_input("商家初始到手金额(¥)", min_value=0.0, value=0.0, step=1.0)

        remark_text = st.text_area(
            "订单备注",
            value="",
            placeholder="粘贴订单备注，多个商品请用 | 分隔",
            height=120,
            help=(
                "支持格式：\n"
                "1. 有具体规格：10头赤嘴母胶/350g/7个【2030】\n"
                "2. 无具体规格：特选珍珠川贝/50g【470】\n"
                "3. 多商品：用 | 分隔\n"
                "4. 附加说明：10.8头土鳘公胶/510g/11个 纸皮筒"
            ),
        )

        submitted = st.form_submit_button("解析并加入订单数据表", type="primary")

    if submitted:
        if not remark_text.strip():
            st.warning("请先输入订单备注。")
        else:
            if not order_id.strip():
                order_id = f"MANUAL-{len(st.session_state['order_items_df']) + 1:03d}"

            new_rows = parse_order_to_rows(
                order_id=order_id,
                remark_text=remark_text,
                buyer_paid_amount=buyer_paid_amount,
                platform_subsidy_amount=platform_subsidy_amount,
                merchant_receivable_amount=merchant_receivable_amount,
            )
            append_order_rows(new_rows)
            st.success(f"已加入 {len(new_rows)} 条商品记录。")

with tab_upload:
    st.markdown(
        '<div class="section-small-title">上传订单文件</div>',
        unsafe_allow_html=True,
    )

    uploaded_file = st.file_uploader(
        "上传订单文件（CSV 或 Excel）",
        type=["csv", "xlsx"],
        label_visibility="collapsed",
        help="文件至少需要包含订单备注列；如果有订单号、买家实付、平台补贴和商家到手金额，也可以一起选择。",
    )

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".csv"):
                uploaded_df = pd.read_csv(uploaded_file)
            else:
                uploaded_df = pd.read_excel(uploaded_file)

            st.markdown("#### 原始订单数据预览")
            st.dataframe(uploaded_df.head(10), use_container_width=True, hide_index=True)

            if uploaded_df.empty:
                st.warning("上传的文件没有数据。")
            else:
                columns = list(uploaded_df.columns)
                optional_columns = ["不使用"] + columns

                col1, col2 = st.columns(2)
                with col1:
                    remark_column = st.selectbox("订单备注所在列", options=columns)
                    order_id_column = st.selectbox("订单号所在列", options=optional_columns)

                with col2:
                    buyer_paid_column = st.selectbox("买家实付金额所在列", options=optional_columns)
                    platform_subsidy_column = st.selectbox("平台补贴金额所在列", options=optional_columns)
                    merchant_receivable_column = st.selectbox("商家初始到手金额所在列", options=optional_columns)

                if st.button("解析并加入订单数据表", type="primary"):
                    all_rows = []

                    for row_index, row in uploaded_df.iterrows():
                        order_id = (
                            row.get(order_id_column)
                            if order_id_column != "不使用"
                            else f"UPLOAD-{row_index + 1:03d}"
                        )
                        buyer_paid_amount = row.get(buyer_paid_column) if buyer_paid_column != "不使用" else None
                        platform_subsidy_amount = row.get(platform_subsidy_column) if platform_subsidy_column != "不使用" else None
                        merchant_receivable_amount = row.get(merchant_receivable_column) if merchant_receivable_column != "不使用" else None

                        rows = parse_order_to_rows(
                            order_id=order_id,
                            remark_text=row.get(remark_column),
                            buyer_paid_amount=buyer_paid_amount,
                            platform_subsidy_amount=platform_subsidy_amount,
                            merchant_receivable_amount=merchant_receivable_amount,
                        )
                        all_rows.append(rows)

                    if all_rows:
                        new_rows_df = pd.concat(all_rows, ignore_index=True)
                        append_order_rows(new_rows_df)
                        st.success(f"已加入 {len(new_rows_df)} 条商品记录。")

        except Exception as error:
            st.error(f"文件处理失败：{error}")

st.divider()

st.subheader("订单数据表")

order_df = st.session_state["order_items_df"].copy()

if order_df.empty:
    st.info("当前还没有订单数据。你可以先手动录入订单备注，或批量上传订单文件。")
else:
    edited_df = st.data_editor(
        order_df,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_order=ORDER_COLUMNS,
    )
    st.session_state["order_items_df"] = edited_df

    col_download, col_clear = st.columns([1, 5])

    with col_download:
        excel_data = to_excel_bytes(edited_df, sheet_name="order_items")
        st.download_button(
            label="下载订单数据 Excel",
            data=excel_data,
            file_name="fish_maw_order_items.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    with col_clear:
        if st.button("清空订单数据"):
            st.session_state["order_items_df"] = pd.DataFrame(columns=ORDER_COLUMNS)
            st.rerun()
