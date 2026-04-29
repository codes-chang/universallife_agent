"""反馈分析工具"""

from typing import List, Tuple
import re

# 负反馈关键词
NEGATIVE_KEYWORDS = [
    "理解错了", "不是这个意思", "你跑偏了", "不对",
    "错了", "错误", "误解", "搞错了", "错了",
    "不是", "重新来", "再来", "算了"
]

# 纠正关键词
CORRECTION_KEYWORDS = [
    "我是要", "我想", "我的意思是", "应该是",
    "实际上", "其实是", "正确的"
]

# 正反馈关键词
POSITIVE_KEYWORDS = [
    "对的", "是的", "正确", "好的", "谢谢", "感谢",
    "帮了我", "有用", "很好"
]


def detect_negative_feedback(feedback: str) -> bool:
    """
    检测是否为负反馈

    Args:
        feedback: 用户反馈文本

    Returns:
        是否为负反馈
    """
    feedback_lower = feedback.lower()
    for keyword in NEGATIVE_KEYWORDS:
        if keyword.lower() in feedback_lower:
            return True
    return False


def detect_positive_feedback(feedback: str) -> bool:
    """
    检测是否为正反馈

    Args:
        feedback: 用户反馈文本

    Returns:
        是否为正反馈
    """
    feedback_lower = feedback.lower()
    for keyword in POSITIVE_KEYWORDS:
        if keyword.lower() in feedback_lower:
            return True
    return False


def extract_correction_intent(feedback: str) -> Tuple[str, str]:
    """
    提取纠正意图

    Args:
        feedback: 用户反馈文本

    Returns:
        (原始意图, 纠正后的意图)
    """
    # 查找纠正模式
    for keyword in CORRECTION_KEYWORDS:
        if keyword in feedback:
            # 分割反馈获取纠正内容
            parts = feedback.split(keyword)
            if len(parts) > 1:
                corrected = parts[1].strip()
                # 移除标点
                corrected = re.sub(r'[。？！，、？!！,.?]', '', corrected)
                return ("", corrected)

    return ("", feedback)


def get_feedback_sentiment(feedback: str) -> str:
    """
    获取反馈情感

    Args:
        feedback: 用户反馈文本

    Returns:
        情感类型: positive, negative, neutral
    """
    if detect_positive_feedback(feedback):
        return "positive"
    elif detect_negative_feedback(feedback):
        return "negative"
    else:
        return "neutral"


def analyze_feedback(feedback: str) -> dict:
    """
    分析反馈

    Args:
        feedback: 用户反馈文本

    Returns:
        分析结果字典
    """
    return {
        "sentiment": get_feedback_sentiment(feedback),
        "is_negative": detect_negative_feedback(feedback),
        "is_positive": detect_positive_feedback(feedback),
        "correction": extract_correction_intent(feedback),
        "has_correction": any(kw in feedback for kw in CORRECTION_KEYWORDS)
    }
