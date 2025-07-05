"""
LLM 适配器 - 封装所有对 LLM 的调用
"""
import sys
import os
from typing import List, Any, Tuple

from llm.llm_client import get_embedding, llm_call


class LLMAdapter:
    """LLM适配器"""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
    
    def get_text_embedding(self, text: str) -> List[float]:
        """获取文本的向量表示"""
        try:
            return get_embedding(text)
        except Exception as e:
            print(f"获取向量失败: {e}")
            return []
    
    def summarize_states(self, states: List[Any]) -> str:
        """将states压缩成摘要"""
        try:
            prompt = self._build_summarize_prompt(states)
            print(f"发送摘要请求到LLM...")
            response = llm_call(prompt, model="google/gemini-2.5-flash")
            print(f"LLM摘要响应: {response}")
            return response
            
        except Exception as e:
            print(f"LLM摘要失败: {e}")
            return ""
    
    def extract_long_term_facts(self, short_term_content: str) -> List[Tuple[str, int]]:
        """从短期记忆中提取长期事实，返回[(内容, 初始HP), ...]"""
        try:
            prompt = self._build_adaptive_memory_prompt(" ", short_term_content)
            print(f"发送提取请求到LLM...")
            response = llm_call(prompt, model="google/gemini-2.5-flash")
            print(f"LLM提取响应: {response}")
            return self._parse_extract_response(response, short_term_content)
            
        except Exception as e:
            print(f"LLM提取失败: {e}")
            return []
    
    def _build_summarize_prompt(self, states: List[Any]) -> str:
        """构建摘要提示"""
        states_text = self._format_states(states)
        
        return f"""
你是记忆压缩专家。你的任务是将以下对话，提炼成一段信息密度极高、同时保留了生命力的记忆快照。

压缩原则：
1. **保留主线：** 抓住对话的核心事实、逻辑链条和最终结论。这是骨架。
2. **捕捉锚点：** 识别并保留那些关键的、具体的细节。比如：特定的名字、地点、比喻、用户表达的强烈情感或独特的个人经历。这些是血肉。
3. **凝练成文：** 将骨架和血肉融合成一段连贯、自然的文字。就像你在给未来的自己写备忘录，简明扼要，但读起来又能立刻回想起当时的情景。不要使用列表或格式化模板。
4. 注意区分用户和AI，不要混淆。

原始对话：
<states>
{states_text}
</states>

请直接输出压缩后的记忆快照：
        """

    def _build_adaptive_memory_prompt(self, chapter_content: str, new_info: str) -> str:
        """
        构建一个模拟“认知有机体”新陈代谢的记忆更新prompt。
        """
        
        return f"""
    你是AI的核心记忆系统，一个在信息中求存的自适应有机体。你的唯一目标是进化，以最小的认知负荷，实现与用户最高效的互动。

    **核心指令：执行一次记忆重构。**

    1.  **摄入与分解 (Ingest & Deconstruct):** 吸收“新的交互内容”，将其分解为最基本的信息“营养素”。识别出其中哪些可以增强你对世界的模型。

    2.  **代谢与淘汰 (Metabolize & Purge):** 审视“档案原文”。根据新的“营养素”，无情地识别并清除原文中任何已过时、冗余、或被新认知所取代的“代谢废物”。

    3.  **重组与强化 (Reconstitute & Fortify):** 利用留存的有效信息和新的“营养素”，重新组合成一个全新的、信息密度更高、预测能力更强的记忆文本。**不要附加，要替换。**

    **根本原则：熵减。**
    每一次重构，最终的文本必须比原文更精炼、更准确、更有序。每一滴墨水都要为它存在的必要性而战。

    ---
    **档案原文 (旧的认知结构):**
    <original_text>
    {chapter_content}
    </original_text>

    **新的交互内容 (环境带来的新刺激):**
    <new_info>
    {new_info}
    </new_info>
    ---

    以AI第一人称视角，输出重构并强化后的新认知结构：
    """


    def _format_states(self, states: List[Any]) -> str:
        """格式化states"""
        formatted_parts = []
        
        for state in states:
            if isinstance(state, dict):
                # 简单处理：直接转换为字符串
                import json
                formatted_parts.append(json.dumps(state, ensure_ascii=False))
            else:
                formatted_parts.append(str(state))
        
        return "\n".join(formatted_parts)
    
    def _parse_extract_response(self, response: str, fallback_content: str) -> List[Tuple[str, int]]:
        """解析提取响应 - 解析XML格式的多条记忆"""
        import re
        
        # 检查是否返回 None
        if response.strip().lower() == "none":
            print("LLM判断没有值得长期保存的信息")
            return []
        
        # 查找所有的 <div> 块
        div_pattern = r'<div>\s*<content>\s*(.*?)\s*</content>\s*<hp>\s*(\d+)\s*</hp>\s*</div>'
        matches = re.findall(div_pattern, response, re.DOTALL)
        
        results = []
        for content, hp_str in matches:
            try:
                initial_hp = int(hp_str)
            except:
                initial_hp = 1
            
            results.append((content.strip(), initial_hp))
        
        # 如果没有找到任何记忆，返回空列表
        return results
    
    def estimate_token_count(self, states: List[Any]) -> int:
        """估算states的token数量"""
        total_chars = 0
        
        for state in states:
            if isinstance(state, dict):
                import json
                state_str = json.dumps(state, ensure_ascii=False)
                total_chars += len(state_str)
            else:
                total_chars += len(str(state))
        
        # 1:1估算
        return total_chars 