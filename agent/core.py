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


def resolve_system_prompt(explicit_prompt: str | None = None) -> str:
    """Return an explicit prompt, a prompt from agent.prompts, or a safe fallback."""
    if explicit_prompt and explicit_prompt.strip():
        return explicit_prompt.strip()

    try:
        prompts_module = import_module("agent.prompts")
    except Exception:
        return DEFAULT_SYSTEM_PROMPT

    for attr_name in (
        "SYSTEM_PROMPT",
        "DEFAULT_SYSTEM_PROMPT",
        "CARDIOBOT_SYSTEM_PROMPT",
    ):
        value = getattr(prompts_module, attr_name, None)
        if isinstance(value, str) and value.strip():
            return value.strip()

    for attr_name in ("get_system_prompt", "build_system_prompt"):
        value = getattr(prompts_module, attr_name, None)
        if callable(value):
            try:
                resolved = value()
            except Exception:
                continue
            if isinstance(resolved, str) and resolved.strip():
                return resolved.strip()

    return DEFAULT_SYSTEM_PROMPT


def should_run_algorithms(
    user_message: str,
    *,
    signal_payload: Mapping[str, Any] | None = None,
    requested_modules: Sequence[str] | None = None,
    run_algorithms: bool | None = None,
) -> bool:
    """Decide whether placeholder algorithms should be called for this turn."""
    if run_algorithms is not None:
        return run_algorithms

    if requested_modules:
        return True

    if signal_payload:
        return True

    normalized = user_message.lower()
    return any(keyword in normalized for values in ALGORITHM_KEYWORDS.values() for keyword in values)


def select_algorithm_modules(
    user_message: str,
    *,
    signal_payload: Mapping[str, Any] | None = None,
    requested_modules: Sequence[str] | None = None,
) -> list[str]:
    """Resolve which placeholder modules should be called for the current turn."""
    if requested_modules:
        modules = [item.strip().lower() for item in requested_modules if item.strip()]
        return [item for item in modules if item in ALGORITHM_KEYWORDS]

    normalized = user_message.lower()
    selected = [
        module_name
        for module_name, keywords in ALGORITHM_KEYWORDS.items()
        if any(keyword in normalized for keyword in keywords)
    ]

    if signal_payload:
        payload_to_module = {
            "ecg_signal": "ecg",
            "pcg_audio": "pcg",
            "rr_intervals": "hrv",
            "cnn_features": "cnn",
            "fusion_context": "fusion",
            "ecg_features": "fusion",
            "hrv_features": "fusion",
            "pcg_features": "fusion",
        }
        for key, module_name in payload_to_module.items():
            if key in signal_payload and module_name not in selected:
                selected.append(module_name)

    return selected


def dispatch_algorithm_results(
    *,
    user_message: str,
    signal_payload: Mapping[str, Any] | None = None,
    requested_modules: Sequence[str] | None = None,
) -> dict[str, dict[str, object]]:
    """Run the selected placeholder algorithms and collect their outputs."""
    payload = dict(signal_payload or {})
    modules = select_algorithm_modules(
        user_message,
        signal_payload=payload,
        requested_modules=requested_modules,
    )
    results: dict[str, dict[str, object]] = {}

    if "ecg" in modules:
        results["ecg"] = _safe_algorithm_call(
            analyze_ecg,
            signal_data=payload.get("ecg_signal"),
        )

    if "pcg" in modules:
        results["pcg"] = _safe_algorithm_call(
            analyze_pcg,
            audio_data=payload.get("pcg_audio"),
        )

    if "hrv" in modules:
        results["hrv"] = _safe_algorithm_call(
            analyze_hrv,
            rr_intervals=payload.get("rr_intervals"),
        )

    if "cnn" in modules:
        results["cnn"] = _safe_algorithm_call(
            analyze_cnn,
            features=payload.get("cnn_features"),
        )

    if "fusion" in modules:
        results["fusion"] = _safe_algorithm_call(
            analyze_fusion,
            ecg_features=payload.get("ecg_features"),
            hrv_features=payload.get("hrv_features"),
            pcg_features=payload.get("pcg_features"),
            extra_context=payload.get("fusion_context"),
        )

    return results


def build_algorithm_context(algorithm_results: Mapping[str, Mapping[str, object]]) -> str:
    """Convert algorithm outputs into a compact text block for the model."""
    if not algorithm_results:
        return ""

    blocks: list[str] = []
    for module_name, result in algorithm_results.items():
        summary = str(result.get("summary", "")).strip()
        risk_level = str(result.get("risk_level", "")).strip()
        status = str(result.get("status", "")).strip()
        metrics = result.get("metrics") or result.get("prediction") or {}

        metric_parts: list[str] = []
        if isinstance(metrics, Mapping):
            for key, value in metrics.items():
                metric_parts.append(f"{key}={value}")

        text = f"{module_name.upper()}: status={status}"
        if risk_level:
            text += f", risk={risk_level}"
        if summary:
            text += f", summary={summary}"
        if metric_parts:
            text += f", metrics: {'; '.join(metric_parts)}"
        blocks.append(text)

    return "\n".join(blocks)


def build_model_input(
    *,
    user_message: str,
    algorithm_results: Mapping[str, Mapping[str, object]],
) -> str:
    """Merge the raw user message with algorithm context for model consumption."""
    algorithm_context = build_algorithm_context(algorithm_results)
    if not algorithm_context:
        return user_message.strip()

    return (
        "以下是当前轮次可用的算法分析结果，请结合这些结果回答用户。\n"
        f"{algorithm_context}\n\n"
        f"用户原始消息：{user_message.strip()}"
    )


def get_agent_response(
    user_message: str,
    *,
    session_id: str = "default",
    system_prompt: str | None = None,
    signal_payload: Mapping[str, Any] | None = None,
    requested_modules: Sequence[str] | None = None,
    run_algorithms: bool | None = None,
    memory_store: MemoryStore | None = None,
    model_client: LLMClient | None = None,
) -> dict[str, object]:
    """Main B-side orchestration entry for multi-turn dialogue."""
    cleaned_message = user_message.strip()
    if not cleaned_message:
        raise ValueError("user_message cannot be empty.")

    resolved_session_id = session_id.strip() or "default"
    store = memory_store or default_memory_store
    client = model_client or default_model_client
    conversation = store.get_session(resolved_session_id)

    resolved_prompt = resolve_system_prompt(system_prompt)
    conversation.set_system_message(resolved_prompt)
    history_before = conversation.get_messages(include_system=False)

    algorithm_results: dict[str, dict[str, object]] = {}
    if should_run_algorithms(
        cleaned_message,
        signal_payload=signal_payload,
        requested_modules=requested_modules,
        run_algorithms=run_algorithms,
    ):
        algorithm_results = dispatch_algorithm_results(
            user_message=cleaned_message,
            signal_payload=signal_payload,
            requested_modules=requested_modules,
        )

    model_input = build_model_input(
        user_message=cleaned_message,
        algorithm_results=algorithm_results,
    )

    try:
        model_response = client.chat(
            user_message=model_input,
            history=history_before,
            system_prompt=resolved_prompt,
        )
    except ModelClientError as exc:
        model_response = ModelResponse(
            text=(
                "当前模型服务暂时不可用，我先保留了本轮消息。"
                f" 你可以稍后重试，或继续进行界面与算法联调。错误信息：{exc}"
            ),
            model_name=client.model_name,
            used_mock=bool(getattr(client, "use_mock", False)),
        )

    conversation.add_user_message(cleaned_message)
    conversation.add_assistant_message(model_response.text)

    return {
        "session_id": resolved_session_id,
        "reply": model_response.text,
        "system_prompt": resolved_prompt,
        "history": conversation.get_messages(),
        "algorithm_results": algorithm_results,
        "model": {
            "name": model_response.model_name,
            "used_mock": model_response.used_mock,
        },
    }


def get_session_history(
    session_id: str = "default",
    *,
    include_system: bool = True,
    memory_store: MemoryStore | None = None,
) -> list[dict[str, str]]:
    """Return the current history for a session."""
    store = memory_store or default_memory_store
    conversation = store.get_session(session_id.strip() or "default")
    return conversation.get_messages(include_system=include_system)


def clear_session_history(
    session_id: str = "default",
    *,
    keep_system_message: bool = True,
    memory_store: MemoryStore | None = None,
) -> None:
    """Clear a session while optionally keeping the leading system prompt."""
    store = memory_store or default_memory_store
    store.clear_session(
        session_id.strip() or "default",
        keep_system_message=keep_system_message,
    )


def _safe_algorithm_call(function: Any, **kwargs: Any) -> dict[str, object]:
    try:
        result = function(**kwargs)
    except Exception as exc:
        module_name = getattr(function, "__name__", "algorithm")
        return {
            "module": module_name,
            "status": "error",
            "summary": f"Placeholder algorithm call failed: {exc}",
            "risk_level": "unknown",
            "meta": {"placeholder_only": True},
        }

    return dict(result)


__all__ = [
    "build_algorithm_context",
    "build_model_input",
    "clear_session_history",
    "dispatch_algorithm_results",
    "get_agent_response",
    "get_session_history",
    "resolve_system_prompt",
]
