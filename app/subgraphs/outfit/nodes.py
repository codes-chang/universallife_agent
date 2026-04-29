"""Outfit 子图节点实现"""

import json
from typing import Any
from langchain_core.messages import HumanMessage, SystemMessage

from ...services.llm_service import get_llm
from ...services.weather_service import get_weather_service
from ...core.logging import logger
from .state import OutfitSubgraphState


# 穿搭 Prompt
OUTFIT_SYSTEM_PROMPT = """你是专业的穿搭顾问。根据天气和场合，为用户提供合适的穿搭建议。

请严格按照以下 JSON 格式输出：
```json
{
  "location": "城市名称",
  "weather": "天气描述",
  "temperature": "温度范围",
  "occasion": "场合",
  "outfit": {
    "top": {"name": "上装名称", "reason": "推荐理由"},
    "bottom": {"name": "下装名称", "reason": "推荐理由"},
    "shoes": {"name": "鞋子", "reason": "推荐理由"},
    "accessories": [{"name": "配饰", "reason": "推荐理由"}]
  },
  "advice": "整体建议和注意事项"
}
```
"""


async def build_plan_node(state: OutfitSubgraphState) -> OutfitSubgraphState:
    """规划节点 - 分析穿搭需求"""
    logger.info("[Outfit] 正在分析穿搭需求...")

    task_input = state.get("task_input", "")

    # 使用 LLM 提取关键信息
    try:
        llm = get_llm()
        extract_prompt = f"""从以下用户请求中提取穿搭相关信息：

用户请求: {task_input}

请提取并输出 JSON 格式：
{{
  "location": "城市名称（如果没有则填'未知'）",
  "occasion": "场合（通勤/休闲/运动/正式/其他）",
  "style_preference": "风格偏好（如果有）",
  "gender": "性别（如果有明确提及）",
  "special_requirements": "特殊要求（如果有）"
}}
"""

        response = await llm.ainvoke([
            SystemMessage(content="你是信息提取专家，请提取关键信息并以 JSON 格式输出。"),
            HumanMessage(content=extract_prompt)
        ])

        content = response.content if hasattr(response, 'content') else str(response)

        # 解析 JSON
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            content = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            content = content[start:end].strip()

        extracted = json.loads(content)

        state["location"] = extracted.get("location", "上海")
        state["occasion"] = extracted.get("occasion", "通勤")
        state["style_preference"] = extracted.get("style_preference", "")
        state["gender"] = extracted.get("gender", None)

        plan = f"""为用户在{state['location']}的{state['occasion']}场景提供穿搭建议"""
        if state["style_preference"]:
            plan += f"，风格偏好: {state['style_preference']}"

        state["plan"] = plan

    except Exception as e:
        logger.error(f"[Outfit] 信息提取失败: {e}")
        state["location"] = "上海"
        state["occasion"] = "通勤"
        state["plan"] = "为用户提供通勤穿搭建议"

    return state


async def execute_tools_node(state: OutfitSubgraphState) -> OutfitSubgraphState:
    """工具执行节点 - 获取天气信息"""
    logger.info("[Outfit] 正在获取天气信息...")

    location = state.get("location", "上海")

    try:
        weather_service = get_weather_service()
        weather_data = await weather_service.get_weather(location, days=1)

        state["weather_condition"] = weather_data

        # 提取关键天气信息
        casts = weather_data.get("casts", [])
        if casts:
            today = casts[0]
            weather_summary = {
                "date": today.get("date"),
                "day_weather": today.get("day_weather"),
                "night_weather": today.get("night_weather"),
                "day_temp": today.get("day_temp"),
                "night_temp": today.get("night_temp")
            }

            intermediate = json.dumps({
                "location": location,
                "weather": weather_summary
            }, ensure_ascii=False)
        else:
            intermediate = json.dumps({"location": location, "weather": "获取失败"})

        state["intermediate_result"] = intermediate

    except Exception as e:
        logger.error(f"[Outfit] 天气获取失败: {e}")
        state["intermediate_result"] = json.dumps({
            "location": location,
            "weather": {"day_weather": "未知", "day_temp": "20"}
        })

    return state


async def synthesize_result_node(state: OutfitSubgraphState) -> OutfitSubgraphState:
    """结果合成节点 - 生成穿搭建议"""
    logger.info("[Outfit] 正在生成穿搭建议...")

    try:
        llm = get_llm()

        # 获取天气信息
        weather_info = state.get("weather_condition", {})
        casts = weather_info.get("casts", [])
        today_weather = casts[0] if casts else {}

        weather_text = f"{today_weather.get('day_weather', '晴')}，{today_weather.get('day_temp', '20')}°C"

        prompt = f"""请根据以下信息提供穿搭建议：

地点: {state.get('location', '上海')}
天气: {weather_text}
场合: {state.get('occasion', '通勤')}
风格偏好: {state.get('style_preference', '无特殊要求')}

请提供完整的穿搭方案，包括上装、下装、鞋子、配饰，并说明推荐理由。
"""

        response = await llm.ainvoke([
            SystemMessage(content=OUTFIT_SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ])

        content = response.content if hasattr(response, 'content') else str(response)

        # 尝试解析 JSON 结果
        try:
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

            outfit_data = json.loads(content)

            # 格式化输出
            outfit = outfit_data.get("outfit", {})
            result_parts = [
                f"👔 {outfit_data.get('location', '上海')} 穿搭建议",
                f"🌤️  天气: {weather_text}",
                f"📍 场合: {state.get('occasion', '通勤')}",
                "",
                "📦 推荐搭配:",
                f"  • 上装: {outfit.get('top', {}).get('name', '轻便外套')}",
                f"    理由: {outfit.get('top', {}).get('reason', '适合当前天气')}",
                f"  • 下装: {outfit.get('bottom', {}).get('name', '休闲长裤')}",
                f"    理由: {outfit.get('bottom', {}).get('reason', '舒适实用')}",
                f"  • 鞋子: {outfit.get('shoes', {}).get('name', '运动鞋')}",
                f"    理由: {outfit.get('shoes', {}).get('reason', '适合通勤')}",
            ]

            accessories = outfit.get("accessories", [])
            if accessories:
                result_parts.append("  • 配饰:")
                for acc in accessories:
                    result_parts.append(f"    - {acc.get('name', '')}: {acc.get('reason', '')}")

            result_parts.append(f"\n💡 建议: {outfit_data.get('advice', '注意天气变化，适当增减衣物')}")

            state["final_result"] = "\n".join(result_parts)

        except json.JSONDecodeError:
            # JSON 解析失败，直接使用原始内容
            state["final_result"] = content

    except Exception as e:
        logger.error(f"[Outfit] 结果合成失败: {e}")
        state["final_result"] = f"根据{state.get('location', '上海')}的天气，建议穿着适合{state.get('occasion', '通勤')}的舒适衣物。"

    return state
