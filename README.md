# 鱼胶订单与成本自动化系统

这是一个基于 Streamlit 的鱼胶电商业务自动化原型，支持：

1. 订单汇总
2. 售后退款计算
3. 库存与成本管理
4. 业务规则说明

## 运行方法

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## 示例数据

进入“订单汇总”页面后，点击“加载示例订单”即可快速生成演示数据。也可以下载示例订单 Excel，用于测试批量上传流程。

进入“库存与成本管理”页面后，点击“加载示例库存”即可查看复称重量变化后的损耗率、当前折算头数和真实成本。

## 当前版本说明

当前版本使用 `st.session_state` 保存临时数据，适合作品集展示和面试演示。
正式产品化时，可以进一步接入数据库、用户登录和抖店 API。
