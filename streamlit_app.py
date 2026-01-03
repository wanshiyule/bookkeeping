import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
import io

# --- 1. 配置与常量定义 ---
st.set_page_config(page_title="全能记账助手 (隔离版)", page_icon="🏦", layout="wide")

# 个人版分类 (用户指定)
PERSONAL_CATS = [
    "餐饮", "交通", "美容", "学习", "零食", "日用品", "烟酒", "医药", 
    "家用电器", "数码", "水电煤", "旅行", "住房", "通讯", "投资", 
    "保险", "运动", "发红包", "其他"
]
PERSONAL_INCOME_CATS = ["工资", "理财收益", "奖金", "红包收入", "其他收入"]

# 企业版会计科目归集 (基于《小企业会计准则》)
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

TAX_RULES = {
    "INCOME": {
        "主营业务收入": ["销售", "货款", "订单", "产品收入", "服务费"],
        "其他业务收入": ["利息", "退税", "政府补助"]
    },
    "EXPENSE": {
        "业务招待费": ["请客", "吃饭", "聚餐", "招待", "宴请", "烟酒", "礼品"],
        "差旅费": ["出差", "机票", "高铁", "住宿", "打车", "滴滴"],
        "办公费": ["纸", "笔", "复印", "快递", "顺丰", "ERP", "订阅", "打印机"],
        "福利费": ["团建", "下午茶", "体检", "食堂", "外卖"],
        "职工薪酬": ["工资", "奖金", "绩效", "社保", "公积金"],
        "车辆使用费": ["加油", "停车", "洗车", "车险", "维修", "保养"],
        "咨询/劳务费": ["咨询", "法律", "财税", "VAT", "代理", "申报"],
        "租赁费": ["房租", "租金", "物业", "仓库", "服务器"],
        "广宣费/佣金": ["佣金", "广告", "Facebook", "投流", "推广"],
        "主营业务成本": ["采购", "进货", "头程", "运费", "物流", "入仓"],
        "财务费用": ["手续费", "结汇", "提现", "银行", "转账"]
    }
}

# --- 2. 数据存储引擎 (双文件隔离) ---
PERSONAL_DB = "personal_ledger.csv"
ENTERPRISE_DB = "enterprise_ledger.csv"

def load_data(db_path):
    if os.path.exists(db_path):
        df = pd.read_csv(db_path)
        df['日期'] = pd.to_datetime(df['日期']).dt.date
        return df
    return pd.DataFrame(columns=['日期', '类型', '分类', '金额', '备注'])

def save_data(df, db_path):
    df.to_csv(db_path, index=False)

def auto_map_tax(row_type, note_text):
    full_text = str(note_text).lower()
    rules = TAX_RULES["INCOME"] if row_type == "收入" else TAX_RULES["EXPENSE"]
    for cat, keywords in rules.items():
        for k in keywords:
            if k.lower() in full_text: return cat
    return "主营业务收入" if row_type == "收入" else "其他支出/待分类"

# --- 3. 侧边栏模式切换 ---
with st.sidebar:
    st.title("🏦 财务中心")
    # 核心：完全隔离的账本选择
    app_mode = st.radio("请选择记账账本", ["个人生活账本", "企业财务账本"], 
                        help="两套账本数据完全隔离，存储在不同文件中")
    
    current_db = PERSONAL_DB if app_mode == "个人生活账本" else ENTERPRISE_DB
    
    st.markdown("---")
    st.subheader("📝 快速录入")
    with st.form("input_form", clear_on_submit=True):
        d = st.date_input("交易日期", datetime.now().date())
        t = st.selectbox("收支类型", ["支出", "收入"])
        
        if app_mode == "个人生活账本":
            cats = PERSONAL_CATS if t == "支出" else PERSONAL_INCOME_CATS
            selected_cat = st.selectbox("分类", cats)
        else:
            st.info("💡 企业模式：系统将根据备注自动识别会计科目")
            selected_cat = "待识别"
            
        a = st.number_input("金额", min_value=0.0, format="%.2f")
        n = st.text_input("备注/摘要")
        
        if st.form_submit_button("确认入账"):
            final_cat = selected_cat if app_mode == "个人生活账本" else auto_map_tax(t, n)
            new_record = pd.DataFrame([{'日期': d, '类型': t, '分类': final_cat, '金额': a, '备注': n}])
            
            # 加载、合并、保存
            current_df = load_data(current_db)
            updated_df = pd.concat([current_df, new_record], ignore_index=True)
            save_data(updated_df, current_db)
            st.success(f"已存入{app_mode}")

# --- 4. 主界面展示逻辑 ---
st.title(f"🚀 {app_mode}")
data = load_data(current_db)

if not data.empty:
    if app_mode == "个人生活账本":
        # --- 个人版：侧重消费统计 ---
        tab1, tab2 = st.tabs(["🗂️ 历史明细与修改", "📈 年度/季度/月度汇总"])
        
        with tab1:
            st.subheader("明细流水")
            edited_p = st.data_editor(data, use_container_width=True, num_rows="dynamic")
            if st.button("保存个人账目修改"):
                save_data(edited_p, PERSONAL_DB)
                st.rerun()
        
        with tab2:
            st.subheader("消费多维度汇总")
            data['日期'] = pd.to_datetime(data['日期'])
            data['年份'] = data['日期'].dt.year
            data['季度'] = data['日期'].dt.to_period('Q').astype(str)
            data['月份'] = data['日期'].dt.to_period('M').astype(str)
            
            view_opt = st.selectbox("视角", ["月度汇总", "季度汇总", "年度汇总"])
            period_col = "月份" if view_opt == "月度汇总" else "季度" if view_opt == "季度汇总" else "年份"
            
            summary = data.groupby([period_col, '类型'])['金额'].sum().reset_index()
            fig_trend = px.bar(summary, x=period_col, y="金额", color="类型", barmode="group", title="收支对比")
            st.plotly_chart(fig_trend, use_container_width=True)
            
            col_left, col_right = st.columns(2)
            with col_left:
                st.write("**支出分类占比**")
                exp_p = data[data['类型'] == '支出']
                fig_p = px.pie(exp_p, values='金额', names='分类', hole=0.4)
                st.plotly_chart(fig_p, use_container_width=True)
            with col_right:
                st.write("**数据摘要**")
                st.dataframe(data.groupby('分类')['金额'].sum().sort_values(ascending=False), use_container_width=True)

    else:
        # --- 企业版：侧重报税报表 ---
        tab1, tab2 = st.tabs(["🗂️ 企业流水管理", "📄 利润表 (一键报税)"])
        
        with tab1:
            st.subheader("企业明细 (可纠正 AI 分类)")
            edited_e = st.data_editor(data, use_container_width=True, num_rows="dynamic")
            if st.button("保存企业账目修改"):
                save_data(edited_e, ENTERPRISE_DB)
                st.rerun()
        
        with tab2:
            st.subheader("小微企业利润表 (参考报税文件)")
            data['日期'] = pd.to_datetime(data['日期'])
            
            y = st.selectbox("年份", sorted(data['日期'].dt.year.unique(), reverse=True))
            m_list = st.multiselect("月份筛选 (多选)", range(1, 13))
            
            f_df = data[data['日期'].dt.year == y]
            if m_list: f_df = f_df[f_df['日期'].dt.month.isin(m_list)]
            
            if not f_df.empty:
                f_df['报表项'] = f_df['分类'].map(FINANCIAL_REPORT_MAPPING).fillna("管理费用")
                stats = f_df.groupby('报表项')['金额'].sum().to_dict()
                
                rev = stats.get("一、营业收入", 0)
                cost = stats.get("二、营业成本", 0)
                s_exp = stats.get("销售费用", 0)
                a_exp = stats.get("管理费用", 0)
                f_exp = stats.get("财务费用", 0)
                profit = rev - cost - s_exp - a_exp - f_exp
                
                report = [
                    {"项目": "一、营业收入", "金额": rev},
                    {"项目": "  减：营业成本", "金额": cost},
                    {"项目": "      销售费用", "金额": s_exp},
                    {"项目": "      管理费用", "金额": a_exp},
                    {"项目": "      财务费用", "金额": f_exp},
                    {"项目": "二、营业利润", "金额": profit},
                    {"项目": "三、利润总额", "金额": profit},
                    {"项目": "  减：所得税费用 (5%测算)", "金额": max(0, profit * 0.05)},
                    {"项目": "四、净利润", "金额": profit - max(0, profit * 0.05)}
                ]
                
                st.table(pd.DataFrame(report).style.format({"金额": "¥{:,.2f}"}))
                
                # 导出 Excel
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    pd.DataFrame(report).to_excel(writer, sheet_name='利润表汇总', index=False)
                    f_df.to_excel(writer, sheet_name='流水明细', index=False)
                
                st.download_button("📥 下载企业报税资料包", output.getvalue(), f"企业报表_{y}.xlsx")
            else:
                st.warning("所选期间无数据")

else:
    st.info(f"💡 {app_mode}目前为空，请开始记账。")

st.markdown("---")
st.caption(f"当前账本：{app_mode} | 数据隔离存储：True | 历史存储期限：3年以上")
