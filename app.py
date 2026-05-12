import streamlit as st

from state_utils import init_session_state


def system_intro_page():
    init_session_state()

    st.title("🐟 鱼胶订单与成本自动化系统")
    st.caption("Dried Fish Maw Operations Automation Prototype")

    st.markdown("""
这是一个面向鱼胶电商业务的自动化原型系统，目标是把依赖人工经验、订单备注和手工计算的流程，
转化为可结构化、可计算、可复核的数据流程。

当前版本用于作品集和业务原型展示，暂未接入抖店 API 或数据库。  
数据会临时保存在本次会话中，也可以通过 Excel 上传和下载进行模拟流转。
""")

    st.divider()

    st.subheader("功能模块")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 🧾 订单汇总")
        st.write("""
支持手动录入订单备注或批量上传订单文件，并自动解析为结构化订单数据。

适用场景：
- 单条订单备注解析
- 批量订单文件解析
- 订单数据表查看、编辑和下载
""")

    with col2:
        st.markdown("### ↩️ 售后退款计算")
        st.write("""
从订单数据表中搜索退款商品，并计算售后退款相关金额。

支持计算：
- 买家退款金额
- 平台补贴冲回金额
- 商家净留存金额
""")

    with col3:
        st.markdown("### 📦 库存与成本管理")
        st.write("""
维护鱼胶库存批次，并根据复称重量自动更新真实成本。

支持管理：
- 当前个数
- 最近复称重量
- 损耗重量
- 损耗率
- 当前折算头数
- 当前真实成本
""")

    st.divider()

    st.subheader("业务规则说明")

    with st.expander("订单备注解析规则", expanded=True):
        st.markdown("""
支持以下备注格式：

1. 有具体规格：`10头赤嘴母胶/350g/7个【2030】`
2. 无具体规格：`特选珍珠川贝/50g【470】`
3. 多商品：用 `|` 分隔
4. 附加说明：`10.8头土鳘公/510g/11个 纸皮筒`

系统会解析出：

- 展示名称
- 商品名称
- 规格头数
- 销售总重
- 销售个数
- 备注金额
- 附加说明
- 解析状态
""")

    with st.expander("售后退款计算规则"):
        st.markdown("""
售后退款拆成三条金额线：

- 买家退款金额
- 平台补贴冲回金额
- 商家净留存金额

当客户退回部分重量时：

- 买家退款按买家实付金额和退货比例计算
- 平台补贴按退货比例冲回
- 商家净留存 = 商家初始到手金额 - 买家退款金额 - 平台补贴冲回金额
""")

    with st.expander("库存与复称成本规则"):
        st.markdown("""
鱼胶属于干制品，库存可能因陈化、干湿度变化而掉秤。

系统按以下逻辑计算：

- 理论剩余重量 = 进货总重 × 当前个数 / 初始个数
- 损耗重量 = 理论剩余重量 - 最近复称重量
- 损耗率 = 损耗重量 / 理论剩余重量
- 当前折算头数 = 当前个数 / 最近复称重量 × 500
- 当前真实成本 = 当前剩余成本 / 最近复称重量 × 500

当最近复称重量变化时，系统会自动更新损耗率、当前折算头数和当前真实成本。
""")

    with st.expander("当前版本说明"):
        st.markdown("""
当前版本是作品集和业务原型展示版，暂未接入：

- 抖店 API
- 数据库
- 用户登录
- 权限系统

当前数据通过 `st.session_state` 临时保存在本次会话中。  
后续正式产品化时，可以升级为：

- Streamlit 前端
- 数据库持久化
- 用户登录与权限控制
- 抖店订单和售后 API 自动同步
""")

    st.divider()

    st.info("请从左侧侧边栏选择功能页面：系统介绍、订单汇总、售后退款计算、库存与成本管理。")


st.set_page_config(
    page_title="鱼胶订单与成本自动化系统",
    page_icon="🐟",
    layout="wide",
)

intro_page = st.Page(
    system_intro_page,
    title="系统介绍",
    icon="🐟",
    default=True,
)

orders_page = st.Page(
    "pages/1_订单汇总.py",
    title="订单汇总",
    icon="🧾",
)

refund_page = st.Page(
    "pages/2_售后退款计算.py",
    title="售后退款计算",
    icon="↩️",
)

inventory_page = st.Page(
    "pages/3_库存与成本管理.py",
    title="库存与成本管理",
    icon="📦",
)

pg = st.navigation(
    [
        intro_page,
        orders_page,
        refund_page,
        inventory_page,
    ],
    position="sidebar",
)

pg.run()
