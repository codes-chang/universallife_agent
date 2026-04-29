"""辅助函数"""

import re
import json
from typing import Any, Optional, Dict, List
from datetime import datetime


def extract_json_from_text(text: str) -> Optional[dict]:
    """
    从文本中提取 JSON

    Args:
        text: 包含 JSON 的文本

    Returns:
        解析后的字典，失败返回 None
    """
    # 尝试不同的提取模式
    patterns = [
        r'```json\s*(.*?)\s*```',  # markdown json 代码块
        r'```\s*(.*?)\s*```',       # markdown 代码块
        r'\{.*\}',                   # 直接的 JSON 对象
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            json_str = match.group(1) if match.lastindex else match.group(0)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                continue

    return None


def truncate_text(text: str, max_length: int = 500, suffix: str = "...") -> str:
    """
    截断文本

    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 后缀

    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_timestamp(timestamp: Optional[str] = None) -> str:
    """
    格式化时间戳

    Args:
        timestamp: ISO 格式时间戳

    Returns:
        格式化后的时间字符串
    """
    if not timestamp:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return timestamp


def clean_whitespace(text: str) -> str:
    """
    清理多余的空白字符

    Args:
        text: 原始文本

    Returns:
        清理后的文本
    """
    return " ".join(text.strip().split())


def extract_keywords(text: str, top_n: int = 5) -> List[str]:
    """
    提取关键词

    Args:
        text: 输入文本
        top_n: 返回前 N 个关键词

    Returns:
        关键词列表
    """
    # 简单的关键词提取（可以替换为更复杂的算法）
    words = re.findall(r'[\w-]+', text.lower(), re.UNICODE)

    # 过滤停用词
    stopwords = {'的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
    keywords = [w for w in words if len(w) > 1 and w not in stopwords]

    # 统计频率
    from collections import Counter
    word_counts = Counter(keywords)

    return [word for word, _ in word_counts.most_common(top_n)]


def merge_dicts(base: dict, update: dict) -> dict:
    """
    深度合并字典

    Args:
        base: 基础字典
        update: 更新字典

    Returns:
        合并后的字典
    """
    result = base.copy()
    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def safe_get(data: dict, key: str, default: Any = None) -> Any:
    """
    安全获取字典值

    Args:
        data: 字典
        key: 键（支持点号分隔的路径）
        default: 默认值

    Returns:
        值或默认值
    """
    keys = key.split('.')
    value = data

    for k in keys:
        if isinstance(value, dict):
            value = value.get(k)
            if value is None:
                return default
        else:
            return default

    return value if value is not None else default


def validate_email(email: str) -> bool:
    """
    验证邮箱格式

    Args:
        email: 邮箱地址

    Returns:
        是否有效
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def mask_sensitive_info(text: str, patterns: List[str] = None) -> str:
    """
    屏蔽敏感信息

    Args:
        text: 原始文本
        patterns: 敏感信息模式列表

    Returns:
        屏蔽后的文本
    """
    if patterns is None:
        patterns = [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # 邮箱
            r'\b\d{3}-\d{4}-\d{4}\b',  # 手机号
            r'\b(?:sk|api|key|token)[-:\s]*[a-zA-Z0-9]{20,}\b',  # API keys
        ]

    masked = text
    for pattern in patterns:
        masked = re.sub(pattern, '***', masked, flags=re.IGNORECASE)

    return masked
