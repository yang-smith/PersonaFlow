SYSTEM_PROMPT = """
你是一个真诚的人。
你对第一性原理，多维度思考，批判性思考，逆向思维，系统理论、行为心理学、群体心理学、传播学、经济学、认知论、演化心理学、生物学、进化论、道家等领域都有深刻的见解。
你同时是专业的开发者。曾经是自动化、机器学习学习专业的学生。
同时也是一个投资者，对查理芒格理论、长期主义有着深刻的理解。
你尊重事实，实事求是。

你对讲故事、人文、可能有启发的文章也感兴趣。

雷点：
1. 你讨厌夸大、煽情、不实信息和隐藏的商业广告（中间插入部分广告可以理解）。
2. 你讨厌逻辑混乱、概念模糊的文章。
3. 你讨厌煽动情绪、制造焦虑、利用人性弱点的“快餐内容”。
"""

BASE_PROMPT = """
阅读内容，然后：
1.  **打分**：给内容打一个 0.0 到 10.0 的分数。
2.  **给出理由**：用一句话简明扼要地解释你打这个分数的核心原因。

**评分标准参考：**
*   **9.0-10.0**: 杰作。
*   **6.0-8.9**: 优秀。
*   **4.0-5.9**: 普通。
*   **0.0-3.9**: 劣质。


内容：{content}

**输出格式：**
你必须严格地、只返回一个JSON对象，不包含任何其他解释性文字。格式如下：
{{
  "score": <你的评分>,
  "rationale": "<你的一句话理由>",
  "summary": "<该文章的摘要（最多五句话）>"
}}
"""

GEN_HTML_PROMPT = """
帮我将下面内容重新排版，保留原文的结构和内容，使用html和内联css让其美观。

要求：
遵循专注、沉浸式阅读的风格。
直接输出HTML主体<body>部分，不要包含<html>和<head>标签。


### 1. Typography (字体排印)
- **Base Font:**
  - `font-family`: Use a system-native, highly readable sans-serif font stack. For example: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen-Sans, Ubuntu, Cantarell, "Helvetica Neue", sans-serif`
  - `font-size`: `17px` for the main body text (`<p>`). All other font sizes should be relative to this baseline.
  - `line-height`: `1.7` for body text. This is crucial for readability.
- **Headings:**
  - `<h1>`: `font-size: 1.8em; font-weight: 600;` (approx 30px)
  - `<h2>`: `font-size: 1.5em; font-weight: 600;` (approx 25px)
  - `<h3>`: `font-size: 1.2em; font-weight: 600;` (approx 20px)
- **Links `<a>`:**
  - Do not change the font style. Just apply the link color.
  - `text-decoration: underline; text-decoration-thickness: 1px; text-underline-offset: 3px;`

### 2. Colors (色彩)
- **Text:** `#222222` (A deep, soft black)
- **Links:** `#005FB8` (A calm, professional blue)
- **Secondary Text (e.g., captions, timestamps):** `#666666` (A gentle gray)

### 3. Spacing (间距)
- **Paragraphs `<p>`:** `margin-bottom: 1.2em;`
- **Headings `<h1>, <h2>, <h3>`:** `margin-top: 2em; margin-bottom: 0.8em;` (Ensure more space above a heading than below it)
- **Lists `<ul>, <ol>`:** `padding-left: 1.5em;`
- **Blockquotes `<blockquote>`:** `margin-left: 1em; padding-left: 1.5em;`

### 4. Special Elements (特殊元素)
- **Images `<img>`:**
  - `max-width: 100%; height: auto; display: block;`
  - `margin-top: 2em; margin-bottom: 2em;`
  - `border-radius: 8px;` (Soft rounded corners)
- **Blockquotes `<blockquote>`:**
  - `border-left: 3px solid #EAEAEA;` (A subtle left border)
  - Apply the `Secondary Text` color to the text inside.
- **Code Blocks `<pre>`:**
  - `background-color: #F5F5F5;`
  - `padding: 1em;`
  - `border-radius: 6px;`
  - `font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;`
  - `font-size: 0.9em;`
  - `white-space: pre-wrap; word-wrap: break-word;` (Ensure code wraps and doesn't break the layout)
- **Horizontal Rules `<hr>`:**
  - `border: none; border-top: 1px solid #EAEAEA; margin: 2.5em 0;`


  
待重新排版的内容：
{content}



"""