import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
import io

# --- 1. 配置与税务规则库 (继承自昨天开发的企业版) ---
st.set_page_config(page_title="全能记账助手", page_icon="📊", layout="wide")

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

def map_tax_category(row_type, note_text):
    """智能税务科目映射逻辑"""
    if row_type == '收入':
        return "主营业务收入"
    full_text = str(note_text).lower()
    for tax_category, keywords in TAX_RULES.items():
        for keyword in keywords:
            if keyword.lower() in full_text:
                return tax_category
    return "其他支出/待分类"

# --- 2. 数据处理逻辑 ---
DATA_FILE = "unified_ledger.csv"

def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df['日期'] = pd.to_datetime(df['日期'])
        return df
    return pd.DataFrame(columns=['日期', '类型', '显示分类', '金额', '备注'])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

if 'data' not in st.session_state:
    st.session_state.data = load_data()

# --- 3. 侧边栏：功能切换与录入 ---
with st.sidebar:
    st.title("⚙️ 控制面板")
    app_mode = st.radio("选择运行模式", ["个人生活模式", "企业报税模式"], help="模式切换会影响分类逻辑和报表展示")
    
    st.markdown("---")
    st.subheader("📝 新增记录")
    with st.form("input_form", clear_on_submit=True):
        date = st.date_input("日期", datetime.now())
        trans_type = st.selectbox("类型", ["支出", "收入"])
        
        if app_mode == "个人生活模式":
            # 个人模式下手动选择生活分类
            cats = ["餐饮", "交通", "购物", "娱乐", "居住", "医疗", "其他"] if trans_type == "支出" else ["工资", "理财", "兼职", "其他"]
            display_cat = st.selectbox("生活分类", cats)
        else:
            # 企业模式下引导输入详细说明，由系统自动映射
            st.info("💡 系统将根据你的【备注】自动识别税务科目")
            display_cat = "系统自动识别"
            
        amount = st.number_input("金额", min_value=0.0, step=1.0)
        note = st.text_input("说明/备注 (如：请客户吃饭、发工资、买打印纸)")
        
        if st.form_submit_button("确认入账"):
            new_row = {
                '日期': pd.to_datetime(date),
                '类型': trans_type,
                '显示分类': display_cat,
                '金额': amount,
                '备注': note
            }
            st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
            save_data(st.session_state.data)
            st.success("入账成功！")

# --- 4. 主界面展示 ---
st.title(f"💰 {app_mode}")
df = st.session_state.data

if not df.empty:
    # 指标统计
    col1, col2, col3 = st.columns(3)
    income = df[df['类型'] == '收入']['金额'].sum()
    expense = df[df['类型'] == '支出']['金额'].sum()
    col1.metric("累计收入", f"¥{income:,.2f}")
    col2.metric("累计支出", f"¥{expense:,.2f}")
    col3.metric("当前结余", f"¥{income - expense:,.2f}")

    # 核心：根据模式展示不同的视图
    if app_mode == "企业报税模式":
        st.subheader("📑 企业税务科目明细 (AI 自动分类)")
        view_df = df.copy()
        # 应用昨天的智能映射逻辑
        view_df['税务科目'] = view_df.apply(lambda x: map_tax_category(x['类型'], x['备注']), axis=1)
        # 重新排序列，让税务科目更显眼
        display_cols = ['日期', '税务科目', '类型', '金额', '备注']
        st.dataframe(view_df[display_cols].sort_values(by='日期', ascending=False), use_container_width=True)
        
        # 企业模式特有的饼图：按税务科目分布
        st.subheader("📊 税务支出构成")
        expense_df = view_df[view_df['类型'] == '支出']
        fig = px.pie(expense_df, values='金额', names='税务科目', hole=0.4)
        st.plotly_chart(fig, use_container_width=True)
        
    else:
        st.subheader("📅 个人生活账单明细")
        st.dataframe(df.sort_values(by='日期', ascending=False), use_container_width=True)
        
        # 个人模式图表：按生活分类
        st.subheader("📊 生活消费支出分布")
        expense_df = df[(df['类型'] == '支出') & (df['显示分类'] != '系统自动识别')]
        if not expense_df.empty:
            fig = px.pie(expense_df, values='金额', names='显示分类', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)

    # 导出功能
    st.markdown("---")
    if app_mode == "企业报税模式":
        # 导出带税务科目的 Excel/CSV
        export_df = df.copy()
        export_df['税务科目'] = export_df.apply(lambda x: map_tax_category(x['类型'], x['备注']), axis=1)
        csv = export_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 导出企业纳税参考报表 (CSV)", csv, "company_tax_report.csv", "text/csv")
    else:
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 导出个人年度对账单 (CSV)", csv, "personal_ledger.csv", "text/csv")

else:
    st.info("暂无数据，请在侧边栏开始记账。")

# --- 5. 底部版权 ---
st.caption("全能记账助手 | 模式：智能税务映射 + 个人生活分类")
