from __future__ import annotations

from importlib import import_module
from typing import Any, Mapping, Sequence

from agent.memory import MemoryStore, default_memory_store
from agent.model import LLMClient, ModelClientError, ModelResponse, default_model_client
from algorithms.deep_models.cnn import analyze_cnn
from algorithms.deep_models.transformer import analyze_fusion
from algorithms.signal_processing.ecg import analyze_ecg
from algorithms.signal_processing.hrv import analyze_hrv
from algorithms.signal_processing.pcg import analyze_pcg


DEFAULT_SYSTEM_PROMPT = (
    "你是一个心血管健康状态评估与主动干预智能助手。"
    "请结合用户描述、历史对话和算法分析结果，给出清晰、谨慎、易理解的回复。"
    "你可以解释 ECG、PCG、HRV 和多模态占位分析结果，但必须明确这些结果当前仅用于系统联调与辅助说明。"
    "当涉及健康风险时，请提醒用户该系统不能替代专业医生诊断。"
)

ALGORITHM_KEYWORDS = {
    "ecg": ("ecg", "心电", "心率", "心律", "波形"),
    "pcg": ("pcg", "心音", "杂音"),
    "hrv": ("hrv", "心率变异", "压力", "恢复"),
    "cnn": ("cnn", "应激", "stress", "风险"),
    "fusion": ("融合", "多模态", "综合", "transformer"),
}

def get_agent_response(
    user_message: str,
    session_id: str = "default",
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    *,
    model_client: LLMClient | None = None,
    memory_store: MemoryStore | None = None,
) -> dict[str, Any]:
    """
    后端的调度中心：处理算法逻辑并调用 LLM。
    """
    client = model_client or default_model_client
    store = memory_store or default_memory_store

    # 1. 获取并保存用户消息
    conversation = store.get_session(session_id.strip() or "default")
    conversation.add_message(role="user", content=user_message)

    # 2. 算法占位逻辑：根据关键词模拟算法分析
    algorithm_results = []
    lower_msg = user_message.lower()
    for algo_id, keywords in ALGORITHM_KEYWORDS.items():
        if any(kw in lower_msg for kw in keywords):
            # 模拟算法调用
            result = _safe_algorithm_call(lambda: {"module": algo_id, "status": "success", "summary": f"检测到{algo_id}相关特征"})
            algorithm_results.append(result)

    # 3. 构造增强提示词
    model_input = user_message
    if algorithm_results:
        algo_summary = "\n".join([f"- {res['module']}: {res['summary']}" for res in algorithm_results])
        model_input += f"\n\n[系统算法分析结果]:\n{algo_summary}"

    # 4. 调用大模型 API
    try:
        history = conversation.get_messages(include_system=False)
        response = client.chat(
            user_message=model_input,
            history=history,
            system_prompt=system_prompt,
        )
        reply_text = response.text
    except ModelClientError as exc:
        reply_text = f"抱歉，处理您的请求时出错：{exc}"

    # 5. 保存助手回复并返回
    conversation.add_message(role="assistant", content=reply_text)
    
    return {
        "reply": reply_text,
        "algorithms": algorithm_results,
        "session_id": session_id,
    }

def get_session_history(
    session_id: str = "default",
    *,
    include_system: bool = True,
    memory_store: MemoryStore | None = None,
) -> list[dict[str, str]]:
    """获取指定会话的历史记录。"""
    store = memory_store or default_memory_store
    conversation = store.get_session(session_id.strip() or "default")
    return conversation.get_messages(include_system=include_system)

def clear_session_history(
    session_id: str = "default",
    *,
    keep_system_message: bool = True,
    memory_store: MemoryStore | None = None,
) -> None:
    """清空会话。"""
    store = memory_store or default_memory_store
    store.clear_session(
        session_id.strip() or "default",
        keep_system_message=keep_system_message,
    )

def _safe_algorithm_call(function: Any, **kwargs: Any) -> dict[str, object]:
    """安全地执行算法占位函数。"""
    try:
        result = function(**kwargs)
    except Exception as exc:
        module_name = getattr(function, "__name__", "algorithm")
        return {
            "module": module_name,
            "status": "error",
            "summary": f"算法调用失败: {exc}",
            "risk_level": "unknown",
            "meta": {"placeholder_only": True},
        }
    return dict(result)