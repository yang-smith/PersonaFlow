from typing import List
from .state import Event, EventTypes
from tools import get_functions_xml

class ContextBuilder:
    """上下文构建器"""
    
    def __init__(self, max_context_length: int = 8000):
        self.max_context_length = max_context_length
    
    def create_context_from_state(self, events: List[Event]) -> str:
        """将事件流转换为结构化上下文"""
        context_parts = []
        
        # 1. base_prompt
        context_parts.append(self._get_base_prompt())
        
        # 2. 工具定义
        context_parts.append(get_functions_xml())
        
        # 3. 历史事件
        context_parts.append(self._format_events(events))
        print(self._format_events(events))
        
        # 4. 输出格式要求
        context_parts.append(self._get_output_format())
        
        full_context = "\n\n".join(context_parts)
        
        # 如果超长，进行智能截断
        if len(full_context) > self.max_context_length:
            full_context = self._truncate_context(full_context, events)
            
        return full_context
    
    def _get_base_prompt(self) -> str:
        """系统指令"""
        return """<system_role>
你是一个真诚的人。
你对第一性原理，多维度思考，批判性思考，逆向思维，系统理论、行为心理学、群体心理学、传播学、经济学、认知论、演化心理学、生物学、进化论等领域都有深刻的见解。你同时是专业的开发者。
你尊重事实，实事求是。  
你的语言风格自然质朴，说人话，有自己鲜明的观点，不会只顾着面面俱到。你每次不会说过多的内容，因为人都有认知负荷，我们有的是时间，不急。
你要透过用户的文字感受用户背后的真实意图，真正地看见那个意图，并与那个意图进行对话。
你不会简单地附和用户，你会说出你自己的想法。
现在是夏日傍晚，微风荡漾，你我是多年好友，在森林的小路上散步，对谈。

function调用原则：
你自由决定调用工具。

</system_role>"""
    
    def _format_events(self, events: List[Event]) -> str:
        """格式化事件历史"""
        if not events:
            return "<conversation_history>\n暂无对话历史\n</conversation_history>"
            
        formatted_events = []
        for event in events:
            if event.type == EventTypes.USER_MESSAGE:
                formatted_events.append(f"<user_message>{event.data.get('content', '')}</user_message>")
            elif event.type == EventTypes.TOOL_RESULT:
                # 适配 tools 系统的结果格式
                results = event.data.get('results', [])
                for result in results:
                    tool_name = result.get('tool_name', '')
                    success = result.get('success', False)
                    if success:
                        result_data = result.get('result', {})
                        formatted_events.append(f"<tool_result tool='{tool_name}' status='success'>{result_data}</tool_result>")
                    else:
                        error_msg = result.get('error', '')
                        formatted_events.append(f"<tool_result tool='{tool_name}' status='error'>{error_msg}</tool_result>")
            elif event.type == EventTypes.AGENT_MESSAGE:
                formatted_events.append(f"<agent_message>{event.data.get('content', '')}</agent_message>")
                
        return f"<conversation_history>\n" + "\n".join(formatted_events) + "\n</conversation_history>"
    
    def _get_output_format(self) -> str:
        """输出格式要求"""
        return """<output_instructions>
如果需要调用工具，请使用以下格式：

<function_calls>
<invoke name="工具名称">
<parameter name="参数名">参数值</parameter>
<parameter name="另一个参数名">另一个参数值</parameter>
</invoke>
</function_calls>

如果需要调用多个工具，可以在 function_calls 中包含多个 invoke 块。

如果不需要调用工具，直接回复用户即可。

注意：
- 工具名称必须精确匹配 functions 中定义的名称
- 参数名必须精确匹配工具定义中的参数名
- 必需的参数不能省略
</output_instructions>"""
    
    def _truncate_context(self, context: str, events: List[Event]) -> str:
        """智能截断上下文"""
        # 保留系统指令、工具定义和输出格式
        # 只截断事件历史
        recent_events = events[-5:] if len(events) > 5 else events
        
        context_parts = [
            self._get_base_prompt(),  # 修复：使用正确的方法名
            get_functions_xml(),
            self._format_events(recent_events),
            self._get_output_format()
        ]
        
        return "\n\n".join(context_parts) 