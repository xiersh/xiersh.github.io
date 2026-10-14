#!/usr/bin/env python3
"""Build the site: render Markdown sources (_src/) into static HTML (_site/).

Usage:
    python3 build.py

Requires: markdown-it-py  (pip install markdown-it-py)
"""

import re
import shutil
import sys
from pathlib import Path

try:
    from markdown_it import MarkdownIt
except ImportError:
    sys.exit("Missing dependency. Run: pip install markdown-it-py")

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "_src"
OUT = ROOT / "_site"
TEMPLATE_PATH = ROOT / "assets" / "template.html"
STYLE_PATH = ROOT / "assets" / "style.css"

# ---------------- Site configuration ----------------

SITE_NAME = "Runshuo Xie"

NAV = [
    ("Home", "/"),
    ("Notes", "/notes/")
    ]

# ---------------- Markdown engine ----------------
try:
    MD = MarkdownIt("gfm-like")  # GitHub 风格：表格、删除线等
    MD.disable("linkify", ignoreInvalid=True)  # linkify 需要额外依赖，这里用不到
except ValueError:
    MD = MarkdownIt("commonmark").enable(["table", "strikethrough"])

# 数学公式：行内 $...$、行间 $$...$$，构建时转成 MathML。
# 公式以纯 HTML 形式写进页面，浏览器原生渲染，不需要 JavaScript。
# 转换失败时保留原文，不中断构建。
def _mathml(content, options):
    from latex2mathml.converter import convert
    display = (options.get("display_mode", False)
               if isinstance(options, dict) else bool(options))
    try:
        return convert(content.strip(), display="block" if display else "inline")
    except Exception:
        return content

try:
    from mdit_py_plugins.dollarmath import dollarmath_plugin
    from mdit_py_plugins.footnote import footnote_plugin
    MD.use(dollarmath_plugin, renderer=_mathml)
    MD.use(footnote_plugin)
except ImportError:
    print("注意: 未安装 mdit-py-plugins / latex2mathml，公式和脚注将按原文输出")

FM_RE = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*\n?", re.DOTALL)


def read_source(path: Path):
    """Split a Markdown file into (front matter dict, body)."""
    text = path.read_text(encoding="utf-8")
    meta = {}
    m = FM_RE.match(text)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                key, _, value = line.partition(":")
                meta[key.strip()] = value.strip()
        text = text[m.end():]
    return meta, text


# ---------------- Languages ----------------
# 全站只有一套页面（默认英文）。唯一的例外是 Notes 里的随笔：
#   _src/notes/<slug>/index.md   英文版（可省略）
#   _src/notes/<slug>/zh.md      中文版（可省略）
# 两个文件至少有一个；都有就是双语文章，页面互相链接。

def is_essay_zh(rel: Path) -> bool:
    """True for _src/notes/<slug>/zh.md (the Chinese version of an essay)."""
    return (len(rel.parts) == 3 and rel.parts[0] == "notes"
            and rel.name == "zh.md")


def lang_of(rel: Path) -> str:
    return "zh" if is_essay_zh(rel) else "en"


def dir_url(parts) -> str:
    parts = tuple(p for p in parts if p not in ("", "."))
    return "/" if not parts else "/" + "/".join(parts) + "/"


# ---------------- Essays ----------------

def collect_essays():
    """Scan _src/notes/<slug>/ for index.md (EN) and/or zh.md (ZH)."""
    essays = []
    notes_dir = SRC / "notes"
    if not notes_dir.is_dir():
        return essays
    for d in sorted(notes_dir.iterdir()):
        if not d.is_dir():
            continue
        slug = d.name
        entry = {"slug": slug, "en": None, "zh": None}
        en_file, zh_file = d / "index.md", d / "zh.md"
        if en_file.exists():
            meta, _ = read_source(en_file)
            entry["en"] = {"title": meta.get("title") or slug.replace("-", " "),
                           "date": meta.get("date", "")}
        if zh_file.exists():
            meta, _ = read_source(zh_file)
            entry["zh"] = {"title": meta.get("title") or slug.replace("-", " "),
                           "date": meta.get("date", "")}
        if entry["en"] or entry["zh"]:
            essays.append(entry)

    def sort_key(e):
        dates = [v["date"] for v in (e["en"], e["zh"]) if v and v["date"]]
        return (max(dates) if dates else "", e["slug"])

    essays.sort(key=sort_key, reverse=True)
    return essays


def essays_html(essays):
    """Render the note list for the Notes index page."""
    if not essays:
        return ""
    items = []
    for e in essays:
        en, zh = e["en"], e["zh"]
        if en and zh:
            if en["title"] == zh["title"]:
                title = f'{en["title"]}'
            else:
                title = f'{en["title"]} / {zh["title"]}'
            badge = "EN & 中文"
            url = f'/notes/{e["slug"]}/'
        elif en:
            title, badge = en["title"], "EN"
            url = f'/notes/{e["slug"]}/'
        else:
            title, badge = zh["title"], "中文"
            url = f'/notes/{e["slug"]}/zh/'
        date = ""
        for v in (en, zh):
            if v and v["date"]:
                date = v["date"]
                break
        date_html = f'<span class="date">{date}</span>' if date else ""
        items.append(f'<li><a href="{url}">{title}</a>'
                     f'<span class="badge">{badge}</span>{date_html}</li>')
    return ('<section class="essay-list">\n<h2>All notes</h2>\n<ul>\n'
            + "\n".join(items) + '\n</ul>\n</section>')


def langswitch_html(rel: Path, essays_by_slug) -> str:
    """Per-essay language cross-link, only when the other version exists."""
    parts = rel.parts
    if len(parts) == 3 and parts[0] == "notes":
        slug = parts[1]
        e = essays_by_slug.get(slug)
        if not e:
            return ""
        if rel.name == "index.md" and e["zh"]:
            return (f'<span class="lang-switch">'
                    f'<a href="/notes/{slug}/zh/">中文</a></span>')
        if rel.name == "zh.md" and e["en"]:
            return (f'<span class="lang-switch">'
                    f'<a href="/notes/{slug}/">English</a></span>')
    return ""


# ---------------- Page rendering ----------------

def nav_html(current: str) -> str:
    items = []
    for label, href in NAV:
        active = ' class="active"' if href == current else ""
        items.append(f'<li{active}><a href="{href}">{label}</a></li>')
    return "<ul>" + "".join(items) + "</ul>"


def build():
    if not SRC.is_dir():
        sys.exit(f"Source directory not found: {SRC}")

    files = sorted(p.relative_to(SRC) for p in SRC.rglob("*.md"))
    essays = collect_essays()
    essays_by_slug = {e["slug"]: e for e in essays}

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    for rel in files:
        meta, body = read_source(SRC / rel)
        lang = lang_of(rel)
        url = dir_url(rel.parent.parts)
        content = MD.render(body)
        content = add_heading_ids(content)
        # Notes 列表页：追加自动生成的文章清单
        if rel.name == "index.md" and rel.parent == Path("notes"):
            content += "\n" + essays_html(essays)
        page = (template
                .replace("{{lang}}", lang)
                .replace("{{title}}", meta.get("title", SITE_NAME))
                .replace("{{sitename}}", SITE_NAME)
                .replace("{{nav}}", nav_html(url))
                .replace("{{langswitch}}", langswitch_html(rel, essays_by_slug))
                .replace("{{content}}", content))
        # 中文版随笔输出到 /notes/<slug>/zh/
        if is_essay_zh(rel):
            out_path = OUT / rel.parent / "zh" / "index.html"
        else:
            out_path = OUT / rel.with_suffix(".html")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(page, encoding="utf-8")

    assets_out = OUT / "assets"
    assets_out.mkdir(exist_ok=True)
    shutil.copy2(STYLE_PATH, assets_out / "style.css")

    print(f"Built {len(files)} page(s) -> {OUT}")


# ---------------- Heading anchors ----------------
# 给所有标题自动添加 id（GitHub 风格），使任意小节都可以被链接：
#   ## OOPSLA'26  ->  <h2 id="oopsla26">
# 规则：取标题文字，转小写、去掉标点、空格变连字符；中文保留；
# 重复标题自动加 -1、-2 后缀。

def slugify(text):
    import html as html_module
    text = html_module.unescape(text)          # &amp; 等实体转回字符
    text = re.sub(r"<[^>]+>", "", text)        # 去掉内部标签（链接、公式等）
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)       # 去掉标点（保留文字/数字/空格/连字符）
    text = re.sub(r"\s+", "-", text)
    return text


def add_heading_ids(html_text):
    used = {}

    def repl(m):
        level, inner = m.group(1), m.group(2)
        slug = slugify(inner) or "section"
        count = used.get(slug, 0)
        used[slug] = count + 1
        if count:
            slug = f"{slug}-{count}"
        return f'<h{level} id="{slug}">{inner}</h{level}>'

    return re.sub(r"<h([1-6])>(.*?)</h\1>", repl, html_text, flags=re.S)


# ---------------- Watch mode ----------------
# python3 build.py --watch : 编译一次后监视 _src/ 和 assets/ 的变化，
# 有改动即自动重新编译（轮询方式，纯标准库，无需额外依赖）。

def snapshot():
    """All source file paths with their mtimes (_src/ and assets/)."""
    stamps = {}
    for base in (SRC, ROOT / "assets"):
        for p in base.rglob("*"):
            if p.is_file():
                stamps[p] = p.stat().st_mtime
    return stamps


def watch(interval=0.6):
    import time
    last = None
    try:
        while True:
            snap = snapshot()
            if snap != last:
                build()
                print(f"  [watch] {time.strftime('%H:%M:%S')} 已自动重新编译，"
                      f"刷新浏览器(Cmd+R)即可查看")
                last = snap
            time.sleep(interval)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    if "--watch" in sys.argv:
        watch()
    else:
        build()
