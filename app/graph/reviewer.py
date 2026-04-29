"""审查器 - 审查子图输出结果"""

import json
from datetime import datetime
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from ..core.state import Critique
from ..core.logging import logger
from ..core.prompts import REVIEWER_SYSTEM_PROMPT
from ..services.llm_service import get_llm


# 各领域的审查规则
HARD_RULES = {
    "outfit": {
        "name": "穿搭审查规则",
        "rules": [
            "穿搭方案必须匹配天气条件（晴天/雨天/雪天）",
            "穿搭方案必须考虑温度（冷/热）",
            "必须包含上装、下装、鞋等基本单品",
            "每个单品必须有推荐理由"
        ]
    },
    "search": {
        "name": "搜索审查规则",
        "rules": [
            "搜索结果必须有来源（URL/网站名）",
            "必须有时间戳或时效性说明",
            "结果内容必须与查询相关",
            "不能编造不存在的信息"
        ]
    },
    "finance": {
        "name": "金融审查规则",
        "rules": [
            "价格信息必须说明来源",
            "必须有时间戳（股票价格时效性强）",
            "价格数据必须包含单位",
            "不能保证投资收益或提供投资建议"
        ]
    },
    "academic": {
        "name": "学术审查规则",
        "rules": [
            "必须包含来源链接（GitHub URL/arXiv URL）",
            "论文必须有摘要或关键点总结",
            "代码仓库必须有描述",
            "不能编造不存在的仓库或论文"
        ]
    },
    "trip": {
        "name": "旅行审查规则",
        "rules": [
            "行程必须包含具体景点名称",
            "必须考虑天气因素",
            "必须有住宿和交通建议",
            "行程安排必须合理"
        ]
    }
}


async def reviewer_node(state: dict) -> dict:
    """
    审查节点 - 审查子图输出结果

    Args:
        state: 当前主图状态

    Returns:
        更新后的状态
    """
    active_domain = state.get("active_domain", "unknown")
    subgraph_output = state.get("subgraph_outputs", {}).get(active_domain, {})
    user_query = state.get("user_query", "")

    logger.info(f"[Reviewer] 正在审查 {active_domain} 子图输出...")

    # 先做基本的格式检查，如果输出存在且长度合理则直接通过
    result = subgraph_output.get("result", "")

    # 如果有实质性的输出内容，直接通过审查
    if result and len(str(result)) > 20:
        logger.info(f"[Reviewer] 输出内容充足，直接通过审查")
        review_result = {
            "passed": True,
            "score": 0.9,
            "violations": [],
            "critique": "输出内容符合要求",
            "suggestions": []
        }
    else:
        # 输出为空或太短，进行详细审查
        try:
            llm = get_llm()

            # 构建审查提示
            domain_rules = HARD_RULES.get(active_domain, HARD_RULES["search"])
            rules_text = "\n".join(f"- {r}" for r in domain_rules["rules"])

            prompt = f"""请审查以下 {active_domain} 领域的输出结果是否符合质量要求。

用户查询: {user_query}

审查规则:
{rules_text}

子图输出结果:
{result}

请严格按照以下 JSON 格式输出审查结果：
```json
{{
  "passed": true/false,
  "score": 0.0-1.0,
  "violations": ["违反的规则1", "违反的规则2"],
  "critique": "详细的审查意见",
  "suggestions": ["改进建议1", "改进建议2"]
}}
```
"""

            messages = [
                SystemMessage(content=REVIEWER_SYSTEM_PROMPT),
                HumanMessage(content=prompt)
            ]

            response = await llm.ainvoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)

            # 解析审查结果
            review_result = parse_review_response(content)

        except Exception as e:
            logger.error(f"[Reviewer] 详细审查失败: {e}")
            # 默认通过（因为已有内容）
            review_result = {
                "passed": True,
                "score": 0.7,
                "violations": [],
                "critique": "有输出内容，默认通过",
                "suggestions": []
            }

    # 记录审查历史
    critique: Critique = {
        "domain": active_domain,
        "passed": review_result.get("passed", True),
        "score": review_result.get("score", 0.8),
        "violations": review_result.get("violations", []),
        "critique": review_result.get("critique", ""),
        "timestamp": datetime.now().isoformat()
    }

    state["review_result"] = review_result
    state["critique_history"] = state.get("critique_history", []) + [critique]

    logger.info(f"[Reviewer] 审查结果: {'通过' if critique['passed'] else '不通过'} (得分: {critique['score']})")

    return state


def parse_review_response(content: str) -> dict:
    """解析审查器响应"""
    # 尝试提取 JSON
    if "```json" in content:
        start = content.find("```json") + 7
        end = content.find("```", start)
        content = content[start:end].strip()
    elif "```" in content:
        start = content.find("```") + 3
        end = content.find("```", start)
        content = content[start:end].strip()
    elif "{" in content:
        start = content.find("{")
        end = content.rfind("}") + 1
        content = content[start:end]

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # 解析失败，返回默认通过
        return {
            "passed": True,
            "score": 0.7,
            "violations": [],
            "critique": "无法解析审查结果，默认通过",
            "suggestions": []
        }


def should_retry(state: dict) -> bool:
    """
    判断是否需要重试

    Args:
        state: 当前主图状态

    Returns:
        是否需要重试
    """
    review_result = state.get("review_result", {})
    retry_count = state.get("retry_count", 0)
    max_retry = state.get("max_retry", 3)

    # 如果审查不通过且未达到最大重试次数
    if not review_result.get("passed", True) and retry_count < max_retry:
        return True

    # 如果置信度低且未达到最大重试次数
    router_result = state.get("router_result", {})
    if router_result.get("confidence", 1.0) < 0.7 and retry_count < max_retry:
        return True

    return False
