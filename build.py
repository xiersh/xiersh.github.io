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
# 网站统计代码（Statcounter 等）：存在即注入到每个页面的 </body> 前，
# 想在全站启用/更换统计代码只需编辑这一个文件，无需改动任何文章。
ANALYTICS_PATH = ROOT / "snippets" / "analytics.html"

# ---------------- Site configuration ----------------

SITE_NAME = "Runshuo Xie"

NAV = [
    ("Home", "/"),
    ("Notes", "/notes/"),
    ("Stories", "/stories/")
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
                value = value.strip()
                # 去掉 YAML 风格的成对引号（title: "..." / '...'）
                if (len(value) >= 2 and value[0] == value[-1]
                        and value[0] in ("'", '"')):
                    value = value[1:-1]
                meta[key.strip()] = value
        text = text[m.end():]
    return meta, text


# ---------------- Languages ----------------
# 全站只有一套页面（默认英文）。例外是多语言文章栏目（随笔 notes、论文故事 stories）：
#   _src/<栏目>/<slug>/index.md   英文版（可省略）
#   _src/<栏目>/<slug>/zh.md      中文版（可省略）
# 两个文件至少有一个；都有就是双语文章，页面互相链接。

COLLECTIONS = {"notes": "All notes", "stories": "All stories"}


def is_essay_zh(rel: Path) -> bool:
    """True for _src/<collection>/<slug>/zh.md (the Chinese version)."""
    return (len(rel.parts) == 3 and rel.parts[0] in COLLECTIONS
            and rel.name == "zh.md")


def lang_of(rel: Path) -> str:
    return "zh" if is_essay_zh(rel) else "en"


def dir_url(parts) -> str:
    parts = tuple(p for p in parts if p not in ("", "."))
    return "/" if not parts else "/" + "/".join(parts) + "/"


# ---------------- Essays ----------------

def collect_essays(collection):
    """Scan _src/<collection>/<slug>/ for index.md (EN) and/or zh.md (ZH)."""
    essays = []
    coll_dir = SRC / collection
    if not coll_dir.is_dir():
        return essays
    for d in sorted(coll_dir.iterdir()):
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


def essays_html(essays, collection, heading):
    """Render the entry list for a collection's index page."""
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
            url = f'/{collection}/{e["slug"]}/'
        elif en:
            title, badge = en["title"], "EN"
            url = f'/{collection}/{e["slug"]}/'
        else:
            title, badge = zh["title"], "中文"
            url = f'/{collection}/{e["slug"]}/zh/'
        date = ""
        for v in (en, zh):
            if v and v["date"]:
                date = v["date"]
                break
        date_html = f'<span class="date">{date}</span>' if date else ""
        items.append(f'<li><a href="{url}">{title}</a>'
                     f'<span class="badge">{badge}</span>{date_html}</li>')
    return ('<section class="essay-list">\n<h2>' + heading + '</h2>\n<ul>\n'
            + "\n".join(items) + '\n</ul>\n</section>')


def langswitch_html(rel: Path, essays_by_slug) -> str:
    """Per-essay language cross-link, only when the other version exists."""
    parts = rel.parts
    if len(parts) == 3 and parts[0] in COLLECTIONS:
        collection, slug = parts[0], parts[1]
        e = essays_by_slug.get((collection, slug))
        if not e:
            return ""
        if rel.name == "index.md" and e["zh"]:
            return (f'<span class="lang-switch">'
                    f'<a href="/{collection}/{slug}/zh/">中文</a></span>')
        if rel.name == "zh.md" and e["en"]:
            return (f'<span class="lang-switch">'
                    f'<a href="/{collection}/{slug}/">English</a></span>')
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
    essays_by_collection = {c: collect_essays(c) for c in COLLECTIONS}
    essays_by_slug = {(c, e["slug"]): e
                      for c, lst in essays_by_collection.items() for e in lst}

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    # 统计代码存在时，注入到每个页面 </body> 前（文件不存在则全站不注入）
    analytics = ""
    if ANALYTICS_PATH.is_file():
        analytics = ANALYTICS_PATH.read_text(encoding="utf-8").strip()

    for rel in files:
        meta, body = read_source(SRC / rel)
        lang = lang_of(rel)
        url = dir_url(rel.parent.parts)
        content = MD.render(body)
        content = add_heading_ids(content)
        # 文章目录：单篇文章页在标题后自动插入二级标题目录
        if len(rel.parts) == 3 and rel.parts[0] in COLLECTIONS:
            toc = toc_html(extract_toc(content), lang)
            if toc:
                content = inject_toc(content, toc)
        # 栏目列表页：追加自动生成的文章清单
        if rel.name == "index.md" and rel.parent.name in COLLECTIONS:
            coll = rel.parent.name
            content += "\n" + essays_html(essays_by_collection[coll],
                                          coll, COLLECTIONS[coll])
        page = (template
                .replace("{{lang}}", lang)
                .replace("{{title}}", meta.get("title", SITE_NAME))
                .replace("{{sitename}}", SITE_NAME)
                .replace("{{nav}}", nav_html(url))
                .replace("{{langswitch}}", langswitch_html(rel, essays_by_slug))
                .replace("{{content}}", content))
        if analytics:
            page = page.replace("</body>", analytics + "\n</body>")
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


# ---------------- 文章目录 ----------------
# 文章页（notes/stories 下的单篇文章）在构建时自动提取所有二级标题生成目录，
# 插在正文标题（h1）下方，纯静态、零 JavaScript、无需手写维护。
# 只有二级标题数 >= 3 时才生成目录，避免给短文章增加噪音。

MIN_TOC_ITEMS = 3


def extract_toc(html_text, min_items=MIN_TOC_ITEMS):
    import html as html_module
    items = []
    for m in re.finditer(r'<h2 id="([^"]+)">(.*?)</h2>', html_text, flags=re.S):
        anchor, inner = m.group(1), m.group(2)
        title = html_module.unescape(re.sub(r"<[^>]+>", "", inner)).strip()
        if title:
            items.append((anchor, title))
    return items if len(items) >= min_items else []


def toc_html(items, lang):
    if not items:
        return ""
    label = "目录" if lang == "zh" else "Contents"
    lis = "\n".join(f'<li><a href="#{a}">{t}</a></li>' for a, t in items)
    return (f'<nav class="toc">\n<p class="toc-title">{label}</p>\n'
            f'<ul>\n{lis}\n</ul>\n</nav>')


def inject_toc(html_text, toc):
    """把目录插到正文标题（h1）之后；文章没有 h1 时保持原样。"""
    return re.sub(r"(<h1[^>]*>.*?</h1>)", r"\1\n" + toc, html_text,
                  count=1, flags=re.S)


# ---------------- Watch mode ----------------
# python3 build.py --watch : 编译一次后监视 _src/ 和 assets/ 的变化，
# 有改动即自动重新编译（轮询方式，纯标准库，无需额外依赖）。

def snapshot():
    """All source file paths with their mtimes (_src/, assets/, build.py)."""
    stamps = {}
    for base in (SRC, ROOT / "assets"):
        for p in base.rglob("*"):
            if p.is_file():
                stamps[p] = p.stat().st_mtime
    build_file = Path(__file__).resolve()
    stamps[build_file] = build_file.stat().st_mtime
    return stamps


def watch(interval=0.6):
    import time
    build_file = Path(__file__).resolve()
    last = None
    try:
        while True:
            snap = snapshot()
            if snap != last:
                # build.py 本身有更新：重启本进程加载新代码，
                # 之后 Leo 再也不用手动重启预览来让功能改动生效。
                if last is not None and snap.get(build_file) != last.get(build_file):
                    print("  [watch] build.py 有更新，正在自动重启编译进程...")
                    import os
                    os.execv(sys.executable,
                             [sys.executable, str(build_file), "--watch"])
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
