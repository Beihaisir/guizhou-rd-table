"""
贵州盖浇面/饭 · 菜品研发过程记录表
Streamlit 应用 - 部署到 Streamlit Cloud
"""

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from openai import OpenAI
import base64

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
        margin-top: 10px; margin-bottom: 4px;
        padding: 5px 10px; background: rgba(233,68,96,0.1);
        border-radius: 4px; border-left: 3px solid #e94560;
    }
    .stButton > button { border-radius: 6px; font-weight: 500; }
    .stTextInput input, .stTextArea textarea {
        font-size: 0.78rem !important; padding: 2px 4px !important;
    }
    /* 打印样式 - 使用 @media print 实现真正的浏览器打印 */
    @media print {
        /* 隐藏 Streamlit 自带元素 */
        header[data-testid="stHeader"],
        .stSidebar,
        .stDeployButton,
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        iframe,
        .stDownloadButton,
        hr {
            display: none !important;
        }
        /* 白色背景 */
        .stApp {
            background: #fff !important;
        }
        .main-title {
            color: #000 !important;
            border-bottom-color: #000 !important;
        }
        .main-title span { color: #000 !important; }
        .section-label {
            color: #000 !important;
            background: #f0f0f0 !important;
            border-left-color: #000 !important;
        }
        /* 确保表格可见 */
        .stMainBlockContainer {
            max-width: 100% !important;
            padding: 0 !important;
        }
        body {
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }
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
if 'trigger_print' not in st.session_state:
    st.session_state.trigger_print = False

try:
    if st.secrets.get("DEEPSEEK_API_KEY"):
        st.session_state.deepseek_key = st.secrets["DEEPSEEK_API_KEY"]
except:
    pass


# ==================== 数据模板 ====================
def create_version_data(flavor_type, is_first=False):
    is_gongbao = (flavor_type == "gongbao")
    return {
        'date': '',
        'purpose': '搭建基础味型框架' if is_first else '',
        'main_name': '鸡腿肉丁' if is_gongbao else '鳝鱼',
        'main_value': '120' if is_first else '',
        'chili_paste': '50' if (is_first and is_gongbao) else '',
        'red_pickled': '20' if (is_first and not is_gongbao) else '',
        'green_pickled': '20' if (is_first and not is_gongbao) else '',
        'fermented_pepper': '10' if (is_first and not is_gongbao) else '',
        'gb_sweet': '', 'gb_soy': '', 'gb_vinegar': '',
        'gb_msg': '', 'gb_sugar': '', 'gb_starch': '', 'gb_broth': '', 'gb_other': '',
        'sp_msg': '3' if (is_first and not is_gongbao) else '',
        'sp_soy': '3' if (is_first and not is_gongbao) else '',
        'sp_vinegar': '3' if (is_first and not is_gongbao) else '',
        'sp_starch': '3' if (is_first and not is_gongbao) else '',
        'sp_salt': '', 'sp_sugar': '', 'sp_other': '',
        'garlic_sprout': '30' if is_first else '',
        'ginger_garlic': '20' if is_first else '',
        'aux_other': '',
        'soybean_oil': '50' if is_first else '',
        'other_oil': '',
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


# ==================== 辅助函数 ====================
def taste_emoji(val):
    m = {'pending': '—', 'pass': '✅', 'fail': '❌'}
    return m.get(val, '—')


def build_context():
    data = st.session_state.table_data
    ctx = f"产品：{data['product_name']}，味型：{data['flavor_label']}\n"
    ctx += f"出品结构：{data.get('structure', '')}\n\n"
    for vk in VERSION_KEYS:
        ver = data['versions'][vk]
        ctx += f"【{vk.replace(chr(10), ' ')}】日期：{ver['date']}，目的：{ver['purpose']}\n"
        ctx += f"主料：{ver['main_name']} {ver['main_value']}g\n"
        if data['flavor_type'] == "gongbao":
            ctx += f"糍粑辣椒：{ver.get('chili_paste', '')}g\n"
            ctx += f"宫保汁：甜酱{ver.get('gb_sweet', '')}g 酱油{ver.get('gb_soy', '')}g 醋{ver.get('gb_vinegar', '')}g 味精{ver.get('gb_msg', '')}g 白糖{ver.get('gb_sugar', '')}g 淀粉{ver.get('gb_starch', '')}g\n"
        else:
            ctx += f"红泡椒{ver.get('red_pickled', '')}g 青泡椒{ver.get('green_pickled', '')}g 糟辣椒{ver.get('fermented_pepper', '')}g\n"
            ctx += f"调料：味精{ver.get('sp_msg', '')}g 酱油{ver.get('sp_soy', '')}g 醋{ver.get('sp_vinegar', '')}g 淀粉{ver.get('sp_starch', '')}g\n"
        ctx += f"辅料：蒜苗{ver.get('garlic_sprout', '')}g 姜蒜泥{ver.get('ginger_garlic', '')}g 大豆油{ver.get('soybean_oil', '')}g\n"
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
        return "⚠️ 请先在侧边栏设置 DeepSeek API Key。\n获取：https://platform.deepseek.com/api_keys"
    try:
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        resp = client.chat.completions.create(
            model="deepseek-chat", messages=messages,
            temperature=0.7, max_tokens=2000,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"❌ API 调用失败：{str(e)}"


def build_full_csv():
    """
    构建完整的菜品研发记录 CSV，包含所有字段：
    配方、工艺流程、品鉴、问题诊断、结论、研发总结
    """
    data = st.session_state.table_data
    is_gongbao = (data['flavor_type'] == "gongbao")

    rows = []
    for vk in VERSION_KEYS:
        ver = data['versions'][vk]

        # 基础信息
        row = {
            '产品名称': data['product_name'],
            '味型': data['flavor_label'],
            '出品结构': data.get('structure', ''),
            '研发师傅': data.get('chef', ''),
            '记录人': data.get('recorder', ''),
            '版本': vk.replace('\n', ' '),
            '日期': ver['date'],
            '研发目的': ver['purpose'],
            # 配方
            '主料名称': ver['main_name'],
            '主料用量(g)': ver['main_value'],
        }

        # 辣椒酱料
        if is_gongbao:
            row['糍粑辣椒(g)'] = ver.get('chili_paste', '')
            row['红泡椒(g)'] = ''
            row['青泡椒(g)'] = ''
            row['糟辣椒(g)'] = ''
        else:
            row['糍粑辣椒(g)'] = ''
            row['红泡椒(g)'] = ver.get('red_pickled', '')
            row['青泡椒(g)'] = ver.get('green_pickled', '')
            row['糟辣椒(g)'] = ver.get('fermented_pepper', '')

        # 汁料
        if is_gongbao:
            row['调味方式'] = '宫保汁（兑碗汁）'
            row['甜酱(g)'] = ver.get('gb_sweet', '')
            row['酱油(g)'] = ver.get('gb_soy', '')
            row['醋(g)'] = ver.get('gb_vinegar', '')
            row['味精(g)'] = ver.get('gb_msg', '')
            row['白糖(g)'] = ver.get('gb_sugar', '')
            row['水淀粉(g)'] = ver.get('gb_starch', '')
            row['高汤/水(g)'] = ver.get('gb_broth', '')
            row['其他汁料(g)'] = ver.get('gb_other', '')
            # 独立调料清空
            for k in ['sp_msg', 'sp_soy', 'sp_vinegar', 'sp_starch', 'sp_salt', 'sp_sugar', 'sp_other']:
                row[f'独立_{k}(g)'] = ''
        else:
            row['调味方式'] = '独立调料（直接撒入，不兑汁）'
            # 宫保汁清空
            for k in ['gb_sweet', 'gb_soy', 'gb_vinegar', 'gb_msg', 'gb_sugar', 'gb_starch', 'gb_broth', 'gb_other']:
                row[f'宫保_{k}(g)'] = ''
            row['味精(g)'] = ver.get('sp_msg', '')
            row['酱油(g)'] = ver.get('sp_soy', '')
            row['醋(g)'] = ver.get('sp_vinegar', '')
            row['淀粉(g)'] = ver.get('sp_starch', '')
            row['盐(g)'] = ver.get('sp_salt', '')
            row['白糖(g)'] = ver.get('sp_sugar', '')
            row['其他调料(g)'] = ver.get('sp_other', '')

        # 辅料
        row['蒜苗(g)'] = ver.get('garlic_sprout', '')
        row['姜蒜泥(g)'] = ver.get('ginger_garlic', '')
        row['其他辅料'] = ver.get('aux_other', '')

        # 用油
        row['大豆油(g)'] = ver.get('soybean_oil', '')
        row['其他油(g)'] = ver.get('other_oil', '')

        # 工艺流程
        proc_labels = [
            "主料处理", "兑汁/备料", "滑油/煸炒", "炒酱料", "爆小料",
            "合炒", "调味/烹汁", "收汁出锅", "煮主食", "其他"
        ]
        for idx, pl in enumerate(proc_labels):
            row[f'步骤{idx+1}_{pl}'] = ver.get(f'proc_{idx+1}', '')

        # 品鉴
        taste_labels = [
            ('观感', 'taste_look'),
            ('香气', 'taste_smell'),
            ('味型', 'taste_flavor'),
            ('主料口感', 'taste_texture'),
            ('芡汁', 'taste_sauce'),
            ('搭配主食', 'taste_staple'),
        ]
        for tl, tk in taste_labels:
            status = ver.get(tk, 'pending')
            note = ver.get(f'{tk}_note', '')
            row[f'品鉴_{tl}'] = taste_emoji(status)
            row[f'品鉴_{tl}_备注'] = note

        # 问题诊断
        row['问题描述'] = ver.get('problem', '')
        row['原因分析'] = ver.get('cause', '')
        row['调整方案'] = ver.get('solution', '')

        # 结论
        conclusion_map = {'pending': '—', 'retain': '保留优化', 'discard': '淘汰', 'finalized': '✅ 定版通过'}
        row['版本结论'] = conclusion_map.get(ver.get('conclusion', 'pending'), '—')

        rows.append(row)

    # 添加研发总结行
    summary_row = {k: '' for k in rows[0].keys()}
    summary_row['产品名称'] = data['product_name']
    summary_row['版本'] = '【研发总结】'
    summary_row['研发目的'] = f"最终配方：{data['summary'].get('final_recipe', '')}"
    summary_row['主料名称'] = f"最终流程：{data['summary'].get('final_process', '')}"
    summary_row['主料用量(g)'] = f"成本：{data['summary'].get('cost', '')}"
    summary_row['调味方式'] = f"周期：{data['summary'].get('duration', '')}"
    summary_row['问题描述'] = f"师傅终签：{data['summary'].get('signature', '')}"
    rows.append(summary_row)

    return pd.DataFrame(rows)


# ==================== 打印功能 ====================
def print_button():
    """生成一个真正能触发浏览器打印的按钮"""
    print_js = """
    <script>
    function triggerPrint() {
        window.print();
    }
    // 监听来自 Streamlit 的消息
    window.addEventListener('message', function(e) {
        if (e.data === 'PRINT_NOW') {
            window.print();
        }
    });
    </script>
    """
    st.components.v1.html(print_js, height=0)

    if st.button("🖨️ 打印预览 (A4横向)", use_container_width=True, key="btn_print_main",
                 help="点击后弹出浏览器打印对话框，请设置纸张为A4横向"):
        # 通过 JavaScript 触发打印
        st.components.v1.html("<script>window.print();</script>", height=0)


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
    sf = st.selectbox("味型", list(fm.keys()), format_func=lambda x: fm[x],
                      index=0 if st.session_state.flavor_type == "gongbao" else 1,
                      key="flv", label_visibility="collapsed")
    if sf != st.session_state.flavor_type:
        st.session_state.flavor_type = sf
        st.session_state.table_data = get_default_data(sf)
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
        st.session_state.table_data = get_default_data(st.session_state.flavor_type)
        st.rerun()
with c6:
    # 真正的打印按钮
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
is_gongbao = (st.session_state.flavor_type == "gongbao")
versions = data['versions']

# ==================== 表格行渲染函数 ====================
COL_RATIO = [1.3] + [1] * NUM_V


def render_row(label, field, placeholder="g", is_area=False, height=40):
    cols = st.columns(COL_RATIO)
    with cols[0]:
        st.markdown(f"<small>{label}</small>", unsafe_allow_html=True)
    for i, vk in enumerate(VERSION_KEYS):
        with cols[i + 1]:
            if is_area:
                versions[vk][field] = st.text_area(
                    label, value=versions[vk][field],
                    key=f"{field}_{vk}", label_visibility="collapsed",
                    height=height, placeholder=placeholder
                )
            else:
                versions[vk][field] = st.text_input(
                    label, value=versions[vk][field],
                    key=f"{field}_{vk}", label_visibility="collapsed",
                    placeholder=placeholder
                )


def render_select(label, field, options, format_func=None):
    cols = st.columns(COL_RATIO)
    with cols[0]:
        st.markdown(f"<small>{label}</small>", unsafe_allow_html=True)
    for i, vk in enumerate(VERSION_KEYS):
        with cols[i + 1]:
            current = versions[vk].get(field, 'pending')
            idx = options.index(current) if current in options else 0
            versions[vk][field] = st.selectbox(
                label, options, index=idx,
                format_func=format_func,
                key=f"{field}_{vk}", label_visibility="collapsed"
            )


def render_taste(label, field):
    cols = st.columns(COL_RATIO)
    with cols[0]:
        st.markdown(f"<small>{label}</small>", unsafe_allow_html=True)
    for i, vk in enumerate(VERSION_KEYS):
        with cols[i + 1]:
            sc1, sc2 = st.columns([0.5, 1])
            with sc1:
                current = versions[vk].get(field, 'pending')
                opts = ['pending', 'pass', 'fail']
                idx = opts.index(current) if current in opts else 0
                versions[vk][field] = st.selectbox(
                    f"{label}状态", opts, index=idx,
                    format_func=taste_emoji,
                    key=f"{field}_{vk}_s", label_visibility="collapsed"
                )
            with sc2:
                versions[vk][f'{field}_note'] = st.text_input(
                    f"{label}备注", value=versions[vk].get(f'{field}_note', ''),
                    key=f"{field}_{vk}_n", label_visibility="collapsed",
                    placeholder="备注"
                )


# ==================== 表格渲染 ====================
# 表头
cols = st.columns(COL_RATIO)
with cols[0]:
    st.markdown("**项目**")
for i, vk in enumerate(VERSION_KEYS):
    with cols[i + 1]:
        st.markdown(f"**{vk.replace(chr(10), '<br>')}**", unsafe_allow_html=True)
st.divider()

# 日期 & 目的
render_row("📅 日期", "date", placeholder="月/日")
render_row("🎯 研发目的", "purpose", placeholder="目的...")

st.markdown('<div class="section-label">📋 配方记录</div>', unsafe_allow_html=True)

# 主料
render_row(f"主料 ({versions[VERSION_KEYS[0]]['main_name']})", "main_value")

# 辣椒
st.caption("辣椒酱料")
if is_gongbao:
    render_row("糍粑辣椒", "chili_paste")
else:
    render_row("红泡椒", "red_pickled")
    render_row("青泡椒", "green_pickled")
    render_row("糟辣椒", "fermented_pepper")

# 汁料
if is_gongbao:
    st.caption("宫保汁（兑碗汁）")
    for lb, fd in [("甜酱", "gb_sweet"), ("酱油", "gb_soy"), ("醋", "gb_vinegar"),
                   ("味精", "gb_msg"), ("白糖", "gb_sugar"), ("水淀粉", "gb_starch"),
                   ("高汤/水", "gb_broth"), ("其他", "gb_other")]:
        render_row(lb, fd)
else:
    st.caption("独立调料（直接撒入，不兑汁）")
    for lb, fd in [("味精", "sp_msg"), ("酱油", "sp_soy"), ("醋", "sp_vinegar"),
                   ("淀粉", "sp_starch"), ("盐", "sp_salt"), ("白糖", "sp_sugar"), ("其他", "sp_other")]:
        render_row(lb, fd)

# 辅料
st.caption("辅料")
render_row("蒜苗", "garlic_sprout")
render_row("姜蒜泥", "ginger_garlic")
render_row("其他", "aux_other")

# 油
st.caption("烹调用油")
render_row("大豆油", "soybean_oil")
render_row("其他油", "other_oil")

# 工艺流程
st.markdown('<div class="section-label">⚙️ 工艺流程</div>', unsafe_allow_html=True)
proc_labels = [
    "1.主料处理", "2.兑汁/备料", "3.滑油/煸炒", "4.炒酱料", "5.爆小料",
    "6.合炒", "7.调味/烹汁", "8.收汁出锅", "9.煮主食", "10.其他"
]
for idx, lb in enumerate(proc_labels):
    render_row(lb, f"proc_{idx + 1}", placeholder="...")

# 品鉴
st.markdown('<div class="section-label">🔍 品鉴记录</div>', unsafe_allow_html=True)
for lb, fd in [("观感", "taste_look"), ("香气", "taste_smell"), ("味型", "taste_flavor"),
               ("主料口感", "taste_texture"), ("芡汁", "taste_sauce"), ("搭配主食", "taste_staple")]:
    render_taste(lb, fd)

# 问题诊断
st.markdown('<div class="section-label">⚠️ 问题诊断与调整</div>', unsafe_allow_html=True)
render_row("问题描述", "problem", placeholder="...", is_area=True, height=50)
render_row("原因分析", "cause", placeholder="...", is_area=True, height=50)
render_row("调整方案", "solution", placeholder="...", is_area=True, height=50)

# 结论
st.markdown('<div class="section-label">📌 版本结论</div>', unsafe_allow_html=True)
conclusion_opts = ['pending', 'retain', 'discard', 'finalized']
conclusion_fmt = lambda x: {'pending': '—', 'retain': '保留优化', 'discard': '淘汰', 'finalized': '✅ 定版'}[x]
render_select("结论", "conclusion", conclusion_opts, conclusion_fmt)

# 研发总结
st.markdown('<div class="section-label">📝 研发总结</div>', unsafe_allow_html=True)
sc1, sc2 = st.columns(2)
with sc1:
    data['summary']['final_recipe'] = st.text_area("最终配方", value=data['summary'].get('final_recipe', ''), height=80,
                                                   key="sr")
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
    st.download_button(
        "📥 导出 JSON（完整研发记录）",
        json.dumps(data, ensure_ascii=False, indent=2),
        f"研发记录_{data['product_name']}_{datetime.now().strftime('%Y%m%d')}.json",
        "application/json",
        use_container_width=True,
    )

with b2:
    uf = st.file_uploader("📤 导入 JSON", type="json", key="jup", label_visibility="collapsed")
    if uf:
        try:
            st.session_state.table_data = json.loads(uf.read())
            st.session_state.flavor_type = st.session_state.table_data.get('flavor_type', 'gongbao')
            st.success("✅ 导入成功")
            st.rerun()
        except Exception as e:
            st.error(f"导入失败：{e}")

with b3:
    # 导出完整研发记录 CSV
    full_df = build_full_csv()
    st.download_button(
        "📊 导出 CSV（完整研发记录表）",
        full_df.to_csv(index=False, encoding='utf-8-sig'),
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
                msgs = [
                    {"role": "system", "content": "你是贵州菜品研发专家。分析配方合理性，指出问题，给出具体建议。用中文。"},
                    {"role": "user", "content": f"分析以下研发记录：\n\n{build_context()}"}]
                rep = call_deepseek(msgs)
            st.session_state.chat_history += [
                {"role": "user", "content": "🔍 分析配方"},
                {"role": "assistant", "content": rep}
            ]
            st.rerun()
    with q2:
        if st.button("📋 对比版本", use_container_width=True):
            with st.spinner("分析中..."):
                msgs = [
                    {"role": "system", "content": "你是贵州菜品研发专家。对比各版本变化，分析调整意图和效果。用中文。"},
                    {"role": "user", "content": f"对比版本差异：\n\n{build_context()}"}]
                rep = call_deepseek(msgs)
            st.session_state.chat_history += [
                {"role": "user", "content": "📋 对比版本"},
                {"role": "assistant", "content": rep}
            ]
            st.rerun()
    q3, q4 = st.columns(2)
    with q3:
        if st.button("💡 优化建议", use_container_width=True):
            with st.spinner("思考中..."):
                msgs = [
                    {"role": "system", "content": "你是贵州菜品研发专家。给出3-5条具体优化建议，要具体到克数或操作。用中文。"},
                    {"role": "user", "content": f"基于以下记录给优化建议：\n\n{build_context()}"}]
                rep = call_deepseek(msgs)
            st.session_state.chat_history += [
                {"role": "user", "content": "💡 优化建议"},
                {"role": "assistant", "content": rep}
            ]
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
            msgs = [{"role": "system", "content": "你是贵州菜品研发专家。根据研发记录和用户问题，给出专业回答。用中文。"},
                    {"role": "user", "content": f"研发记录：\n\n{build_context()}\n\n用户问题：{um}"}]
            rep = call_deepseek(msgs)
        st.session_state.chat_history.append({"role": "assistant", "content": rep})
        st.rerun()

# 页脚
st.divider()
st.caption(
    "贵州盖浇面/饭 · 菜品研发过程记录表 | 宫保：糍粑辣椒+宫保汁（兑碗汁） | 泡椒：红泡椒+青泡椒+糟辣椒+独立调料（直接撒入，不兑汁） | Powered by Streamlit + DeepSeek")
