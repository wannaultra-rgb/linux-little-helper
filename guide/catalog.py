"""把各分类词条汇总为唯一目录，并做基础一致性校验。"""

from .data_admin import COMMANDS as ADMIN
from .data_core import COMMANDS as CORE
from .data_net import COMMANDS as NET
from .data_search import COMMANDS as SEARCH
from .data_system import COMMANDS as SYSTEM
from .schema import CATEGORY_ORDER

COMMANDS = CORE + SEARCH + NET + SYSTEM + ADMIN
COMMANDS_BY_NAME = {item["name"]: item for item in COMMANDS}
TOTAL_COMMANDS = len(COMMANDS)


def _validate():
    if len(COMMANDS_BY_NAME) != TOTAL_COMMANDS:
        raise ValueError("命令名重复，请检查词条")
    known = set(COMMANDS_BY_NAME)
    for item in COMMANDS:
        if item["category"] not in CATEGORY_ORDER:
            raise ValueError("未知分类: %s" % item["category"])
        for field in ("name", "title", "syntax", "summary", "keywords"):
            if not item[field].strip():
                raise ValueError("%s 缺少字段 %s" % (item["name"], field))
        if not item["examples"]:
            raise ValueError("%s 至少需要一个示例" % item["name"])
        for related in item["related"]:
            if related not in known:
                raise ValueError("%s 引用了不存在的相关命令: %s" % (item["name"], related))


_validate()


def category_counts():
    counts = {category: 0 for category in CATEGORY_ORDER}
    for item in COMMANDS:
        counts[item["category"]] += 1
    return counts


def get_command(name):
    """按命令名或别名取词条。"""
    name = name.strip().lower()
    if name in COMMANDS_BY_NAME:
        return COMMANDS_BY_NAME[name]
    for item in COMMANDS:
        if name in (alias.lower() for alias in item["aliases"]):
            return item
    return None
