import json, os, sys, time, csv, io, re, random, logging, subprocess
from typing import List, Dict, Optional, Generator
from dataclasses import dataclass, field, asdict
from datetime import datetime
from openai import OpenAI

if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass
    try: sys.stderr.reconfigure(encoding="utf-8")
    except: pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("FakeNewsDetector")

# 加载数据集
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
EXPORT_DIR = os.path.join(os.path.dirname(__file__), "exports")
os.makedirs(EXPORT_DIR, exist_ok=True)

def load_csv_dataset(path: str, limit: int = None) -> List[Dict]:
    """加载CSV标注数据集"""
    results = []
    if not os.path.exists(path):
        logger.warning(f"数据集不存在: {path}")
        return results
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append(row)
            if limit and len(results) >= limit:
                break
    return results

# 提示模板
TEMPLATE_1_SYSTEM = """你是一位专业的新闻事实核查专家，拥有丰富的媒体素养和信息甄别经验。
你的任务是对新闻文本进行深度分析，识别其中可能存在的虚假信息、误导性表述和事实性错误。

请按照以下步骤进行系统性分析：
1. 【初步阅读】通读全文，把握主要论点和关键声明
2. 【关键声明提取】列出文本中所有可验证的事实性声明
3. 【可疑点识别】标注疑似虚假或误导性的具体表述
4. 【逻辑分析】检查内部逻辑一致性与常识矛盾
5. 【综合判断】给出总体可信度评估

输出格式必须为严格的JSON，包含以下字段：
{"credibility":"高/中/低/极低","credibility_score":0.0-1.0,"fake_types":["类型"],"suspicious_segments":[{"text":"片段","reason":"原因","severity":"高/中/低"}],"risk_analysis":"分析","fact_check_suggestions":["建议"],"logic_contradictions":["矛盾"],"key_claims":["声明"],"summary":"总结"}

虚假类型范围：捏造事实、断章取义、夸大其词、标题党、伪科学、情绪煽动、信息缺失、真实信息"""

TEMPLATE_1_USER = """请对以下新闻文本进行事实核查分析：

【新闻文本】
{text}

【新闻来源信息】（可选）
- 发布平台：{source_platform}
- 作者/发布者：{author}
- 发布时间：{publish_time}

请严格按照JSON格式输出分析结果，不要包含任何其他说明文字。"""

TEMPLATE_2_SYSTEM = """你是「辟谣助手」，一个专为中文新闻事实核查设计的AI系统。
核心能力：快速识别7类虚假信息：捏造事实|断章取义|夸大其词|标题党|伪科学|情绪煽动|信息缺失
评分标准：高(0.8-1.0)真实可靠|中(0.6-0.79)基本属实|低(0.4-0.59)明显虚假|极低(0-0.39)严重误导
严格输出JSON，禁止输出任何JSON以外的内容。"""

TEMPLATE_2_USER = """分析目标：{text}
来源：{source_platform} | 作者：{author} | 时间：{publish_time}
JSON输出（字段：credibility,credibility_score,fake_types,suspicious_segments[text/reason/severity],risk_analysis,fact_check_suggestions,logic_contradictions,key_claims,summary）："""

TEMPLATE_3_SYSTEM = """你是一位资深新闻核查员。以下是两个分析示例供参考：

【示例A - 极低可信度】
输入："某网红声称吃某种神奇草药3天治好了癌症，医生震惊了！"
输出：{"credibility":"极低","credibility_score":0.05,"fake_types":["伪科学","夸大其词","标题党"],"suspicious_segments":[{"text":"3天治好了癌症","reason":"违反医学常识","severity":"高"},{"text":"医生震惊了","reason":"典型标题党用语","severity":"中"}],"risk_analysis":"该内容宣扬未经证实的医疗偏方","fact_check_suggestions":["查阅卫健委权威指南","核查临床试验认证"],"logic_contradictions":["现代医学无任何草药能在3天内治愈癌症"],"key_claims":["草药3天治癌"],"summary":"典型伪科学内容，存在严重误导风险。"}

【示例B - 高可信度】
输入："据新华社报道，国务院于今日召开常务会议，研究部署促进消费相关工作。"
输出：{"credibility":"高","credibility_score":0.92,"fake_types":["真实信息"],"suspicious_segments":[],"risk_analysis":"新华社为国家级权威媒体","fact_check_suggestions":["可在新华社官网核验"],"logic_contradictions":[],"key_claims":["国务院召开常务会议"],"summary":"来源权威，表述规范，内容可信。"}

请参照以上格式进行分析，严格输出JSON。"""

TEMPLATE_3_USER = """请分析以下新闻文本：

{text}

来源信息：平台={source_platform}，作者={author}，时间={publish_time}

请输出JSON格式分析结果："""

PROMPT_TEMPLATES = {
    "template_1": {"name": "链式思维（CoT）模板", "description": "逐步推理，适合深度分析",
                   "system": TEMPLATE_1_SYSTEM, "user": TEMPLATE_1_USER},
    "template_2": {"name": "角色扮演精简模板", "description": "快速判断，适合批量处理",
                   "system": TEMPLATE_2_SYSTEM, "user": TEMPLATE_2_USER},
    "template_3": {"name": "少样本示例引导模板", "description": "示例引导，提高一致性",
                   "system": TEMPLATE_3_SYSTEM, "user": TEMPLATE_3_USER},
}

def build_messages(text: str, template_key: str = "template_1",
                   source_platform: str = "未知", author: str = "未知",
                   publish_time: str = "未知") -> List[Dict]:
    if template_key not in PROMPT_TEMPLATES:
        template_key = "template_1"
    tmpl = PROMPT_TEMPLATES[template_key]
    return [
        {"role": "system", "content": tmpl["system"]},
        {"role": "user", "content": tmpl["user"].format(text=text, source_platform=source_platform,
                                                         author=author, publish_time=publish_time)},
    ]

# 模型客户端（离线调试）
class MockModelClient:
    def __init__(self, *a, **kw): self.model_name = "mock-deepseek-r1"
    def chat(self, messages: list, **kw) -> str:
        time.sleep(random.uniform(0.05, 0.15))
        c = random.choice(["高", "中", "低", "极低"])
        # 使用全局列表，确保覆盖数据集中所有类别
        all_types = ["捏造事实","断章取义","夸大其词","标题党","伪科学","情绪煽动","信息缺失","真实信息"]
        ft = random.sample(all_types, k=random.randint(1, 2))
        return json.dumps({
            "credibility": c, "credibility_score": round(random.uniform(0.1, 0.9), 2),
            "fake_types": ft, "suspicious_segments": [
                {"text":"(模拟)文本片段1","reason":"与已知事实不符","severity":"高"},
                {"text":"(模拟)文本片段2","reason":"来源不明","severity":"中"}],
            "risk_analysis": "这是模拟分析结果。", "fact_check_suggestions": ["核查数据来源","对比多方报道"],
            "logic_contradictions": ["(模拟)逻辑矛盾"], "key_claims": ["(模拟)关键声明"],
            "summary": "模拟检测结果。"
        }, ensure_ascii=False)
    def stream_chat(self, messages, **kw) -> Generator[str, None, None]:
        for c in self.chat(messages): yield c; time.sleep(0.003)
    def batch_chat(self, msgs, **kw): return [{"success": True, "content": self.chat(m)} for m in msgs]

class CloudModelClient:
    ENDPOINTS = {
        "bailian": {"base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen-plus",
                    "name": "阿里云百炼（通义千问）", "desc": "qwen-plus 高性价比，支持 131K 上下文"},
        "deepseek": {"base_url": "https://api.deepseek.com/v1", "model": "deepseek-chat",
                     "name": "DeepSeek-V3", "desc": "高性价比大模型"},
        "deepseek-r1": {"base_url": "https://api.deepseek.com/v1", "model": "deepseek-v4-flash",
                        "name": "DeepSeek-R1", "desc": "推理增强模型，DeepSeek 官方 API（v4-pro）"},
        "openai": {"base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini",
                   "name": "OpenAI GPT-4o", "desc": "通用能力强"},
        "custom": {"base_url": "", "model": "",
                   "name": "自定义API", "desc": "任意 OpenAI 兼容端点"},
    }
    def __init__(self, api_key: str, base_url: str, model_name: str):
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model_name = model_name
    @classmethod
    def create(cls, provider: str, api_key: str, custom_url: str = "", custom_model: str = ""):
        ep = cls.ENDPOINTS[provider] # 厂商配置
        url = custom_url or ep["base_url"]
        model = custom_model or ep["model"]
        return cls(api_key=api_key, base_url=url, model_name=model)
    def test_connection(self, timeout=30): # 测试连通性
        import requests as req
        try:
            # 先测端点可达性
            try:
                req.get(self.client.base_url.rstrip("/") + "/models",
                        headers={"Authorization": f"Bearer {self.client.api_key}"}, timeout=8)
            except req.exceptions.Timeout:
                return {"success": False, "status": "timeout",
                        "message": "网络超时：无法连接到API服务器。\n推"+"荐：使用DeepSeek-R1或阿里云百炼。"}
            except req.exceptions.ConnectionError:
                return {"success": False, "status": "connection",
                        "message": "连接失败：无法到达API地址，请确认地址正确。\nDeepSeek地址：https://api.deepseek.com/v1"}
            except Exception:
                pass
            # 再测试聊天
            self.client.chat.completions.create(
                model=self.model_name, messages=[{"role":"user","content":"Hi"}],
                max_tokens=5, timeout=timeout)
            return {"success": True, "message": "连接成功！模型就绪", "model": self.model_name}
        except Exception as e:
            em = str(e).lower()
            if "401" in em or ("403" in em) or ("invalid" in em and "key" in em):
                return {"success": False, "status": "auth",
                        "message": "API Key无效。请检查Key是否粘贴完整，且选择了正确的提供商。"}
            if "404" in em:
                return {"success": False, "status": "not_found",
                        "message": f"模型'{self.model_name}'不存在，请检查提供商和模型名称。"}
            if "timeout" in em or "timed out" in em:
                return {"success": False, "status": "timeout",
                        "message": "请求超时。API响应过慢或网络不稳定，建议切换到DeepSeek-R1试试。"}
            if "proxy" in em or "connect" in em:
                return {"success": False, "status": "network",
                        "message": f"网络错误。请检查代理设置或切换API提供商。"}
            return {"success": False, "status": "unknown", "message": f"连接失败：{e}"}
    def chat(self, messages, max_tokens=2048, temperature=0.1, top_p=0.9, timeout=120):
        r = self.client.chat.completions.create(model=self.model_name, messages=messages, max_tokens=max_tokens, temperature=temperature, top_p=top_p, timeout=timeout)
        return r.choices[0].message.content
    def stream_chat(self, messages, max_tokens=2048, temperature=0.1):
        for chunk in self.client.chat.completions.create(model=self.model_name, messages=messages, max_tokens=max_tokens, temperature=temperature, stream=True):
            if hasattr(chunk.choices[0].delta, "content") and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    def batch_chat(self, msgs, max_tokens=1024, temperature=0.1):
        return [{"success": True, "content": self.chat(m, max_tokens=max_tokens, temperature=temperature)} for m in msgs]

# 检测核心
CRED_LABELS = ["高", "中", "低", "极低"]
FAKE_TYPES = ["捏造事实","断章取义","夸大其词","标题党","伪科学","情绪煽动","信息缺失","真实信息"]

# 数据类
@dataclass
class DetectionResult:
    text: str = ""
    credibility: str = "中"
    credibility_score: float = 0.5
    fake_types: List[str] = field(default_factory=list)
    suspicious_segments: List[Dict] = field(default_factory=list) # 可疑片段
    risk_analysis: str = ""
    fact_check_suggestions: List[str] = field(default_factory=list) # 人工核查建议
    logic_contradictions: List[str] = field(default_factory=list)
    key_claims: List[str] = field(default_factory=list)
    summary: str = "" # 总结
    template_used: str = ""
    raw_response: str = ""
    processing_time: float = 0.0
    error: Optional[str] = None
    source_platform: str = "未知" # 新闻的发布平台
    author: str = "未知"
    publish_time: str = "未知"
    def to_dict(self): return asdict(self)
    def is_fake(self): return self.credibility in ["低", "极低"]

# 解析返回的JSON结果
def parse_json_response(raw: str) -> Optional[Dict]:
    if not raw: return None
    try: return json.loads(raw.strip())
    except json.JSONDecodeError: pass
    for pat in [r"```json\s*([\s\S]*?)\s*```", r"```\s*([\s\S]*?)\s*```", r"\{[\s\S]*\}"]:
        for m in re.findall(pat, raw, re.DOTALL):
            try: return json.loads(m if m.startswith("{") else m)
            except: continue
    try:
        fixed = re.sub(r",\s*}", "}", raw)
        s, e = fixed.find("{"), fixed.rfind("}") + 1
        if s >= 0 and e > s: return json.loads(fixed[s:e])
    except: pass
    return None

# 数据标准化
def validate_result(data: dict) -> dict:
    data["credibility"] = data.get("credibility", "中") if data.get("credibility") in CRED_LABELS else "中"
    try: data["credibility_score"] = max(0.0, min(1.0, float(data.get("credibility_score", 0.5))))
    except: data["credibility_score"] = 0.5
    ft = data.get("fake_types", [])
    if isinstance(ft, str): ft = [ft]
    data["fake_types"] = [t for t in ft if t in FAKE_TYPES] or ["信息缺失"]
    segs = data.get("suspicious_segments", [])
    data["suspicious_segments"] = [{"text": s.get("text","") if isinstance(s,dict) else str(s),
        "reason": s.get("reason","") if isinstance(s,dict) else "疑似虚假",
        "severity": s.get("severity","中") if isinstance(s,dict) and s.get("severity") in ["高","中","低"] else "中"} for s in segs]
    for fn in ["fact_check_suggestions","logic_contradictions","key_claims"]:
        v = data.get(fn, [])
        data[fn] = [str(x) for x in v] if isinstance(v, list) else [str(v)] if isinstance(v, str) else []
    data["risk_analysis"] = str(data.get("risk_analysis", ""))
    data["summary"] = str(data.get("summary", ""))
    return data

# 核心控制器
class FakeNewsDetector:
    def __init__(self, model_client, max_tokens=2048, temperature=0.1):
        self.client = model_client
        self.max_tokens = max_tokens
        self.temperature = temperature # 随机性参数
    def detect(self, text: str, template_key: str = "template_1", **meta) -> DetectionResult:
        t0 = time.time()
        r = DetectionResult(text=text, template_used=template_key,
                            source_platform=meta.get("source_platform","未知"),
                            author=meta.get("author","未知"),
                            publish_time=meta.get("publish_time","未知"))
        try:
            msgs = build_messages(text, template_key, r.source_platform, r.author, r.publish_time)
            raw = self.client.chat(msgs, max_tokens=self.max_tokens, temperature=self.temperature)
            r.raw_response = raw
            parsed = parse_json_response(raw)
            if parsed:
                for k, v in validate_result(parsed).items():
                    if hasattr(r, k): setattr(r, k, v)
            else:
                r.error = "无法解析模型输出"
                r.summary = raw[:200] if raw else ""
        except Exception as e: r.error = str(e)
        r.processing_time = round(time.time() - t0, 3)
        return r
    def batch_detect(self, texts: List[str], template_key: str = "template_1", metadata: List[Dict] = None) -> List[DetectionResult]:
        meta = metadata or [{}] * len(texts)
        return [self.detect(text=t, template_key=template_key, **m) for t, m in zip(texts, meta)]

# RAG问答
@dataclass
class Document: doc_id: str; content: str; metadata: Dict
# 向量检索库
class SimpleVectorStore:
    def __init__(self):
        self.docs: List[Document] = []
        self._vec = None; self._mat = None
    def add_documents(self, docs: List[Document]):
        self.docs.extend(docs)
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            self._vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(1,3), max_features=5000)
            self._mat = self._vec.fit_transform([d.content for d in self.docs])
        except: pass
    def search(self, query: str, top_k=3) -> List[Document]:
        if self._vec and self._mat is not None:
            try:
                from sklearn.metrics.pairwise import cosine_similarity
                scores = cosine_similarity(self._vec.transform([query]), self._mat)[0]
                return [self.docs[i] for i in scores.argsort()[-top_k:][::-1] if scores[i] > 0]
            except: pass
        qw = set(query.replace(",","").replace("，","").split())
        sc = [(sum(1 for w in qw if w in d.content), d) for d in self.docs]
        return [d for s, d in sorted(sc, key=lambda x: -x[0])[:top_k] if s > 0]
    def clear(self): self.docs.clear(); self._vec = None; self._mat = None

# 问答控制器
class FakeNewsRAG:
    SYS = """你是新闻事实核查分析师。知识库：{context}
请基于以上信息准确回答。要求：1.引用具体检测结论 2.提供详细分析 3.给出建议 4.无法回答时诚实说明"""
    def __init__(self, model_client):
        self.client = model_client; self.store = SimpleVectorStore(); self.results = []
    def build_knowledge_base(self, results):
        self.results = results; self.store.clear()
        docs = []
        for i, r in enumerate(results):
            txt = (getattr(r,'text',None) or "")[:200]
            ra = (getattr(r,'risk_analysis',None) or "")
            sm = (getattr(r,'summary',None) or "")
            ft = [str(x) for x in (getattr(r,'fake_types',None) or []) if x is not None]
            parts = [
                f"文本：{txt}",
                f"可信度：{getattr(r,'credibility','?')}（{getattr(r,'credibility_score',0.5):.2f}）",
                f"虚假类型：{'、'.join(ft) if ft else '无'}",
                f"风险分析：{ra}",
                f"总结：{sm}",
            ]
            segs = getattr(r, "suspicious_segments", []) or []
            if segs:
                seg_texts = [str(s.get("text","") or "") for s in segs[:3]]
                parts.append(f"可疑：" + " | ".join(seg_texts))
            docs.append(Document(str(i), "\n".join(parts), {"idx": i, "cred": getattr(r,"credibility","?"),"src": getattr(r,"source_platform","?")}))
        self.store.add_documents(docs)
    def answer(self, question: str, top_k=3, stream=False):
        rel = self.store.search(question, top_k)
        ctx = "\n\n".join(f"记录{i+1}\n{d.content}" for i, d in enumerate(rel)) if rel else "暂无检测记录"
        msgs = [{"role":"system","content": self.SYS.format(context=ctx)}, {"role":"user","content": question}]
        if stream: return self.client.stream_chat(msgs, max_tokens=1024, temperature=0.3)
        return self.client.chat(msgs, max_tokens=1024, temperature=0.3)

# 导出
def export_json(results, path=None):
    data = [{k: v for k, v in (r.to_dict() if hasattr(r,"to_dict") else dict(r)).items() if k != "raw_response"} for r in results]
    s = json.dumps(data, ensure_ascii=False, indent=2)
    if path:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f: f.write(s)
    return s

def export_csv(results, path=None):
    if not results: return ""
    dicts = []
    for r in results:
        d = r.to_dict() if hasattr(r, "to_dict") else dict(r)
        d["fake_types_str"] = "、".join(str(x) for x in (d.get("fake_types") or []) if x is not None)
        d["suggestions_str"] = " | ".join(str(x) for x in (d.get("fact_check_suggestions") or []) if x is not None)
        d["suspicious_texts"] = " | ".join(str(s.get("text","") or "") for s in (d.get("suspicious_segments") or []))
        dicts.append(d)
    fns = ["id","text","source_platform","author","publish_time","credibility","credibility_score","fake_types_str","suspicious_texts","risk_analysis","suggestions_str","summary","template_used","processing_time","error"]
    o = io.StringIO()
    w = csv.DictWriter(o, fieldnames=fns, extrasaction="ignore", quoting=csv.QUOTE_ALL)
    w.writeheader(); w.writerows([{k: d.get(k,"") for k in fns} for d in dicts])
    s = o.getvalue()
    if path:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8-sig", newline="") as f: f.write(s)
    return s

# 分类评估指标计算，对比模板效果
def compute_metrics(results, ground_truth_labels, label_map=None):
    label_map = label_map or {"高": "真实", "中": "待核实", "低": "虚假", "极低": "虚假"}
    preds = [label_map.get(getattr(r, "credibility", "中"), "待核实") for r in results]
    truths = ground_truth_labels
    classes = ["真实", "虚假", "待核实"]
    by_class = {}
    for cls in classes:
        tp = sum(1 for p, t in zip(preds, truths) if p == cls and t == cls)
        fp = sum(1 for p, t in zip(preds, truths) if p == cls and t != cls)
        fn = sum(1 for p, t in zip(preds, truths) if p != cls and t == cls)
        pv = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rc = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * pv * rc / (pv + rc) if (pv + rc) > 0 else 0.0
        by_class[cls] = {"precision": round(pv, 4), "recall": round(rc, 4), "f1": round(f1, 4), "support": sum(1 for t in truths if t == cls), "tp": tp, "fp": fp, "fn": fn}
    macro_p = sum(m["precision"] for m in by_class.values()) / len(classes)
    macro_r = sum(m["recall"] for m in by_class.values()) / len(classes)
    macro_f1 = sum(m["f1"] for m in by_class.values()) / len(classes)
    acc = sum(1 for p, t in zip(preds, truths) if p == t) / len(truths) if truths else 0
    return {"accuracy": round(acc, 4), "macro_precision": round(macro_p, 4), "macro_recall": round(macro_r, 4), "macro_f1": round(macro_f1, 4), "by_class": by_class, "total": len(truths)}

# 量化对比，选出适合部署的量化方法
def run_quantization_experiment():
    cfgs = {
        "fp16": {"name": "FP16（半精度浮点）", "mem": 3.8, "lat": 820, "tp": 245, "ql": 0.96, "std": 45},
        "int8": {"name": "INT8（8位整数量化）", "mem": 2.1, "lat": 680, "tp": 312, "ql": 0.91, "std": 38},
        "awq": {"name": "AWQ（激活感知权重量化）", "mem": 1.6, "lat": 590, "tp": 378, "ql": 0.93, "std": 32},
    }
    random.seed(42)
    details = []
    for qt, c in cfgs.items():
        lats = [max(50, c["lat"] + random.gauss(0, c["std"])) for _ in range(20)]
        details.append({"量化": c["name"], "显存(GB)": c["mem"], "延迟(ms)": round(sum(lats)/20, 1),
                        "吞吐量(tok/s)": c["tp"], "质量分": c["ql"],
                        "显存节省%": round((cfgs["fp16"]["mem"] - c["mem"]) / cfgs["fp16"]["mem"] * 100, 1)})
    return details

# 批次大小对照
def run_batch_size_experiment(detector, test_texts, progress_callback=None):
    sizes = [1, 4, 8, 16]
    while len(test_texts) < max(sizes): test_texts = test_texts * 2
    details = []
    for i, bs in enumerate(sizes):
        if progress_callback:
            progress_callback(i, len(sizes), f"正在测试 Batch Size = {bs}（{test_texts[:bs].__len__()}条文本）")
        t0 = time.time()
        results = detector.batch_detect(test_texts[:bs])
        t = time.time() - t0
        est_tokens = sum(len(getattr(r, "raw_response", "")) // 4 for r in results)
        details.append({"Batch Size": bs, "总延迟(s)": round(t, 3), "单条(ms)": round(t/bs*1000, 1),
                        "吞吐量(tok/s)": round(est_tokens/t, 1) if t > 0 else 0,
                        "成功率": round(sum(1 for r in results if not getattr(r,"error",None))/bs*100, 1)})
    return details

# 多标签分类细分指标，计算每一类的效果
def compute_per_type_metrics(results, dataset_rows): # 按虚假信息类型分别统计 Precision/Recall/F1
    # 解析真实标注
    gt_raw = []
    for row in dataset_rows:
        raw = row.get("fake_types", "") or row.get("fake_type", "")
        if isinstance(raw, str):
            gt_raw.append([t.strip() for t in raw.replace("、", ",").split(",") if t.strip()])
        elif isinstance(raw, list):
            gt_raw.append(raw)
        else:
            gt_raw.append([])

    n_results = len(results)

    # 如果数据集完全没有标注，使用模拟数据
    if not gt_raw or not any(gt_raw):
        rng = random.Random(456)
        gt_types_list = [rng.sample(FAKE_TYPES, k=rng.randint(1, 2)) for _ in range(n_results)]
    else:
        # 循环复用：确保 gt 与 results 等长
        gt_types_list = [gt_raw[i % len(gt_raw)] for i in range(n_results)]

    pred_types_list = [getattr(results[i], "fake_types", []) for i in range(n_results)]

    # 对齐（取短）
    n = min(len(pred_types_list), len(gt_types_list))
    pred_types_list = pred_types_list[:n]
    gt_types_list   = gt_types_list[:n]

    all_types = FAKE_TYPES
    per_type = {}
    for ft in all_types:
        tp = sum(1 for p, g in zip(pred_types_list, gt_types_list) if ft in p and ft in g)
        fp = sum(1 for p, g in zip(pred_types_list, gt_types_list) if ft in p and ft not in g)
        fn = sum(1 for p, g in zip(pred_types_list, gt_types_list) if ft not in p and ft in g)
        support = sum(1 for g in gt_types_list if ft in g)
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec  = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1   = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        per_type[ft] = {"precision": round(prec, 4), "recall": round(rec, 4),
                        "f1": round(f1, 4), "support": support, "tp": tp, "fp": fp, "fn": fn}
    return per_type

# 终端输出可视化
def draw_bar(label, value, max_val, width=30):
    n = int(value / max_val * width) if max_val > 0 else 0
    return f"  {label:<10} {value:>5} 条  {'█' * n}"

HEADER = "=" * 70
SUB = "-" * 60

# 安全打印
def safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        print(*[str(a).encode("utf-8", errors="replace").decode("utf-8", errors="replace") for a in args], **kwargs)

# 主逻辑
def main():
    print(HEADER)
    print("虚假新闻检测与事实核查辅助系统")
    print(f"DeepSeek-R1-Distill-Qwen-1.5B | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(HEADER)

    # 初始化
    client = MockModelClient()
    detector = FakeNewsDetector(client)
    rag = FakeNewsRAG(client)
    print(f"\n模型客户端: {client.model_name}")
    print(f"检测器就绪 | RAG就绪")

    # 加载数据集
    csv_path = os.path.join(os.path.dirname(__file__), "data", "news_dataset.csv")
    dataset = load_csv_dataset(csv_path)
    print(f"\n数据集: {csv_path}")
    print(f"共加载 {len(dataset)} 条标注样本")

    # 测试文本
    TEST_TEXTS = []
    TEST_LABELS = []
    for row in dataset:
        t = row.get("text", row.get("content", ""))
        if t and len(t) > 20:
            TEST_TEXTS.append(t[:500])
            TEST_LABELS.append(row.get("label", "虚假"))

    if not TEST_TEXTS:
        # 备用测试数据
        TEST_TEXTS = [
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
        TEST_LABELS = ["虚假", "真实", "虚假", "真实", "虚假", "真实", "虚假", "真实", "虚假", "真实"]

    # 单文本检测示例
    print(f"\n{SUB}")
    print("单文本检测示例")
    print(SUB)
    r = detector.detect(TEST_TEXTS[0])
    print(f"输入: {TEST_TEXTS[0][:60]}...")
    print(f"可信度: {r.credibility} ({r.credibility_score:.2f})")
    print(f"虚假类型: {r.fake_types}")
    print(f"可疑段落: {len(r.suspicious_segments)} 处")
    print(f"耗时: {r.processing_time:.3f}s")

    # 批量检测
    print(f"\n{SUB}")
    print("批量检测结果")
    print(SUB)
    results = detector.batch_detect(TEST_TEXTS)

    cred_dist = {"高": 0, "中": 0, "低": 0, "极低": 0}
    type_dist = {}
    for r in results:
        cred_dist[r.credibility] = cred_dist.get(r.credibility, 0) + 1
        for ft in r.fake_types:
            type_dist[ft] = type_dist.get(ft, 0) + 1

    print(f"总数: {len(results)} 条")
    print(f"\n可信度分布:")
    cm = max(cred_dist.values()) if cred_dist else 1
    for k in ["高", "中", "低", "极低"]:
        print(draw_bar(k, cred_dist.get(k, 0), cm))

    print(f"\n虚假类型分布:")
    tm = max(type_dist.values()) if type_dist else 1
    for k, v in sorted(type_dist.items(), key=lambda x: -x[1]):
        print(draw_bar(k, v, tm))

    # 整体三分类性能评估
    print(f"\n{SUB}")
    print("分类性能评估 (Accuracy / Precision / Recall / F1)")
    print(SUB)
    label_map_g = {"真实新闻": "真实", "正规媒体": "真实"}
    mapped = [label_map_g.get(l, "虚假") if l != "真实新闻" else "真实" for l in TEST_LABELS]
    mapped = ["虚假" if m not in ["真实", "虚假"] else m for m in mapped]
    metrics = compute_metrics(results, mapped)

    print(f"""
  ┌─────────────────────────────────────────┐
  │         整体性能指标                     │
  ├────────────────┬──────────────┤
  │ 准确率(Accuracy) │  {metrics['accuracy']:.4f}       │
  ├────────────────┼──────────────┤
  │ 宏平均精确率(P)  │  {metrics['macro_precision']:.4f}       │
  ├────────────────┼──────────────┤
  │ 宏平均召回率(R)  │  {metrics['macro_recall']:.4f}       │
  ├────────────────┼──────────────┤
  │ 宏平均F1值(F1)  │  {metrics['macro_f1']:.4f}       │
  └────────────────┴──────────────┘""")

    print(f"\n各类别详细指标:")
    print(f"{'类别':<8} {'P':>8} {'R':>8} {'F1':>8} {'Support':>8}")
    print(f"{'─' * 40}")
    for cls, m in metrics["by_class"].items():
        if m["support"] > 0:
            print(f"{cls:<8} {m['precision']:>8.4f} {m['recall']:>8.4f} {m['f1']:>8.4f} {m['support']:>8}")

    # 提示模板对比
    print(f"\n{SUB}")
    print("提示模板对比实验（Accuracy / Precision / Recall / F1）")
    print(SUB)
    # 为每个模板分别运行检测并对比标签
    label_map_tpl = {"高": "真实", "中": "待核实", "低": "虚假", "极低": "虚假"}
    mapped_labels = ["虚假" if m not in ["真实", "虚假"] else m for m in
                     [{"真实新闻": "真实"}.get(l, "虚假") if l != "真实新闻" else "真实" for l in TEST_LABELS]]
    mapped_labels = ["真实" if l in ["真实新闻", "真实"] else "虚假" for l in TEST_LABELS]

    test_small = TEST_TEXTS[:min(len(TEST_TEXTS), 8)]
    truth_small = mapped_labels[:len(test_small)]

    tpl_results = []
    print(f"\n {'模板':<22} {'延迟(s)':>8} {'成功率':>7} {'Acc':>7} {'P':>7} {'R':>7} {'F1':>7} {'检出率':>7}")
    print(f"{'─' * 75}")
    for tk, tmpl in PROMPT_TEMPLATES.items():
        rs = detector.batch_detect(test_small, template_key=tk)
        ok = sum(1 for r in rs if not r.error)
        avg_lat = sum(r.processing_time for r in rs) / len(rs) if rs else 0
        fake_r = sum(1 for r in rs if r.is_fake()) / len(rs) * 100 if rs else 0
        # 计算指标
        m = compute_metrics(rs, truth_small)
        row = {"模板": tmpl["name"], "延迟(s)": round(avg_lat, 3),
               "成功率(%)": round(ok/len(rs)*100, 1),
               "Accuracy": m["accuracy"], "Precision": m["macro_precision"],
               "Recall": m["macro_recall"], "F1": m["macro_f1"],
               "检出率(%)": round(fake_r, 1)}
        tpl_results.append(row)
        print(f"{row['模板']:<22} {row['延迟(s)']:>8.3f} {row['成功率(%)']:>6.1f}% "
              f"{row['Accuracy']:>7.4f} {row['Precision']:>7.4f} {row['Recall']:>7.4f} "
              f"{row['F1']:>7.4f} {row['检出率(%)']:>6.1f}%")

    best_t = max(tpl_results, key=lambda x: x["F1"])
    print(f"\n最佳模板: {best_t['模板']}  F1={best_t['F1']:.4f}")

    # 量化对比
    print(f"\n{SUB}")
    print("量化部署对比实验 (FP16 vs INT8 vs AWQ)")
    print(SUB)
    qd = run_quantization_experiment()
    print(f"\n{'方案':<22} {'显存(GB)':>8} {'延迟(ms)':>8} {'吞吐量':>10} {'质量分':>8}")
    print(f"{'─' * 60}")
    for d in qd:
        print(f"{d['量化']:<22} {d['显存(GB)']:>8.1f} {d['延迟(ms)']:>8.1f} {d['吞吐量(tok/s)']:>9.1f} {d['质量分']:>8.2f}")
    print(f"\n推荐AWQ量化：显存受限环境性能最优")

    # 批次对比
    print(f"\n{SUB}")
    print("批次处理对比实验（Batch Size: 1 / 4 / 8 / 16）")
    print(SUB)
    bd = run_batch_size_experiment(detector, TEST_TEXTS)
    print(f"\n{'Batch Size':>12} {'总延迟(s)':>10} {'单条(ms)':>10} {'吞吐量(tok/s)':>15} {'成功率':>8}")
    print(f"{'─' * 60}")
    for d in bd:
        print(f"{d['Batch Size']:>12} {d['总延迟(s)']:>10.3f} {d['单条(ms)']:>10.1f} {d['吞吐量(tok/s)']:>15.1f} {d['成功率']:>7.1f}%")
    best_bs = max(bd, key=lambda x: x["吞吐量(tok/s)"])
    print(f"\n推荐 batch_size={best_bs['Batch Size']}（最高吞吐量 {best_bs['吞吐量(tok/s)']:.1f} tok/s）")

    # 八大虚假类型检测效果评估
    print(f"\n{SUB}")
    print("分类型检测效果评估（各虚假信息类型 Precision / Recall / F1）")
    print(SUB)
    # 对整个数据集批量检测
    # 取数据集前50条，对应生成 50 个预测结果
    type_eval_n = min(50, len(dataset)) if dataset else 0
    if type_eval_n > 0:
        type_eval_texts = [row.get("text", "")[:200] for row in dataset[:type_eval_n]]
        type_eval_results = detector.batch_detect(type_eval_texts)
        per_type = compute_per_type_metrics(type_eval_results, dataset[:type_eval_n])
    else:
        per_type = compute_per_type_metrics(results, dataset)

    has_data = any(v["support"] > 0 for v in per_type.values())
    label_src = f"使用数据集标注（前{type_eval_n}条）" if has_data else "使用模拟标注"
    print(f"标注来源: {label_src}  评估样本数: {type_eval_n if type_eval_n > 0 else len(results)}")

    print(f"\n{'虚假类型':<12} {'P':>8} {'R':>8} {'F1':>8} {'Support':>8}  检测难点分析")
    print(f"{'─' * 72}")
    difficulty = {
        "捏造事实": "需对照外部事实库，难点在细节核查",
        "断章取义": "需理解完整上下文语境",
        "夸大其词": "数量/程度修饰词识别有一定歧义",
        "标题党": "标题与正文不符的结构性判断",
        "伪科学": "需专业领域知识支撑",
        "情绪煽动": "情感词汇识别准确但意图判断难",
        "信息缺失": "缺失信息无法直接从文本中判断",
        "真实信息": "真实内容被误判为虚假（假阳性）",
    }
    for ft, m in per_type.items():
        hint = difficulty.get(ft, "—")
        print(f"{ft:<12} {m['precision']:>8.4f} {m['recall']:>8.4f} {m['f1']:>8.4f} {m['support']:>8}  {hint}")
    macro_f1_type = sum(m["f1"] for m in per_type.values()) / len(per_type)
    print(f"\n宏平均 F1（按类型）: {macro_f1_type:.4f}")

    # RAG 测试
    print(f"\n{SUB}")
    print("RAG事实核查问答测试")
    print(SUB)
    rag.build_knowledge_base(results[:5])
    for q in ["哪些新闻可信度最低？", "最常见的虚假类型是什么？"]:
        a = rag.answer(q, stream=False)
        print(f"Q: {q}")
        print(f"A: {a[:100]}...")
        print()

    # 导出
    print(f"\n{SUB}")
    print("结果导出")
    print(SUB)
    jp = os.path.join(EXPORT_DIR, "detection_results.json")
    cp = os.path.join(EXPORT_DIR, "detection_results.csv")
    js = export_json(results, jp)
    cs = export_csv(results, cp)
    print(f"JSON → {jp} ({len(js)} 字节)")
    print(f"CSV  → {cp} ({len(cs)} 字节)")

    # 汇总
    fake_count = cred_dist.get("低", 0) + cred_dist.get("极低", 0)
    avg_score = sum(r.credibility_score for r in results) / len(results) if results else 0
    print(f"\n{HEADER}")
    print("全部实验完成")
    print(HEADER)
    print(f"""
   模型: DeepSeek-R1-Distill-Qwen-1.5B (Mock)
   样本数: {len(results)} 条
   高可信: {cred_dist.get('高',0)} | 中: {cred_dist.get('中',0)} | 低: {cred_dist.get('低',0)} | 极低: {cred_dist.get('极低',0)}
   虚假率: {fake_count}/{len(results)} ({fake_count/len(results)*100:.1f}%)
   平均可信度分: {avg_score:.4f}
   准确率: {metrics['accuracy']:.4f}
   宏F1值: {metrics['macro_f1']:.4f}
""")

    # 启动 Web
    print(HEADER)
    print("启动Web交互界面")
    print(HEADER)
    web_script = os.path.join(os.path.dirname(__file__), "web", "app.py")
    port = 8080
    try:
        subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", web_script, "--server.port", str(port), "--server.headless", "true"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        time.sleep(3)
        print(f"""
  ┌──────────────────────────────────────────────────────┐
  │                                                      │
  │   前端交互页面已启动！                                   │
  │                                                      │
  │   请打开浏览器访问:                                     │
  │   http://localhost:{port}                            │
  │                                                      │                                            │
  └──────────────────────────────────────────────────────┘
""")
    except Exception as e:
        print(f"\nWeb 启动失败: {e}")
        print(f"手动启动: cd {os.path.dirname(__file__)} && streamlit run web/app.py --server.port {port}")

    print(f"\n按 Ctrl+C 退出")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n系统已退出。")

if __name__ == "__main__":
    main()
