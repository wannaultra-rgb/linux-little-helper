"""共享数据结构与分类定义。"""

CATEGORY_ORDER = [
    "文件与目录",
    "文本处理",
    "查找与搜索",
    "压缩归档",
    "网络与下载",
    "软件包管理",
    "系统与进程",
    "磁盘与存储",
    "权限与用户",
    "远程与传输",
    "开发与版本",
    "帮助与效率",
]


def C(
    name,
    title,
    category,
    syntax,
    summary,
    keywords,
    examples,
    options=(),
    caution="",
    related=(),
    aliases=(),
    danger="safe",
    options_title="常用参数",
):
    """构造一条命令词条，字段保持纯数据，便于搜索与测试。"""
    if category not in CATEGORY_ORDER:
        raise ValueError("未知分类: %s" % category)
    if danger not in ("safe", "caution", "danger"):
        raise ValueError("未知风险等级: %s" % danger)
    return {
        "name": name,
        "aliases": tuple(aliases),
        "title": title,
        "category": category,
        "syntax": syntax,
        "summary": summary,
        "keywords": keywords,
        "examples": tuple((desc, cmd) for desc, cmd in examples),
        "options": tuple(options),
        "options_title": options_title,
        "caution": caution,
        "related": tuple(related),
        "danger": danger,
    }
