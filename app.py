import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import re

def test_rss_feed():
    """测试RSS订阅并保存内容到txt文件"""
    
    rss_url = "https://feedx.net/rss/economist.xml"
    output_file = "economist_rss_content.txt"
    
    try:
        print(f"正在获取RSS内容: {rss_url}")
        
        # 发送HTTP请求获取RSS内容
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(rss_url, headers=headers, timeout=30)
        response.raise_for_status()  # 如果状态码不是200会抛出异常
        
        print(f"RSS请求成功，状态码: {response.status_code}")
        print(f"内容长度: {len(response.content)} 字节")
        
        # 解析XML内容
        root = ET.fromstring(response.content)
        
        # 查找所有的item元素
        items = root.findall('.//item')
        
        print(f"找到 {len(items)} 个RSS条目")
        
        # 准备写入文件的内容
        content_lines = []
        content_lines.append(f"RSS测试报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        content_lines.append("=" * 50)
        content_lines.append(f"RSS链接: {rss_url}")
        content_lines.append(f"状态码: {response.status_code}")
        content_lines.append(f"条目数量: {len(items)}")
        content_lines.append("=" * 50)
        content_lines.append("")
        
        # 处理每个RSS条目
        for i, item in enumerate(items, 1):
            content_lines.append(f"条目 {i}:")
            content_lines.append("-" * 30)
            
            # 提取标题
            title = item.find('title')
            if title is not None and title.text:
                # 清理CDATA标签
                clean_title = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', title.text)
                content_lines.append(f"标题: {clean_title}")
            
            # 提取链接
            link = item.find('link')
            if link is not None and link.text:
                content_lines.append(f"链接: {link.text}")
            
            # 提取发布日期
            pub_date = item.find('pubDate')
            if pub_date is not None and pub_date.text:
                content_lines.append(f"发布时间: {pub_date.text}")
            
            # 提取描述/内容
            description = item.find('description')
            if description is not None and description.text:
                # 清理HTML标签和CDATA
                clean_desc = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', description.text)
                clean_desc = re.sub(r'<[^>]+>', '', clean_desc)  # 移除HTML标签
                clean_desc = clean_desc.strip()
                if clean_desc:
                    content_lines.append(f"描述: {clean_desc[:200]}...")  # 只显示前200个字符
            
            content_lines.append("")
        
        # 将内容写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content_lines))
        
        print(f"RSS内容已成功保存到: {output_file}")
        print("测试完成！")
        
        return True
        
    except requests.exceptions.RequestException as e:
        error_msg = f"网络请求错误: {e}"
        print(error_msg)
        
        # 即使出错也要记录到文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"RSS测试失败 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 50 + "\n")
            f.write(f"RSS链接: {rss_url}\n")
            f.write(f"错误信息: {error_msg}\n")
        
        return False
        
    except ET.ParseError as e:
        error_msg = f"XML解析错误: {e}"
        print(error_msg)
        
        # 记录原始内容以便调试
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"RSS测试失败 - XML解析错误 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 50 + "\n")
            f.write(f"RSS链接: {rss_url}\n")
            f.write(f"错误信息: {error_msg}\n")
            f.write("\n原始响应内容（前1000字符）:\n")
            f.write(response.text[:1000] if 'response' in locals() else "无法获取响应内容")
        
        return False
        
    except Exception as e:
        error_msg = f"未知错误: {e}"
        print(error_msg)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"RSS测试失败 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 50 + "\n")
            f.write(f"RSS链接: {rss_url}\n")
            f.write(f"错误信息: {error_msg}\n")
        
        return False

if __name__ == "__main__":
    print("开始测试RSS订阅...")
    success = test_rss_feed()
    if success:
        print("✅ RSS测试成功完成")
    else:
        print("❌ RSS测试失败")
