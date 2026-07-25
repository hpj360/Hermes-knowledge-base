"""M2-10：LLM token 成本估算（CNY）。

按模型名查表估算单次问答成本。设计要点：
- 价格单位：CNY / 1K tokens（参考各厂商 2025 年公开定价）
- **未配置真实 LLM 或 mock 模型**：返回 0（不计成本）
- **未知模型**：返回 0（不抛异常，避免审计/日志写入失败）
- 价格表可被外部覆盖（便于调价后无需改代码）

参考定价（CNY / 1K tokens，2025-01）：
- glm-4-flash: 0.0001 / 0.0001（智谱，极便宜）
- glm-4: 0.1 / 0.1（智谱）
- gpt-4o-mini: 0.00105 / 0.0042（OpenAI，按汇率 7.2 换算）
- gpt-4o: 0.021 / 0.084
- gpt-3.5-turbo: 0.0035 / 0.007
- deepseek-chat: 0.001 / 0.002
- moonshot-v1-8k: 0.012 / 0.012
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

log = logging.getLogger("hermes_kb.token_cost")


@dataclass(frozen=True)
class ModelPrice:
    """模型定价（CNY / 1K tokens）。"""

    input: float  # 输入 token 价格
    output: float  # 输出 token 价格


# 模型定价表（CNY / 1K tokens）
# 来源：各厂商 2025-01 公开定价页
_MODEL_PRICES: dict[str, ModelPrice] = {
    # 智谱 GLM 系列
    "glm-4-flash": ModelPrice(0.0001, 0.0001),
    "glm-4": ModelPrice(0.1, 0.1),
    "glm-4-air": ModelPrice(0.001, 0.001),
    "glm-4-airx": ModelPrice(0.005, 0.005),
    # OpenAI 系列
    "gpt-4o": ModelPrice(0.021, 0.084),
    "gpt-4o-mini": ModelPrice(0.00105, 0.0042),
    "gpt-4-turbo": ModelPrice(0.0714, 0.2142),
    "gpt-3.5-turbo": ModelPrice(0.0035, 0.007),
    # DeepSeek
    "deepseek-chat": ModelPrice(0.001, 0.002),
    # Moonshot
    "moonshot-v1-8k": ModelPrice(0.012, 0.012),
    "moonshot-v1-32k": ModelPrice(0.024, 0.024),
    # 阿里通义千问
    "qwen-turbo": ModelPrice(0.002, 0.006),
    "qwen-plus": ModelPrice(0.004, 0.012),
    # Mock（不计成本）
    "mock-llm": ModelPrice(0.0, 0.0),
    "mock": ModelPrice(0.0, 0.0),
}


def get_model_price(model: str) -> ModelPrice | None:
    """查模型定价，未找到返回 None。"""
    if not model:
        return None
    return _MODEL_PRICES.get(model.lower())


def calculate_cost(
    model: str, prompt_tokens: int, completion_tokens: int
) -> float:
    """估算单次问答成本（CNY）。

    Args:
        model: 模型名（如 "glm-4-flash"）
        prompt_tokens: 输入 token 数
        completion_tokens: 输出 token 数

    Returns:
        成本（CNY，浮点）；未知模型或 mock 返回 0.0

    Note:
        未知模型不抛异常，返回 0（避免审计/日志写入失败）。
        可通过日志监控未知模型调用，后续补充定价。
    """
    price = get_model_price(model)
    if price is None:
        # 未知模型：记录 warning 便于运营补充定价表
        log.warning(
            "unknown model %r, cost calculated as 0 (consider adding to price table)",
            model,
        )
        return 0.0
    cost = (prompt_tokens / 1000.0) * price.input + (
        completion_tokens / 1000.0
    ) * price.output
    # 四舍五入到 6 位小数（避免浮点精度问题）
    return round(cost, 6)


def estimate_tokens(text: str) -> int:
    """估算文本 token 数（粗略，用于流式场景无 usage 时兜底）。

    经验值：
    - 中文：约 1.5 字/token（GB/T 10781 等术语密集）
    - 英文：约 4 字符/token
    - 混合：取 2.5 字符/token 作为折中

    Note:
        仅用于流式无 usage 时的兜底估算，精度不重要（成本估算 ±50% 可接受）。
    """
    if not text:
        return 0
    # 简单启发式：每 2.5 字符约 1 token
    return max(1, int(len(text) / 2.5))


def register_model_price(model: str, input_price: float, output_price: float) -> None:
    """运行时注册新模型定价（用于调价或新增模型）。

    Args:
        model: 模型名（小写不敏感）
        input_price: 输入价格（CNY / 1K tokens）
        output_price: 输出价格（CNY / 1K tokens）
    """
    _MODEL_PRICES[model.lower()] = ModelPrice(input_price, output_price)
