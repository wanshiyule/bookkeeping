import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

# --- 1. 配置与税务规则库 ---
st.set_page_config(page_title="小微企业智能记账报税助手", page_icon="🏦", layout="wide")

# 标准会计科目与报表行项映射 (基于《小企业会计准则》)
# 我们将细分科目归集到利润表的三大费用中
FINANCIAL_REPORT_MAPPING = {
    "主营业务收入": "一、营业收入",
    "主营业务成本": "二、营业成本",
    "广宣费/佣金": "销售费用",
    "业务招待费": "管理费用",
    "差旅费": "管理费用",
    "办公费": "管理费用",
    "福利费": "管理费用",
    "职工薪酬": "管理费用",
    "车辆使用费": "管理费用",
    "咨询/劳务费": "管理费用",
    "租赁费": "管理费用",
    "财务费用": "财务费用",
    "其他支出/待分类": "管理费用"
}

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
    if row_type == '收入': return "主营业务收入"
    full_text = str(note_text).lower()
    for tax_category, keywords in TAX_RULES.items():
        for keyword in keywords:
            if keyword.lower() in full_text: return tax_category
    return "其他支出/待分类"

# --- 2. 数据处理 ---
DATA_FILE = "unified_ledger_tax_v4.csv"

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

# --- 3. 侧边栏 ---
with st.sidebar:
    st.title("🏦 财务管理系统")
    app_mode = st.radio("模式切换", ["个人记账", "企业报税(专业)"])
    
    st.markdown("---")
    with st.form("add_record"):
        st.subheader("📝 快速记账")
        d = st.date_input("日期", datetime.now().date())
        t = st.selectbox("类型", ["支出", "收入"])
        a = st.number_input("金额", min_value=0.0)
        n = st.text_input("描述 (如：上海出差酒店费)")
        if st.form_submit_button("保存"):
            cat = auto_map_tax(t, n) if app_mode == "企业报税(专业)" else "生活支出"
            new_data = pd.DataFrame([{'日期': d, '类型': t, '分类': cat, '金额': a, '备注': n}])
            st.session_state.data = pd.concat([st.session_state.data, new_data], ignore_index=True)
            save_data(st.session_state.data)
            st.toast("入账成功")

# --- 4. 主界面 ---
st.title(f"🚀 {app_mode}工作台")

if not st.session_state.data.empty:
    tab_view, tab_tax_report = st.tabs(["📊 流动明细与管理", "📄 智能报税利润表"])

    with tab_view:
        st.subheader("明细修正")
        edited_df = st.data_editor(st.session_state.data, use_container_width=True, num_rows="dynamic")
        if st.button("💾 同步并保存更改"):
            st.session_state.data = edited_df
            save_data(edited_df)
            st.success("数据已更新")
            st.rerun()

    with tab_tax_report:
        st.subheader("📅 小微企业利润表 (损益表参考)")
        
        # 筛选器
        df_report = st.session_state.data.copy()
        df_report['日期'] = pd.to_datetime(df_report['日期'])
        years = df_report['日期'].dt.year.unique()
        
        col_y, col_m = st.columns(2)
        sel_year = col_y.selectbox("选择年份", years)
        sel_month = col_m.multiselect("选择月份 (不选则查看全年)", range(1, 13))
        
        # 过滤数据
        filtered_df = df_report[df_report['日期'].dt.year == sel_year]
        if sel_month:
            filtered_df = filtered_df[filtered_df['日期'].dt.month.isin(sel_month)]
        
        if not filtered_df.empty:
            # 1. 自动归集会计科目
            filtered_df['会计报表项'] = filtered_df['分类'].map(FINANCIAL_REPORT_MAPPING).fillna("其他费用")
            
            # 2. 计算各项汇总
            summary = filtered_df.groupby('会计报表项')['金额'].sum().to_dict()
            
            # 3. 构造利润表结构
            rev = summary.get("一、营业收入", 0)
            cost = summary.get("二、营业成本", 0)
            sell_exp = summary.get("销售费用", 0)
            admin_exp = summary.get("管理费用", 0)
            fin_exp = summary.get("财务费用", 0)
            
            op_profit = rev - cost - sell_exp - admin_exp - fin_exp
            
            report_data = [
                {"项目": "一、营业收入", "本期金额": rev},
                {"项目": "  减：营业成本", "本期金额": cost},
                {"项目": "      销售费用", "本期金额": sell_exp},
                {"项目": "      管理费用", "本期金额": admin_exp},
                {"项目": "      财务费用", "本期金额": fin_exp},
                {"项目": "二、营业利润", "本期金额": op_profit},
                {"项目": "三、利润总额", "本期金额": op_profit},
                {"项目": "  减：所得税费用 (参考 20% / 25%)", "本期金额": max(0, op_profit * 0.2)},
                {"项目": "四、净利润", "本期金额": op_profit - max(0, op_profit * 0.2)}
            ]
            
            final_report_df = pd.DataFrame(report_data)
            
            # 美化展示
            st.table(final_report_df.style.format({"本期金额": "¥{:,.2f}"}))
            
            st.markdown("---")
            st.subheader("📦 报税一键导出")
            
            # 导出明细和汇总
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                final_report_df.to_excel(writer, sheet_name='利润表汇总', index=False)
                filtered_df.to_excel(writer, sheet_name='原始流水明细', index=False)
            
            st.download_button(
                label="📥 点击下载 Excel 报税参考包",
                data=output.getvalue(),
                file_name=f"小微企业报税表_{sel_year}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("该时间段内暂无记录")

else:
    st.info("请先在左侧输入账单数据")

# 引入导出所需的库
import io
