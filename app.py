"""
贵州盖浇面/饭 · 菜品研发过程记录表
Streamlit 应用 - 部署到 Streamlit Cloud
GitHub: https://github.com/你的用户名/guizhou-rd-table
"""

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from openai import OpenAI
import copy

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="贵州盖浇面/饭·研发记录表",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==================== 自定义CSS ====================
st.markdown("""
<style>
    .stApp { background-color: #1a1a2e; }
    .main-title {
        font-size: 1.5rem; font-weight: 700; color: #e94560;
        text-align: center; padding: 8px 0; letter-spacing: 1px;
        border-bottom: 2px solid #e94560; margin-bottom: 12px;
    }
    .main-title span { color: #fff; }
    .stButton > button {
        border-radius: 6px; font-weight: 500; transition: all 0.2s;
    }
    .stButton > button:hover { border-color: #e94560 !important; }
    .section-label {
        font-weight: 700; font-size: 0.9rem; color: #e94560;
        margin-top: 8px; margin-bottom: 4px;
        padding: 4px 8px; background: rgba(233,68,96,0.1);
        border-radius: 4px; border-left: 3px solid #e94560;
    }
    .taste-pass { color: #0a0; font-weight: 700; }
    .taste-fail { color: #e00; font-weight: 700; }
    .stTextInput > div > div > input, .stTextArea > div > div > textarea {
        font-size: 0.8rem !important;
    }
    @media print {
        header, .stSidebar, .stButton, .stDownloadButton, hr { display: none !important; }
        .stApp { background: #fff !important; }
        .main-title { color: #000 !important; border-bottom-color: #000 !important; }
        .main-title span { color: #000 !important; }
        .section-label { color: #000 !important; background: #f0f0f0 !important; border-left-color: #000 !important; }
    }
</style>
""", unsafe_allow_html=True)

# ==================== 初始化 Session State ====================
if 'table_data' not in st.session_state:
    st.session_state.table_data = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'flavor_type' not in st.session_state:
    st.session_state.flavor_type = "gongbao"
if 'deepseek_key' not in st.session_state:
    # 优先从环境变量读取，方便 Streamlit Cloud 设置 secrets
    st.session_state.deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")

# Streamlit Cloud secrets 支持
try:
    if st.secrets.get("DEEPSEEK_API_KEY"):
        st.session_state.deepseek_key = st.secrets["DEEPSEEK_API_KEY"]
except:
    pass

# ==================== 数据模板 ====================
VERSION_KEYS = ['V1.0\n首次试做', 'V1.1\n调整', 'V1.2\n调整', 'V2.0\n改版', '终版\n定型']
VERSION_LABELS = ['V1.0（首次试做）', 'V1.1（调整）', 'V1.2（调整）', 'V2.0（改版）', '终版定型']


def create_version_data(flavor_type, is_first=False):
    """创建一个版本的数据模板"""
    is_gongbao = (flavor_type == "gongbao")
    return {
        'date': '',
        'purpose': '搭建基础味型框架' if is_first else '',
        'main_name': '鸡腿肉丁' if is_gongbao else '鳝鱼',
        'main_value': '120' if is_first else '',
        # 辣椒酱料
        'chili_paste': '50' if (is_first and is_gongbao) else '',
        'red_pickled': '20' if (is_first and not is_gongbao) else '',
        'green_pickled': '20' if (is_first and not is_gongbao) else '',
        'fermented_pepper': '10' if (is_first and not is_gongbao) else '',
        # 宫保汁（兑碗汁）
        'gb_sweet': '', 'gb_soy': '', 'gb_vinegar': '',
        'gb_msg': '', 'gb_sugar': '', 'gb_starch': '', 'gb_broth': '', 'gb_other': '',
        # 独立调料（泡椒味型，直接撒入，不兑汁）
        'sp_msg': '3' if (is_first and not is_gongbao) else '',
        'sp_soy': '3' if (is_first and not is_gongbao) else '',
        'sp_vinegar': '3' if (is_first and not is_gongbao) else '',
        'sp_starch': '3' if (is_first and not is_gongbao) else '',
        'sp_salt': '', 'sp_sugar': '', 'sp_other': '',
        # 辅料
        'garlic_sprout': '30' if is_first else '',
        'ginger_garlic': '20' if is_first else '',
        'aux_other': '',
        # 烹调用油
        'soybean_oil': '50' if is_first else '',
        'other_oil': '',
        # 工艺流程
        'proc_1': '', 'proc_2': '', 'proc_3': '', 'proc_4': '', 'proc_5': '',
        'proc_6': '', 'proc_7': '', 'proc_8': '', 'proc_9': '', 'proc_10': '',
        # 品鉴: pending / pass / fail
        'taste_look': 'pending', 'taste_look_note': '',
        'taste_smell': 'pending', 'taste_smell_note': '',
        'taste_flavor': 'pending', 'taste_flavor_note': '',
        'taste_texture': 'pending', 'taste_texture_note': '',
        'taste_sauce': 'pending', 'taste_sauce_note': '',
        'taste_staple': 'pending', 'taste_staple_note': '',
        # 问题诊断
        'problem': '', 'cause': '', 'solution': '',
        # 结论: pending / retain / discard / finalized
        'conclusion': 'retain' if is_first else 'pending',
    }


def get_default_data(flavor_type):
    """获取完整默认数据"""
    is_gongbao = (flavor_type == "gongbao")
    data = {
        'product_name': '宫保鸡丁' if is_gongbao else '泡椒鳝鱼',
        'flavor_type': flavor_type,
        'flavor_label': '宫保（糊辣荔枝）' if is_gongbao else '泡椒（酸辣）',
        'chef': '',
        'recorder': '',
        'structure': '宽面280g / 细面250g / 天麻面280g / 米饭250g',
        'versions': {},
        'summary': {
            'final_recipe': '',
            'final_process': '',
            'cost': '',
            'duration': '',
            'signature': '',
        },
    }
    for i, vk in enumerate(VERSION_KEYS):
        data['versions'][vk] = create_version_data(flavor_type, is_first=(i == 0))
    return data


# 初始化
if st.session_state.table_data is None:
    st.session_state.table_data = get_default_data("gongbao")


# ==================== 辅助函数 ====================
def taste_options():
    return ['pending', 'pass', 'fail']


def taste_display(val):
    if val == 'pass':
        return '✅ 达标'
    elif val == 'fail':
        return '❌ 不达标'
    return '—'


def taste_emoji(val):
    return {'pending': '—', 'pass': '✅', 'fail': '❌'}.get(val, '—')


def build_table_context():
    """构建当前表格数据的文本摘要，用于发送给 AI"""
    data = st.session_state.table_data
    ctx = f"产品：{data['product_name']}，味型：{data['flavor_label']}\n"
    ctx += f"出品结构：{data.get('structure', '')}\n\n"

    for vk in VERSION_KEYS:
        ver = data['versions'][vk]
        ctx += f"【{vk.replace(chr(10), ' ')}】日期：{ver['date']}，目的：{ver['purpose']}\n"
        ctx += f"主料：{ver['main_name']} {ver['main_value']}g\n"

        if data['flavor_type'] == "gongbao":
            ctx += f"糍粑辣椒：{ver.get('chili_paste', '')}g\n"
            ctx += f"宫保汁（兑碗汁）：甜酱{ver.get('gb_sweet', '')}g 酱油{ver.get('gb_soy', '')}g 醋{ver.get('gb_vinegar', '')}g 味精{ver.get('gb_msg', '')}g 白糖{ver.get('gb_sugar', '')}g 淀粉{ver.get('gb_starch', '')}g 汤{ver.get('gb_broth', '')}g\n"
        else:
            ctx += f"红泡椒{ver.get('red_pickled', '')}g 青泡椒{ver.get('green_pickled', '')}g 糟辣椒{ver.get('fermented_pepper', '')}g\n"
            ctx += f"独立调料（直接撒入，不兑汁）：味精{ver.get('sp_msg', '')}g 酱油{ver.get('sp_soy', '')}g 醋{ver.get('sp_vinegar', '')}g 淀粉{ver.get('sp_starch', '')}g 盐{ver.get('sp_salt', '')}g 白糖{ver.get('sp_sugar', '')}g\n"

        ctx += f"辅料：蒜苗{ver.get('garlic_sprout', '')}g 姜蒜泥{ver.get('ginger_garlic', '')}g 大豆油{ver.get('soybean_oil', '')}g\n"

        # 品鉴
        tastes = []
        taste_map = [
            ('taste_look', '观感'), ('taste_smell', '香气'), ('taste_flavor', '味型'),
            ('taste_texture', '主料口感'), ('taste_sauce', '芡汁'), ('taste_staple', '搭配主食')
        ]
        for t_key, t_label in taste_map:
            status = ver.get(t_key, 'pending')
            note = ver.get(f'{t_key}_note', '')
            if status == 'fail':
                tastes.append(f"{t_label}❌({note})")
            elif status == 'pass':
                tastes.append(f"{t_label}✅")
        if tastes:
            ctx += f"品鉴：{'  '.join(tastes)}\n"

        ctx += f"结论：{ver.get('conclusion', '')}\n"
        if ver.get('problem'):
            ctx += f"问题：{ver['problem']}\n原因：{ver['cause']}\n方案：{ver['solution']}\n"
        ctx += "\n"

    return ctx


def call_deepseek(messages):
    """调用 DeepSeek API"""
    api_key = st.session_state.deepseek_key

    if not api_key:
        return "⚠️ 请先在侧边栏设置 DeepSeek API Key。\n\n获取方式：https://platform.deepseek.com/api_keys"

    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
        )
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.7,
            max_tokens=2000,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ API 调用失败：{str(e)}"


def quick_analyze():
    """快捷分析配方"""
    ctx = build_table_context()
    messages = [
        {"role": "system",
         "content": "你是贵州菜品研发专家。请分析当前配方的合理性，指出潜在问题，并给出具体调整建议。回答简洁专业，用中文。"},
        {"role": "user", "content": f"请分析以下研发记录：\n\n{ctx}"}
    ]
    return call_deepseek(messages)


def quick_compare():
    """快捷对比版本"""
    ctx = build_table_context()
    messages = [
        {"role": "system",
         "content": "你是贵州菜品研发专家。请对比各版本的配方变化，分析每次调整的意图和效果，指出还需要优化的方向。用中文回答。"},
        {"role": "user", "content": f"请对比以下研发记录中各个版本的差异：\n\n{ctx}"}
    ]
    return call_deepseek(messages)


def quick_suggest():
    """快捷优化建议"""
    ctx = build_table_context()
    messages = [
        {"role": "system",
         "content": "你是贵州菜品研发专家。基于当前研发记录，给出3-5条具体的优化建议，每条建议要具体到克数或操作细节。用中文回答。"},
        {"role": "user", "content": f"基于以下研发记录给出优化建议：\n\n{ctx}"}
    ]
    return call_deepseek(messages)


# ==================== 主界面 ====================
st.markdown('<div class="main-title">🔥 <span>贵州盖浇面/饭</span> · 菜品研发过程记录表</div>', unsafe_allow_html=True)

# ---- 顶部信息栏 ----
col1, col2, col3, col4, col5, col6 = st.columns([2, 1.5, 1, 1, 0.8, 0.8])

with col1:
    product_name = st.text_input(
        "产品名称",
        value=st.session_state.table_data['product_name'],
        key="top_product_name",
        label_visibility="collapsed",
        placeholder="产品名称"
    )
    st.session_state.table_data['product_name'] = product_name

with col2:
    flavor_map = {"gongbao": "宫保鸡丁（糊辣荔枝）", "paojiao": "泡椒鳝鱼（酸辣）"}
    selected_flavor = st.selectbox(
        "味型",
        list(flavor_map.keys()),
        format_func=lambda x: flavor_map[x],
        index=0 if st.session_state.flavor_type == "gongbao" else 1,
        key="top_flavor",
        label_visibility="collapsed"
    )
    if selected_flavor != st.session_state.flavor_type:
        st.session_state.flavor_type = selected_flavor
        st.session_state.table_data = get_default_data(selected_flavor)
        st.rerun()

with col3:
    chef = st.text_input(
        "师傅",
        value=st.session_state.table_data.get('chef', ''),
        key="top_chef",
        label_visibility="collapsed",
        placeholder="研发师傅"
    )
    st.session_state.table_data['chef'] = chef

with col4:
    recorder = st.text_input(
        "记录人",
        value=st.session_state.table_data.get('recorder', ''),
        key="top_recorder",
        label_visibility="collapsed",
        placeholder="记录人"
    )
    st.session_state.table_data['recorder'] = recorder

with col5:
    if st.button("🔄 重置", use_container_width=True, key="btn_reset"):
        st.session_state.table_data = get_default_data(st.session_state.flavor_type)
        st.rerun()

with col6:
    if st.button("🖨️ 打印", use_container_width=True, key="btn_print"):
        st.markdown("<script>window.print();</script>", unsafe_allow_html=True)

# 出品结构
structure = st.text_input(
    "出品结构",
    value=st.session_state.table_data.get('structure', ''),
    key="top_structure",
    placeholder="如：宽面280g / 细面250g / 天麻面280g / 米饭250g"
)
st.session_state.table_data['structure'] = structure

# ---- 数据变量 ----
data = st.session_state.table_data
is_gongbao = (st.session_state.flavor_type == "gongbao")
versions = data['versions']

# ==================== 主表格 ====================
# 使用 st.columns 构建表格

# 列宽比例：标签列 + 5个版本列
col_ratios = [1.3] + [1] * NUM_V
cols = st.columns(col_ratios)

# 表头行
with cols[0]:
    st.markdown("**研发阶段**")
for i, vk in enumerate(VERSION_KEYS):
    with cols[i + 1]:
        st.markdown(f"**{vk.replace(chr(10), '<br>')}**", unsafe_allow_html=True)

st.divider()

# ---- 日期 ----
cols = st.columns(col_ratios)
with cols[0]:
    st.markdown("**日期**")
for i, vk in enumerate(VERSION_KEYS):
    with cols[i + 1]:
        versions[vk]['date'] = st.text_input(
            "日期", value=versions[vk]['date'],
            key=f"date_{vk}", label_visibility="collapsed", placeholder="月/日"
        )

# ---- 研发目的 ----
cols = st.columns(col_ratios)
with cols[0]:
    st.markdown("**研发目的**")
for i, vk in enumerate(VERSION_KEYS):
    with cols[i + 1]:
        versions[vk]['purpose'] = st.text_input(
            "目的", value=versions[vk]['purpose'],
            key=f"purpose_{vk}", label_visibility="collapsed", placeholder="目的..."
        )

# ==================== 配方区域 ====================
st.markdown('<div class="section-label">📋 配方记录</div>', unsafe_allow_html=True)

# ---- 主料 ----
cols = st.columns(col_ratios)
with cols[0]:
    st.markdown(f"**主料**<br>({versions[VERSION_KEYS[0]]['main_name']})", unsafe_allow_html=True)
for i, vk in enumerate(VERSION_KEYS):
    with cols[i + 1]:
        versions[vk]['main_value'] = st.text_input(
            "主料g", value=versions[vk]['main_value'],
            key=f"main_{vk}", label_visibility="collapsed", placeholder="g"
        )

# ---- 辣椒酱料 ----
st.markdown("*辣椒酱料*")
if is_gongbao:
    cols = st.columns(col_ratios)
    with cols[0]:
        st.markdown("糍粑辣椒")
    for i, vk in enumerate(VERSION_KEYS):
        with cols[i + 1]:
            versions[vk]['chili_paste'] = st.text_input(
                "糍粑g", value=versions[vk]['chili_paste'],
                key=f"chili_{vk}", label_visibility="collapsed", placeholder="g"
            )
else:
    for label, field in [("红泡椒", "red_pickled"), ("青泡椒", "green_pickled"), ("糟辣椒", "fermented_pepper")]:
        cols = st.columns(col_ratios)
        with cols[0]:
            st.markdown(label)
        for i, vk in enumerate(VERSION_KEYS):
            with cols[i + 1]:
                versions[vk][field] = st.text_input(
                    f"{label}g", value=versions[vk][field],
                    key=f"{field}_{vk}", label_visibility="collapsed", placeholder="g"
                )

# ---- 宫保汁 / 独立调料 ----
if is_gongbao:
    st.markdown("*宫保汁（兑碗汁，预调混合）*")
    gb_fields = [
        ("甜酱", "gb_sweet"), ("酱油", "gb_soy"), ("醋", "gb_vinegar"),
        ("味精", "gb_msg"), ("白糖", "gb_sugar"), ("水淀粉", "gb_starch"),
        ("高汤/水", "gb_broth"), ("其他", "gb_other"),
    ]
    for label, field in gb_fields:
        cols = st.columns(col_ratios)
        with cols[0]:
            st.markdown(label)
        for i, vk in enumerate(VERSION_KEYS):
            with cols[i + 1]:
                versions[vk][field] = st.text_input(
                    f"{label}g", value=versions[vk][field],
                    key=f"{field}_{vk}", label_visibility="collapsed", placeholder="g"
                )
else:
    st.markdown("*独立调料（直接撒入，不兑汁）*")
    sp_fields = [
        ("味精", "sp_msg"), ("酱油", "sp_soy"), ("醋", "sp_vinegar"),
        ("淀粉", "sp_starch"), ("盐", "sp_salt"), ("白糖", "sp_sugar"), ("其他", "sp_other"),
    ]
    for label, field in sp_fields:
        cols = st.columns(col_ratios)
        with cols[0]:
            st.markdown(label)
        for i, vk in enumerate(VERSION_KEYS):
            with cols[i + 1]:
                versions[vk][field] = st.text_input(
                    f"{label}g", value=versions[vk][field],
                    key=f"{field}_{vk}", label_visibility="collapsed", placeholder="g"
                )

# ---- 辅料 ----
st.markdown("*辅料*")
for label, field in [("蒜苗", "garlic_sprout"), ("姜蒜泥", "ginger_garlic"), ("其他", "aux_other")]:
    cols = st.columns(col_ratios)
    with cols[0]:
        st.markdown(label)
    for i, vk in enumerate(VERSION_KEYS):
        with cols[i + 1]:
            versions[vk][field] = st.text_input(
                f"{label}g", value=versions[vk][field],
                key=f"{field}_{vk}", label_visibility="collapsed", placeholder="g"
            )

# ---- 烹调用油 ----
st.markdown("*烹调用油*")
for label, field in [("大豆油", "soybean_oil"), ("其他油", "other_oil")]:
    cols = st.columns(col_ratios)
    with cols[0]:
        st.markdown(label)
    for i, vk in enumerate(VERSION_KEYS):
        with cols[i + 1]:
            versions[vk][field] = st.text_input(
                f"{label}g", value=versions[vk][field],
                key=f"{field}_{vk}", label_visibility="collapsed", placeholder="g"
            )

# ==================== 工艺流程 ====================
st.markdown('<div class="section-label">⚙️ 工艺流程</div>', unsafe_allow_html=True)
proc_labels = [
    "1.主料处理", "2.兑汁/备料", "3.滑油/煸炒", "4.炒酱料", "5.爆小料",
    "6.合炒", "7.调味/烹汁", "8.收汁出锅", "9.煮主食", "10.其他"
]
for idx, label in enumerate(proc_labels):
    field = f"proc_{idx + 1}"
    cols = st.columns(col_ratios)
    with cols[0]:
        st.markdown(label)
    for i, vk in enumerate(VERSION_KEYS):
        with cols[i + 1]:
            versions[vk][field] = st.text_input(
                f"步骤{idx + 1}", value=versions[vk][field],
                key=f"{field}_{vk}", label_visibility="collapsed", placeholder="..."
            )

# ==================== 品鉴记录 ====================
st.markdown('<div class="section-label">🔍 品鉴记录</div>', unsafe_allow_html=True)
taste_items = [
    ("观感", "taste_look"),
    ("香气", "taste_smell"),
    ("味型", "taste_flavor"),
    ("主料口感", "taste_texture"),
    ("芡汁", "taste_sauce"),
    ("搭配主食", "taste_staple"),
]

for label, field in taste_items:
    cols = st.columns(col_ratios)
    with cols[0]:
        st.markdown(label)
    for i, vk in enumerate(VERSION_KEYS):
        with cols[i + 1]:
            current = versions[vk].get(field, 'pending')
            current_note = versions[vk].get(f'{field}_note', '')
            c1, c2 = st.columns([0.6, 1])
            with c1:
                versions[vk][field] = st.selectbox(
                    f"{label}状态", ['pending', 'pass', 'fail'],
                    index=['pending', 'pass', 'fail'].index(current) if current in ['pending', 'pass',
                                                                                    'fail'] else 0,
                    format_func=taste_emoji,
                    key=f"{field}_{vk}_status",
                    label_visibility="collapsed"
                )
            with c2:
                versions[vk][f'{field}_note'] = st.text_input(
                    f"{label}备注", value=current_note,
                    key=f"{field}_{vk}_note",
                    label_visibility="collapsed", placeholder="问题"
                )

# ==================== 问题诊断 ====================
st.markdown('<div class="section-label">⚠️ 问题诊断与调整方案</div>', unsafe_allow_html=True)
for label, field in [("问题描述", "problem"), ("原因分析", "cause"), ("调整方案", "solution")]:
    cols = st.columns(col_ratios)
    with cols[0]:
        st.markdown(label)
    for i, vk in enumerate(VERSION_KEYS):
        with cols[i + 1]:
            versions[vk][field] = st.text_area(
                label, value=versions[vk][field],
                key=f"{field}_{vk}", label_visibility="collapsed", height=50, placeholder="..."
            )

# ==================== 版本结论 ====================
st.markdown('<div class="section-label">📌 版本结论</div>', unsafe_allow_html=True)
conclusion_map = {'pending': '—', 'retain': '保留优化', 'discard': '淘汰', 'finalized': '✅ 定版通过'}
cols = st.columns(col_ratios)
with cols[0]:
    st.markdown("结论")
for i, vk in enumerate(VERSION_KEYS):
    with cols[i + 1]:
        current = versions[vk].get('conclusion', 'pending')
        versions[vk]['conclusion'] = st.selectbox(
            "结论", ['pending', 'retain', 'discard', 'finalized'],
            index=['pending', 'retain', 'discard', 'finalized'].index(current) if current in ['pending', 'retain',
                                                                                               'discard',
                                                                                               'finalized'] else 0,
            format_func=lambda x: conclusion_map[x],
            key=f"conclusion_{vk}",
            label_visibility="collapsed"
        )

# ==================== 研发总结 ====================
st.markdown('<div class="section-label">📝 研发总结</div>', unsafe_allow_html=True)
sc1, sc2 = st.columns(2)
with sc1:
    data['summary']['final_recipe'] = st.text_area(
        "最终配方", value=data['summary'].get('final_recipe', ''),
        height=80, key="sum_recipe"
    )
    data['summary']['final_process'] = st.text_area(
        "最终流程（关键控制点）", value=data['summary'].get('final_process', ''),
        height=80, key="sum_process"
    )
with sc2:
    data['summary']['cost'] = st.text_input(
        "浇头成本（元/份）", value=data['summary'].get('cost', ''), key="sum_cost"
    )
    data['summary']['duration'] = st.text_input(
        "研发周期", value=data['summary'].get('duration', ''),
        key="sum_duration", placeholder="共__天，__个版本"
    )
    data['summary']['signature'] = st.text_input(
        "师傅终签", value=data['summary'].get('signature', ''), key="sum_signature"
    )

# ==================== 底部操作栏 ====================
st.divider()
col_a, col_b, col_c, col_d = st.columns(4)

with col_a:
    # 导出 JSON
    json_str = json.dumps(st.session_state.table_data, ensure_ascii=False, indent=2)
    st.download_button(
        label="📥 导出 JSON 数据",
        data=json_str,
        file_name=f"研发记录_{data['product_name']}_{datetime.now().strftime('%Y%m%d')}.json",
        mime="application/json",
        use_container_width=True,
    )

with col_b:
    # 导入 JSON
    uploaded = st.file_uploader("📤 导入 JSON", type="json", key="json_uploader", label_visibility="collapsed")
    if uploaded is not None:
        try:
            imported = json.loads(uploaded.read())
            st.session_state.table_data = imported
            st.session_state.flavor_type = imported.get('flavor_type', 'gongbao')
            st.success("✅ 导入成功！")
            st.rerun()
        except Exception as e:
            st.error(f"导入失败：{e}")

with col_c:
    # 导出 CSV
    rows = []
    for vk in VERSION_KEYS:
        ver = versions[vk]
        rows.append({
            '版本': vk.replace('\n', ' '),
            '日期': ver['date'],
            '主料': f"{ver['main_name']} {ver['main_value']}g",
            '糍粑辣椒': ver.get('chili_paste', ''),
            '红泡椒': ver.get('red_pickled', ''),
            '青泡椒': ver.get('green_pickled', ''),
            '糟辣椒': ver.get('fermented_pepper', ''),
            '蒜苗': ver.get('garlic_sprout', ''),
            '姜蒜泥': ver.get('ginger_garlic', ''),
            '大豆油': ver.get('soybean_oil', ''),
            '结论': ver.get('conclusion', ''),
        })
    df = pd.DataFrame(rows)
    csv_data = df.to_csv(index=False)
    st.download_button(
        label="📊 导出 CSV 配方表",
        data=csv_data,
        file_name=f"配方表_{data['product_name']}.csv",
        mime="text/csv",
        use_container_width=True,
    )

with col_d:
    if st.button("🖨️ 打印预览 (A4横向)", use_container_width=True):
        st.markdown("<script>window.print();</script>", unsafe_allow_html=True)


# ==================== 侧边栏：DeepSeek AI 助手 ====================
with st.sidebar:
    st.markdown("## 🤖 DeepSeek 研发助手")

    # API Key 设置
    api_key = st.text_input(
        "🔑 API Key",
        type="password",
        value=st.session_state.deepseek_key,
        placeholder="sk-...",
        help="在 https://platform.deepseek.com/api_keys 获取。\nStreamlit Cloud 可在 Settings > Secrets 设置 DEEPSEEK_API_KEY。"
    )
    if api_key != st.session_state.deepseek_key:
        st.session_state.deepseek_key = api_key

    st.divider()

    # 快捷按钮
    st.markdown("**快捷指令：**")
    qc1, qc2 = st.columns(2)
    with qc1:
        if st.button("🔍 分析配方", use_container_width=True):
            with st.spinner("分析中..."):
                reply = quick_analyze()
            st.session_state.chat_history.append({"role": "user", "content": "🔍 分析当前配方"})
            st.session_state.chat_history.append({"role": "assistant", "content": reply})
            st.rerun()
    with qc2:
        if st.button("📋 对比版本", use_container_width=True):
            with st.spinner("分析中..."):
                reply = quick_compare()
            st.session_state.chat_history.append({"role": "user", "content": "📋 对比版本差异"})
            st.session_state.chat_history.append({"role": "assistant", "content": reply})
            st.rerun()

    qc3, qc4 = st.columns(2)
    with qc3:
        if st.button("💡 优化建议", use_container_width=True):
            with st.spinner("思考中..."):
                reply = quick_suggest()
            st.session_state.chat_history.append({"role": "user", "content": "💡 请给优化建议"})
            st.session_state.chat_history.append({"role": "assistant", "content": reply})
            st.rerun()
    with qc4:
        if st.button("🧹 清空对话", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()

    st.divider()

    # 对话区域
    st.markdown("**对话记录：**")
    with st.container(height=380):
        if not st.session_state.chat_history:
            st.info("👋 你好！我可以帮你分析配方、对比版本、给出优化建议。\n\n试试点击上面的快捷按钮，或在下方输入你的问题。")
        else:
            for msg in st.session_state.chat_history:
                if msg['role'] == 'user':
                    with st.chat_message("user"):
                        st.markdown(msg['content'])
                else:
                    with st.chat_message("assistant"):
                        st.markdown(msg['content'])

    # 对话输入
    user_msg = st.chat_input("输入你的问题...")
    if user_msg:
        st.session_state.chat_history.append({"role": "user", "content": user_msg})
        with st.spinner("思考中..."):
            ctx = build_table_context()
            messages = [
                {"role": "system",
                 "content": "你是贵州菜品研发专家助手。根据用户的问题和当前研发记录数据，给出专业、具体的回答。可以引用表格中的具体数据。用中文回答。"},
                {"role": "user", "content": f"当前研发记录数据：\n\n{ctx}\n\n用户问题：{user_msg}"}
            ]
            reply = call_deepseek(messages)
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        st.rerun()

# ==================== 页脚 ====================
st.divider()
st.caption(
    "贵州盖浇面/饭 · 菜品研发过程记录表 | "
    "宫保（糊辣荔枝）味型：糍粑辣椒 + 宫保汁（兑碗汁） | "
    "泡椒（酸辣）味型：红泡椒+青泡椒+糟辣椒 + 独立调料（直接撒入，不兑汁） | "
    "Powered by Streamlit + DeepSeek"
)
