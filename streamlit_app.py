import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

# --- 1. 配置与税务规则库 ---
st.set_page_config(page_title="全能记账助手 Pro", page_icon="⚖️", layout="wide")

# 标准税务科目列表
TAX_CATEGORIES = [
    "业务招待费", "差旅费", "办公费", "福利费", "职工薪酬", 
    "车辆使用费", "咨询/劳务费", "租赁费", "广宣费/佣金", 
    "主营业务成本", "财务费用", "其他支出/待分类"
]

# 智能识别规则
TAX_RULES = {
    "业务招待费": ["请客", "吃饭", "聚餐", "招待", "宴请", "烟酒", "礼品", "酒店住宿"],
    "差旅费": ["出差", "机票", "高铁", "火车", "住宿", "打车", "滴滴", "行程"],
    "办公费": ["纸", "笔", "复印", "耗材", "快递", "顺丰", "ERP", "订阅", "文具", "打印机"],
    "福利费": ["团建", "下午茶", "节日", "体检", "食堂", "外卖", "月饼"],
    "职工薪酬": ["工资", "奖金", "绩效", "社保", "公积金", "加班费"],
    "车辆使用费": ["加油", "停车", "洗车", "车险", "维修", "保养", "油费"],
    "咨询/劳务费": ["咨询", "法律", "财税", "VAT", "商标", "代理", "申报", "服务费"],
    "租赁费": ["房租", "租金", "物业", "仓库", "服务器", "AWS"],
    "广宣费/佣金": ["佣金", "广告", "Facebook", "投流", "网红", "推广", "流量"],
    "主营业务成本": ["采购", "进货", "货款", "头程", "运费", "物流", "入仓"],
    "财务费用": ["手续费", "结汇", "提现", "汇兑", "银行", "转账"]
}

def auto_map_tax(row_type, note_text):
    """自动识别税务科目"""
    if row_type == '收入':
        return "主营业务收入"
    full_text = str(note_text).lower()
    for tax_category, keywords in TAX_RULES.items():
        for keyword in keywords:
            if keyword.lower() in full_text:
                return tax_category
    return "其他支出/待分类"

# --- 2. 数据持久化 ---
DATA_FILE = "unified_ledger_v3.csv"

def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df['日期'] = pd.to_datetime(df['日期']).dt.date
        return df
    return pd.DataFrame(columns=['日期', '类型', '分类', '金额', '备注'])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

if 'data' not in st.session_state:
    st.session_state.data = load_data()

# --- 3. 侧边栏：录入数据 ---
with st.sidebar:
    st.title("💰 记账面板")
    app_mode = st.radio("当前模式", ["个人生活模式", "企业报税模式"])
    
    st.markdown("---")
    with st.form("add_form", clear_on_submit=True):
        date = st.date_input("日期", datetime.now().date())
        trans_type = st.selectbox("类型", ["支出", "收入"])
        
        amount = st.number_input("金额", min_value=0.0, step=1.0)
        note = st.text_input("备注 (系统将根据此项自动匹配)")
        
        # 预设分类逻辑
        if app_mode == "个人生活模式":
            personal_cats = ["餐饮", "交通", "购物", "娱乐", "居住", "医疗", "其他"] if trans_type == "支出" else ["工资", "理财", "兼职", "其他"]
            selected_cat = st.selectbox("选择生活分类", personal_cats)
        else:
            # 企业模式下，尝试先自动识别，用户也可以手动微调
            suggested_cat = auto_map_tax(trans_type, note)
            st.caption(f"💡 自动识别结果预览：{suggested_cat}")
            selected_cat = suggested_cat # 初始保存自动识别的结果
            
        if st.form_submit_button("保存账单"):
            final_cat = selected_cat if app_mode == "个人生活模式" else auto_map_tax(trans_type, note)
            new_row = pd.DataFrame([{
                '日期': date,
                '类型': trans_type,
                '分类': final_cat,
                '金额': amount,
                '备注': note
            }])
            st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
            save_data(st.session_state.data)
            st.toast(f"已存入：{final_cat}")

# --- 4. 主界面 ---
st.title(f"📊 {app_mode}工作台")

if not st.session_state.data.empty:
    # A. 核心数据汇总
    df = st.session_state.data
    income = df[df['类型'] == '收入']['金额'].sum()
    expense = df[df['类型'] == '支出']['金额'].sum()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("总收入", f"¥{income:,.2f}")
    m2.metric("总支出", f"¥{expense:,.2f}")
    m3.metric("本期盈余", f"¥{income - expense:,.2f}")

    # B. 核心功能区
    tab_manage, tab_analysis = st.tabs(["🗂️ 账单明细管理", "📈 数据分析图表"])

    with tab_manage:
        st.subheader("明细查看与修正")
        st.info("💡 技巧：如果 AI 识别分类错误，请直接点击下方的“分类”单元格，从下拉列表中选择正确的税务科目。修改后请记得点击“保存更改”。")
        
        # 配置编辑器的列属性
        all_possible_cats = list(set(TAX_CATEGORIES + ["餐饮", "交通", "购物", "娱乐", "居住", "医疗", "其他", "工资", "理财", "兼职", "主营业务收入"]))
        
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "日期": st.column_config.DateColumn("日期"),
                "类型": st.column_config.SelectboxColumn("类型", options=["支出", "收入"]),
                "分类": st.column_config.SelectboxColumn("分类 (可手动纠正)", options=all_possible_cats),
                "金额": st.column_config.NumberColumn("金额", format="¥%.2f"),
                "备注": st.column_config.TextColumn("备注/说明", width="large")
            }
        )
        
        if st.button("💾 保存所有修改（同步至图表）", type="primary"):
            st.session_state.data = edited_df
            save_data(edited_df)
            st.success("数据已成功更新，分析图表已同步！")
            st.rerun()

    with tab_analysis:
        analysis_df = st.session_state.data
        
        # 1. 收支趋势
        st.write("**收支变动趋势**")
        trend_fig = px.line(analysis_df.sort_values("日期"), x="日期", y="金额", color="类型", markers=True)
        st.plotly_chart(trend_fig, use_container_width=True)
        
        col_left, col_right = st.columns(2)
        
        with col_left:
            # 2. 支出分类分布 (这是你关注的核心)
            st.write(f"**{app_mode} - 支出构成**")
            exp_df = analysis_df[analysis_df['类型'] == '支出']
            if not exp_df.empty:
                # 直接使用“分类”列，这样你在管理页面修改的结果会立刻体现
                fig_pie = px.pie(exp_df, values='金额', names='分类', hole=0.4)
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.warning("暂无支出数据")

        with col_right:
            # 3. 收入来源分析
            st.write("**收入来源分析**")
            inc_df = analysis_df[analysis_df['类型'] == '收入']
            if not inc_df.empty:
                fig_inc = px.bar(inc_df.groupby("分类")["金额"].sum().reset_index(), x="分类", y="金额", color="分类")
                st.plotly_chart(fig_inc, use_container_width=True)
            else:
                st.warning("暂无收入数据")

    # C. 导出
    st.markdown("---")
    csv = st.session_state.data.to_csv(index=False).encode('utf-8-sig')
    st.download_button(f"📥 导出为 {app_mode} 报表", csv, f"ledger_{app_mode}.csv", "text/csv")

else:
    st.info("记录为空，请开始记账吧！")
