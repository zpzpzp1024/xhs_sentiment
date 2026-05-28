# 小红书评论情感分析工具

基于 Python + DrissionPage + OpenAI API 的小红书评论抓取与情感分析工具。

## 功能特性

- ✅ **小红书评论抓取**：自动搜索指定关键词，获取笔记评论（支持主评论和子回复）
- ✅ **情感分析**：调用大模型 API 对评论进行情感倾向分析（正面/中性/负面）
- ✅ **数据导出**：生成 Excel 报告，包含评论明细、统计概览和关键词分析
- ✅ **灵活配置**：支持多种大模型接口（DeepSeek/通义千问/Moonshot 等）
- ✅ **防封禁机制**：随机延迟、模拟真人操作

## 环境要求

- Python 3.10+
- Chrome / Edge 浏览器
- 大模型 API Key（如 DeepSeek、阿里云通义千问等）

## 安装步骤

```bash
# 克隆项目
git clone <项目地址>
cd mypy

# 安装依赖
pip install -r requirements.txt
```

## 配置说明

### 1. 复制并修改配置文件

```bash
cp .env.example .env
```

### 2. 编辑 `.env` 文件

```env
# 大模型 API 配置
LLM_BASE_URL=https://api.deepseek.com/v1  # API 地址
LLM_API_KEY=your-api-key-here             # 你的 API Key
LLM_MODEL=deepseek-chat                   # 模型名称

# 浏览器路径配置（根据实际安装路径修改）
CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe
# 或使用 Edge
# CHROME_PATH=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe
```

### 支持的大模型

| 服务商 | BASE_URL | MODEL |
|--------|----------|-------|
| DeepSeek | https://api.deepseek.com/v1 | deepseek-chat |
| 通义千问 | https://dashscope.aliyuncs.com/compatible-mode/v1 | qwen-turbo |
| Moonshot | https://api.moonshot.cn/v1 | moonshot-v1-8k |

## 使用方法

### 基础用法

```bash
python xhs_sentiment.py --keyword "长安启源Q05" --count 100
```

### 参数说明

| 参数 | 缩写 | 类型 | 默认值 | 说明 |
|------|------|------|--------|------|
| --keyword | -k | str | 必填 | 搜索关键词 |
| --count | -c | int | 100 | 目标评论数量 |

### 执行流程

1. 启动浏览器并打开小红书搜索页面
2. 手动完成登录（如需要）
3. 自动抓取笔记评论
4. 调用大模型进行情感分析
5. 生成 Excel 报告

## 项目结构

```
mypy/
├── xhs_sentiment.py    # 主程序
├── .env                # 配置文件
├── .env.example        # 配置模板
├── requirements.txt    # 依赖列表
└── README.md           # 项目说明
```

## 输出报告

生成的 Excel 文件包含三个部分：

1. **评论明细**：所有抓取的评论及其情感分析结果
2. **统计概览**：正面/中性/负面评论数量及占比
3. **关键词统计**：评论中出现频率最高的关键词

## 注意事项

1. **登录要求**：首次运行需要手动登录小红书账号
2. **API 费用**：情感分析会消耗大模型 API 额度，请留意费用
3. **爬虫合规**：请遵守小红书平台规则，合理控制抓取频率
4. **浏览器版本**：确保浏览器版本与 DrissionPage 兼容

## 常见问题

### Q1: 提示"无法找到浏览器可执行文件"

A: 在 `.env` 文件中配置正确的浏览器路径：
```env
CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe
```

### Q2: 抓取到的评论数量为 0

A: 可能原因：
- 登录状态失效，请重新登录
- 页面结构变化，请检查选择器
- 网络问题，请检查网络连接

### Q3: 情感分析失败

A: 检查 `.env` 中的 API 配置是否正确，确保 API Key 有效。

## License

MIT License
