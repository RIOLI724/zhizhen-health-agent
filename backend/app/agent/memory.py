"""会话记忆：从对话里提取已提及的症状，供分诊、路由和生成复用。

记忆只在本会话内有效，不落库、不发给任何第三方；提取是纯关键词规则，
不依赖模型，保证无 Key 时记忆依然工作。
"""

from __future__ import annotations

from typing import Any

SYMPTOM_KEYWORDS: dict[str, tuple[str, ...]] = {
    "vertigo": ("天旋地转",),
    "lightheaded": ("昏沉", "眼前发黑"),
    "tinnitus": ("耳鸣", "听力下降"),
    "neuro": ("手脚麻木", "说话不清", "口角歪", "视物重影"),
    "chest_pain": ("胸痛", "胸闷", "胸口"),
    "fever": ("发烧", "发热"),
    "abdominal_pain": ("肚子痛", "腹痛", "肚子疼"),
    "headache": ("头痛", "头疼"),
    "sleep": ("失眠", "睡不好", "睡眠"),
    "vomiting": ("恶心", "呕吐", "吐了"),
    "diarrhea": ("腹泻", "拉肚子", "拉稀"),
    "palpitation": ("心悸", "心慌"),
    "dysphagia": ("吞咽困难", "咽不下东西"),
    "consciousness": ("意识不清", "叫不醒", "昏迷", "意识模糊"),
    "bleeding": ("呕血", "黑便", "便血"),
}

SYMPTOM_LABELS: dict[str, str] = {
    "vertigo": "天旋地转",
    "lightheaded": "昏沉/眼前发黑",
    "tinnitus": "耳鸣/听力下降",
    "neuro": "手脚麻木/说话不清",
    "chest_pain": "胸痛",
    "fever": "发热",
    "abdominal_pain": "腹痛",
    "headache": "头痛",
    "sleep": "睡眠问题",
    "vomiting": "恶心呕吐",
    "diarrhea": "腹泻",
    "palpitation": "心悸",
    "dysphagia": "吞咽困难",
    "consciousness": "意识障碍",
    "bleeding": "呕血/黑便/便血",
}


def build_memory(
    history: list[dict[str, str]], current: str
) -> dict[str, Any]:
    """合并历史与当前消息，返回去重后的症状记忆。"""
    symptoms: list[str] = []
    for message in [*history, {"role": "user", "content": current}]:
        if message.get("role") != "user":
            continue
        text = message.get("content", "")
        for symptom, keywords in SYMPTOM_KEYWORDS.items():
            if symptom in symptoms:
                continue
            if any(keyword in text for keyword in keywords):
                symptoms.append(symptom)
    return {"symptoms": symptoms}


def memory_note(memory: dict[str, Any] | None) -> str:
    """生成给 LLM 的记忆提示；无记忆返回空串。"""
    symptoms = (memory or {}).get("symptoms") or []
    labels = [SYMPTOM_LABELS[s] for s in symptoms if s in SYMPTOM_LABELS]
    if not labels:
        return ""
    return "【会话记忆】用户本次会话已提到：" + "、".join(labels)
