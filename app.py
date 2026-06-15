"""
贵州盖浇面/饭 · 菜品研发过程记录表
Streamlit 应用 - 支持配方动态增减
"""

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from openai import OpenAI

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="贵州盖浇面/饭·研发记录表",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==================== 常量 ====================
VERSION_KEYS = ['V1.0\n首次试做', 'V1.1\n调整', 'V1.2\n调整', 'V2.0\n改版', '终版\n定型']
VERSION_LABELS = ['V1.0（首次试做）', 'V1.1（调整）', 'V1.2（调整）', 'V2.0（改版）', '终版定型']
NUM_V = len(VERSION_KEYS)

# ==================== CSS ====================
st.markdown("""
<style>
    .stApp { background-color: #1a1a2e; }
    .main-title {
        font-size: 1.5rem; font-weight: 700; color: #e94560;
        text-align: center; padding: 8px 0; letter-spacing: 1px;
        border-bottom: 2px solid #e94560; margin-bottom: 12px;
    }
    .main-title span { color: #fff; }
    .section-label {
        font-weight: 700; font-size: 0.9rem; color: #e94560;
        margin-top: 10px; margin-bottom: 6px;
        padding: 5px 10px; background: rgba(233,68,96,0.1);
        border-radius: 4px; border-left: 3px solid #e94560;
    }
    .stButton > button { border-radius: 6px; font-weight: 500; }
    .stTextInput input, .stTextArea textarea {
        font-size: 0.78rem !important; padding: 2px 4px !important;
    }
    .delete-btn button {
        background: transparent !important;
        border: 1px solid #e94560 !important;
        color: #e94560 !important;
        padding: 2px 8px !important;
        font-size: 0.7rem !important;
    }
    .add-btn button {
        background: transparent !important;
        border: 1px dashed #0f9 !important;
        color: #0f9 !important;
        font-size: 0.78rem !important;
    }
    @media print {
        header[data-testid="stHeader"], .stSidebar, .stDeployButton,
        [data-testid="stToolbar"], [data-testid="stDecoration"],
        iframe, .stDownloadButton, hr, .delete-btn, .add-btn {
            display: none !important;
        }
        .stApp { background: #fff !important; }
        .main-title { color: #000 !important; border-bottom-color: #000 !important; }
        .main-title span { color: #000 !important; }
        .section-label { color: #000 !important; background: #f0f0f0 !important; border-left-color: #000 !important; }
        body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    }
</style>
""", unsafe_allow_html=True)

# ==================== Session State ====================
if 'table_data' not in st.session_state:
    st.session_state.table_data = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'flavor_type' not in st.session_state:
    st.session_state.flavor_type = "gongbao"
if 'deepseek_key' not in st.session_state:
    st.session_state.deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
if 'recipe_rows' not in st.session_state:
    st.session_state.recipe_rows = []

try:
    if st.secrets.get("DEEPSEEK_API_KEY"):
        st.session_state.deepseek_key = st.secrets["DEEPSEEK_API_KEY"]
except:
    pass


# ==================== 数据模板 ====================
def create_version_data(flavor_type, is_first=False):
    return {
        'date': '',
        'purpose': '搭建基础味型框架' if is_first else '',
        'proc_1': '', 'proc_2': '', 'proc_3': '', 'proc_4': '', 'proc_5': '',
        'proc_6': '', 'proc_7': '', 'proc_8': '', 'proc_9': '', 'proc_10': '',
        'taste_look': 'pending', 'taste_look_note': '',
        'taste_smell': 'pending', 'taste_smell_note': '',
        'taste_flavor': 'pending', 'taste_flavor_note': '',
        'taste_texture': 'pending', 'taste_texture_note': '',
        'taste_sauce': 'pending', 'taste_sauce_note': '',
        'taste_staple': 'pending', 'taste_staple_note': '',
        'problem': '', 'cause': '', 'solution': '',
        'conclusion': 'retain' if is_first else 'pending',
    }


def get_default_recipe_rows(flavor_type):
    is_gongbao = (flavor_type == "gongbao")
    if is_gongbao:
        return [
            {'category': '主料', 'name': '鸡腿肉丁', 'values': ['120', '', '', '', '']},
            {'category': '辣椒酱料', 'name': '糍粑辣椒', 'values': ['50', '', '', '', '']},
            {'category': '宫保汁（兑碗汁）', 'name': '甜酱', 'values': ['', '', '', '', '']},
            {'category': '宫保汁（兑碗汁）', 'name': '酱油', 'values': ['', '', '', '', '']},
            {'category': '宫保汁（兑碗汁）', 'name': '醋', 'values': ['', '', '', '', '']},
            {'category': '宫保汁（兑碗汁）', 'name': '味精', 'values': ['', '', '', '', '']},
            {'category': '宫保汁（兑碗汁）', 'name': '白糖', 'values': ['', '', '', '', '']},
            {'category': '宫保汁（兑碗汁）', 'name': '水淀粉', 'values': ['', '', '', '', '']},
            {'category': '宫保汁（兑碗汁）', 'name': '高汤/水', 'values': ['', '', '', '', '']},
            {'category': '辅料', 'name': '蒜苗', 'values': ['30', '', '', '', '']},
            {'category': '辅料', 'name': '姜蒜泥', 'values': ['20', '', '', '', '']},
            {'category': '烹调用油', 'name': '大豆油', 'values': ['50', '', '', '', '']},
        ]
    else:
        return [
            {'category': '主料', 'name': '鳝鱼', 'values': ['120', '', '', '', '']},
            {'category': '辣椒酱料', 'name': '红泡椒', 'values': ['20', '', '', '', '']},
            {'category': '辣椒酱料', 'name': '青泡椒', 'values': ['20', '', '', '', '']},
            {'category': '辣椒酱料', 'name': '糟辣椒', 'values': ['10', '', '', '', '']},
            {'category': '独立调料（直接撒入）', 'name': '味精', 'values': ['3', '', '', '', '']},
            {'category': '独立调料（直接撒入）', 'name': '酱油', 'values': ['3', '', '', '', '']},
            {'category': '独立调料（直接撒入）', 'name': '醋', 'values': ['3', '', '', '', '']},
            {'category': '独立调料（直接撒入）', 'name': '淀粉', 'values': ['3', '', '', '', '']},
            {'category': '辅料', 'name': '蒜苗', 'values': ['30', '', '', '', '']},
            {'category': '辅料', 'name': '姜蒜泥', 'values': ['20', '', '', '', '']},
            {'category': '烹调用油', 'name': '大豆油', 'values': ['50', '', '', '', '']},
        ]


def get_default_data(flavor_type):
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


if st.session_state.table_data is None:
    st.session_state.table_data = get_default_data("gongbao")
    st.session_state.recipe_rows = get_default_recipe_rows("gongbao")


# ==================== 辅助函数 ====================
def taste_emoji(val):
    m = {'pending': '—', 'pass': '✅', 'fail': '❌'}
    return m.get(val, '—')


def taste_text(val):
    m = {'pending': '—', 'pass': '达标', 'fail': '不达标'}
    return m.get(val, '—')


def conclusion_text(val):
    m = {'pending': '—', 'retain': '保留优化', 'discard': '淘汰', 'finalized': '定版通过'}
    return m.get(val, '—')


def build_context():
    data = st.session_state.table_data
    rows = st.session_state.recipe_rows
    ctx = f"产品：{data['product_name']}，味型：{data['flavor_label']}\n"
    ctx += f"出品结构：{data.get('structure', '')}\n\n"
    for vi, vk in enumerate(VERSION_KEYS):
        ver = data['versions'][vk]
        ctx += f"【{vk.replace(chr(10), ' ')}】日期：{ver['date']}，目的：{ver['purpose']}\n"
        for r in rows:
            val = r['values'][vi] if vi < len(r['values']) else ''
            if val:
                ctx += f"{r['category']} - {r['name']}：{val}g\n"
        tastes = []
        for tk, tl in [('taste_look', '观感'), ('taste_smell', '香气'), ('taste_flavor', '味型'),
                       ('taste_texture', '口感'), ('taste_sauce', '芡汁'), ('taste_staple', '配主食')]:
            s = ver.get(tk, 'pending')
            n = ver.get(f'{tk}_note', '')
            if s == 'fail':
                tastes.append(f"{tl}❌({n})")
            elif s == 'pass':
                tastes.append(f"{tl}✅")
        if tastes:
            ctx += f"品鉴：{' '.join(tastes)}\n"
        ctx += f"结论：{ver.get('conclusion', '')}\n\n"
    return ctx


def call_deepseek(messages):
    api_key = st.session_state.deepseek_key
    if not api_key:
        return "⚠️ 请先设置 DeepSeek API Key。\nhttps://platform.deepseek.com/api_keys"
    try:
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        resp = client.chat.completions.create(
            model="deepseek-chat", messages=messages,
            temperature=0.7, max_tokens=2000,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"❌ API 调用失败：{str(e)}"


def build_export_csv():
    """
    构建导出 CSV：和页面表格结构一致
    格式：
    区块标题行（如"📋 配方记录"）
    项目, 类别, 原料名称, V1.0, V1.1, V1.2, V2.0, 终版
    """
    data = st.session_state.table_data
    rows = st.session_state.recipe_rows
    versions = data['versions']

    lines = []

    # ===== 表头信息 =====
    lines.append(f"产品名称,{data['product_name']}")
    lines.append(f"味型,{data['flavor_label']}")
    lines.append(f"出品结构,{data.get('structure', '')}")
    lines.append(f"研发师傅,{data.get('chef', '')}")
    lines.append(f"记录人,{data.get('recorder', '')}")
    lines.append("")

    # ===== 日期 =====
    header = "项目,," + ",".join([vk.replace('\n', ' ') for vk in VERSION_KEYS])
    lines.append(header)
    lines.append("日期,," + ",".join([versions[vk]['date'] for vk in VERSION_KEYS]))
    lines.append("研发目的,," + ",".join([versions[vk]['purpose'] for vk in VERSION_KEYS]))
    lines.append("")

    # ===== 配方记录 =====
    lines.append("【配方记录】")
    lines.append(header)
    for r in rows:
        vals = [r['values'][vi] if vi < len(r['values']) else '' for vi in range(NUM_V)]
        lines.append(f",{r['category']},{r['name']}," + ",".join(vals))
    lines.append("")

    # ===== 工艺流程 =====
    lines.append("【工艺流程】")
    lines.append(header)
    proc_labels = [
        "1.主料处理", "2.兑汁/备料", "3.滑油/煸炒", "4.炒酱料", "5.爆小料",
        "6.合炒", "7.调味/烹汁", "8.收汁出锅", "9.煮主食", "10.其他"
    ]
    for idx, lb in enumerate(proc_labels):
        vals = [versions[vk].get(f'proc_{idx + 1}', '') for vk in VERSION_KEYS]
        lines.append(f",,{lb}," + ",".join(vals))
    lines.append("")

    # ===== 品鉴记录 =====
    lines.append("【品鉴记录】")
    lines.append(header)
    for lb, fd in [("观感", "taste_look"), ("香气", "taste_smell"), ("味型", "taste_flavor"),
                   ("主料口感", "taste_texture"), ("芡汁", "taste_sauce"), ("搭配主食", "taste_staple")]:
        statuses = [taste_text(versions[vk].get(fd, 'pending')) for vk in VERSION_KEYS]
        notes = [versions[vk].get(f'{fd}_note', '') for vk in VERSION_KEYS]
        lines.append(f",,{lb}（状态）," + ",".join(statuses))
        lines.append(f",,{lb}（备注）," + ",".join(notes))
    lines.append("")

    # ===== 问题诊断 =====
    lines.append("【问题诊断与调整】")
    lines.append(header)
    for lb, fd in [("问题描述", "problem"), ("原因分析", "cause"), ("调整方案", "solution")]:
        vals = [versions[vk].get(fd, '') for vk in VERSION_KEYS]
        lines.append(f",,{lb}," + ",".join(vals))
    lines.append("")

    # ===== 版本结论 =====
    lines.append("【版本结论】")
    lines.append(header)
    vals = [conclusion_text(versions[vk].get('conclusion', 'pending')) for vk in VERSION_KEYS]
    lines.append(f",,结论," + ",".join(vals))
    lines.append("")

    # ===== 研发总结 =====
    lines.append("【研发总结】")
    lines.append(f"最终配方,{data['summary'].get('final_recipe', '')}")
    lines.append(f"最终流程,{data['summary'].get('final_process', '')}")
    lines.append(f"浇头成本（元/份）,{data['summary'].get('cost', '')}")
    lines.append(f"研发周期,{data['summary'].get('duration', '')}")
    lines.append(f"师傅终签,{data['summary'].get('signature', '')}")

    return "\n".join(lines)


def add_recipe_row():
    st.session_state.recipe_rows.append({
        'category': '',
        'name': '',
        'values': ['', '', '', '', ''],
    })


def delete_recipe_row(idx):
    if len(st.session_state.recipe_rows) > 1:
        st.session_state.recipe_rows.pop(idx)


def switch_flavor(new_flavor):
    st.session_state.flavor_type = new_flavor
    st.session_state.table_data = get_default_data(new_flavor)
    st.session_state.recipe_rows = get_default_recipe_rows(new_flavor)


# ==================== 主界面 ====================
st.markdown('<div class="main-title">🔥 <span>贵州盖浇面/饭</span> · 菜品研发过程记录表</div>', unsafe_allow_html=True)

# ---- 顶部信息 ----
c1, c2, c3, c4, c5, c6 = st.columns([2, 1.5, 1, 1, 0.8, 0.8])
with c1:
    st.session_state.table_data['product_name'] = st.text_input(
        "产品名称", value=st.session_state.table_data['product_name'],
        key="pn", label_visibility="collapsed"
    )
with c2:
    fm = {"gongbao": "宫保鸡丁（糊辣荔枝）", "paojiao": "泡椒鳝鱼（酸辣）"}
    current_idx = 0 if st.session_state.flavor_type == "gongbao" else 1
    sf = st.selectbox("味型", list(fm.keys()), format_func=lambda x: fm[x],
                      index=current_idx, key="flv", label_visibility="collapsed")
    if sf != st.session_state.flavor_type:
        switch_flavor(sf)
        st.rerun()
with c3:
    st.session_state.table_data['chef'] = st.text_input(
        "师傅", value=st.session_state.table_data.get('chef', ''),
        key="chf", label_visibility="collapsed", placeholder="研发师傅"
    )
with c4:
    st.session_state.table_data['recorder'] = st.text_input(
        "记录人", value=st.session_state.table_data.get('recorder', ''),
        key="rcr", label_visibility="collapsed", placeholder="记录人"
    )
with c5:
    if st.button("🔄 重置", use_container_width=True):
        switch_flavor(st.session_state.flavor_type)
        st.rerun()
with c6:
    st.components.v1.html("""
    <button onclick="window.print()" style="
        width:100%; padding:8px; border-radius:6px; border:1px solid #0f9;
        background:#0f3460; color:#0f9; font-weight:600; cursor:pointer;
        font-size:0.85rem; font-family:inherit;
    ">🖨️ 打印</button>
    """, height=40)

st.session_state.table_data['structure'] = st.text_input(
    "出品结构", value=st.session_state.table_data.get('structure', ''),
    key="struc", placeholder="宽面280g / 细面250g / 天麻面280g / 米饭250g"
)

data = st.session_state.table_data
versions = data['versions']
recipe_rows = st.session_state.recipe_rows

# ==================== 表格渲染 ====================
FULL_COLS = [1.0, 1.0] + [1] * NUM_V
PROC_COLS = [2.0] + [1] * NUM_V

# 表头
cols = st.columns(FULL_COLS)
with cols[0]:
    st.markdown("**类别**")
with cols[1]:
    st.markdown("**原料名称**")
for i, vk in enumerate(VERSION_KEYS):
    with cols[i + 2]:
        st.markdown(f"**{vk.replace(chr(10), '<br>')}**", unsafe_allow_html=True)
st.divider()

# 日期 & 目的
cols = st.columns(FULL_COLS)
with cols[0]:
    st.markdown("**📅 日期**")
with cols[1]:
    st.markdown("**🎯 研发目的**")
for i, vk in enumerate(VERSION_KEYS):
    with cols[i + 2]:
        versions[vk]['date'] = st.text_input("日期", value=versions[vk]['date'],
                                             key=f"date_{vk}", label_visibility="collapsed", placeholder="月/日")
        versions[vk]['purpose'] = st.text_input("目的", value=versions[vk]['purpose'],
                                                key=f"purpose_{vk}", label_visibility="collapsed", placeholder="目的...")
st.divider()

# ==================== 配方记录（动态行） ====================
st.markdown(
    '<div class="section-label">📋 配方记录 <span style="font-weight:400;font-size:0.75rem;">（可自由增删行）</span></div>',
    unsafe_allow_html=True)

delete_idx = None
for ri, row in enumerate(recipe_rows):
    cols = st.columns(FULL_COLS)
    with cols[0]:
        row['category'] = st.text_input(
            f"类别{ri}", value=row['category'],
            key=f"cat_{ri}", label_visibility="collapsed",
            placeholder="如：主料、辅料..."
        )
    with cols[1]:
        nc1, nc2 = st.columns([3, 1])
        with nc1:
            row['name'] = st.text_input(
                f"原料{ri}", value=row['name'],
                key=f"name_{ri}", label_visibility="collapsed",
                placeholder="原料名称"
            )
        with nc2:
            st.markdown('<div class="delete-btn">', unsafe_allow_html=True)
            if st.button("✕", key=f"del_{ri}", help="删除此行"):
                delete_idx = ri
            st.markdown('</div>', unsafe_allow_html=True)
    for vi in range(NUM_V):
        with cols[vi + 2]:
            while len(row['values']) <= vi:
                row['values'].append('')
            row['values'][vi] = st.text_input(
                f"值{ri}_{vi}", value=row['values'][vi],
                key=f"val_{ri}_{vi}", label_visibility="collapsed",
                placeholder="g"
            )

if delete_idx is not None:
    delete_recipe_row(delete_idx)
    st.rerun()

st.markdown('<div class="add-btn">', unsafe_allow_html=True)
if st.button("＋ 添加一行配方", use_container_width=True, key="add_recipe"):
    add_recipe_row()
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# ==================== 工艺流程 ====================
st.markdown('<div class="section-label">⚙️ 工艺流程</div>', unsafe_allow_html=True)
proc_labels = [
    "1.主料处理", "2.兑汁/备料", "3.滑油/煸炒", "4.炒酱料", "5.爆小料",
    "6.合炒", "7.调味/烹汁", "8.收汁出锅", "9.煮主食", "10.其他"
]
for idx, lb in enumerate(proc_labels):
    cols = st.columns(PROC_COLS)
    with cols[0]:
        st.markdown(f"<small>{lb}</small>", unsafe_allow_html=True)
    for i, vk in enumerate(VERSION_KEYS):
        with cols[i + 1]:
            versions[vk][f'proc_{idx + 1}'] = st.text_input(
                f"步骤{idx + 1}", value=versions[vk][f'proc_{idx + 1}'],
                key=f"proc_{idx + 1}_{vk}", label_visibility="collapsed", placeholder="..."
            )

# ==================== 品鉴记录 ====================
st.markdown('<div class="section-label">🔍 品鉴记录</div>', unsafe_allow_html=True)
for lb, fd in [("观感", "taste_look"), ("香气", "taste_smell"), ("味型", "taste_flavor"),
               ("主料口感", "taste_texture"), ("芡汁", "taste_sauce"), ("搭配主食", "taste_staple")]:
    cols = st.columns(PROC_COLS)
    with cols[0]:
        st.markdown(f"<small>{lb}</small>", unsafe_allow_html=True)
    for i, vk in enumerate(VERSION_KEYS):
        with cols[i + 1]:
            sc1, sc2 = st.columns([0.5, 1])
            with sc1:
                cur = versions[vk].get(fd, 'pending')
                opts = ['pending', 'pass', 'fail']
                idx = opts.index(cur) if cur in opts else 0
                versions[vk][fd] = st.selectbox(
                    f"{lb}状态", opts, index=idx, format_func=taste_emoji,
                    key=f"{fd}_{vk}_s", label_visibility="collapsed"
                )
            with sc2:
                versions[vk][f'{fd}_note'] = st.text_input(
                    f"{lb}备注", value=versions[vk].get(f'{fd}_note', ''),
                    key=f"{fd}_{vk}_n", label_visibility="collapsed", placeholder="备注"
                )

# ==================== 问题诊断 ====================
st.markdown('<div class="section-label">⚠️ 问题诊断与调整</div>', unsafe_allow_html=True)
for lb, fd in [("问题描述", "problem"), ("原因分析", "cause"), ("调整方案", "solution")]:
    cols = st.columns(PROC_COLS)
    with cols[0]:
        st.markdown(f"<small>{lb}</small>", unsafe_allow_html=True)
    for i, vk in enumerate(VERSION_KEYS):
        with cols[i + 1]:
            versions[vk][fd] = st.text_area(
                lb, value=versions[vk][fd],
                key=f"{fd}_{vk}", label_visibility="collapsed", height=50, placeholder="..."
            )

# ==================== 版本结论 ====================
st.markdown('<div class="section-label">📌 版本结论</div>', unsafe_allow_html=True)
conclusion_opts = ['pending', 'retain', 'discard', 'finalized']
conclusion_fmt = lambda x: {'pending': '—', 'retain': '保留优化', 'discard': '淘汰', 'finalized': '✅ 定版'}[x]
cols = st.columns(PROC_COLS)
with cols[0]:
    st.markdown("<small>结论</small>", unsafe_allow_html=True)
for i, vk in enumerate(VERSION_KEYS):
    with cols[i + 1]:
        cur = versions[vk].get('conclusion', 'pending')
        idx = conclusion_opts.index(cur) if cur in conclusion_opts else 0
        versions[vk]['conclusion'] = st.selectbox(
            "结论", conclusion_opts, index=idx, format_func=conclusion_fmt,
            key=f"conclusion_{vk}", label_visibility="collapsed"
        )

# ==================== 研发总结 ====================
st.markdown('<div class="section-label">📝 研发总结</div>', unsafe_allow_html=True)
sc1, sc2 = st.columns(2)
with sc1:
    data['summary']['final_recipe'] = st.text_area("最终配方", value=data['summary'].get('final_recipe', ''),
                                                   height=80, key="sr")
    data['summary']['final_process'] = st.text_area("最终流程（关键控制点）",
                                                    value=data['summary'].get('final_process', ''), height=80, key="sp")
with sc2:
    data['summary']['cost'] = st.text_input("浇头成本（元/份）", value=data['summary'].get('cost', ''), key="sc")
    data['summary']['duration'] = st.text_input("研发周期", value=data['summary'].get('duration', ''),
                                                key="sd", placeholder="共__天，__个版本")
    data['summary']['signature'] = st.text_input("师傅终签", value=data['summary'].get('signature', ''), key="ss")

# ==================== 底部按钮 ====================
st.divider()
b1, b2, b3 = st.columns(3)
with b1:
    export_data = {**data, 'recipe_rows': st.session_state.recipe_rows}
    st.download_button(
        "📥 导出 JSON",
        json.dumps(export_data, ensure_ascii=False, indent=2),
        f"研发记录_{data['product_name']}_{datetime.now().strftime('%Y%m%d')}.json",
        "application/json",
        use_container_width=True,
    )
with b2:
    uf = st.file_uploader("📤 导入 JSON", type="json", key="jup", label_visibility="collapsed")
    if uf:
        try:
            imported = json.loads(uf.read())
            st.session_state.recipe_rows = imported.pop('recipe_rows', get_default_recipe_rows(
                imported.get('flavor_type', 'gongbao')))
            st.session_state.table_data = imported
            st.session_state.flavor_type = imported.get('flavor_type', 'gongbao')
            st.success("✅ 导入成功")
            st.rerun()
        except Exception as e:
            st.error(f"导入失败：{e}")
with b3:
    csv_content = build_export_csv()
    st.download_button(
        "📊 导出 CSV（与页面表格一致）",
        csv_content,
        f"研发记录表_{data['product_name']}_{datetime.now().strftime('%Y%m%d')}.csv",
        "text/csv",
        use_container_width=True,
    )

# ==================== 侧边栏 ====================
with st.sidebar:
    st.markdown("## 🤖 DeepSeek 研发助手")
    ak = st.text_input("🔑 API Key", type="password", value=st.session_state.deepseek_key,
                       placeholder="sk-...", help="https://platform.deepseek.com/api_keys")
    if ak != st.session_state.deepseek_key:
        st.session_state.deepseek_key = ak
    st.divider()
    st.markdown("**快捷指令：**")
    q1, q2 = st.columns(2)
    with q1:
        if st.button("🔍 分析配方", use_container_width=True):
            with st.spinner("分析中..."):
                msgs = [{"role": "system",
                         "content": "你是贵州菜品研发专家。分析配方合理性，指出问题，给出具体建议。用中文。"},
                        {"role": "user", "content": f"分析以下研发记录：\n\n{build_context()}"}]
                rep = call_deepseek(msgs)
            st.session_state.chat_history += [{"role": "user", "content": "🔍 分析配方"},
                                              {"role": "assistant", "content": rep}]
            st.rerun()
    with q2:
        if st.button("📋 对比版本", use_container_width=True):
            with st.spinner("分析中..."):
                msgs = [{"role": "system",
                         "content": "你是贵州菜品研发专家。对比各版本变化，分析调整意图和效果。用中文。"},
                        {"role": "user", "content": f"对比版本差异：\n\n{build_context()}"}]
                rep = call_deepseek(msgs)
            st.session_state.chat_history += [{"role": "user", "content": "📋 对比版本"},
                                              {"role": "assistant", "content": rep}]
            st.rerun()
    q3, q4 = st.columns(2)
    with q3:
        if st.button("💡 优化建议", use_container_width=True):
            with st.spinner("思考中..."):
                msgs = [{"role": "system",
                         "content": "你是贵州菜品研发专家。给出3-5条具体优化建议，要具体到克数或操作。用中文。"},
                        {"role": "user", "content": f"基于以下记录给优化建议：\n\n{build_context()}"}]
                rep = call_deepseek(msgs)
            st.session_state.chat_history += [{"role": "user", "content": "💡 优化建议"},
                                              {"role": "assistant", "content": rep}]
            st.rerun()
    with q4:
        if st.button("🧹 清空", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()
    st.divider()
    st.markdown("**对话记录：**")
    with st.container(height=380):
        if not st.session_state.chat_history:
            st.info("👋 点击快捷按钮或输入问题开始对话")
        else:
            for m in st.session_state.chat_history:
                with st.chat_message(m['role']):
                    st.markdown(m['content'])
    um = st.chat_input("输入问题...")
    if um:
        st.session_state.chat_history.append({"role": "user", "content": um})
        with st.spinner("思考中..."):
            msgs = [{"role": "system",
                     "content": "你是贵州菜品研发专家。根据研发记录和用户问题，给出专业回答。用中文。"},
                    {"role": "user", "content": f"研发记录：\n\n{build_context()}\n\n用户问题：{um}"}]
            rep = call_deepseek(msgs)
        st.session_state.chat_history.append({"role": "assistant", "content": rep})
        st.rerun()

st.divider()
st.caption(
    "贵州盖浇面/饭 · 菜品研发过程记录表 | 配方行可自由增删 | 宫保：糍粑辣椒+宫保汁（兑碗汁） | 泡椒：红泡椒+青泡椒+糟辣椒+独立调料（直接撒入） | Powered by Streamlit + DeepSeek")
