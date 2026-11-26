"""中文 ↔ 指令的双向检索与排序。"""

import re
import unicodedata

from .catalog import COMMANDS

_ALL = "全部"

# 用户常把问题整句输入，这些词不参与命令匹配。
_INTENT_WORDS = (
    "请问",
    "帮我",
    "帮忙",
    "我想",
    "我要",
    "一个",
    "怎么用",
    "如何使用",
    "怎么",
    "如何",
    "怎样",
    "是什么",
    "是啥",
    "什么意思",
    "有什么用",
    "的用法",
    "用法",
    "一下",
    "命令",
    "指令",
)

# 中文需求常以“动词 + 对象”出现。动作不是硬条件时只参与加权，
# 避免“查看端口”因为“查看”而召回所有带“查看”的命令。
_ACTION_GROUPS = (
    ("删除", "删除", True),
    ("移除", "删除", True),
    ("删掉", "删除", True),
    ("删", "删除", True),
    ("修改", "修改", True),
    ("更改", "修改", True),
    ("改", "修改", True),
    ("安装", "安装", True),
    ("卸载", "卸载", True),
    ("压缩", "压缩", True),
    ("打包", "压缩", True),
    ("解压", "解压", True),
    ("解包", "解压", True),
    ("下载", "下载", True),
    ("上传", "上传", True),
    ("复制", "复制", True),
    ("拷贝", "复制", True),
    ("移动", "移动", True),
    ("重命名", "重命名", True),
    ("创建", "创建", True),
    ("新建", "创建", True),
    ("启动", "启动", True),
    ("停止", "停止", True),
    ("重启", "重启", True),
    ("挂载", "挂载", True),
    ("格式化", "格式化", True),
    ("替换", "替换", True),
    ("运行", "运行", True),
    ("执行", "运行", True),
    ("登录", "登录", True),
    ("连接", "连接", True),
    ("同步", "同步", True),
    ("备份", "备份", True),
    ("排序", "排序", True),
    ("查看", "查看", False),
    ("显示", "查看", False),
    ("列出", "查看", False),
    ("查找", "查找", False),
    ("搜索", "查找", False),
    ("找", "查找", False),
    ("看", "查看", False),
    ("筛选", "筛选", False),
    ("过滤", "筛选", False),
    ("统计", "统计", False),
    ("比较", "比较", False),
)
_ACTIONS = sorted(_ACTION_GROUPS, key=lambda row: len(row[0]), reverse=True)
_GENERIC_OBJECTS = {"文件", "目录", "文件夹", "东西"}

_ASCII_TOKEN = re.compile(r"^[a-z0-9][a-z0-9._+\-]*$")


def normalize(text):
    """统一全角字符、大小写和多余空白，保持命令中的符号。"""
    text = unicodedata.normalize("NFKC", text or "")
    text = text.lower()
    text = re.sub(r"[？?！!。，,、；;：:]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def strip_intent(text):
    """去掉“如何 / 是什么 / 命令”等提问词，但不把查询清空。"""
    cleaned = text
    for word in _INTENT_WORDS:
        cleaned = cleaned.replace(word, " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or text


def _contains(haystack, needle):
    if not haystack or not needle:
        return False
    if _ASCII_TOKEN.match(needle):
        index = haystack.find(needle)
        while index != -1:
            if index == 0 or not re.match(r"[a-z0-9_-]", haystack[index - 1]):
                return True
            index = haystack.find(needle, index + 1)
        return False
    return needle in haystack


def _field_score(item, token):
    """一个词在一条命令上的最佳字段分。字段越靠前，权重越高。"""
    scores = []
    name = item["name"].lower()
    aliases = [alias.lower() for alias in item["aliases"]]
    title = item["title"].lower()
    keywords = item["keywords"].lower()
    summary = item["summary"].lower()

    if token == name:
        scores.append(140)
    elif _contains(name, token):
        scores.append(85 if name.startswith(token) else 70)

    for alias in aliases:
        if token == alias:
            scores.append(130)
        elif _contains(alias, token):
            scores.append(75)

    if token == title:
        scores.append(75)
    elif _contains(title, token):
        scores.append(62)

    keyword_list = [word for word in re.split(r"\s+", keywords) if word]
    for word in keyword_list:
        if token == word:
            scores.append(55)
            break
        if len(word) >= 2 and len(token) >= 2 and _contains(token, word):
            scores.append(38)
            break
        if _contains(word, token):
            scores.append(34)
            break
    else:
        if _contains(keywords, token):
            scores.append(26)

    if _contains(summary, token):
        scores.append(24)
    if _contains(item["syntax"].lower(), token):
        scores.append(14)
    if _contains(" ".join(cmd for _, cmd in item["examples"]).lower(), token):
        scores.append(11)
    if _contains(" ".join(f"{flag} {desc}" for flag, desc in item["options"]).lower(), token):
        scores.append(9)
    return max(scores) if scores else 0


def _phrase_bonus(item, phrase):
    if not phrase or " " in phrase:
        return 0
    title = item["title"].lower()
    keywords = item["keywords"].lower()
    summary = item["summary"].lower()
    bonus = 0
    if phrase == item["name"].lower() or phrase in (a.lower() for a in item["aliases"]):
        bonus += 120
    if _contains(title, phrase):
        bonus += 55
    if _contains(keywords, phrase):
        bonus += 24
    if _contains(summary, phrase):
        bonus += 12
    return bonus


def _match_action(raw):
    for word, canonical, strong in _ACTIONS:
        if raw.startswith(word):
            return word, canonical, strong, raw[len(word):]
    return None


def _segment_query(text):
    """把“查看端口 / 改权限 / 下载文件”拆成对象、硬动作和软动作。"""
    original_tokens = [token for token in text.split(" ") if token]
    objects = []
    hard_actions = []
    soft_actions = []

    def add_unique(target, value):
        if value and value not in target:
            target.append(value)

    for raw in original_tokens:
        strong = False
        match = _match_action(raw)
        if match:
            word, canonical, strong, remainder = match
            if strong:
                add_unique(hard_actions, canonical)
            else:
                add_unique(soft_actions, canonical)
            if not remainder:
                continue
            raw = remainder

        if strong and raw in _GENERIC_OBJECTS:
            add_unique(soft_actions, raw)
        else:
            add_unique(objects, raw)

    if not objects:
        fallback = hard_actions or soft_actions or original_tokens
        objects = list(fallback)
        hard_actions = []
        soft_actions = [term for term in soft_actions if term not in objects]

    return objects, hard_actions, soft_actions


def search_commands(query="", category=_ALL):
    """返回按相关度排序的命令列表；category 为“全部”时不过滤。"""
    pool = COMMANDS if category == _ALL else [c for c in COMMANDS if c["category"] == category]
    text = normalize(query)
    if not text:
        return list(pool)

    searchable = strip_intent(text)
    objects, hard_actions, soft_actions = _segment_query(searchable)
    required_terms = objects + hard_actions
    if not required_terms:
        return list(pool)

    ranked = []
    for index, item in enumerate(pool):
        total = 0
        matched_all = True
        for term in required_terms:
            score = _field_score(item, term)
            if score == 0:
                matched_all = False
                break
            total += score
        if not matched_all:
            continue
        for term in soft_actions:
            total += min(26, _field_score(item, term)) // 2
        total += _phrase_bonus(item, searchable)
        ranked.append((-total, index, item))
    ranked.sort(key=lambda row: (row[0], row[1]))
    return [item for _, _, item in ranked]


def search_with_terms(query):
    """供界面显示当前实际检索词，空查询返回空串。"""
    return strip_intent(normalize(query))
