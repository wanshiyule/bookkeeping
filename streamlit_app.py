import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

# --- 1. 配置与税务规则库 ---
st.set_page_config(page_title="全能记账助手 Pro", page_icon="⚖️", layout="wide")

TAX_RULES = {
    "业务招待费": ["请客", "吃饭", "聚餐", "招待", "宴请", "烟酒", "礼品", "酒店住宿"],
    "差旅费": ["出差", "机票", "高铁", "火车", "住宿", "打车", "滴滴", "行程"],
    "办公费": ["纸", "笔", "复印", "耗材", "快递", "顺丰", "ERP", "订阅", "文具", "打印机"],
    "福利费": ["团建", "下午茶", "节日", "体检", "食堂", "外卖", "月饼", "奶茶"],
    "职工薪酬": ["工资", "奖金", "绩效", "社保", "公积金", "加班费"],
    "车辆使用费": ["加油", "停车", "洗车", "车险", "维修", "保养", "油费"],
    "咨询/劳务费": ["咨询", "法律", "财税", "VAT", "商标", "代理", "申报", "服务费"],
    "租赁费": ["房租", "租金", "物业", "仓库", "服务器", "AWS"],
    "广宣费/佣金": ["佣金", "广告", "Facebook", "投流", "网红", "推广", "流量"],
    "主营业务成本": ["采购", "进货", "货款", "头程", "运费", "物流", "入仓"],
    "财务费用": ["手续费", "结汇", "提现", "汇兑", "银行", "转账"]
}

def map_tax_category(row_type, note_text):
    if row_type == '收入':
        return "主营业务收入"
    full_text = str(note_text).lower()
    for tax_category, keywords in TAX_RULES.items():
        for keyword in keywords:
            if keyword.lower() in full_text:
                return tax_category
    return "其他支出/待分类"

# --- 2. 数据持久化 ---
DATA_FILE = "unified_ledger_v2.csv"

def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df['日期'] = pd.to_datetime(df['日期']).dt.date # 保持日期格式简洁
        return df
    return pd.DataFrame(columns=['日期', '类型', '显示分类', '金额', '备注'])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

if 'data' not in st.session_state:
    st.session_state.data = load_data()

# --- 3. 侧边栏：录入数据 ---
with st.sidebar:
    st.title("💰 快速记账")
    app_mode = st.radio("当前视图模式", ["个人生活模式", "企业报税模式"])
    
    st.markdown("---")
    with st.form("add_form", clear_on_submit=True):
        date = st.date_input("日期", datetime.now().date())
        trans_type = st.selectbox("类型", ["支出", "收入"])
        
        if app_mode == "个人生活模式":
            cats = ["餐饮", "交通", "购物", "娱乐", "居住", "医疗", "其他"] if trans_type == "支出" else ["工资", "理财", "兼职", "其他"]
            display_cat = st.selectbox("分类", cats)
        else:
            display_cat = "系统自动识别"
            
        amount = st.number_input("金额", min_value=0.0, step=1.0)
        note = st.text_input("备注/说明")
        
        if st.form_submit_button("保存账单"):
            new_row = pd.DataFrame([{
                '日期': date,
                '类型': trans_type,
                '显示分类': display_cat,
                '金额': amount,
                '备注': note
            }])
            st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
            save_data(st.session_state.data)
            st.toast("已保存记录！")

# --- 4. 主界面 ---
st.title(f"📊 {app_mode}")

if not st.session_state.data.empty:
    # A. 数据仪表盘
    income = st.session_state.data[st.session_state.data['类型'] == '收入']['金额'].sum()
    expense = st.session_state.data[st.session_state.data['类型'] == '支出']['金额'].sum()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("总收入", f"¥{income:,.2f}")
    m2.metric("总支出", f"¥{expense:,.2f}", delta=f"-{expense:,.2f}", delta_color="inverse")
    m3.metric("结余", f"¥{income - expense:,.2f}")

    # B. 核心管理区：修改与删除
    st.markdown("---")
    tab_manage, tab_analysis = st.tabs(["🗂️ 账单管理 (可编辑/删除)", "📈 可视化分析"])

    with tab_manage:
        st.subheader("历史明细")
        st.caption("💡 提示：你可以直接点击单元格修改内容；点击左侧多选框后按 Delete 键或点击下方的删除图标即可删除记录。")
        
        # 使用 data_editor 实现编辑和删除
        edited_df = st.data_editor(
            st.session_state.data,
            use_container_width=True,
            num_rows="dynamic", # 允许动态增减行
            column_config={
                "日期": st.column_config.DateColumn("日期"),
                "类型": st.column_config.SelectboxColumn("类型", options=["支出", "收入"]),
                "金额": st.column_config.NumberColumn("金额", format="¥%.2f"),
                "备注": st.column_config.TextColumn("备注/说明", width="large")
            }
        )
        
        # 如果数据发生变化，保存
        if st.button("💾 保存所有更改", type="primary"):
            st.session_state.data = edited_df
            save_data(edited_df)
            st.success("更改已持久化到系统！")
            st.rerun()

    with tab_analysis:
        if app_mode == "企业报税模式":
            analysis_df = st.session_state.data.copy()
            analysis_df['税务科目'] = analysis_df.apply(lambda x: map_tax_category(x['类型'], x['备注']), axis=1)
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.write("**税务科目分布**")
                exp_df = analysis_df[analysis_df['类型'] == '支出']
                fig = px.pie(exp_df, values='金额', names='税务科目', hole=0.3)
                st.plotly_chart(fig, use_container_width=True)
            with col_b:
                st.write("**税务报表预览**")
                st.dataframe(analysis_df[['日期', '税务科目', '金额', '备注']], height=300)
        else:
            fig = px.line(st.session_state.data.sort_values("日期"), x="日期", y="金额", color="类型", markers=True)
            st.plotly_chart(fig, use_container_width=True)

    # C. 导出
    csv = st.session_state.data.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 导出当前数据 (CSV)", csv, "ledger_backup.csv", "text/csv")

else:
    st.info("还没有任何账单记录，请从左侧开始记账吧！")
