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
NUM_V = len(VERSION_KEYS)  # 5

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
    .stButton > button {
        border-radius: 6px; font-weight: 500;
    }
    div[data-testid="stVerticalBlock"] > div[style*="flex"] {
        gap: 2px !important;
    }
    .stTextInput input, .stTextArea textarea {
        font-size: 0.78rem !important;
        padding: 2px 4px !important;
    }
    @media print {
        header, .stSidebar, .stButton, .stDownloadButton, hr, iframe {
            display: none !important;
        }
        .stApp { background: #fff !important; }
        .main-title { color: #000 !important; border-bottom-color: #000 !important; }
        .main-title span { color: #000 !important; }
        .section-label { color: #000 !important; background: #f0f0f0 !important; border-left-color: #000 !important; }
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
        # 辣椒
        'chili_paste': '50' if (is_first and is_gongbao) else '',
        'red_pickled': '20' if (is_first and not is_gongbao) else '',
        'green_pickled': '20' if (is_first and not is_gongbao) else '',
        'fermented_pepper': '10' if (is_first and not is_gongbao) else '',
        # 宫保汁
        'gb_sweet': '', 'gb_soy': '', 'gb_vinegar': '',
        'gb_msg': '', 'gb_sugar': '', 'gb_starch': '', 'gb_broth': '', 'gb_other': '',
        # 独立调料
        'sp_msg': '3' if (is_first and not is_gongbao) else '',
        'sp_soy': '3' if (is_first and not is_gongbao) else '',
        'sp_vinegar': '3' if (is_first and not is_gongbao) else '',
        'sp_starch': '3' if (is_first and not is_gongbao) else '',
        'sp_salt': '', 'sp_sugar': '', 'sp_other': '',
        # 辅料
        'garlic_sprout': '30' if is_first else '',
        'ginger_garlic': '20' if is_first else '',
        'aux_other': '',
        # 油
        'soybean_oil': '50' if is_first else '',
        'other_oil': '',
        # 流程
        'proc_1': '', 'proc_2': '', 'proc_3': '', 'proc_4': '', 'proc_5': '',
        'proc_6': '', 'proc_7': '', 'proc_8': '', 'proc_9': '', 'proc_10': '',
        # 品鉴
        'taste_look': 'pending', 'taste_look_note': '',
        'taste_smell': 'pending', 'taste_smell_note': '',
        'taste_flavor': 'pending', 'taste_flavor_note': '',
        'taste_texture': 'pending', 'taste_texture_note': '',
        'taste_sauce': 'pending', 'taste_sauce_note': '',
        'taste_staple': 'pending', 'taste_staple_note': '',
        # 问题
        'problem': '', 'cause': '', 'solution': '',
        # 结论
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
            model="deepseek-chat",
            messages=messages,
            temperature=0.7,
            max_tokens=2000,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"❌ API 调用失败：{str(e)}"


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
    if st.button("🖨️ 打印", use_container_width=True):
        st.markdown("<script>window.print();</script>", unsafe_allow_html=True)

st.session_state.table_data['structure'] = st.text_input(
    "出品结构", value=st.session_state.table_data.get('structure', ''),
    key="struc", placeholder="宽面280g / 细面250g / 天麻面280g / 米饭250g"
)

data = st.session_state.table_data
is_gongbao = (st.session_state.flavor_type == "gongbao")
versions = data['versions']

# ==================== 核心思路：用表格行来组织输入 ====================
# 定义一个行渲染函数，输入标签和字段key，输出5个版本的输入框
COL_RATIO = [1.3] + [1] * NUM_V  # 这里 NUM_V = 5，安全


def render_row(label, field, placeholder="g", is_area=False, height=40):
    """渲染一行输入：标签 + 5个版本的输入框"""
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
    """渲染一行下拉选择"""
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
    """渲染品鉴行：选择+备注"""
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

# 日期
render_row("📅 日期", "date", placeholder="月/日")
# 目的
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

# ==================== 工艺流程 ====================
st.markdown('<div class="section-label">⚙️ 工艺流程</div>', unsafe_allow_html=True)
proc_labels = [
    "1.主料处理", "2.兑汁/备料", "3.滑油/煸炒", "4.炒酱料", "5.爆小料",
    "6.合炒", "7.调味/烹汁", "8.收汁出锅", "9.煮主食", "10.其他"
]
for idx, lb in enumerate(proc_labels):
    render_row(lb, f"proc_{idx + 1}", placeholder="...")

# ==================== 品鉴 ====================
st.markdown('<div class="section-label">🔍 品鉴记录</div>', unsafe_allow_html=True)
for lb, fd in [("观感", "taste_look"), ("香气", "taste_smell"), ("味型", "taste_flavor"),
               ("主料口感", "taste_texture"), ("芡汁", "taste_sauce"), ("搭配主食", "taste_staple")]:
    render_taste(lb, fd)

# ==================== 问题诊断 ====================
st.markdown('<div class="section-label">⚠️ 问题诊断与调整</div>', unsafe_allow_html=True)
render_row("问题描述", "problem", placeholder="...", is_area=True, height=50)
render_row("原因分析", "cause", placeholder="...", is_area=True, height=50)
render_row("调整方案", "solution", placeholder="...", is_area=True, height=50)

# ==================== 结论 ====================
st.markdown('<div class="section-label">📌 版本结论</div>', unsafe_allow_html=True)
conclusion_opts = ['pending', 'retain', 'discard', 'finalized']
conclusion_fmt = lambda x: {'pending': '—', 'retain': '保留优化', 'discard': '淘汰', 'finalized': '✅ 定版'}[x]
render_select("结论", "conclusion", conclusion_opts, conclusion_fmt)

# ==================== 研发总结 ====================
st.markdown('<div class="section-label">📝 研发总结</div>', unsafe_allow_html=True)
sc1, sc2 = st.columns(2)
with sc1:
    data['summary']['final_recipe'] = st.text_area(
        "最终配方", value=data['summary'].get('final_recipe', ''), height=80, key="sr"
    )
    data['summary']['final_process'] = st.text_area(
        "最终流程（关键控制点）", value=data['summary'].get('final_process', ''), height=80, key="sp"
    )
with sc2:
    data['summary']['cost'] = st.text_input("浇头成本（元/份）", value=data['summary'].get('cost', ''), key="sc")
    data['summary']['duration'] = st.text_input("研发周期", value=data['summary'].get('duration', ''),
                                                key="sd", placeholder="共__天，__个版本")
    data['summary']['signature'] = st.text_input("师傅终签", value=data['summary'].get('signature', ''), key="ss")

# ==================== 底部按钮 ====================
st.divider()
b1, b2, b3, b4 = st.columns(4)
with b1:
    st.download_button("📥 导出 JSON", json.dumps(data, ensure_ascii=False, indent=2),
                       f"研发记录_{data['product_name']}_{datetime.now().strftime('%Y%m%d')}.json",
                       "application/json", use_container_width=True)
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
    rows = []
    for vk in VERSION_KEYS:
        v = versions[vk]
        rows.append({
            '版本': vk.replace('\n', ' '), '日期': v['date'],
            '主料': f"{v['main_name']} {v['main_value']}g",
            '糍粑辣椒': v.get('chili_paste', ''), '红泡椒': v.get('red_pickled', ''),
            '青泡椒': v.get('green_pickled', ''), '糟辣椒': v.get('fermented_pepper', ''),
            '蒜苗': v.get('garlic_sprout', ''), '姜蒜泥': v.get('ginger_garlic', ''),
            '大豆油': v.get('soybean_oil', ''), '结论': v.get('conclusion', ''),
        })
    st.download_button("📊 导出 CSV", pd.DataFrame(rows).to_csv(index=False),
                       f"配方表_{data['product_name']}.csv", "text/csv", use_container_width=True)
with b4:
    if st.button("🖨️ 打印预览", use_container_width=True):
        st.markdown("<script>window.print();</script>", unsafe_allow_html=True)

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
                msgs = [{"role": "system", "content": "你是贵州菜品研发专家。分析配方合理性，指出问题，给出具体建议。用中文。"},
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
                msgs = [{"role": "system", "content": "你是贵州菜品研发专家。对比各版本变化，分析调整意图和效果。用中文。"},
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
                msgs = [{"role": "system", "content": "你是贵州菜品研发专家。给出3-5条具体优化建议，要具体到克数或操作。用中文。"},
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
st.caption("贵州盖浇面/饭 · 菜品研发过程记录表 | 宫保：糍粑辣椒+宫保汁（兑碗汁） | 泡椒：红泡椒+青泡椒+糟辣椒+独立调料（直接撒入，不兑汁） | Powered by Streamlit + DeepSeek")
