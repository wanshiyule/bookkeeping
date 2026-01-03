import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

# --- 页面配置 ---
st.set_page_config(page_title="简约记账本", page_icon="💰", layout="wide")

# --- 数据持久化逻辑 ---
DATA_FILE = "ledger.csv"

def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df['日期'] = pd.to_datetime(df['日期'])
        return df
    else:
        return pd.DataFrame(columns=['日期', '类型', '分类', '金额', '备注'])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# 初始化数据
if 'data' not in st.session_state:
    st.session_state.data = load_data()

# --- 侧边栏：输入区域 ---
st.sidebar.header("新增记录")
with st.sidebar.form("add_record_form", clear_on_submit=True):
    date = st.date_input("日期", datetime.now())
    trans_type = st.selectbox("类型", ["支出", "收入"])
    
    # 动态分类
    expense_cats = ["餐饮", "交通", "购物", "娱乐", "居住", "医疗", "其他"]
    income_cats = ["工资", "理财", "兼职", "奖金", "其他"]
    category = st.selectbox("分类", expense_cats if trans_type == "支出" else income_cats)
    
    amount = st.number_input("金额", min_value=0.0, step=0.1, format="%.2f")
    note = st.text_input("备注")
    
    submit = st.form_submit_button("保存记录")

if submit:
    new_record = {
        '日期': pd.to_datetime(date),
        '类型': trans_type,
        '分类': category,
        '金额': amount,
        '备注': note
    }
    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_record])], ignore_index=True)
    save_data(st.session_state.data)
    st.sidebar.success("记录已保存！")

# --- 主界面 ---
st.title("💰 我的个人财务看板")

# 数据处理
df = st.session_state.data

if not df.empty:
    # 顶部指标
    total_income = df[df['类型'] == '收入']['金额'].sum()
    total_expense = df[df['类型'] == '支出']['金额'].sum()
    balance = total_income - total_expense

    col1, col2, col3 = st.columns(3)
    col1.metric("总收入", f"¥{total_income:,.2f}", delta_color="normal")
    col2.metric("总支出", f"¥{total_expense:,.2f}", delta_color="inverse")
    col3.metric("当前余额", f"¥{balance:,.2f}")

    st.markdown("---")

    # 图表分析展示区
    tab1, tab2, tab3 = st.tabs(["收支趋势", "支出分布", "明细数据"])

    with tab1:
        st.subheader("每日收支趋势")
        # 按日期汇总
        trend_df = df.groupby(['日期', '类型'])['金额'].sum().reset_index()
        fig_trend = px.line(trend_df, x='日期', y='金额', color='类型',
                           line_shape="spline", markers=True,
                           color_discrete_map={"收入": "#2ecc71", "支出": "#e74c3c"})
        st.plotly_chart(fig_trend, use_container_width=True)

    with tab2:
        st.subheader("支出构成分析")
        expense_df = df[df['类型'] == '支出']
        if not expense_df.empty:
            fig_pie = px.pie(expense_df, values='金额', names='分类', 
                            hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("暂无支出数据可分析")

    with tab3:
        st.subheader("历史明细")
        # 提供删除功能
        edited_df = st.data_editor(
            df.sort_values(by='日期', ascending=False),
            use_container_width=True,
            num_rows="dynamic"
        )
        if st.button("更新修改"):
            st.session_state.data = edited_df
            save_data(edited_df)
            st.rerun()

    # 导出 CSV 按钮
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="导出数据为 CSV",
        data=csv,
        file_name=f'ledger_{datetime.now().strftime("%Y%m%d")}.csv',
        mime='text/csv',
    )
else:
    st.info("欢迎使用记账工具！请在左侧侧边栏添加你的第一笔记录。")

# --- 底部 ---
st.markdown("---")
st.caption("由 Streamlit 驱动 | 数据存储于本地 ledger.csv")