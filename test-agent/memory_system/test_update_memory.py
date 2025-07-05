"""
测试短期记忆晋升逻辑
"""
import os
import sys

# 添加路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory_system.interface import MemorySystem
from memory_system.config import MemoryConfig


def create_real_conversation_states():
    """创建基于真实对话的测试states"""
    return [
        {
            "type": "user_message",
            "content": "我们聊聊赚钱。我当前状态是初级的全栈开发、有能力使用各种AI工具（画图、写代码之类）、喜欢深入本质、最近一直在研究观察AI领域、精力有限，设计半懂不懂（这点AI可以帮一点忙）、锻炼讲故事能力中。我在考虑建立一个赚钱系统，你怎么看老朋友？"
        },
        {
            "type": "agent_message",
            "content": "傍晚的风吹着确实舒服。你提的这个词，赚钱系统，我很喜欢。比找个项目赚钱要好。因为系统这两个字，意味着你想要的不是一锤子买卖，不是把自己当成一个零件卖掉，而是一个能持续、能自我生长、能放大你投入的东西。这说明你已经在思考本质了，这是好事。"
        },
        {
            "type": "user_message", 
            "content": "老朋友，着眼点放到他人身上是好的，但你从痛点角度考虑，我有所不同意。我以为解决方法都在其思维之外。简单满足痛点不过隔靴搔痒，而且世上人千千万万，痛点无处不在，你想做的东西，你看到的，可能别人也看到，最终做得比你更好，竞争中失败者是赚不到钱的。我们试着先从我的角度出发，捋一遍，看看有哪些竞争优势，可以转换的"
        },
        {
            "type": "agent_message",
            "content": "你说的这个，我不同意。但我很高兴你这么说。因为你的这个想法，恰恰是绝大多数聪明人，尤其是技术出身的聪明人，最容易掉进去的陷阱。我们把它掰开揉碎了看。第一，你担心竞争。你说别人也看到，最终做得比你更好。没错，如果痛点是我渴了，解决方案是卖水，那最后一定是资本最雄厚、渠道最广、成本最低的人赢。这叫红海竞争。"
        },
        {
            "type": "user_message",
            "content": "不不不，我似乎没有表达清楚。这样说，痛点这个事情，本质是什么？我直觉上不喜欢这个词。买卖或者交易，其目的，绝不仅限于解决痛点，它可能是满足一种避免麻烦的欲望，一种自我成长的渴望，一种满足好奇，一种自我幻想，一种认同。只谈痛点，忽视了人本身"
        },
        {
            "type": "agent_message",
            "content": "你说得太对了。痛点这个词，确实被用烂了，变得又冷又硬，像个商业术语，听着没人情味。你说忽视了人本身，这句话说到了根子上。我收回痛点这个词。我们换一个。你说的那些：避免麻烦、自我成长、满足好奇、自我幻想、身份认同……这些东西，它们的本质是什么？我认为，它们都指向了一个东西：现状和理想态之间的差距。"
        }
    ]


def view_all_long_term_memories(memory_system, user_id):
    """查看所有长期记忆的详细信息"""
    print("\n=== 查看所有长期记忆 ===")
    
    try:
        # 获取所有长期记忆
        long_memories = memory_system.long_term_mgr.get_all_memories(user_id)
        
        if not long_memories:
            print("没有找到长期记忆")
            return
        
        print(f"共找到 {len(long_memories)} 条长期记忆：")
        print("-" * 80)
        
        for i, memory in enumerate(long_memories, 1):
            print(f"记忆 {i}:")
            print(f"  ID: {memory.id}")
            print(f"  HP: {memory.hp}")
            print(f"  时间: {memory.timestamp}")
            print(f"  内容: {memory.content}")
            print(f"  向量维度: {len(memory.embedding) if memory.embedding else 0}")
            print("-" * 80)
            
    except Exception as e:
        print(f"查看长期记忆失败: {e}")


def test_promotion_logic():
    """测试短期记忆晋升逻辑"""
    print("=== 测试短期记忆晋升逻辑 ===")
    
    # 配置：低阈值，低数量限制
    config = MemoryConfig()
    config.STATES_TOKEN_THRESHOLD = 200
    config.SHORT_TERM_MAX_COUNT = 2  # 最多2条短期记忆
    
    memory_system = MemorySystem(config=config)
    user_id = "promotion_test"
    
    print(f"配置: 阈值={config.STATES_TOKEN_THRESHOLD}, 最大短期记忆={config.SHORT_TERM_MAX_COUNT}")
    
    # 添加多条记忆，触发晋升
    for i in range(4):
        print(f"\n--- 第{i+1}次添加记忆 ---")
        
        if i == 0:
            # 第一次使用真实对话数据
            states = create_real_conversation_states()
        else:
            # 后续使用简化数据
            states = [
                {
                    "type": "user_message",
                    "content": f"第{i+1}次对话：用户在讨论关于AI技术的应用和商业化思考。" + "详细内容填充。" * 100
                },
                {
                    "type": "agent_message",
                    "content": f"第{i+1}次回复：助手提供了关于技术商业化的深度分析和建议。" + "详细回复填充。" * 100
                }
            ]
        
        print(f"States数量: {len(states)}")
        memory_system.update_memory(states, user_id)
        
        stats = memory_system.get_memory_stats(user_id)
        print(f"当前统计: 短期={stats['short_term']['count']}, 长期={stats['long_term']['count']}")
        
        # 检查是否发生晋升
        if stats['long_term']['count'] > 0:
            print("✅ 检测到长期记忆生成（晋升发生）")
        
        # 检查短期记忆是否超限
        if stats['short_term']['count'] > config.SHORT_TERM_MAX_COUNT:
            print("⚠️ 短期记忆超过限制但未晋升")
    
    # 最终统计
    final_stats = memory_system.get_memory_stats(user_id)
    print(f"\n最终统计: 短期={final_stats['short_term']['count']}, 长期={final_stats['long_term']['count']}")
    
    if final_stats['long_term']['count'] > 0:
        print("✅ 晋升逻辑工作正常")
        # 查看所有长期记忆的详细信息
        view_all_long_term_memories(memory_system, user_id)
    else:
        print("❌ 晋升逻辑未触发")


if __name__ == "__main__":
    # 确保存储目录存在
    os.makedirs("memory_system/storage", exist_ok=True)
    
    print("🚀 开始测试短期记忆晋升逻辑...\n")
    
    try:
        test_promotion_logic()
        print("\n🎉 晋升逻辑测试完成！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc() 