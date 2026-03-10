# Novel Writer Skill

小说创作助手，支持人物设定、世界观管理、大纲控制和 AI 章节生成。

## 环境配置

```bash
# 必填
export NOVEL_API_KEY="your-api-key"
export NOVEL_API_BASE_URL="https://your-api.com/v1"

# 可选
export NOVEL_MODEL="gpt-3.5-turbo"
export NOVEL_TEMPERATURE="0.8"
export NOVEL_DEFAULT_STYLE="wuxia"
```

## 使用方法

```bash
# 创建新小说
python core.py --new "我的奇幻世界"

# 设定人物
python core.py --novel-title "我的奇幻世界" --set-character "林风" "主角，25岁，剑客"

# 设定世界观
python core.py --novel-title "我的奇幻世界" --set-world "一个充满魔法的大陆"

# 添加大纲
python core.py --novel-title "我的奇幻世界" --add-outline 1 "初遇" "林风在森林中救下受伤的少女"

# 生成章节
python core.py --novel-title "我的奇幻世界" --generate 1 2300

# 查看进度
python core.py --novel-title "我的奇幻世界" --status
```

## CLI 选项

| 参数 | 说明 |
|------|------|
| `--new` | 创建新小说项目 |
| `--novel-title` | 指定小说名称（已有项目） |
| `--set-character` | 设定人物 |
| `--set-world` | 设定世界观 |
| `--set-style` | 设定写作风格 |
| `--add-outline` | 添加大纲 |
| `--generate` | 生成章节 |
| `--status` | 查看进度 |

## 项目结构

```
novel_writer/
├── core.py              # 核心逻辑 + CLI
├── config.json          # 配置（使用环境变量）
├── SKILL.md             # 详细文档
└── templates/           # 创作模板
```

## License

MIT