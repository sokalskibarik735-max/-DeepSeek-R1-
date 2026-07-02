import streamlit as st
import sys, os, time, json, re, io, random, chardet
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Optional, Generator
from dataclasses import dataclass, field, asdict
from datetime import datetime
from openai import OpenAI

# 设置页面
st.set_page_config(page_title="DeepSeek-R1 · 虚假新闻检测系统", page_icon="⚖️", layout="wide", initial_sidebar_state="expanded")

# 强制UTF-8
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass
    try: sys.stderr.reconfigure(encoding="utf-8")
    except: pass

# 自定义主题CSS
LIGHT_CSS = """
<style>
/* 全局浅色主题变量 */
:root {
    --bg-primary: #f1f5f9;
    --bg-surface: #ffffff;
    --bg-card: #f8fafc;
    --bg-card-hover: #f1f5f9;
    --border: #e2e8f0;
    --border-active: #94a3b8;
    --primary: #3b82f6;
    --primary-glow: rgba(59,130,246,0.2);
    --secondary: #06b6d4;
    --accent: #f59e0b;
    --success: #10b981;
    --warning: #f59e0b;
    --danger: #ef4444;
    --text: #0f172a;
    --text-secondary: #334155;
    --text-muted: #64748b;
}
html, body, [class*="css"] {
    background-color: var(--bg-primary) !important;
    color: var(--text) !important;
    font-family: 'Inter', 'PingFang SC', 'Microsoft YaHei', sans-serif !important;
}
.stApp { background-color: var(--bg-primary) !important; }
#MainMenu { display: none !important; }
footer { display: none !important; }
/* 保留 header，让侧边栏切换按钮可见 */

/* 侧边栏 */
[data-testid="stSidebar"] {
    background-color: var(--bg-surface) !important;
    border-right: 1px solid var(--border) !important;
    box-shadow: 2px 0 12px rgba(0,0,0,0.05) !important;
}
[data-testid="stSidebar"] * {
    color: var(--text-secondary) !important;
}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4, [data-testid="stSidebar"] h5, [data-testid="stSidebar"] h6 {
    color: var(--text) !important;
}
[data-testid="stSidebar"] .stButton > button {
    background: rgba(0,0,0,0.03) !important;
    color: var(--text-secondary) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    transition: all 0.2s ease !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(59,130,246,0.08) !important;
    color: var(--primary) !important;
    border-color: var(--border-active) !important;
    transform: translateX(3px);
}

/* 卡片 */
.glass-card {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 24px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    transition: all 0.2s ease;
}
.glass-card:hover {
    border-color: var(--border-active);
    box-shadow: 0 4px 16px rgba(0,0,0,0.06);
}

/* 按钮 */
.stButton > button {
    background: linear-gradient(135deg, var(--primary), #60a5fa) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 10px 24px !important;
    font-weight: 600 !important;
    box-shadow: 0 2px 8px var(--primary-glow) !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 16px rgba(59,130,246,0.3) !important;
}
.stButton > button[kind="secondary"] {
    background: rgba(0,0,0,0.04) !important;
    color: var(--text-secondary) !important;
    border: 1px solid var(--border) !important;
    box-shadow: none !important;
}
.stButton > button[kind="secondary"]:hover {
    background: rgba(59,130,246,0.06) !important;
    color: var(--primary) !important;
    border-color: var(--border-active) !important;
}

/* 输入框 */
.stTextInput input, .stTextArea textarea, [data-testid="stSelectbox"] > div > div {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text) !important;
    caret-color: var(--primary) !important;
}
.stTextInput input:focus, .stTextArea textarea:focus,
[data-testid="stSelectbox"] > div > div:focus-within {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.1) !important;
}

/* 标题渐变 */
.gradient-text {
    background: linear-gradient(135deg, var(--primary), var(--secondary), var(--accent));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-weight: 800;
    letter-spacing: -0.5px;
}

/* 标签 */
.tag {
    display: inline-block; padding: 4px 12px; border-radius: 6px;
    font-size: 12px; font-weight: 600; margin: 2px 4px;
}
.tag-green  { background: #d1fae5; color: #065f46; border: 1px solid #a7f3d0; }
.tag-red    { background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }
.tag-orange { background: #fef3c7; color: #92400e; border: 1px solid #fde68a; }
.tag-blue   { background: #dbeafe; color: #1e40af; border: 1px solid #bfdbfe; }
.tag-cyan   { background: #cffafe; color: #0e7490; border: 1px solid #a5f3fc; }
.tag-purple { background: #ede9fe; color: #5b21b6; border: 1px solid #ddd6fe; }
.tag-gray   { background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; }

/* 徽章 */
.badge {
    display: inline-block; padding: 6px 18px; border-radius: 8px;
    font-size: 14px; font-weight: 700; letter-spacing: 0.3px;
}
.badge-high     { background: #d1fae5; color: #065f46; border: 1px solid #a7f3d0; }
.badge-medium   { background: #fef3c7; color: #92400e; border: 1px solid #fde68a; }
.badge-low      { background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }
.badge-critical { background: #fecaca; color: #7f1d1d; border: 1px solid #fca5a5; }

/* Metric卡片 */
.metric-card {
    background: linear-gradient(135deg, var(--c1), var(--c2));
    border-radius: 14px; padding: 18px 16px; color: #fff; text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.metric-card .value { font-size: 32px; font-weight: 800; line-height: 1.2; }
.metric-card .label { font-size: 13px; opacity: 0.9; margin-top: 4px; font-weight: 500; }

/* 进度条 */
.stProgress > div > div > div {
    background: linear-gradient(90deg, var(--primary), var(--secondary), var(--accent)) !important;
    background-size: 200% 100% !important;
    animation: shimmer 2s ease infinite !important;
}
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: 0 0; } }

/* 表格 */
[data-testid="stDataFrame"] th {
    background: #e2e8f0 !important;
    color: var(--text) !important;
    border-color: var(--border) !important;
}
[data-testid="stDataFrame"] td {
    background: var(--bg-surface) !important;
    color: var(--text) !important;
    border-color: var(--border) !important;
}

/* 分隔线 */
hr { border-color: var(--border) !important; }

/* 状态点 */
.status-dot {
    display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px;
}
.status-dot.connected { background: var(--success); }
.status-dot.mock { background: var(--accent); }

/* 其他 */
.info-banner {
    background: #e0f2fe; border: 1px solid #bae6fd; border-radius: 10px;
    padding: 12px 18px; margin: 10px 0; color: #0c4a6e;
}
.border-left-indigo {
    border-left: 3px solid var(--primary);
    padding: 10px 16px; background: #f8fafc; border-radius: 0 8px 8px 0;
}
.border-left-red {
    border-left: 3px solid var(--danger);
    padding: 10px 16px; background: #fef2f2; border-radius: 0 8px 8px 0;
}
.border-left-amber {
    border-left: 3px solid var(--accent);
    padding: 10px 16px; background: #fffbeb; border-radius: 0 8px 8px 0;
}
.filter-bar {
    background: var(--bg-surface); border: 1px solid var(--border);
    border-radius: 12px; padding: 16px; margin: 12px 0;
}
.result-row {
    background: var(--bg-surface); border: 1px solid var(--border);
    border-radius: 8px; padding: 10px 14px; margin: 4px 0;
}
.result-row:hover {
    border-color: var(--border-active); background: var(--bg-card-hover);
}
</style>
"""
st.markdown(LIGHT_CSS, unsafe_allow_html=True)

# 导入核心模块

try:
    from main import (FakeNewsDetector, DetectionResult, CloudModelClient, MockModelClient,
                      PROMPT_TEMPLATES, load_csv_dataset, compute_metrics, compute_per_type_metrics,
                      run_quantization_experiment, run_batch_size_experiment, FAKE_TYPES,
                      export_json, export_csv, FakeNewsRAG)
except ImportError:
    st.error("请确保 main.py 文件存在于同一目录，或将所有核心逻辑内联。")
    st.stop()

#  会话状态初始化

for key, default in [
    ("logged_in", False),
    ("client", None),
    ("provider", "deepseek-r1"),
    ("model_name", "deepseek-v4-flash"),
    ("api_key", ""),
    ("history", []),
    ("page", "dashboard"),          # 导航页面
    ("batch_texts", []),
    ("batch_metadata", []),
    ("batch_results", None),
    ("rag", None),
    ("chat_history", []),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# 辅助渲染函数
def render_credibility_badge(c):
    m = {"高": "badge-high", "中": "badge-medium", "低": "badge-low", "极低": "badge-critical"}
    e = {"高": "✓", "中": "◈", "低": "✕", "极低": "⊘"}
    return f'<span class="badge {m.get(c,"badge-medium")}">{e.get(c,"")} {c}可信度</span>'

def render_type_tags(types):
    colors = {"捏造事实":"tag-red","断章取义":"tag-orange","夸大其词":"tag-orange",
              "标题党":"tag-purple","伪科学":"tag-cyan","情绪煽动":"tag-red",
              "信息缺失":"tag-gray","真实信息":"tag-green"}
    return "".join(f'<span class="tag {colors.get(t,"tag-gray")}">{t}</span>' for t in types)

# 各功能页面渲染函数
def render_dashboard():
    """仪表盘"""
    st.markdown("""
    <div style="display:flex;align-items:center;gap:16px;margin-bottom:8px;">
        <div style="width:52px;height:52px;border-radius:16px;
                    background:linear-gradient(135deg,#3b82f6,#06b6d4);
                    display:flex;align-items:center;justify-content:center;
                    font-size:26px;box-shadow:0 4px 12px rgba(59,130,246,0.2);">🏠</div>
        <div>
            <h1 style="font-size:2rem;margin:0;" class="gradient-text">系统仪表盘</h1>
            <p style="color:var(--text-secondary);margin:2px 0 0 0;font-size:14px;">基于 DeepSeek-R1 的虚假新闻检测与事实核查辅助系统</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    history = st.session_state.get("history", [])
    fake_count = sum(1 for r in history if getattr(r, "credibility", "") in ["低", "极低"])
    avg_score = sum(getattr(r, "credibility_score", 0.5) for r in history) / max(len(history), 1)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="metric-card" style="--c1:#3b82f6;--c2:#60a5fa;">
            <div class="value">{len(history)}</div><div class="label">检测记录</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card" style="--c1:#ef4444;--c2:#f87171;">
            <div class="value">{fake_count}</div><div class="label">疑似虚假</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card" style="--c1:#06b6d4;--c2:#22d3ee;">
            <div class="value">{avg_score:.2f}</div><div class="label">平均可信度</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        provider_name = st.session_state.provider.upper()
        st.markdown(f"""
        <div class="metric-card" style="--c1:#10b981;--c2:#34d399;">
            <div class="value">{provider_name}</div><div class="label">模型引擎</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### ⚡ 核心功能")
    features = [
        ("📝", "单文本检测", "输入新闻文本，AI 自动分析真实性", "single"),
        ("📦", "批量检测", "上传文件或批量输入，批量处理", "batch"),
        ("💬", "事实核查问答", "基于 RAG 的知识库问答", "qa"),
        ("📊", "统计分析", "可视化检测结果", "stats"),
        ("🧪", "对比实验", "提示模板、量化、批次对比", "experiment"),
        ("📥", "结果导出", "导出 JSON / CSV", "export"),
    ]
    cols = st.columns(3)
    for idx, (icon, title, desc, page_key) in enumerate(features):
        col = cols[idx % 3]
        with col:
            st.markdown(f"""
            <div style="background:var(--bg-surface);border:1px solid var(--border);border-radius:16px;
                        padding:24px 20px;text-align:center;cursor:pointer;transition:all 0.2s;"
                 onmouseover="this.style.borderColor='#3b82f6';this.style.boxShadow='0 4px 16px rgba(0,0,0,0.06)';"
                 onmouseout="this.style.borderColor='var(--border)';this.style.boxShadow='none';">
                <div style="font-size:40px;margin-bottom:12px;">{icon}</div>
                <div style="font-weight:700;font-size:16px;color:var(--text);">{title}</div>
                <div style="font-size:13px;color:var(--text-muted);margin-top:8px;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"进入 {title}", key=f"dash_{page_key}", use_container_width=True, type="secondary"):
                st.session_state.page = page_key
                st.rerun()

    # 最近记录
    if history:
        st.markdown("---")
        st.markdown(" 最近检测记录")
        for i, r in enumerate(reversed(history[-5:])):
            idx = len(history) - i
            cred = getattr(r, "credibility", "中")
            badge = render_credibility_badge(cred)
            ftags = render_type_tags(getattr(r, "fake_types", []))
            st.markdown(f"""
            <div class="result-row" style="display:flex;align-items:center;gap:12px;">
                <span style="font-size:12px;color:var(--text-muted);min-width:30px;">#{idx}</span>
                <span>{badge}</span>
                <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--text-secondary);">
                    {getattr(r, 'text', '')[:80]}
                </span>
                <span style="font-size:12px;color:var(--text-muted);">{getattr(r, 'processing_time', 0):.3f}s</span>
                <span>{ftags}</span>
            </div>
            """, unsafe_allow_html=True)

def render_single_detect():
    """单文本检测"""
    st.markdown("""
    <div style="display:flex;align-items:center;gap:16px;margin-bottom:8px;">
        <div style="width:48px;height:48px;border-radius:14px;background:linear-gradient(135deg,#3b82f6,#60a5fa);
                    display:flex;align-items:center;justify-content:center;font-size:22px;box-shadow:0 4px 12px rgba(59,130,246,0.2);">📝</div>
        <div><h1 style="font-size:1.8rem;margin:0;" class="gradient-text">单文本检测</h1>
            <p style="color:var(--text-secondary);margin:2px 0 0 0;font-size:14px;">输入新闻文本，AI 自动分析真实性</p></div>
    </div>
    """, unsafe_allow_html=True)

    col_left, col_right = st.columns([3, 1])
    with col_left:
        text = st.text_area("新闻文本内容", height=220,
                            placeholder="请粘贴需要检测的新闻文本...", key="single_text", label_visibility="collapsed")
    with col_right:
        st.markdown("""
        <div style="background:var(--bg-surface);border-radius:12px;padding:16px;border:1px solid var(--border);">
            <p style="font-weight:600;color:var(--text-secondary);margin:0 0 12px 0;font-size:13px;">📋 元信息（可选）</p>
        </div>
        """, unsafe_allow_html=True)
        source = st.text_input(" 发布平台", placeholder="如：微信公众号", key="src")
        author = st.text_input(" 作者", placeholder="如：健康养生号", key="aut")
        pub_time = st.text_input(" 发布时间", placeholder="如：2024-06-09", key="ptm")
        template = st.selectbox(" 提示模板", ["template_1", "template_2", "template_3"],
                                format_func=lambda x: {"template_1": " 链式思维(CoT)",
                                                       "template_2": " 角色扮演精简",
                                                       "template_3": " 少样本示例引导"}[x])

    EXAMPLE_LIST = {
        "示例1：伪科学健康谣言": ("神奇疗法：每天吃三颗这种果子，彻底告别高血压！", "微信群", "养生大师", "2025-01-05"),
        "示例2：阴谋论政治": ("内部消息：某国将秘密废除所有对外债务！", "自媒体", "深度爆料", "2025-01-01"),
        "示例3：夸大广告": ("这款面膜含稀有金箔，敷一次年轻十岁！", "小红书", "护肤博主", "2025-01-03"),
        "示例4：真实科技": ("工信部：2025年将新增5G基站60万个，覆盖城乡。", "工信部官网", "发布", "2025-01-06"),
        "示例5：真实政策": ("国家统计局：2024年全国粮食产量再创历史新高。", "央视新闻", "官方", "2025-01-04"),
        "示例6：虚假食品安全": ("惊天黑幕！知名乳企使用过期原料，产品已流入市场！", "微博", "食品观察", "2025-01-08"),
        "示例7：真实财经": ("国家统计局：2024年CPI同比上涨0.2%，物价总体平稳。", "新华社", "经济分析师", "2025-01-07"),
        "示例8：标题党社会": ("不看后悔！这个日常习惯正在悄悄毁掉你的健康！", "今日头条", "生活助手", "2025-01-09"),
        "示例9：真实教育": ("教育部：2025年将全面推行中小学课后服务5+2模式。", "教育部官网", "新闻办", "2025-01-10"),
        "示例10：虚假灾害": ("紧急！某地发生大地震，官方却封锁消息！", "社交媒体", "匿名用户", "2025-01-11"),
    }
    def _on_example_select():
        selected = st.session_state.get("example_picker", "")
        if selected != "（手动输入）" and selected in EXAMPLE_LIST:
            txt, src_val, aut_val, ptm_val = EXAMPLE_LIST[selected]
            st.session_state.single_text = txt
            st.session_state.src = src_val
            st.session_state.aut = aut_val
            st.session_state.ptm = ptm_val

    selected_example = st.selectbox(
        "选择快速示例（自动填充）",
        options=["（手动输入）"] + list(EXAMPLE_LIST.keys()),
        key="example_picker",
        on_change=_on_example_select,
    )

    c1, c2, c3 = st.columns([2.5, 1, 1])
    with c1:
        detect_btn = st.button(" 开始智能检测", use_container_width=True, type="primary")
    with c2:
        clear_btn = st.button("🗑 清空", use_container_width=True,
                              on_click=lambda: [st.session_state.__setitem__(k, "") for k in ["single_text","src","aut","ptm"] if k in st.session_state])

    if detect_btn and text.strip():
        with st.spinner("AI 正在深度分析中..."):
            detector = FakeNewsDetector(st.session_state.client)
            result = detector.detect(text.strip(), template_key=template,
                                     source_platform=source or "未知",
                                     author=author or "未知",
                                     publish_time=pub_time or "未知")
            st.session_state.history.append(result)

        st.markdown("---")
        # 可信度徽章
        badges = {"高": ("badge-high"," 高可信度"), "中": ("badge-medium"," 中可信度"),
                  "低": ("badge-low"," 低可信度"), "极低": ("badge-critical"," 极低可信度")}
        bcls, blabel = badges.get(result.credibility, badges["中"])
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:20px;margin:16px 0;">
            <span class="badge {bcls}">{blabel}</span>
            <div style="flex:1;">
                <div style="font-size:13px;color:var(--text-muted);margin-bottom:4px;">综合可信度分数</div>
                <div style="height:10px;background:#e2e8f0;border-radius:10px;overflow:hidden;">
                    <div style="width:{result.credibility_score*100}%;height:100%;border-radius:10px;
                                background:linear-gradient(90deg,#3b82f6,#06b6d4,#f59e0b);transition:width 0.6s;"></div>
                </div>
                <div style="text-align:right;font-size:13px;color:var(--text-secondary);margin-top:4px;">{result.credibility_score:.2f}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric(" 可信度分数", f"{result.credibility_score:.2f}")
        mc2.metric(" 处理耗时", f"{result.processing_time:.3f}s")
        mc3.metric(" 可疑段落", f"{len(result.suspicious_segments)} 处")
        mc4.metric(" 虚假类型", f"{len(result.fake_types)} 种")

        st.markdown("#####  虚假类型分类")
        st.markdown(render_type_tags(result.fake_types), unsafe_allow_html=True)

        if result.suspicious_segments:
            st.markdown("#####  可疑段落标注")
            for i, seg in enumerate(result.suspicious_segments):
                sev = seg.get("severity", "中")
                cls = {"高":"border-left-red","中":"border-left-amber","低":"border-left-indigo"}
                icon = {"高":"🔴","中":"🟡","低":"⚪"}
                st.markdown(f"""
                <div class="{cls.get(sev,'border-left-indigo')}">
                    <b>{icon.get(sev,'')} #{i+1} · 可疑文本</b><br>
                    <span style="font-style:italic;color:var(--text-secondary);">"{seg.get('text','')}"</span><br>
                    <span style="font-size:13px;">📋 {seg.get('reason','')} · 严重度：{sev}</span>
                </div>
                """, unsafe_allow_html=True)

        tab1, tab2, tab3 = st.tabs([" 事实核查建议", " 逻辑矛盾", " 关键声明"])
        with tab1:
            if result.fact_check_suggestions:
                for s in result.fact_check_suggestions:
                    st.markdown(f"- {s}")
            else: st.info(" 未检测到需要特别核查的内容")
        with tab2:
            if result.logic_contradictions:
                for lc in result.logic_contradictions: st.warning(f"⚠ {lc}")
            else: st.success(" 未发现逻辑矛盾")
        with tab3:
            if result.key_claims:
                for kc in result.key_claims: st.markdown(f"- 📌 {kc}")
            else: st.info(" 未提取到关键声明")

        with st.expander(" 综合分析报告", expanded=True):
            rc1, rc2 = st.columns(2)
            with rc1:
                if result.risk_analysis:
                    st.markdown(f"** 风险分析**\n\n{result.risk_analysis}")
                st.caption(f" 模板：{template} · ⏱ {result.processing_time:.3f}s")
            with rc2:
                if result.summary:
                    st.markdown(f"** 总结**\n\n{result.summary}")
                st.caption(f" {source or '未知'} · 👤 {author or '未知'}")

    elif detect_btn and not text.strip():
        st.warning(" 请先输入新闻文本内容")

def render_batch_detect():
    """批量检测"""
    st.markdown("""
    <div style="display:flex;align-items:center;gap:16px;margin-bottom:8px;">
        <div style="width:48px;height:48px;border-radius:14px;background:linear-gradient(135deg,#ef4444,#f87171);
                    display:flex;align-items:center;justify-content:center;font-size:22px;box-shadow:0 4px 12px rgba(239,68,68,0.2);">📦</div>
        <div><h1 style="font-size:1.8rem;margin:0;" class="gradient-text">批量检测</h1>
            <p style="color:var(--text-secondary);margin:2px 0 0 0;font-size:14px;">上传文件或输入多条新闻，批量分析</p></div>
    </div>
    """, unsafe_allow_html=True)

    mode = st.radio(" 输入方式", [" 文件上传", " 手动输入", " 粘贴列表"], horizontal=True, key="batch_mode")

    if mode == " 文件上传":
        uploaded = st.file_uploader("拖拽或点击上传新闻文件", type=["txt","md","csv"], accept_multiple_files=True, key="batch_uploader")
        if uploaded and st.button(" 解析文件", use_container_width=True, type="secondary"):
            texts, meta = [], []
            for f in uploaded:
                try:
                    raw = f.getvalue()
                    enc = chardet.detect(raw).get("encoding","utf-8") or "utf-8"
                    content = raw.decode(enc, errors="replace")
                except Exception as e:
                    st.error(f"读取 {f.name} 失败：{e}")
                    continue
                try:
                    if f.name.lower().endswith(".csv"):
                        df = pd.read_csv(io.StringIO(content))
                        col_candidates = ["text","content","body","news","article","Text","Content","TEXT"]
                        col = None
                        for c in col_candidates:
                            if c in df.columns: col = c; break
                        if col is None:
                            cols_lower = {c.lower(): c for c in df.columns}
                            for c in col_candidates:
                                if c.lower() in cols_lower:
                                    col = cols_lower[c.lower()]; break
                        if col is None:
                            str_cols = [c for c in df.columns if df[c].dtype == object]
                            if str_cols:
                                best = max(str_cols, key=lambda c: df[c].dropna().astype(str).str.len().mean())
                                col = best
                            else:
                                col = df.columns[0]
                        for _, row in df.iterrows():
                            t = str(row[col]).strip()
                            if t.lower() not in ("nan","none","null","") and len(t) > 5:
                                texts.append(t)
                                meta.append({"source_platform": "CSV导入", "author": "未知"})
                    else:
                        for line in content.replace("\r","").split("\n"):
                            line = line.strip()
                            if len(line) > 5:
                                texts.append(line)
                                meta.append({"source_platform": f.name, "author": "未知"})
                except Exception as e:
                    st.error(f"解析 {f.name} 失败：{e}")
                    continue
            if texts:
                st.session_state.batch_texts = texts
                st.session_state.batch_metadata = meta
                st.session_state.batch_results = None
                st.success(f" 成功加载 {len(texts)} 条文本")
                st.rerun()
            else:
                st.warning("未提取到有效文本")
    elif mode == " 手动输入":
        manual = st.text_area("每行一条新闻", height=220, placeholder="每条新闻单独一行", label_visibility="collapsed", key="batch_manual")
        if st.button(" 加载文本", use_container_width=True, type="secondary") and manual.strip():
            texts = [l.strip() for l in manual.strip().split("\n") if len(l.strip())>5]
            st.session_state.batch_texts = texts
            st.session_state.batch_metadata = [{"source_platform":"手动输入","author":"未知"}]*len(texts)
            st.session_state.batch_results = None
            st.success(f" 成功加载 {len(texts)} 条文本")
            st.rerun()
    else:
        paste = st.text_area("粘贴多条新闻", height=220, placeholder="直接粘贴列表，支持序号", label_visibility="collapsed", key="batch_paste")
        if st.button(" 加载文本", use_container_width=True, key="load_paste", type="secondary"):
            texts = []
            for line in (paste or "").strip().split("\n"):
                line = re.sub(r'^\d+[\.\)、]\s*','', line.strip())
                if len(line) > 5:
                    texts.append(line)
            st.session_state.batch_texts = texts
            st.session_state.batch_metadata = [{"source_platform":"粘贴导入","author":"未知"}]*len(texts)
            st.session_state.batch_results = None
            st.success(f"成功加载 {len(texts)} 条文本")
            st.rerun()

    texts = st.session_state.batch_texts
    meta = st.session_state.batch_metadata
    if texts:
        st.markdown(f"""<div class="info-banner"> 已加载 <b>{len(texts)}</b> 条待检测文本</div>""", unsafe_allow_html=True)
        with st.expander(f" 预览（前 {min(5,len(texts))} 条）"):
            for i,t in enumerate(texts[:5]):
                st.markdown(f"""<div class="result-row"><b>#{i+1}</b> {t[:120]}{'...' if len(t)>120 else ''}</div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("##### ⚙ 检测设置")
        cs1,cs2,cs3,cs4 = st.columns([1.5,1,1,1])
        with cs1:
            template = st.selectbox(" 提示模板", ["template_1","template_2","template_3"],
                                    format_func=lambda x: f"方案{x[-1]}", key="batch_template")
        with cs2:
            batch_size = st.number_input(" 批处理大小", 1, max(1,len(texts)), min(max(1,len(texts)//10),20), key="batch_bs")
        with cs3:
            st.markdown("<br>", unsafe_allow_html=True)
            show_detail = st.checkbox(" 详细表格", True)
        with cs4:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑 清空", use_container_width=True):
                for k in ["batch_texts","batch_metadata","batch_results"]:
                    st.session_state[k] = ([] if k!="batch_results" else None)
                st.rerun()

        if st.button(" 开始批量检测", use_container_width=True, type="primary"):
            progress_bar = st.progress(0, text="准备检测...")
            status_area = st.empty()
            detector = FakeNewsDetector(st.session_state.client)
            results = []
            total = len(texts)
            for i in range(0, total, batch_size):
                chunk = texts[i:i+batch_size]
                chunk_meta = meta[i:i+batch_size] if meta else [{}]*len(chunk)
                for j, (t, m) in enumerate(zip(chunk, chunk_meta)):
                    idx = i+j
                    status_area.markdown(f"""<div class="result-row"> 正在检测 <b>{idx+1}/{total}</b> · {t[:50]}...</div>""", unsafe_allow_html=True)
                    try:
                        r = detector.detect(t, template_key=template, **m)
                    except Exception as e:
                        r = DetectionResult(text=t[:200], template_used=template,
                                            source_platform=m.get("source_platform","未知"),
                                            author=m.get("author","未知"))
                        r.error = str(e)
                    results.append(r)
                    st.session_state.history.append(r)
                    progress_bar.progress((idx+1)/total, text=f"已完成 {idx+1}/{total}")
            st.session_state.batch_results = results
            progress_bar.empty()
            status_area.empty()
            st.rerun()

    # 显示结果
    results = st.session_state.batch_results
    if results is not None:
        total = len(results)
        errors = [r for r in results if getattr(r,"error","")]
        ok = total - len(errors)
        cred_dist = {"高":0,"中":0,"低":0,"极低":0}
        type_dist = {}
        total_time = sum(getattr(r,"processing_time",0) for r in results)
        for r in results:
            c = getattr(r,"credibility","中")
            cred_dist[c] = cred_dist.get(c,0)+1
            for ft in getattr(r,"fake_types",[]):
                type_dist[ft] = type_dist.get(ft,0)+1
        fake_count = cred_dist.get("低",0)+cred_dist.get("极低",0)
        avg_time = total_time/max(total,1)

        st.markdown("---")
        st.markdown("###  批量检测报告")
        c1,c2,c3,c4,c5 = st.columns(5)
        with c1:
            st.markdown(f"""<div class="metric-card" style="--c1:#3b82f6;--c2:#60a5fa;"><div class="value">{total}</div><div class="label">检测总数</div></div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""<div class="metric-card" style="--c1:#ef4444;--c2:#f87171;"><div class="value">{fake_count}</div><div class="label">疑似虚假 ({fake_count/max(total,1)*100:.1f}%)</div></div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""<div class="metric-card" style="--c1:#10b981;--c2:#34d399;"><div class="value">{ok}</div><div class="label">检测成功</div></div>""", unsafe_allow_html=True)
        with c4:
            st.markdown(f"""<div class="metric-card" style="--c1:#06b6d4;--c2:#22d3ee;"><div class="value">{total_time:.1f}s</div><div class="label">总耗时</div></div>""", unsafe_allow_html=True)
        with c5:
            st.markdown(f"""<div class="metric-card" style="--c1:#f59e0b;--c2:#fbbf24;color:#0f172a;"><div class="value">{avg_time:.2f}s</div><div class="label">平均/条</div></div>""", unsafe_allow_html=True)

        cc1,cc2 = st.columns(2)
        with cc1:
            st.markdown("#####  可信度等级分布")
            fig = px.bar(x=list(cred_dist.keys()), y=list(cred_dist.values()),
                         color=list(cred_dist.keys()),
                         color_discrete_map={"高":"#10b981","中":"#f59e0b","低":"#ef4444","极低":"#dc2626"},
                         labels={"x":"可信度","y":"数量"}, text_auto=True)
            fig.update_layout(showlegend=False, bargap=0.3, height=350, margin=dict(t=20),
                              plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
        with cc2:
            st.markdown("#####  虚假类型分布")
            if type_dist:
                fig2 = px.pie(names=list(type_dist.keys()), values=list(type_dist.values()),
                              hole=0.5, color_discrete_sequence=px.colors.qualitative.Bold)
                fig2.update_traces(textinfo="label+percent")
                fig2.update_layout(height=350, margin=dict(t=20), paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("暂无数据")

        if errors:
            with st.expander(f" {len(errors)} 条失败"):
                for i,r in enumerate(errors):
                    st.warning(f"#{i+1} · {getattr(r,'text','')[:60]}...\n错误：{r.error}")

        # 筛选
        st.markdown("---")
        st.markdown('<div class="filter-bar">', unsafe_allow_html=True)
        st.markdown("#####  结果筛选")
        f1,f2,f3 = st.columns([1,1,2])
        with f1:
            cred_filter = st.multiselect("可信度", ["高","中","低","极低"], default=[], placeholder="全部")
        with f2:
            type_filter = st.multiselect("虚假类型", sorted(type_dist.keys()), default=[], placeholder="全部")
        with f3:
            keyword = st.text_input(" 搜索关键词", placeholder="在文本中搜索")
        filtered = results
        if cred_filter:
            filtered = [r for r in filtered if getattr(r,"credibility","") in cred_filter]
        if type_filter:
            filtered = [r for r in filtered if any(ft in getattr(r,"fake_types",[]) for ft in type_filter)]
        if keyword:
            filtered = [r for r in filtered if keyword.lower() in getattr(r,"text","").lower()]
        st.markdown(f"<span style='color:var(--text-muted);font-size:13px;'>筛选结果：{len(filtered)}/{total} 条</span>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        if show_detail and filtered:
            st.markdown("###  详细结果")
            page_size = 20
            total_pages = max(1, (len(filtered)+page_size-1)//page_size)
            if total_pages > 1:
                page = st.number_input("页码", 1, total_pages, 1)
            else:
                page = 1
            start = (page-1)*page_size
            page_data = filtered[start:start+page_size]
            rows = [{"序号":start+i+1,
                     "文本摘要":getattr(r,"text","")[:80],
                     "可信度":getattr(r,"credibility","中"),
                     "分数":getattr(r,"credibility_score",0.5),
                     "虚假类型":"、".join(getattr(r,"fake_types",[])),
                     "耗时(s)":getattr(r,"processing_time",0)} for i,r in enumerate(page_data)]
            df = pd.DataFrame(rows)
            def style_cred(v):
                return {"高":"background:#d1fae5;color:#065f46",
                        "中":"background:#fef3c7;color:#92400e",
                        "低":"background:#fee2e2;color:#991b1b",
                        "极低":"background:#fecaca;color:#7f1d1d"}.get(v, "")
            st.dataframe(df.style.applymap(style_cred, subset=["可信度"]),
                         use_container_width=True, height=500,
                         column_config={"分数": st.column_config.ProgressColumn(format="%.2f", min_value=0, max_value=1)})
            if total_pages > 1:
                st.caption(f"第 {page}/{total_pages} 页，共 {len(filtered)} 条")

        # 导出
        st.markdown("---")
        st.markdown("#####  导出结果")
        ec1,ec2 = st.columns(2)
        csv_rows = [{"text":getattr(r,"text",""),
                     "credibility":getattr(r,"credibility",""),
                     "score":getattr(r,"credibility_score",0),
                     "fake_types":"、".join(getattr(r,"fake_types",[])),
                     "risk_analysis":getattr(r,"risk_analysis",""),
                     "summary":getattr(r,"summary",""),
                     "processing_time":getattr(r,"processing_time",0),
                     "error":getattr(r,"error","")} for r in filtered]
        with ec1:
            st.download_button("⬇ CSV 报告",
                               pd.DataFrame(csv_rows).to_csv(index=False).encode("utf-8-sig"),
                               f"batch_report_{int(time.time())}.csv", "text/csv",
                               use_container_width=True)
        with ec2:
            json_rows = [{"text":getattr(r,"text",""),
                          "credibility":getattr(r,"credibility",""),
                          "credibility_score":getattr(r,"credibility_score",0),
                          "fake_types":getattr(r,"fake_types",[]),
                          "suspicious_segments":getattr(r,"suspicious_segments",[]),
                          "risk_analysis":getattr(r,"risk_analysis",""),
                          "summary":getattr(r,"summary",""),
                          "processing_time":getattr(r,"processing_time",0)} for r in filtered]
            st.download_button("⬇ JSON 报告",
                               json.dumps(json_rows, ensure_ascii=False, indent=2).encode("utf-8"),
                               f"batch_report_{int(time.time())}.json", "application/json",
                               use_container_width=True)

def render_qa():
    """事实核查问答"""
    st.markdown("""
    <div style="display:flex;align-items:center;gap:16px;margin-bottom:8px;">
        <div style="width:48px;height:48px;border-radius:14px;background:linear-gradient(135deg,#06b6d4,#22d3ee);
                    display:flex;align-items:center;justify-content:center;font-size:22px;box-shadow:0 4px 12px rgba(6,182,212,0.2);">💬</div>
        <div><h1 style="font-size:1.8rem;margin:0;" class="gradient-text">事实核查问答</h1>
            <p style="color:var(--text-secondary);margin:2px 0 0 0;font-size:14px;">基于 RAG 的智能问答</p></div>
    </div>
    """, unsafe_allow_html=True)

    if "rag" not in st.session_state or st.session_state.rag is None:
        st.session_state.rag = FakeNewsRAG(st.session_state.client)
    rag = st.session_state.rag
    db_size = len(rag.results)

    if db_size == 0:
        has_hist = len(st.session_state.get("history",[]))
        st.warning(" 知识库为空！请先在「单文本检测」或「批量检测」中检测文本。")
        if has_hist > 0:
            st.info(f" 检测到 {has_hist} 条历史记录，可构建知识库")
            if st.button(" 从检测历史构建知识库", use_container_width=True, type="primary"):
                with st.spinner(" 正在构建"):
                    rag.build_knowledge_base(st.session_state.history)
                st.rerun()
        else:
            st.markdown("""<div style="text-align:center;padding:40px;"><div style="font-size:48px;opacity:0.1;">📚</div>
                <p style="color:var(--text-muted);">暂无数据，请先执行检测任务</p></div>""", unsafe_allow_html=True)
    else:
        with st.expander(f" 知识库 · {db_size} 条", expanded=db_size<=5):
            for i, r in enumerate(rag.results[:15]):
                cc = {"高":"#10b981","中":"#f59e0b","低":"#ef4444","极低":"#dc2626"}
                st.markdown(f"""<div style="padding:8px 12px;margin:3px 0;border-radius:8px;background:var(--bg-surface);border:1px solid var(--border);font-size:14px;">
                    <b style="color:{cc.get(r.credibility,'#64748b')};">#{i+1} [{r.credibility}]</b> {r.text[:80]}{'...' if len(r.text)>80 else ''}</div>""", unsafe_allow_html=True)
            if db_size > 15:
                st.caption(f"... 还有 {db_size-15} 条")

        with st.columns([3,1])[1]:
            if st.button("🗑 清空知识库", use_container_width=True):
                rag.results = []
                rag.store.clear()
                st.rerun()

        st.markdown("#####  快捷提问（点击即自动问答）")
        presets = [
            ("哪条新闻可信度最低？", "🔍"),
            ("最常见的虚假类型是什么？", "📊"),
            ("有哪些新闻被标记为伪科学？", "🔬"),
            ("请总结所有检测结果", "📝"),
            ("有没有标题党的新闻？", "📰"),
        ]
        cols = st.columns(len(presets))
        for i, (q, icon) in enumerate(presets):
            with cols[i]:
                if st.button(f"{icon} {q}", key=f"preset_{i}", use_container_width=True):
                    st.session_state.current_question = q
                    st.session_state.qa_input = q
                    st.session_state.auto_ask = True
                    st.rerun()

        question = st.text_input("输入你的问题", value=st.session_state.get("current_question",""),
                                 placeholder="例如：哪些新闻可信度最低？", key="qa_input", label_visibility="collapsed")

        c1,c2 = st.columns([2.5,1])
        with c1:
            ask_btn = st.button(" 提问分析", use_container_width=True, type="primary")
        with c2:
            stream = st.checkbox(" 流式输出", True)

        if ask_btn and question.strip():
            st.markdown("---")
            st.markdown(f"""<div style="background:#e0f2fe;padding:12px 16px;border-radius:10px;border-left:4px solid #3b82f6;margin-bottom:12px;">
                <b>❓ 问题：</b>{question}</div>""", unsafe_allow_html=True)
            placeholder = st.empty()
            if stream:
                try:
                    parts = []
                    for chunk in rag.answer(question, stream=True):
                        parts.append(chunk)
                        placeholder.markdown(f"""<div style="background:var(--bg-surface);padding:14px 18px;border-radius:10px;border:1px solid var(--border);line-height:1.8;">
                            <b> 回答：</b>{''.join(parts)}</div>""", unsafe_allow_html=True)
                    full_response = "".join(parts)
                except:
                    full_response = rag.answer(question, stream=False)
            else:
                with st.spinner(" 分析中..."):
                    full_response = rag.answer(question, stream=False)
            placeholder.markdown(f"""<div style="background:var(--bg-surface);padding:14px 18px;border-radius:10px;border:1px solid var(--border);line-height:1.8;">
                <b> 回答：</b>{full_response}</div>""", unsafe_allow_html=True)
            st.session_state.chat_history.append({"q":question,"a":full_response})

        if st.session_state.chat_history:
            st.markdown("---")
            st.markdown("#####  对话历史")
            for i, chat in enumerate(reversed(st.session_state.chat_history[-10:])):
                with st.expander(f"Q{i+1}: {chat['q'][:50]}{'...' if len(chat['q'])>50 else ''}"):
                    st.markdown(f"** Q:** {chat['q']}")
                    st.markdown(f"** A:** {chat['a']}")

def render_stats():
    """统计分析"""
    st.markdown("""
    <div style="display:flex;align-items:center;gap:16px;margin-bottom:8px;">
        <div style="width:48px;height:48px;border-radius:14px;background:linear-gradient(135deg,#10b981,#34d399);
                    display:flex;align-items:center;justify-content:center;font-size:22px;box-shadow:0 4px 12px rgba(16,185,129,0.2);">📊</div>
        <div><h1 style="font-size:1.8rem;margin:0;" class="gradient-text">统计分析</h1>
            <p style="color:var(--text-secondary);margin:2px 0 0 0;font-size:14px;">可视化检测数据</p></div>
    </div>
    """, unsafe_allow_html=True)

    history = st.session_state.get("history", [])
    if not history:
        st.warning(" 暂无检测记录")
        return

    st.markdown(f"""<div class="info-banner"> 基于 <b>{len(history)}</b> 条检测记录分析</div>""", unsafe_allow_html=True)

    cred_dist = {"高":0,"中":0,"低":0,"极低":0}
    type_dist = {}
    scores, times = [], []
    for r in history:
        c = getattr(r,"credibility","中")
        cred_dist[c] = cred_dist.get(c,0)+1
        for ft in getattr(r,"fake_types",[]):
            type_dist[ft] = type_dist.get(ft,0)+1
        scores.append(getattr(r,"credibility_score",0.5))
        times.append(getattr(r,"processing_time",0))

    fake_count = cred_dist.get("低",0)+cred_dist.get("极低",0)
    avg_score = sum(scores)/len(scores) if scores else 0

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric(" 检测总数", len(history))
    c2.metric(" 疑似虚假", f"{fake_count} 条")
    c3.metric(" 虚假率", f"{fake_count/len(history)*100:.1f}%")
    c4.metric(" 平均可信度", f"{avg_score:.2f}")
    c5.metric(" 平均耗时", f"{sum(times)/len(times):.3f}s" if times else "0s")

    st.markdown("---")
    col1,col2 = st.columns(2)
    with col1:
        st.markdown("#####  可信度等级分布")
        fig = px.bar(x=list(cred_dist.keys()), y=list(cred_dist.values()),
                     color=list(cred_dist.keys()),
                     color_discrete_map={"高":"#10b981","中":"#f59e0b","低":"#ef4444","极低":"#dc2626"},
                     labels={"x":"可信度","y":"数量"}, text_auto=True)
        fig.update_layout(showlegend=False, bargap=0.3, height=350, margin=dict(t=20),
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.markdown("#####  虚假类型分布")
        if type_dist:
            fig2 = px.pie(names=list(type_dist.keys()), values=list(type_dist.values()),
                          hole=0.5, color_discrete_sequence=px.colors.qualitative.Bold)
            fig2.update_traces(textinfo="label+percent")
            fig2.update_layout(height=350, margin=dict(t=20), paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("暂无数据")

    col3,col4 = st.columns(2)
    with col3:
        st.markdown("#####  可信度分数分布")
        fig3 = px.histogram(scores, nbins=20, labels={"value":"可信度分数","count":"频次"},
                            color_discrete_sequence=["#3b82f6"])
        fig3.update_layout(bargap=0.1, height=350, margin=dict(t=20),
                           plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig3, use_container_width=True)
    with col4:
        st.markdown("#####  处理耗时分布")
        fig4 = px.box(times, labels={"value":"耗时(s)"}, color_discrete_sequence=["#ef4444"])
        fig4.update_layout(height=350, margin=dict(t=20),
                           plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig4, use_container_width=True)

    st.markdown("#####  可信度 × 虚假类型 交叉分析")
    cross_data = []
    for r in history:
        for ft in getattr(r,"fake_types",[]):
            cross_data.append({"可信度":getattr(r,"credibility","中"), "虚假类型":ft})
    if cross_data:
        df_cross = pd.DataFrame(cross_data)
        st.dataframe(pd.crosstab(df_cross["可信度"], df_cross["虚假类型"]), use_container_width=True)

    if len(history)>1:
        st.markdown("#####  检测趋势")
        trend_data = [{"序号":i+1,"可信度分数":getattr(r,"credibility_score",0.5)} for i,r in enumerate(history)]
        df_trend = pd.DataFrame(trend_data)
        df_trend["移动平均"] = df_trend["可信度分数"].rolling(window=min(5,len(df_trend)), min_periods=1).mean()
        fig5 = go.Figure()
        fig5.add_trace(go.Scatter(y=df_trend["可信度分数"], mode="markers", name="单条分数",
                                  marker=dict(size=10,color="#3b82f6")))
        fig5.add_trace(go.Scatter(y=df_trend["移动平均"], mode="lines", name="移动平均",
                                  line=dict(width=3,color="#ef4444",shape="spline")))
        fig5.update_layout(height=380, xaxis_title="检测序号", yaxis_title="可信度分数",
                           yaxis_range=[0,1], margin=dict(t=20),
                           plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                           legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99))
        st.plotly_chart(fig5, use_container_width=True)

def render_experiment():
    """对比实验"""
    st.markdown("""
    <div style="display:flex;align-items:center;gap:16px;margin-bottom:8px;">
        <div style="width:48px;height:48px;border-radius:14px;background:linear-gradient(135deg,#f59e0b,#fbbf24);
                    display:flex;align-items:center;justify-content:center;font-size:22px;box-shadow:0 4px 12px rgba(245,158,11,0.2);">🧪</div>
        <div><h1 style="font-size:1.8rem;margin:0;" class="gradient-text">对比实验</h1>
            <p style="color:var(--text-secondary);margin:2px 0 0 0;font-size:14px;">提示模板 · 量化 · 批次 · 分类型评估</p></div>
    </div>
    """, unsafe_allow_html=True)

    # 准备测试数据
    history_ = st.session_state.get("history", [])
    test_texts_hist = [getattr(r,"text","") for r in history_[:10] if getattr(r,"text","")]
    FALLBACK_TEXTS = [
        "紧急！某地发现大规模核泄漏，官方隐瞒真相！",
        "国家卫健委：2025年流感疫苗供应充足，建议及时接种。",
        "神奇疗法：每天吃三颗这种果子，彻底告别高血压！",
        "交通运输部：2025年春运旅客发送量预计再创新高。",
        "惊天黑幕！知名乳企使用过期原料，产品已流入市场！",
        "国家统计局：2024年全国粮食产量再创历史新高。",
        "独家！某顶流明星与圈外女友秘密领证，已在筹备婚礼！",
        "教育部：2025年将全面推行中小学课后服务5+2模式。",
        "震惊！科学家证实人类大脑仅开发10%，剩余90%被封印！",
        "工信部：2025年将新增5G基站60万个，覆盖城乡。",
    ]
    FALLBACK_LABELS = ["虚假", "真实", "虚假", "真实", "虚假", "真实", "虚假", "真实", "虚假", "真实"]
    test_texts = test_texts_hist if len(test_texts_hist)>=3 else FALLBACK_TEXTS

    DATA_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "news_dataset.csv")
    dataset_rows = load_csv_dataset(DATA_CSV, limit=50) if os.path.exists(DATA_CSV) else []

    st.caption(f" 测试集：{len(test_texts)} 条 · 数据集：{len(dataset_rows)} 条标注")

    tab1, tab2, tab3, tab4 = st.tabs([" 提示模板对比", " 量化方案对比", " 批次处理对比", " 分类型效果评估"])

    with tab1:
        st.markdown("""<div class="info-banner">比较三种提示策略（CoT / 角色扮演 / 少样本）的 Acc/P/R/F1 等指标</div>""", unsafe_allow_html=True)
        c1,c2 = st.columns([2,1])
        with c1:
            n_test = st.slider("每模板测试条数", 2, min(10,len(test_texts)), min(5,len(test_texts)), key="tpl_n")
        with c2:
            run_tpl = st.button("▶ 运行提示模板对比", type="primary", key="run_tpl", use_container_width=True)

        if run_tpl:
            detector = FakeNewsDetector(st.session_state.client)
            texts_sub = test_texts[:n_test]
            truth_labels = FALLBACK_LABELS[:n_test] if len(test_texts_hist)<3 else ["虚假"]*len(texts_sub)
            truth_mapped = ["真实" if l in ["真实新闻","真实","real","True","1"] else "虚假" for l in truth_labels]
            rows = []
            progress = st.progress(0, " 运行中")
            for idx, (tk, tmpl) in enumerate(PROMPT_TEMPLATES.items()):
                t0 = time.time()
                rs = [detector.detect(t, template_key=tk) for t in texts_sub]
                elapsed = time.time()-t0
                ok = sum(1 for r in rs if not getattr(r,"error",""))
                fake_r = sum(1 for r in rs if r.is_fake())/len(rs)*100 if rs else 0
                m = compute_metrics(rs, truth_mapped)
                rows.append({"模板名称":tmpl["name"], "策略说明":tmpl["description"],
                             "平均延迟(s)":round(elapsed/n_test,4), "成功率(%)":round(ok/n_test*100,1),
                             "Accuracy":m["accuracy"], "Precision":m["macro_precision"],
                             "Recall":m["macro_recall"], "F1":m["macro_f1"],
                             "检出率(%)":round(fake_r,1)})
                progress.progress((idx+1)/len(PROMPT_TEMPLATES), f"完成：{tmpl['name']}")
            progress.empty()
            st.session_state["tpl_exp_results"] = rows

        if "tpl_exp_results" in st.session_state:
            rows = st.session_state["tpl_exp_results"]
            df_tpl = pd.DataFrame(rows)
            best_row = df_tpl.loc[df_tpl["F1"].idxmax()]
            kpi_cols = st.columns(3)
            for i, row in enumerate(rows):
                with kpi_cols[i]:
                    is_best = row["模板名称"]==best_row["模板名称"]
                    badge = " 最优" if is_best else ""
                    border = "2px solid #f59e0b" if is_best else "1px solid var(--border)"
                    bg = "rgba(245,158,11,0.08)" if is_best else "var(--bg-surface)"
                    st.markdown(f"""
                    <div style="background:{bg};border-radius:14px;padding:16px;border:{border};text-align:center;">
                        <div style="font-weight:700;font-size:15px;color:var(--text);">{row['模板名称']} {badge}</div>
                        <div style="font-size:12px;color:var(--text-muted);margin:4px 0 10px 0;">{row['策略说明']}</div>
                        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                            <div style="background:#e0f2fe;border-radius:8px;padding:8px;">
                                <div style="font-size:20px;font-weight:800;color:#3b82f6;">{row['Accuracy']:.4f}</div><div style="font-size:11px;color:var(--text-muted);">Acc</div></div>
                            <div style="background:#fee2e2;border-radius:8px;padding:8px;">
                                <div style="font-size:20px;font-weight:800;color:#ef4444;">{row['F1']:.4f}</div><div style="font-size:11px;color:var(--text-muted);">F1</div></div>
                            <div style="background:#d1fae5;border-radius:8px;padding:8px;">
                                <div style="font-size:18px;font-weight:700;color:#10b981;">{row['Precision']:.4f}</div><div style="font-size:11px;color:var(--text-muted);">Precision</div></div>
                            <div style="background:#fef3c7;border-radius:8px;padding:8px;">
                                <div style="font-size:18px;font-weight:700;color:#f59e0b;">{row['Recall']:.4f}</div><div style="font-size:11px;color:var(--text-muted);">Recall</div></div>
                        </div>
                        <div style="margin-top:8px;font-size:13px;color:var(--text-secondary);">⏱ {row['平均延迟(s)']:.3f}s ·  {row['成功率(%)']:.1f}%</div>
                    </div>""", unsafe_allow_html=True)

            st.markdown("####  六维综合雷达图")
            categories = ["Acc","Precision","Recall","F1","成功率","速度"]
            max_lat = max(r["平均延迟(s)"] for r in rows)
            fig_radar = go.Figure()
            colors = ["#3b82f6","#ef4444","#10b981"]
            for i, row in enumerate(rows):
                vals = [row["Accuracy"], row["Precision"], row["Recall"], row["F1"],
                        row["成功率(%)"]/100, (max_lat-row["平均延迟(s)"])/max_lat if max_lat>0 else 1]
                fig_radar.add_trace(go.Scatterpolar(r=vals+[vals[0]], theta=categories+[categories[0]],
                                                    fill="toself", name=row["模板名称"],
                                                    line=dict(color=colors[i], width=2)))
            fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,1.1])),
                                    height=420, paper_bgcolor="rgba(0,0,0,0)", margin=dict(t=30))
            st.plotly_chart(fig_radar, use_container_width=True)

            st.markdown("####  延迟 vs F1")
            st.dataframe(df_tpl[["模板名称","平均延迟(s)","成功率(%)","Accuracy","Precision","Recall","F1"]],
                         use_container_width=True, hide_index=True)
            st.success(f" 最优：**{best_row['模板名称']}** — F1={best_row['F1']:.4f}")

    with tab2:
        st.markdown("""<div class="info-banner">对比 FP16/INT8/AWQ 在显存、延迟、质量三维度的表现</div>""", unsafe_allow_html=True)
        c1,c2 = st.columns([2,1])
        with c2:
            if st.button(" 运行量化对比", type="primary", key="run_quant", use_container_width=True):
                with st.spinner(" 加载中..."):
                    st.session_state["quant_results"] = run_quantization_experiment()

        if "quant_results" in st.session_state:
            qd = st.session_state["quant_results"]
            qc = st.columns(3)
            icons = ["🔵","🟡","🟢"]
            desc = ["原始部署，质量最高", "8位量化，显存减少45%", "激活感知量化，最优平衡"]
            for i, d in enumerate(qd):
                with qc[i]:
                    st.markdown(f"""
                    <div style="background:var(--bg-surface);border:1px solid var(--border);border-radius:14px;padding:16px;text-align:center;">
                        <div style="font-size:24px;">{icons[i]}</div>
                        <div style="font-weight:700;font-size:16px;color:var(--text);margin:6px 0;">{d['量化']}</div>
                        <div style="font-size:12px;color:var(--text-muted);margin-bottom:12px;">{desc[i]}</div>
                        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;">
                            <div style="background:#e0f2fe;border-radius:8px;padding:8px;"><div style="font-size:18px;font-weight:800;color:#3b82f6;">{d['显存(GB)']}GB</div><div style="font-size:11px;color:var(--text-muted);">显存</div></div>
                            <div style="background:#fee2e2;border-radius:8px;padding:8px;"><div style="font-size:18px;font-weight:800;color:#ef4444;">{d['延迟(ms)']}ms</div><div style="font-size:11px;color:var(--text-muted);">延迟</div></div>
                            <div style="background:#d1fae5;border-radius:8px;padding:8px;"><div style="font-size:18px;font-weight:800;color:#10b981;">{d['质量分']:.2f}</div><div style="font-size:11px;color:var(--text-muted);">质量</div></div>
                        </div>
                        <div style="margin-top:8px;font-size:13px;color:#3b82f6;font-weight:600;">节省 {d['显存节省%']:.1f}%</div>
                    </div>""", unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(qd), use_container_width=True, hide_index=True)
            st.info(" AWQ 在显存受限（<4GB）下提供最优性价比；显存充裕时 FP16 质量最高。")

    with tab3:
        st.markdown("""<div class="info-banner">测试 bs=1/4/8/16 下吞吐量与延迟变化</div>""", unsafe_allow_html=True)
        c1,c2 = st.columns([2,1])
        with c2:
            if st.button(" 运行批次对比", type="primary", key="run_batch", use_container_width=True):
                detector = FakeNewsDetector(st.session_state.client)
                progress_bar = st.progress(0, " 初始化...")
                status_text = st.empty()
                def batch_progress(current, total, msg):
                    progress_bar.progress((current + 1) / total, msg)
                    status_text.caption(f"⏳ {msg}")
                st.session_state["_batch_exp_results"] = run_batch_size_experiment(
                    detector, test_texts, progress_callback=batch_progress)
                progress_bar.progress(1.0, " 批次对比完成！")
                status_text.empty()

        if "_batch_exp_results" in st.session_state:
            bd = st.session_state["_batch_exp_results"]
            if not bd or not isinstance(bd, list):
                st.warning(" 实验数据无效，请重新运行")
            else:
                best_bs = max(bd, key=lambda x: x["吞吐量(tok/s)"])
                bc = st.columns(len(bd))
                for i,d in enumerate(bd):
                    with bc[i]:
                        is_best = d["Batch Size"] == best_bs["Batch Size"]
                        st.markdown(f"""
                        <div style="background:{'rgba(245,158,11,0.08)' if is_best else 'var(--bg-surface)'};border:{'2px solid #f59e0b' if is_best else '1px solid var(--border)'};
                                    border-radius:14px;padding:14px;text-align:center;">
                            <div style="font-size:28px;font-weight:800;color:#3b82f6;">{d['Batch Size']}</div>
                            <div style="font-size:12px;color:var(--text-muted);margin-bottom:8px;">Batch Size</div>
                            <div style="font-size:16px;font-weight:700;color:#ef4444;">{d['吞吐量(tok/s)']:.1f}</div>
                            <div style="font-size:11px;color:var(--text-muted);">tok/s</div>
                            <div style="margin-top:6px;font-size:14px;color:#10b981;font-weight:600;">{d['单条(ms)']:.1f}ms</div>
                            {'<div style="margin-top:8px;font-size:12px;font-weight:700;color:#f59e0b;">🏆 最优</div>' if is_best else ''}
                        </div>""", unsafe_allow_html=True)

                st.markdown("####  吞吐量 × 批次")
                fig_tp = go.Figure()
                bs_vals = [d["Batch Size"] for d in bd]
                fig_tp.add_trace(go.Scatter(x=bs_vals, y=[d["吞吐量(tok/s)"] for d in bd],
                                            mode="lines+markers+text",
                                            text=[f"{d['吞吐量(tok/s)']:.1f}" for d in bd],
                                            textposition="top center",
                                            marker=dict(size=16,color="#3b82f6"),
                                            line=dict(width=3,color="#3b82f6",shape="spline")))
                fig_tp.update_layout(height=350, xaxis=dict(title="Batch Size"),
                                     plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                     margin=dict(t=20), showlegend=False)
                st.plotly_chart(fig_tp, use_container_width=True)

                st.dataframe(pd.DataFrame(bd), use_container_width=True, hide_index=True)
                st.success(f" 推荐 bs=**{best_bs['Batch Size']}**（吞吐量 {best_bs['吞吐量(tok/s)']:.1f} tok/s）")

    with tab4:
        st.markdown("""<div class="info-banner">按虚假类型统计 P/R/F1，分析检测难点</div>""", unsafe_allow_html=True)
        c1,c2 = st.columns([2,1])
        with c2:
            if st.button(" 运行分类型评估", type="primary", key="run_type", use_container_width=True):
                detector = FakeNewsDetector(st.session_state.client)
                eval_n = min(50, len(dataset_rows)) if dataset_rows else 20
                progress_bar = st.progress(0, " 初始化评估...")
                status_text = st.empty()
                if dataset_rows:
                    eval_texts = [row.get("text",row.get("title",""))[:200] for row in dataset_rows[:eval_n]]
                    type_results = []
                    batch_size = 5
                    total_batches = (len(eval_texts) + batch_size - 1) // batch_size
                    for bi in range(0, len(eval_texts), batch_size):
                        batch = eval_texts[bi:bi+batch_size]
                        batch_num = bi // batch_size + 1
                        progress_bar.progress(batch_num / total_batches,
                            f" 检测中 {bi+1}-{min(bi+batch_size,len(eval_texts))}/{len(eval_texts)} 条")
                        status_text.caption(f" 正在处理第 {batch_num}/{total_batches} 批...")
                        type_results.extend(detector.batch_detect(batch))
                    per_type = compute_per_type_metrics(type_results, dataset_rows[:eval_n])
                else:
                    eval_texts_20 = test_texts[:20]
                    per_type = compute_per_type_metrics(detector.batch_detect(eval_texts_20), [])
                progress_bar.progress(1.0, "分类型评估完成！")
                status_text.empty()
                st.session_state["type_eval_results"] = per_type

        if "type_eval_results" in st.session_state:
            per_type = st.session_state["type_eval_results"]
            rows_per = [{"虚假类型":ft, "Precision":m["precision"], "Recall":m["recall"],
                         "F1":m["f1"], "Support":m["support"], "TP":m["tp"], "FP":m["fp"], "FN":m["fn"]}
                        for ft,m in per_type.items()]
            df_type = pd.DataFrame(rows_per)
            valid = [r for r in rows_per if r["Support"]>0 or r["TP"]+r["FP"]>0]
            if valid:
                avg_f1 = sum(r["F1"] for r in valid)/len(valid)
                best = max(valid, key=lambda x: x["F1"])
                worst = min(valid, key=lambda x: x["F1"])
                km = st.columns(4)
                km[0].metric(" 宏平均 F1", f"{avg_f1:.4f}")
                km[1].metric(" 宏平均 Precision", f"{sum(r['Precision'] for r in valid)/len(valid):.4f}")
                km[2].metric(" 宏平均 Recall", f"{sum(r['Recall'] for r in valid)/len(valid):.4f}")
                km[3].metric(" 类型数", len(valid))
                st.dataframe(df_type, use_container_width=True, hide_index=True)
                cbb,cww = st.columns(2)
                cbb.success(f" 最佳：**{best['虚假类型']}**（F1={best['F1']:.4f}）")
                cww.warning(f" 最差：**{worst['虚假类型']}**（F1={worst['F1']:.4f}）")

def render_export():
    """结果导出"""
    st.markdown("""
    <div style="display:flex;align-items:center;gap:16px;margin-bottom:8px;">
        <div style="width:48px;height:48px;border-radius:14px;background:linear-gradient(135deg,#f59e0b,#fbbf24);
                    display:flex;align-items:center;justify-content:center;font-size:22px;box-shadow:0 4px 12px rgba(245,158,11,0.2);">📥</div>
        <div><h1 style="font-size:1.8rem;margin:0;" class="gradient-text">结果导出</h1>
            <p style="color:var(--text-secondary);margin:2px 0 0 0;font-size:14px;">导出为 JSON / CSV 格式</p></div>
    </div>
    """, unsafe_allow_html=True)

    history = st.session_state.get("history", [])
    if not history:
        st.warning(" 暂无检测记录")
        return

    st.markdown(f"""<div class="info-banner"> 当前共 <b>{len(history)}</b> 条检测记录</div>""", unsafe_allow_html=True)

    col1,col2 = st.columns([2,1])
    with col1:
        export_mode = st.radio(" 导出范围", ["全部记录", "仅高风险（低/极低可信度）", "自定义数量"], horizontal=True, key="export_mode")
    with col2:
        if export_mode == "自定义数量":
            n = st.number_input("导出条数", 1, len(history), min(10, len(history)))
        else:
            n = None

    if export_mode == "仅高风险（低/极低可信度）":
        export_data = [r for r in history if getattr(r,"credibility","中") in ["低","极低"]]
    elif export_mode == "自定义数量":
        export_data = history[:n]
    else:
        export_data = history

    st.markdown(f" 将导出 **{len(export_data)}** 条记录")

    with st.expander(" 预览导出数据", expanded=len(export_data)<=5):
        rows = [{"序号":i+1, "文本摘要":getattr(r,"text","")[:60],
                 "可信度":getattr(r,"credibility","?"),
                 "分数":getattr(r,"credibility_score",0),
                 "虚假类型":"、".join(getattr(r,"fake_types",[])),
                 "耗时(s)":getattr(r,"processing_time",0)} for i,r in enumerate(export_data[:20])]
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

    st.markdown("---")
    ca,cb = st.columns(2)
    with ca:
        st.markdown("####  JSON 格式")
        json_str = export_json(export_data)
        st.download_button(" 下载 JSON", json_str.encode("utf-8"),
                           "detection_results.json", "application/json",
                           use_container_width=True, type="primary")
        st.caption(f" {len(json_str.encode('utf-8')):,} 字节")
    with cb:
        st.markdown("####  CSV 格式")
        csv_str = export_csv(export_data)
        st.download_button(" 下载 CSV", csv_str.encode("utf-8-sig"),
                           "detection_results.csv", "text/csv",
                           use_container_width=True)
        st.caption(f" {len(csv_str.encode('utf-8-sig')):,} 字节")

# 主应用
def main():
    # 未登录：显示登录界面
    if not st.session_state.logged_in:
        st.markdown("<br><br>", unsafe_allow_html=True)
        left_spacer, content, right_spacer = st.columns([1, 2.2, 1])
        with content:
            st.markdown("""
            <div style="text-align:center;margin-bottom:8px;">
                <div style="display:inline-block;width:72px;height:72px;border-radius:20px;
                            background:linear-gradient(135deg,#3b82f6,#06b6d4);
                            display:flex;align-items:center;justify-content:center;
                            font-size:36px;box-shadow:0 8px 24px rgba(59,130,246,0.3);">⚖️</div>
            </div>
            <h1 style="text-align:center;font-size:2rem;margin:12px 0 8px;" class="gradient-text">
                基于 DeepSeek-R1<br>虚假新闻检测与事实核查系统
            </h1>
            <p style="text-align:center;color:var(--text-secondary);font-size:16px;margin-bottom:32px;">
                基于大语言模型的智能虚假信息检测与事实核查平台
            </p>
            """, unsafe_allow_html=True)

            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown("""
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:16px;">
                <span style="font-size:20px;">⚙️</span>
                <span style="font-size:16px;font-weight:600;">API 连接配置</span>
            </div>
            """, unsafe_allow_html=True)

            provider_list = ["deepseek-r1", "bailian", "deepseek", "openai", "custom"]
            provider_names = {
                "deepseek-r1": " DeepSeek-R1（推荐）",
                "bailian": " 阿里云百炼（通义千问）",
                "deepseek": " DeepSeek-V3",
                "openai": " OpenAI GPT-4o",
                "custom": " 自定义 API 接口",
            }
            provider = st.selectbox("选择模型提供商", provider_list,
                                    format_func=lambda x: provider_names[x], key="login_provider")
            api_key = st.text_input("API Key", type="password", placeholder="", key="login_api_key")
            if provider == "custom":
                custom_url = st.text_input("API 地址", placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1")
                custom_model = st.text_input("模型名称", placeholder="deepseek-reasoner")
            else:
                custom_url, custom_model = "", ""

            use_mock = st.checkbox(" 使用模拟模式（无需API Key）", help="适合演示和开发调试")

            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                test_clicked = st.button(" 测试连接", use_container_width=True, disabled=(not api_key and not use_mock), key="login_test")
            with btn_col2:
                login_clicked = st.button(" 连接并进入系统", use_container_width=True, type="primary", key="login_enter")
            st.markdown('</div>', unsafe_allow_html=True)

            if test_clicked:
                if not api_key and not use_mock:
                    st.error("请先输入 API Key 或启用模拟模式")
                else:
                    with st.spinner(" 正在测试连接"):
                        try:
                            client = CloudModelClient.create(provider, api_key, custom_url, custom_model)
                            result = client.test_connection(timeout=30)
                            if result["success"]:
                                st.success(f" {result['message']}")
                            else:
                                st.error(f" 连接失败：{result['message']}")
                        except Exception as e:
                            st.error(f" 异常：{e}")

            if login_clicked:
                if not use_mock and not api_key:
                    st.error("请输入 API Key 或启用模拟模式")
                elif provider == "custom" and not use_mock and (not custom_url or not custom_model):
                    st.error("自定义 API 需要填写地址和模型名称")
                else:
                    with st.spinner("验证连接"):
                        if use_mock:
                            st.session_state.client = MockModelClient()
                            st.session_state.provider = "mock"
                            st.session_state.model_name = "模拟模式 (Mock)"
                            st.session_state.logged_in = True
                            st.success(" 模拟模式已就绪")
                            time.sleep(1)
                            st.rerun()
                        else:
                            try:
                                client = CloudModelClient.create(provider, api_key, custom_url, custom_model)
                                result = client.test_connection(timeout=30)
                                if result["success"]:
                                    st.session_state.client = client
                                    st.session_state.provider = provider
                                    st.session_state.model_name = result.get("model", "未知模型")
                                    st.session_state.api_key = api_key
                                    st.session_state.logged_in = True
                                    st.success(f" {result['message']}")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f" 验证失败：{result['message']}")
                            except Exception as e:
                                st.error(f" 连接失败：{e}")

            st.markdown("""
            <div style="text-align:center;color:var(--text-muted);font-size:13px;margin-top:20px;">
                <b> 推荐：DeepSeek-R1</b> · 推理增强模型<br>
                <span style="font-size:12px;">
                获取 Key：<a href="https://platform.deepseek.com/api_keys" target="_blank" style="color:#3b82f6;">platform.deepseek.com</a>
                </span>
            </div>
            """, unsafe_allow_html=True)
        return

    # 已登录：主界面
    # 侧边栏导航
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center;padding:12px 0 16px;border-bottom:1px solid var(--border);margin-bottom:12px;">
            <div style="font-size:28px;">⚖️</div>
            <div style="font-size:18px;font-weight:700;color:var(--text);">DeepSeek-R1</div>
            <div style="font-size:12px;color:var(--text-muted);">事实核查系统</div>
        </div>
        """, unsafe_allow_html=True)

        dot_class = "connected" if st.session_state.provider != "mock" else "mock"
        st.markdown(f"""
        <div style="background:var(--bg-surface);border-radius:10px;padding:12px;margin-bottom:12px;border:1px solid var(--border);">
            <div style="font-size:12px;color:var(--text-muted);margin-bottom:4px;">当前模型</div>
            <div style="display:flex;align-items:center;gap:6px;">
                <span class="status-dot {dot_class}"></span>
                <span style="font-weight:600;font-size:14px;">{st.session_state.model_name}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("<div style='font-size:12px;color:var(--text-muted);margin-bottom:8px;'> 功能导航</div>", unsafe_allow_html=True)

        nav_items = [
            ("🏠 仪表盘", "dashboard"),
            ("📝 单文本检测", "single"),
            ("📦 批量检测", "batch"),
            ("💬 问答", "qa"),
            ("📊 统计分析", "stats"),
            ("🧪 对比实验", "experiment"),
            ("📥 结果导出", "export"),
        ]
        for label, page_key in nav_items:
            btn_type = "primary" if st.session_state.page == page_key else "secondary"
            if st.button(label, use_container_width=True, key=f"nav_{page_key}", type=btn_type):
                st.session_state.page = page_key
                st.rerun()

        st.markdown("---")
        if st.button(" 退出登录", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.client = None
            st.session_state.history = []
            st.session_state.page = "dashboard"
            st.rerun()

    page = st.session_state.get("page", "dashboard")
    if page == "dashboard":
        render_dashboard()
    elif page == "single":
        render_single_detect()
    elif page == "batch":
        render_batch_detect()
    elif page == "qa":
        render_qa()
    elif page == "stats":
        render_stats()
    elif page == "experiment":
        render_experiment()
    elif page == "export":
        render_export()
    else:
        render_dashboard()

if __name__ == "__main__":
    main()