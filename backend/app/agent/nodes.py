"""Agent 节点：意图识别、追问、检索、回答、急救、报告、模型工具循环。"""

import json
import re
from typing import Any

from app.agent.memory import build_memory, memory_note
from app.agent.state import AgentState
from app.data.content import REPLIES
from app.llm.openai_compatible import is_unsafe
from app.llm.vision import ReportImageError
from app.tools.mock_tools import interpret_report, search_health_kb, triage_assess

FOLLOW_UP_INTENTS = {"dizziness_intro", "dizziness_vertigo", "dizziness_unclear"}
DIRECT_REPLY_INTENTS = FOLLOW_UP_INTENTS | {"imaging", "sleep_meds"}

NEURO_KEYWORDS = ("手脚麻木", "说话不清", "口角歪", "视物重影", "走路不稳")
CHEST_KEYWORDS = (
    "冷汗",
    "放射",
    "左臂",
    "下颌",
    "呼吸困难",
    "晕厥",
    "压榨",
    "超过15",
    "持续",
)
FEVER_KEYWORDS = (
    "意识模糊",
    "抽搐",
    "脖子",
    "颈项",
    "出血点",
    "呼吸困难",
    "口唇发紫",
    "呕吐",
    "喝不进水",
)
ABDOMINAL_KEYWORDS = (
    "呕血",
    "黑便",
    "发硬",
    "晕厥",
    "怀孕",
    "停经",
    "血便",
    "出血",
)
HEADACHE_KEYWORDS = (
    "炸裂",
    "脖子",
    "颈项强直",
    "无力",
    "说话不清",
    "口角",
    "视物",
    "重影",
    "外伤",
    "呕吐",
)

RETRIEVAL_QUERIES = {
    "fallback": "",
    "dizziness_meniere": "梅尼埃病 耳鸣 听力下降 眩晕",
    "dizziness_bppv": "良性阵发性位置性眩晕 位置试验",
    "dizziness_lightheaded": "体位性低血压 站起 头晕 眼前发黑",
    "checks": "眩晕 位置试验 听力 前庭功能 检查",
    "observe": "眩晕 发作 记录 诱因 观察",
    "sleep": "失眠 睡眠卫生 非药物干预",
    "sleep_meds": "失眠 安眠药 医生评估",
    "anemia_diet": "贫血 补铁 铁蛋白 饮食",
    "recheck": "血常规 复查 白细胞 血红蛋白",
}

INTENT_DOC_IDS = {
    "dizziness_meniere": {"diz-meniere", "diz-stroke"},
    "dizziness_bppv": {"diz-bppv", "diz-stroke"},
    "dizziness_lightheaded": {"diz-orthostatic"},
    "checks": {"diz-bppv", "diz-meniere", "diz-stroke"},
    "observe": {"diz-bppv", "diz-meniere"},
    "sleep": {"sleep-hygiene"},
    "sleep_meds": {"sleep-hygiene"},
    "anemia_diet": {"anemia-diet", "report-cbc"},
    "recheck": {"report-cbc"},
}

RISK_CASES = {
    "dizziness_meniere": (
        "dizziness",
        {"nature": "vertigo", "associated": ["tinnitus"]},
    ),
    "dizziness_bppv": (
        "dizziness",
        {"nature": "vertigo", "associated": ["none"]},
    ),
    "dizziness_lightheaded": (
        "dizziness",
        {"nature": "lightheaded", "associated": ["none"]},
    ),
    "checks": ("dizziness", {"nature": "unclear", "associated": ["none"]}),
    "observe": ("dizziness", {"nature": "unclear", "associated": ["none"]}),
}


def _detect_emergency(
    text: str,
    profile: dict[str, Any] | None = None,
    memory: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]] | None:
    """从自然语言 + 会话档案 + 会话记忆里提取红旗组合，交给规则引擎分级。"""
    profile = profile or {}
    memory_symptoms = set((memory or {}).get("symptoms", []))

    # 记忆兜底：本会话早前提过神经症状，现在又提到头晕 → 按卒中红旗处理
    if "neuro" in memory_symptoms and any(
        keyword in text for keyword in ("头晕", "眩晕", "头昏")
    ):
        return "dizziness", {"nature": "vertigo", "associated": ["neuro"]}

    if any(keyword in text for keyword in NEURO_KEYWORDS):
        associated = ["neuro"]
        if "胸痛" in text or "心悸" in text:
            associated.append("chest")
        return "dizziness", {"nature": "vertigo", "associated": associated}

    if "胸" in text and any(keyword in text for keyword in CHEST_KEYWORDS):
        duration = (
            "gt15m"
            if any(keyword in text for keyword in ("超过15", "持续"))
            else "lt5m"
        )
        associated = []
        if "冷汗" in text:
            associated.append("sweat")
        if any(keyword in text for keyword in ("放射", "左臂", "下颌")):
            associated.append("radiate")
        if "呼吸困难" in text:
            associated.append("dyspnea")
        if "晕厥" in text:
            associated.append("syncope")
        quality = (
            "pressure"
            if any(keyword in text for keyword in ("压榨", "紧缩"))
            else ""
        )
        if duration == "gt15m" or associated or quality:
            answers: dict[str, Any] = {
                "duration": duration,
                "associated": associated or ["none"],
            }
            if quality:
                answers["quality"] = quality
            return "chest_pain", answers

    if ("发热" in text or "发烧" in text) and any(
        keyword in text for keyword in FEVER_KEYWORDS
    ):
        associated = []
        if any(keyword in text for keyword in ("意识模糊", "抽搐")):
            associated.append("consciousness")
        if any(keyword in text for keyword in ("脖子", "颈项")):
            associated.append("neck")
        if "出血点" in text:
            associated.append("purpura")
        if "呼吸困难" in text or "口唇发紫" in text:
            associated.append("breathing")
        if "呕吐" in text or "喝不进水" in text:
            associated.append("vomiting")
        if profile.get("pregnant"):
            age = "pregnant"
        elif isinstance(profile.get("age"), int) and profile["age"] < 14:
            age = "child"
        elif any(keyword in text for keyword in ("孩子", "儿童", "宝宝")):
            age = "child"
        else:
            age = "adult"
        return "fever", {
            "age": age,
            "temp": "38to39",
            "duration": "1to3d",
            "associated": associated or ["none"],
        }

    if ("腹" in text or "肚子" in text) and "痛" in text and any(
        keyword in text for keyword in ABDOMINAL_KEYWORDS
    ):
        associated = []
        if "呕血" in text or "黑便" in text:
            associated.append("hematemesis")
        if "发硬" in text:
            associated.append("rigid")
        if "晕厥" in text:
            associated.append("syncope")
        if any(keyword in text for keyword in ("怀孕", "停经")):
            associated.append("pregnant_bleed")
        if "血便" in text:
            associated.append("bloodstool")
        if profile.get("pregnant") and any(
            keyword in text for keyword in ("下腹", "出血")
        ):
            associated.append("pregnant_bleed")
        return "abdominal_pain", {
            "severity": "severe" if "剧烈" in text else "moderate",
            "associated": associated or ["none"],
        }

    if "头痛" in text and any(
        keyword in text for keyword in HEADACHE_KEYWORDS
    ):
        associated = []
        if any(keyword in text for keyword in ("发热", "脖子", "颈项强直")):
            associated.append("fever_neck")
        if any(keyword in text for keyword in ("无力", "说话不清", "口角")):
            associated.append("neuro")
        if any(keyword in text for keyword in ("视物", "重影")):
            associated.append("vision")
        if "外伤" in text:
            associated.append("trauma")
        if "呕吐" in text:
            associated.append("vomit")
        return "headache", {
            "onset": "thunderclap" if "炸裂" in text else "gradual",
            "associated": associated or ["none"],
        }

    # 独立出血（不伴腹痛也按消化道出血评估）
    if "呕血" in text or "黑便" in text:
        return "abdominal_pain", {
            "severity": "moderate",
            "associated": ["hematemesis"],
        }
    if "便血" in text:
        return "abdominal_pain", {
            "severity": "moderate",
            "associated": ["bloodstool"],
        }

    return _detect_value_or_state_redflag(text)


_VALUE_PATTERNS = {
    "glucose_high": re.compile(r"血糖[^0-9]{0,3}(\d+(?:\.\d+)?)"),
    "glucose_low": re.compile(r"血糖[^0-9]{0,3}(\d+(?:\.\d+)?)"),
    "bp_high": re.compile(r"血压[^0-9]{0,3}(\d{2,3})(?:\s*[/／]\s*(\d{2,3}))?"),
    "spo2_low": re.compile(r"血氧[^0-9]{0,3}(\d{2,3})"),
}

_STATE_KEYWORDS = {
    "consciousness": ("意识不清", "叫不醒", "昏迷", "意识模糊", "神志不清"),
    "dysphagia": ("吞咽困难", "咽不下东西"),
}


def _detect_value_or_state_redflag(
    text: str,
) -> tuple[str, dict[str, Any]] | None:
    """数值型红旗（血糖/血压/血氧）与独立急症状态（意识/吞咽）。

    数值按国内常用单位理解：血糖 mmol/L、血压 mmHg、血氧饱和度 %。
    """
    glucose = _VALUE_PATTERNS["glucose_high"].search(text)
    if glucose:
        value = float(glucose.group(1))
        if value >= 16.7:
            return "vitals", {"vital": ["glucose_high"]}
        if 0 < value <= 3.9:
            return "vitals", {"vital": ["glucose_low"]}

    blood_pressure = _VALUE_PATTERNS["bp_high"].search(text)
    if blood_pressure:
        systolic = float(blood_pressure.group(1))
        diastolic = blood_pressure.group(2)
        if systolic >= 180 or (diastolic and float(diastolic) >= 120):
            return "vitals", {"vital": ["bp_high"]}

    spo2 = _VALUE_PATTERNS["spo2_low"].search(text)
    if spo2:
        value = float(spo2.group(1))
        if 50 <= value <= 93:
            return "vitals", {"vital": ["spo2_low"]}

    for state, keywords in _STATE_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return "general_redflag", {"state": [state]}

    return None


def _rule_intent(text: str) -> str:
    """确定性规则：追问标签、固定演示入口优先。"""
    report_triggers = ("报告", "化验", "单子", "样例")
    if "血常规" in text and any(k in text for k in report_triggers):
        return "report_result"
    if "肝功能" in text and any(k in text for k in report_triggers):
        return "report_result_2"
    if "甲状腺" in text and any(k in text for k in report_triggers):
        return "report_result_3"
    if "耳鸣" in text or "听力下降" in text:
        return "dizziness_meniere"
    if "天旋地转" in text:
        return "dizziness_vertigo"
    if "昏沉" in text or "眼前发黑" in text:
        return "dizziness_lightheaded"
    if "说不清" in text:
        return "dizziness_unclear"
    if "都没有" in text:
        return "dizziness_bppv"
    if any(
        keyword in text
        for keyword in ("CT", "ct", "核磁", "MRI", "磁共振", "片子", "影像")
    ):
        return "imaging"
    if "使用样例报告" in text:
        return "report_result"
    if "报告" in text or "体检" in text:
        return "report"
    if "安眠药" in text or "吃药" in text:
        return "sleep_meds"
    if "失眠" in text or "睡不好" in text or "睡眠" in text:
        return "sleep"
    if "检查" in text:
        return "checks"
    if "观察" in text:
        return "observe"
    if "贫血" in text or "补铁" in text:
        return "anemia_diet"
    if "复查" in text:
        return "recheck"
    if "回到头晕" in text:
        return "dizziness_intro"
    if "头晕" in text or "眩晕" in text:
        return "dizziness_intro"
    return "fallback"


def classify(state: AgentState) -> dict[str, Any]:
    """意图识别：规则兜底确定性流程，开放表达交给 LLM 路由。"""
    text = state["message"]
    memory = build_memory(state.get("history", []), text)
    emergency = _detect_emergency(text, state.get("profile"), memory)

    if emergency:
        symptom, answers = emergency
        return {
            "intent": "emergency",
            "emergency_symptom": symptom,
            "emergency_answers": answers,
            "memory": memory,
            "tool_calls": [
                {"name": "classify", "arguments": {"intent": "emergency"}}
            ],
        }

    if state.get("report_image"):
        return {
            "intent": "report_upload",
            "memory": memory,
            "tool_calls": [
                {"name": "classify", "arguments": {"intent": "report_upload"}}
            ],
        }

    intent = _rule_intent(text)
    llm = state.get("llm")
    if intent == "fallback" and llm is not None:
        routed = llm.route_intent(text, state.get("history", []))
        if routed:
            intent = routed

    return {
        "intent": intent,
        "memory": memory,
        "tool_calls": [{"name": "classify", "arguments": {"intent": intent}}],
    }


REPORT_SAMPLE_INTENTS = {"report_result", "report_result_2", "report_result_3"}


def route_after_classify(state: AgentState) -> str:
    """条件边：急救/固定回复/样例报告走确定性流程，其余交给模型工具循环。

    “report”是开放报告请求：有工具模型时让模型自选 interpret_report；
    无模型时走固定介绍。样例选择（血常规样例等）永远确定性执行。
    """
    intent = state["intent"]
    if intent == "emergency":
        return "emergency"
    if intent == "report_upload":
        return "report_upload"
    if intent in DIRECT_REPLY_INTENTS:
        return "follow_up"
    if intent in REPORT_SAMPLE_INTENTS:
        return "report"
    if intent == "report":
        llm = state.get("llm")
        if llm is not None and llm.supports_tools:
            return "agent"
        return "report"
    llm = state.get("llm")
    if llm is not None and llm.supports_tools:
        return "agent"
    return "retrieve"


def follow_up(state: AgentState) -> dict[str, Any]:
    reply = REPLIES.get(state["intent"], REPLIES["fallback"])
    return {"answer": reply["text"], "chips": reply.get("chips", [])}


def _filtered_evidence(
    result: dict[str, Any], allowed: set[str]
) -> tuple[list[str], str]:
    """只保留与当前意图对应的文档，并重建与引用编号一致的上下文。"""
    hits = [
        hit
        for hit in result.get("hits", [])
        if hit.get("doc_id") in allowed
    ]

    unique_hits = []
    seen: set[tuple[str, str]] = set()
    for hit in hits:
        key = (hit.get("source", ""), hit.get("section", ""))
        if key in seen:
            continue
        seen.add(key)
        unique_hits.append(hit)

    citations = [
        f"{hit['source']} · {hit['section']}"
        for hit in unique_hits
        if hit.get("source") and hit.get("section")
    ]
    context = "\n\n".join(
        f"[{index}] {hit.get('doc_name', '')}（{hit.get('source', '')}）\n"
        f"{hit.get('text', '')}"
        for index, hit in enumerate(unique_hits, 1)
    )
    return citations, context


def _risk_for_intent(state: AgentState) -> dict[str, Any] | None:
    """症状类回答附带结构化风险结论；无规则支撑或无工具时返回 None。"""
    case = RISK_CASES.get(state["intent"])
    tool = state.get("tools", {}).get("triage_assess")
    if not case or not tool:
        return None

    symptom, answers = case
    result = tool(symptom, answers)
    return {
        "level": result.get("level", "L3"),
        "department": result.get("department", ""),
        "timeframe": result.get("timeframe", ""),
        "note": "；".join(result.get("reasons", [])),
        "evidence": list(result.get("evidence", [])),
    }


def _profile_note(profile: dict[str, Any]) -> str:
    """把会话档案注入 LLM 提示词，不改变默认文案。"""
    if not profile:
        return ""

    parts = ["家人" if profile.get("relation") == "family" else "本人"]
    if profile.get("age") is not None:
        parts.append(f"年龄 {profile['age']} 岁")
    sex_label = {"male": "男", "female": "女", "other": "其他"}.get(
        str(profile.get("sex") or ""), ""
    )
    if sex_label:
        parts.append(f"性别 {sex_label}")
    if profile.get("pregnant"):
        parts.append("孕产期")

    if len(parts) == 1:
        return ""
    return "\n\n【本次会话档案】就诊人：" + "；".join(parts)


def retrieve(state: AgentState) -> dict[str, Any]:
    intent = state["intent"]
    query = RETRIEVAL_QUERIES.get(intent, state["message"])

    if not query:
        return {"citations": [], "context": ""}

    tool_name = "deep_search" if state.get("deep_search") else "search_health_kb"
    tool = state.get("tools", {}).get(tool_name)

    if tool:
        result = tool(query)
        allowed = INTENT_DOC_IDS.get(intent, set())
        if allowed and result.get("hits"):
            citations, context = _filtered_evidence(result, allowed)
        else:
            citations = result.get("citations", [])
            context = result.get("context", "")
    else:
        citations = search_health_kb(intent)
        context = ""

    tool_calls = [
        *state.get("tool_calls", []),
        {"name": tool_name, "arguments": {"query": query}},
    ]
    return {
        "citations": citations,
        "context": context,
        "tool_calls": tool_calls,
    }


def answer(state: AgentState) -> dict[str, Any]:
    """无 Key 时的模板兜底路径；有 Key 的开放问答由 agent 节点处理。"""
    reply = REPLIES.get(state["intent"], REPLIES["fallback"])
    risk = _risk_for_intent(state)

    result: dict[str, Any] = {
        "chips": reply.get("chips", []),
        "citations": state.get("citations", []),
    }
    if risk:
        result["risk"] = risk
    result["answer"] = reply["text"]
    return result


MAX_AGENT_TURNS = 4

AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_health_kb",
            "description": "按症状或问题检索公开健康指南条目，返回带来源的证据；日常健康问答优先使用",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "检索关键词，例如：眩晕 耳鸣",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "deep_search",
            "description": "多角度深度检索指南证据；第一轮结果不够时，可换关键词再次调用",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "检索关键词"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "interpret_report",
            "description": "解读体检报告样例并返回结构化指标；sample-1=血常规, sample-2=肝功能血脂, sample-3=甲状腺",
            "parameters": {
                "type": "object",
                "properties": {
                    "report_id": {
                        "type": "string",
                        "enum": ["sample-1", "sample-2", "sample-3"],
                    },
                },
                "required": ["report_id"],
            },
        },
    },
]

AGENT_PROMPT = """你是「智诊」健康助手，通过调用工具查资料后回答健康问题。

工具使用规则：
1. 医学内容必须先查资料再回答，不要凭空作答；普通问答用 search_health_kb，需要更全面证据用 deep_search；
2. 第一轮结果不足以回答时，可以换关键词再查（总轮次系统会自动限制）；
3. 演示环境没有真实上传文件，报告解读只用内置样例，必须区分两种情况：
   a) 用户没说要看哪一类报告（如只说“帮我看看体检报告”）→ 不要调用工具，
      直接简短说明“演示版暂不支持上传，回复「血常规样例 / 肝功能样例 / 甲状腺样例」可体验解读”；
   b) 用户明确说了种类（血常规/肝功能/甲状腺）或带了“样例”二字 → 调用 interpret_report
      （血常规→sample-1，肝功能/血脂→sample-2，甲状腺→sample-3），且回答第一句必须是
      “这是演示样例数据，不是你的真实报告”，绝不能把样例说成用户本人的报告；
4. 问题太模糊时不需要工具，直接用一句简短追问澄清。

回答规则（拿到资料后）：
1. 严格遵守三段输出格式，每段以【】标记开头、独占一行：
【结论】一两句话给出方向
【需要注意】需要警惕的情况，短句分号分隔
【就医建议】科室 / 检查 / 时限
2. 不诊断病名、不开药、不给剂量、不解读 CT/MRI 影像；
3. 资料不足就明确说“资料不足，建议就医”，不要编造；
4. 不要输出 [1][2] 这类资料编号；
5. 结合会话记忆里用户已提到的症状，不要重复追问已知信息；
6. 纯寒暄或澄清追问可以不用三段格式，直接简短回答。

输出示例（格式照抄）：
【结论】头晕伴耳鸣更偏向耳部及内耳方向的问题，需要排查相关疾病。
【需要注意】如出现手脚麻木、说话不清、视物重影，需警惕中枢性病因，应立即急诊。
【就医建议】建议尽快到耳鼻喉科就诊，做听力测试与前庭功能检查。"""


def _execute_agent_tool(
    name: str,
    arguments: dict[str, Any],
    tools: dict[str, Any],
    fallback_query: str,
) -> dict[str, Any]:
    fn = tools.get(name)
    if fn is None:
        return {"error": f"工具 {name} 不可用"}
    try:
        if name == "interpret_report":
            return dict(fn(str(arguments.get("report_id", "sample-1"))))
        query = str(arguments.get("query") or fallback_query)
        return dict(fn(query))
    except Exception as exc:  # noqa: BLE001 - 单个工具失败不中断循环
        return {"error": f"工具执行失败：{exc}"}


_TOOL_CALL_NAME = ("search_health_kb", "deep_search", "interpret_report")
_TOOL_CALL_TEXT = re.compile(
    r"^(search_health_kb|deep_search|interpret_report)\s*[\(（:：]?\s*(.+?)\s*[\)）]?\s*$",
    re.DOTALL,
)
_KWARG_PAIR = re.compile(r'([a-zA-Z_]\w*)\s*=\s*"([^"]*)"')


def _coerce_text_tool_call(content: str) -> tuple[str, dict[str, Any]] | None:
    """模型把工具调用写成纯文本时，尝试还原成真正的调用。

    兼容两种写法：`name {"query": "..."}` 与 `name(query="...")`。
    """
    match = _TOOL_CALL_TEXT.match(content)
    if not match:
        return None
    name, raw = match.group(1), match.group(2).strip()

    if raw.startswith("{"):
        try:
            arguments = json.loads(raw)
        except Exception:  # noqa: BLE001 - 解析失败按普通文本
            return None
        return (name, arguments) if isinstance(arguments, dict) else None

    if raw.startswith("(") and raw.endswith(")"):
        raw = raw[1:-1].strip()
    if not raw:
        return name, {}
    pairs = {key: value for key, value in _KWARG_PAIR.findall(raw)}
    return (name, pairs) if pairs else None


def agent(state: AgentState) -> dict[str, Any]:
    """模型自主工具循环：自选工具、自定检索轮次；失败或越界回退模板。

    安全边界：进入本节点前，红旗急救与固定拒答已由规则分流，模型不参与。
    """
    llm = state.get("llm")
    tools = state.get("tools", {})
    intent = state["intent"]
    reply = REPLIES.get(intent, REPLIES["fallback"])

    system_prompt = (
        AGENT_PROMPT
        + _profile_note(state.get("profile") or {})
        + memory_note(state.get("memory"))
    )
    if state.get("deep_search"):
        system_prompt += (
            "\n【深度搜索已开启】用户要求更全面的证据："
            "优先使用 deep_search，并可换关键词多查几轮。"
        )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        *state.get("history", [])[-6:],
        {"role": "user", "content": state["message"]},
    ]

    citations: list[str] = []
    contexts: list[str] = []
    report_payload: dict[str, Any] | None = None
    trace = list(state.get("tool_calls", []))
    emit = state.get("emit_event")
    streamed_tokens = 0

    # 症状类问题先做一次确定性检索：即使模型不主动调工具，回答也有资料兜底
    pre_query = RETRIEVAL_QUERIES.get(intent)
    search_tool = tools.get("search_health_kb")
    if pre_query and search_tool:
        pre_result = search_tool(pre_query)
        trace.append(
            {"name": "search_health_kb", "arguments": {"query": pre_query}}
        )
        citations.extend(pre_result.get("citations", []))
        if pre_result.get("context"):
            contexts.append(pre_result["context"])
            messages.append(
                {
                    "role": "system",
                    "content": "已检索到以下资料，回答必须基于它：\n"
                    + pre_result["context"][:3000],
                }
            )

    def _on_delta(token: str) -> None:
        nonlocal streamed_tokens
        streamed_tokens += 1
        if emit:
            emit({"type": "delta", "content": token})

    for _ in range(MAX_AGENT_TURNS):
        turn = llm.chat_with_tools(
            messages,
            AGENT_TOOLS,
            on_delta=_on_delta if emit else None,
        )
        calls = list(turn.tool_calls)
        content = (turn.content or "").strip()

        if not calls and content:
            coerced = _coerce_text_tool_call(content)
            if coerced is not None:
                calls = [
                    {
                        "id": "coerced",
                        "name": coerced[0],
                        "arguments": coerced[1],
                    }
                ]
                content = ""
            elif content.startswith(_TOOL_CALL_NAME):
                # 形似工具调用但解析不了：绝不原样展示，走模板兜底
                content = ""

        if calls:
            messages.append(
                turn.assistant_message
                or {"role": "assistant", "content": content or None}
            )
            for call in calls:
                name = str(call.get("name", ""))
                arguments = call.get("arguments") or {}
                trace.append({"name": name, "arguments": arguments})
                result = _execute_agent_tool(
                    name, arguments, tools, state["message"]
                )
                if name == "interpret_report" and "error" not in result:
                    report_payload = result
                for citation in result.get("citations", []):
                    if citation not in citations:
                        citations.append(citation)
                if result.get("context"):
                    contexts.append(result["context"])
                model_payload = (
                    {"error": result["error"]}
                    if "error" in result
                    else {
                        key: value
                        for key, value in result.items()
                        if key in {"citations", "context", "title", "rows", "note"}
                    }
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.get("id", ""),
                        "content": json.dumps(model_payload, ensure_ascii=False)[:4000],
                    }
                )
            continue

        if content and not is_unsafe(content):
            return {
                "intent": intent,
                "answer": content,
                "chips": reply.get("chips", []),
                "citations": citations,
                "context": contexts[-1] if contexts else "",
                "report": report_payload,
                "tool_calls": trace,
                "streamed": streamed_tokens > 0,
            }
        if content and is_unsafe(content) and streamed_tokens > 0:
            # 已流式输出的内容越界：通知前端替换为安全模板
            return {
                "intent": intent,
                "answer": reply["text"],
                "chips": reply.get("chips", []),
                "citations": citations,
                "context": contexts[-1] if contexts else "",
                "report": report_payload,
                "tool_calls": trace,
                "streamed": True,
                "replace_stream": True,
            }
        break

    return {
        "intent": intent,
        "answer": reply["text"],
        "chips": reply.get("chips", []),
        "citations": citations,
        "context": contexts[-1] if contexts else "",
        "report": report_payload,
        "tool_calls": trace,
        "streamed": streamed_tokens > 0,
    }


def emergency(state: AgentState) -> dict[str, Any]:
    tool = state.get("tools", {}).get("triage_assess")
    symptom = state.get("emergency_symptom", "dizziness")
    answers = state.get("emergency_answers") or {
        "nature": "vertigo",
        "associated": ["neuro"],
    }
    triage = (
        tool(symptom, answers)
        if tool
        else triage_assess(state["message"])
    )

    level = triage.get("level", "L1")
    reasons = triage.get("reasons") or [
        triage.get("desc", "存在需要紧急处理的警示信号。")
    ]
    evidence = triage.get("evidence") or search_health_kb("emergency")

    tool_calls = [
        *state.get("tool_calls", []),
        {
            "name": "triage_assess",
            "arguments": {"symptom": symptom, "answers": answers},
        },
    ]
    return {
        "answer": REPLIES["emergency"]["text"],
        "chips": [],
        "emergency": {
            "level": level,
            "title": "请立即拨打 120" if level == "L1" else "请尽快就医",
            "desc": "；".join(reasons),
            "department": triage.get("department", "急诊科"),
            "timeframe": triage.get("timeframe", "立即就医"),
            "cta": "拨打 120" if level == "L1" else "查看就医建议",
        },
        "citations": evidence,
        "tool_calls": tool_calls,
    }


def report_upload(state: AgentState) -> dict[str, Any]:
    """真实上传链路：视觉提取 → 指南检索 → 分块解读。

    图片只在内存中传递给识别服务，不落盘、不存储、不回显。
    """
    vision = state.get("vision")
    image = state.get("report_image") or {}
    trace = list(state.get("tool_calls", []))

    if vision is None:
        reply = REPLIES["report"]
        return {
            "intent": "report_upload",
            "answer": reply["text"],
            "chips": reply.get("chips", []),
            "citations": [],
            "report": None,
            "tool_calls": trace,
        }

    try:
        report_data = vision.extract(
            str(image.get("data", "")), str(image.get("mime", "image/jpeg"))
        )
    except ReportImageError as exc:
        return {
            "intent": "report_upload",
            "answer": f"报告识别失败：{exc}",
            "chips": [],
            "citations": [],
            "report": None,
            "tool_calls": trace,
        }

    trace.append(
        {"name": "extract_report", "arguments": {"title": report_data["title"]}}
    )

    abnormal = [
        row["name"] for row in report_data["rows"] if row["flag"] != "normal"
    ]
    query = " ".join(abnormal[:3]) or report_data["title"]
    search_tool = state.get("tools", {}).get("search_health_kb")
    citations: list[str] = []
    context = ""
    if search_tool:
        result = search_tool(query)
        citations = result.get("citations", [])
        context = result.get("context", "")
        trace.append({"name": "search_health_kb", "arguments": {"query": query}})

    answer = None
    llm = state.get("llm")
    if llm is not None:
        flag_label = {"high": "偏高", "low": "偏低", "normal": "正常"}
        rows_text = "；\n".join(
            f"{row['name']} {row['value']}{row['unit']}"
            f"（参考 {row['range'] or '无'}，{flag_label[row['flag']]}）"
            for row in report_data["rows"]
        )
        user_content = (
            "用户上传了一张体检报告图片，识别结果如下。\n"
            f"【报告识别结果】{report_data['title']}\n{rows_text}\n\n"
            f"【参考资料】\n{context}\n\n"
            "请按【结论】【需要注意】【就医建议】三段格式解读。"
            "第一段开头先说明：这是图片识别结果，仅供参考，请以医生解读为准。"
            "不要把识别值说成问诊获得的信息。"
        )
        generated = llm.generate_answer(
            user_content,
            state.get("history", []),
            context,
            citations,
        )
        if generated:
            answer = generated

    if answer is None:
        answer = (
            f"已识别 {report_data['title']}，共 {len(report_data['rows'])} 项指标"
            "（详见下方报告卡）。识别结果仅供参考，请以医生解读为准。"
        )

    return {
        "intent": "report_upload",
        "answer": answer,
        "chips": REPLIES["report_upload"].get("chips", []),
        "citations": citations,
        "report": report_data,
        "tool_calls": trace,
    }


REPORT_IDS = {
    "report_result": "sample-1",
    "report_result_2": "sample-2",
    "report_result_3": "sample-3",
}

REPORT_QUERIES = {
    "report_result": "血常规 血红蛋白 白细胞",
    "report_result_2": "肝功能 转氨酶 血脂",
    "report_result_3": "甲状腺 TSH 抗体",
}

REPORT_DOC_IDS = {
    "report_result": {"report-cbc"},
    "report_result_2": {"report-lft"},
    "report_result_3": {"report-thyroid"},
}


def report(state: AgentState) -> dict[str, Any]:
    intent = state["intent"]
    reply = REPLIES.get(intent, REPLIES["report"])
    report_tool = state.get("tools", {}).get("interpret_report")
    search_tool = state.get("tools", {}).get("search_health_kb")

    report_id = REPORT_IDS.get(intent)
    payload = None
    if report_id:
        payload = (
            report_tool(report_id)
            if report_tool
            else interpret_report(report_id)
        )

    query = REPORT_QUERIES.get(intent, "体检报告 解读")
    citations = []
    if intent != "report":
        if search_tool:
            result = search_tool(query)
            allowed = REPORT_DOC_IDS.get(intent, set())
            citations = list(
                dict.fromkeys(
                    f"{hit['source']} · {hit['section']}"
                    for hit in result.get("hits", [])
                    if hit.get("doc_id") in allowed
                    and hit.get("source")
                    and hit.get("section")
                )
            )
            if not citations:
                citations = result.get("citations", [])
        else:
            citations = search_health_kb(intent)

    tool_calls = list(state.get("tool_calls", []))
    if report_id:
        tool_calls.append(
            {"name": "interpret_report", "arguments": {"report_id": report_id}}
        )

    return {
        "answer": reply["text"],
        "chips": reply.get("chips", []),
        "report": payload,
        "citations": citations,
        "tool_calls": tool_calls,
    }
