#!/usr/bin/env python3
"""
novel_writer 技能核心逻辑 (增强版 v2.0)
功能：辅助用户创作长篇小说，支持真实 LLM API 调用、记忆管理、大纲控制
优化点：
- 字数控制：严格 2200-2500 字/章
- 逻辑自检：伏笔、人物状态、战力、时间线
- 风格统一：起点风格、第一人称、爽点密集
"""

import os
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

WORK_DIR = Path(os.environ.get("WORKDIR", Path(__file__).parent.parent / "working"))
NOVELS_DIR = WORK_DIR / "novels"
SKILL_DIR = Path(__file__).parent
CONFIG_FILE = SKILL_DIR / "config.json"

NOVELS_DIR.mkdir(parents=True, exist_ok=True)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: openai library not installed. Run: pip install openai")


def load_api_config() -> dict:
    """从环境变量加载 API 配置，fallback 到 config.json"""
    config = {
        "api": {
            "provider": os.environ.get("NOVEL_API_PROVIDER", "openai"),
            "base_url": os.environ.get("NOVEL_API_BASE_URL", ""),
            "api_key": os.environ.get("NOVEL_API_KEY", ""),
            "model": os.environ.get("NOVEL_MODEL", "gpt-3.5-turbo"),
            "temperature": float(os.environ.get("NOVEL_TEMPERATURE", "0.8")),
            "max_tokens": int(os.environ.get("NOVEL_MAX_TOKENS", "4096"))
        },
        "project": {
            "default_style": os.environ.get("NOVEL_DEFAULT_STYLE", "wuxia"),
            "auto_save": os.environ.get("NOVEL_AUTO_SAVE", "true").lower() == "true"
        }
    }

    if not config["api"]["api_key"] and CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            saved = json.load(f)
            if "api" in saved:
                config["api"].update(saved["api"])
            if "project" in saved:
                config["project"].update(saved["project"])

    return config


class NovelWriter:
    def __init__(self, novel_title: str = "未命名小说", config_path: Optional[Path] = None):
        self.novel_title = novel_title
        self.config_path = config_path or CONFIG_FILE
        self.config = self._load_config()
        self.project_dir = NOVELS_DIR / novel_title
        self.context = self._load_context()
        self._init_project_dir()

        if OPENAI_AVAILABLE and self.config["api"]["api_key"]:
            self.client = OpenAI(
                base_url=self.config["api"]["base_url"],
                api_key=self.config["api"]["api_key"]
            )
        else:
            self.client = None
            if not self.config["api"]["api_key"]:
                print("Error: NOVEL_API_KEY not set. Please configure your API key.")

    def _load_config(self) -> dict:
        """加载 API 配置（环境变量优先）"""
        return load_api_config()

    def _load_context(self) -> dict:
        """加载记忆上下文"""
        context_file = self.project_dir / "meta" / "context.json"
        if context_file.exists():
            with open(context_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "novel_title": self.novel_title,
            "characters": {},
            "world": "",
            "outline": [],
            "chapters": [],
            "style": self.config.get("project", {}).get("default_style", "default")
        }

    def _save_context(self):
        """保存记忆上下文"""
        context_file = self.project_dir / "meta" / "context.json"
        context_file.parent.mkdir(parents=True, exist_ok=True)
        with open(context_file, 'w', encoding='utf-8') as f:
            json.dump(self.context, f, ensure_ascii=False, indent=2)

    def _init_project_dir(self):
        """初始化项目目录结构"""
        dirs = ["characters", "world", "outline", "chapters", "meta"]
        for d in dirs:
            (self.project_dir / d).mkdir(parents=True, exist_ok=True)

        config_file = self.project_dir / "config.json"
        if not config_file.exists():
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "title": self.novel_title,
                    "style": self.context["style"],
                    "created_at": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)

    def set_character(self, name: str, profile: str):
        """添加/更新人物设定"""
        self.context["characters"][name] = profile
        self._save_context()

        char_file = self.project_dir / "characters" / f"{name}.md"
        with open(char_file, 'w', encoding='utf-8') as f:
            f.write(f"# {name}\n\n{profile}\n\n*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

        return f"人物 '{name}' 设定已保存."

    def set_world(self, setting: str):
        """设置世界观"""
        self.context["world"] = setting
        self._save_context()

        world_file = self.project_dir / "world" / "main.md"
        with open(world_file, 'w', encoding='utf-8') as f:
            f.write(f"# 世界观设定\n\n{setting}\n\n*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

        return f"世界观设定已保存."

    def add_outline(self, chapter_num: int, title: str, summary: str):
        """添加大纲节点"""
        node = {
            "chapter": chapter_num,
            "title": title,
            "summary": summary,
            "status": "planned"
        }

        found = False
        for i, item in enumerate(self.context["outline"]):
            if item["chapter"] == chapter_num:
                self.context["outline"][i] = node
                found = True
                break

        if not found:
            self.context["outline"].append(node)

        self.context["outline"].sort(key=lambda x: x["chapter"])
        self._save_context()

        outline_file = self.project_dir / "outline" / f"ch{chapter_num:03d}_{title.replace(' ', '_')}.md"
        with open(outline_file, 'w', encoding='utf-8') as f:
            f.write(f"# 第 {chapter_num} 章：{title}\n\n**摘要**: {summary}\n\n**状态**: 规划中\n")

        return f"第 {chapter_num} 章大纲已更新: {title}"

    def generate_chapter(self, chapter_num: int, target_words: int = 2300) -> str:
        """生成指定章节"""
        if not self.client:
            return "Error: LLM client not initialized. Please check NOVEL_API_KEY."

        prev_summary = ""
        if chapter_num > 1:
            for chapter in reversed(self.context["chapters"]):
                if chapter["chapter"] == chapter_num - 1:
                    prev_summary = chapter["summary"]
                    break

        current_outline = next((o for o in self.context["outline"] if o["chapter"] == chapter_num), None)
        outline_text = current_outline["summary"] if current_outline else "无大纲"
        chapter_title = current_outline["title"] if current_outline else f"第 {chapter_num} 章"

        system_prompt = f"""你是一位专业的起点中文网小说家，擅长创作{self.context['style']}风格的长篇小说。
请根据以下设定和大纲，创作小说《{self.novel_title}》的第 {chapter_num} 章。

【核心设定】
- 人物：{json.dumps(self.context['characters'], ensure_ascii=False)}
- 世界观：{self.context['world']}
- 风格：{self.context['style']}

【剧情上下文】
- 上一章摘要：{prev_summary}
- 本章大纲：{outline_text}

【严格要求】
1. 字数控制：正文必须严格控制在 2200-2500 字（中文）。
2. 逻辑闭环：伏笔必须回收，人物状态一致，战力逻辑合理。
3. 细节描写：心理独白、环境渲染、动作细节、配角反应。
4. 爽点密度：每章至少包含1个小爽点。
5. 第一人称：严格保持我的视角。
6. 作者说：章节末尾必须添加作者说。
7. 输出格式：纯文本。
8. 章节标题：{chapter_title}。

请开始创作。"""

        user_prompt = f"请开始创作第 {chapter_num} 章，标题为：{chapter_title}。"

        try:
            response = self.client.chat.completions.create(
                model=self.config["api"]["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.config["api"]["temperature"],
                max_tokens=self.config["api"]["max_tokens"]
            )
            content = response.choices[0].message.content.strip()

            word_count = len(content)
            if word_count < 2200:
                print(f"Warning: Chapter {chapter_num} word count ({word_count}) is below 2200")

            chapter_file = self.project_dir / "chapters" / f"ch{chapter_num:03d}_{chapter_title.replace(' ', '_')}.md"
            with open(chapter_file, 'w', encoding='utf-8') as f:
                f.write(f"# {chapter_title}\n\n{content}")

            chapter_data = {
                "chapter": chapter_num,
                "title": chapter_title,
                "content": content,
                "summary": content[:200] + "..." if len(content) > 200 else content,
                "timestamp": datetime.now().isoformat(),
                "word_count": len(content)
            }
            self.context["chapters"].append(chapter_data)

            if current_outline:
                current_outline["status"] = "done"
            self._save_context()

            return f"Chapter {chapter_num} saved to {chapter_file.name}\nWord count: {len(content)}"

        except Exception as e:
            return f"Generation failed: {str(e)}"

    def get_status(self) -> str:
        """获取创作进度"""
        lines = [
            f"Novel: {self.novel_title}",
            f"Characters: {len(self.context['characters'])}",
            f"Outline: {len(self.context['outline'])} chapters",
            f"Written: {len(self.context['chapters'])} chapters",
            "\nOutline preview:"
        ]

        for item in self.context["outline"][:5]:
            status_icon = "[OK]" if item["status"] == "done" else "[...]" if item["status"] == "writing" else "[--]"
            lines.append(f" {status_icon} Chapter {item['chapter']}: {item['title']}")

        return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Novel Writer - Novel Writing Assistant")
    parser.add_argument("--new", metavar="TITLE", help="Create new novel project")
    parser.add_argument("--set-character", nargs=2, metavar=("NAME", "PROFILE"), help="Set character")
    parser.add_argument("--set-world", metavar="SETTING", help="Set world setting")
    parser.add_argument("--set-style", metavar="STYLE", help="Set writing style")
    parser.add_argument("--add-outline", nargs=3, metavar=("NUM", "TITLE", "SUMMARY"), help="Add outline (chapter_num title summary)")
    parser.add_argument("--generate", nargs=2, type=int, metavar=("NUM", "WORDS"), help="Generate chapter (chapter_num target_words)")
    parser.add_argument("--status", action="store_true", help="Show writing progress")
    parser.add_argument("--update-outline", nargs=3, metavar=("NUM", "TITLE", "SUMMARY"), help="Update outline")
    parser.add_argument("--novel-title", metavar="TITLE", default="未命名小说", help="Novel title (for existing projects)")

    args = parser.parse_args()

    novel = NovelWriter(args.novel_title)

    if args.new:
        novel = NovelWriter(args.new)
        print(f"Novel project '{args.new}' created")
    elif args.set_character:
        name, profile = args.set_character
        print(novel.set_character(name, profile))
    elif args.set_world:
        print(novel.set_world(args.set_world))
    elif args.set_style:
        novel.context["style"] = args.set_style
        novel._save_context()
        print(f"Writing style set to: {args.set_style}")
    elif args.add_outline:
        num, title, summary = args.add_outline
        print(novel.add_outline(int(num), title, summary))
    elif args.generate:
        num, words = args.generate
        print(novel.generate_chapter(num, words))
    elif args.status:
        print(novel.get_status())
    elif args.update_outline:
        num, title, summary = args.update_outline
        print(novel.add_outline(int(num), title, summary))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()