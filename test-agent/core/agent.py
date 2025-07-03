import re
from typing import Dict, Any
from .state import StateManager, EventTypes
from .context import ContextBuilder

class Agent:
    """Agent 核心 - 实现状态机循环"""
    
    def __init__(self, llm_client, tool_registry):
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self.state_manager = StateManager()
        self.context_builder = ContextBuilder()
        self.max_iterations = 20  # 防止无限循环
    
    def run(self, initial_prompt: str) -> None:
        """运行 Agent 主循环"""
        # 初始化状态
        self.state_manager.add_event(
            EventTypes.USER_MESSAGE, 
            {"content": initial_prompt}
        )
        
        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1
            
            # 1. 构建上下文
            current_state = self.state_manager.get_state()
            context = self.context_builder.create_context_from_state(current_state)
            
            # 2. LLM 决策
            try:
                llm_response = self.llm_client.call(context)
                intent, params, reasoning = self._parse_llm_response(llm_response)
                
                print(f"\n--- 迭代 {iteration} ---")
                print(f"LLM 意图: {intent}")
                print(f"推理: {reasoning}")
                
            except Exception as e:
                print(f"LLM 调用失败: {e}")
                self.state_manager.add_event(EventTypes.ERROR, {"error": str(e)})
                continue
            
            # 3. 执行工具或完成任务
            if intent == "finish":
                print("\nAgent: 任务完成。")
                break
            elif intent in self.tool_registry.tools:
                result = self._execute_tool(intent, params)
                self.state_manager.add_event(
                    EventTypes.TOOL_RESULT,
                    {"tool_name": intent, "result": result}
                )
            else:
                print(f"未知意图: {intent}")
                self.state_manager.add_event(
                    EventTypes.ERROR, 
                    {"error": f"Unknown intent: {intent}"}
                )
        
        if iteration >= self.max_iterations:
            print("达到最大迭代次数，任务终止。")
    
    def _parse_llm_response(self, response: str) -> tuple:
        """解析 LLM 响应"""
        intent_match = re.search(r'<intent>(.*?)</intent>', response, re.DOTALL)
        params_match = re.search(r'<params>(.*?)</params>', response, re.DOTALL)
        reasoning_match = re.search(r'<reasoning>(.*?)</reasoning>', response, re.DOTALL)
        
        intent = intent_match.group(1).strip() if intent_match else "unknown"
        params = params_match.group(1).strip() if params_match else ""
        reasoning = reasoning_match.group(1).strip() if reasoning_match else ""
        
        return intent, params, reasoning
    
    def _execute_tool(self, tool_name: str, params: str) -> Dict[str, Any]:
        """执行工具"""
        try:
            tool = self.tool_registry.get_tool(tool_name)
            return tool.execute(params)
        except Exception as e:
            return {"error": str(e), "success": False} 