import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
import io

# --- 1. 全局配置与税务会计规则库 ---
st.set_page_config(page_title="小微企业财税助手", page_icon="🏦", layout="wide")

# 标准会计科目归集映射 (利润表行项)
# 将用户记账的“明细科目”映射到“报表项”
FINANCIAL_REPORT_MAPPING = {
    "主营业务收入": "一、营业收入",
    "其他业务收入": "一、营业收入",
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

# 智能识别规则库
TAX_RULES = {
    # 收入类映射
    "INCOME": {
        "主营业务收入": ["销售", "货款", "订单", "卖货", "回款", "产品收入", "服务费"],
        "其他业务收入": ["利息", "退税", "变卖", "废料", "政府补助"]
    },
    # 支出类映射
    "EXPENSE": {
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
}

def auto_map_tax(row_type, note_text):
    """根据备注智能识别税务科目"""
    full_text = str(note_text).lower()
    rules = TAX_RULES["INCOME"] if row_type == "收入" else TAX_RULES["EXPENSE"]
    
    for tax_category, keywords in rules.items():
        for keyword in keywords:
            if keyword.lower() in full_text:
                return tax_category
    
    return "主营业务收入" if row_type == "收入" else "其他支出/待分类"

# --- 2. 数据存储逻辑 ---
DATA_FILE = "unified_ledger_tax_v5.csv"

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

# --- 3. 侧边栏交互 ---
with st.sidebar:
    st.title("🛡️ 财税安全中心")
    app_mode = st.radio("运行模式", ["个人生活模式", "企业专业报税"])
    
    st.markdown("---")
    st.subheader("📝 快速录入")
    with st.form("input_form", clear_on_submit=True):
        d = st.date_input("交易日期", datetime.now().date())
        t = st.selectbox("收支类型", ["支出", "收入"])
        
        # 动态分类逻辑
        if app_mode == "个人生活模式":
            cats = ["餐饮", "交通", "购物", "娱乐", "居住", "医疗", "其他"] if t == "支出" else ["工资", "理财", "外快", "其他"]
            selected_cat = st.selectbox("选择分类", cats)
        else:
            st.info("💡 系统将根据备注自动匹配会计科目")
            selected_cat = "系统自动识别"
            
        a = st.number_input("金额 (CNY)", min_value=0.0, format="%.2f")
        n = st.text_input("备注/摘要 (如：销售3月货款、请客户吃饭)")
        
        if st.form_submit_button("确认存入"):
            # 企业模式下运行智能识别
            final_cat = auto_map_tax(t, n) if app_mode == "企业专业报税" else selected_cat
            new_record = pd.DataFrame([{'日期': d, '类型': t, '分类': final_cat, '金额': a, '备注': n}])
            st.session_state.data = pd.concat([st.session_state.data, new_record], ignore_index=True)
            save_data(st.session_state.data)
            st.success(f"已存入: {final_cat}")

# --- 4. 主界面逻辑 ---
st.title(f"🚀 {app_mode}工作台")

if not st.session_state.data.empty:
    tab_manage, tab_report = st.tabs(["🗂️ 账单流水管理", "📄 利润表 (一键报税参考)"])

    with tab_manage:
        st.subheader("全量明细与修改")
        # 允许用户直接在表格里纠正 AI 的分类
        edited_df = st.data_editor(st.session_state.data, use_container_width=True, num_rows="dynamic")
        if st.button("💾 保存更改并刷新报表"):
            st.session_state.data = edited_df
            save_data(edited_df)
            st.rerun()

    with tab_report:
        st.subheader("📈 小微企业利润表")
        
        # --- 数据预处理 ---
        df_rep = st.session_state.data.copy()
        df_rep['日期'] = pd.to_datetime(df_rep['日期'])
        
        # 时间筛选器
        col_y, col_m = st.columns(2)
        cur_year = datetime.now().year
        sel_year = col_y.selectbox("年份", sorted(df_rep['日期'].dt.year.unique(), reverse=True))
        sel_month = col_m.multiselect("月份 (可多选，不选为全年)", range(1, 13))
        
        # 过滤数据
        mask = (df_rep['日期'].dt.year == sel_year)
        if sel_month:
            mask &= (df_rep['日期'].dt.month.isin(sel_month))
        f_df = df_rep[mask]

        if not f_df.empty:
            # 关键逻辑：将会计科目映射到报表行
            # 先给数据打上报表项标签
            f_df['报表项'] = f_df['分类'].map(FINANCIAL_REPORT_MAPPING).fillna("管理费用")
            
            # 汇总计算
            stats = f_df.groupby('报表项')['金额'].sum().to_dict()
            
            # 构建利润表
            rev = stats.get("一、营业收入", 0)
            cost = stats.get("二、营业成本", 0)
            s_exp = stats.get("销售费用", 0)
            a_exp = stats.get("管理费用", 0)
            f_exp = stats.get("财务费用", 0)
            
            profit = rev - cost - s_exp - a_exp - f_exp
            
            report_struct = [
                {"项目": "一、营业收入", "金额": rev},
                {"项目": "  减：营业成本", "金额": cost},
                {"项目": "      销售费用", "金额": s_exp},
                {"项目": "      管理费用", "金额": a_exp},
                {"项目": "      财务费用", "金额": f_exp},
                {"项目": "二、营业利润", "金额": profit},
                {"项目": "  加：营业外收支净额", "金额": 0.0},
                {"项目": "三、利润总额", "金额": profit},
                {"项目": "  减：所得税费用 (测算)", "金额": max(0, profit * 0.05) if profit < 1000000 else max(0, profit * 0.25)},
                {"项目": "四、净利润", "金额": profit - (max(0, profit * 0.05) if profit < 1000000 else max(0, profit * 0.25))}
            ]
            
            st.table(pd.DataFrame(report_struct).style.format({"金额": "¥{:,.2f}"}))
            
            # 导出 Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                pd.DataFrame(report_struct).to_excel(writer, sheet_name='利润表', index=False)
                f_df.to_excel(writer, sheet_name='流水明细', index=False)
            
            st.download_button(
                label="📥 下载本期报税 Excel 资料包",
                data=output.getvalue(),
                file_name=f"财税报表_{sel_year}_{sel_month}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("选定时间段内没有财务记录")
else:
    st.info("💡 请在侧边栏录入第一笔数据（无论是收入还是支出）")

# 版权底部
st.markdown("---")
st.caption("中国小微企业《小企业会计准则》合规辅助工具 | 数据存储于本地 CSV")
