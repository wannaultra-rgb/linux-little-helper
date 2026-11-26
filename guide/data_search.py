"""查找与压缩归档类命令。"""

from .schema import C

COMMANDS = [
    # ---------------- 查找与搜索 ----------------
    C(
        "find", "按条件查找文件", "查找与搜索",
        "find [路径] [条件] [动作]",
        "find 会实时遍历目录，按名字、类型、大小、时间、权限等条件找文件，还能直接对结果执行删除或执行命令。它是 Linux 里最通用的文件查找工具。",
        "查找 文件 搜索 目录 按名字 大小 时间 类型 删除",
        [
            ("按文件名查找", "find . -name '*.log'"),
            ("查找最近一天修改过的文件", "find /var/log -type f -mtime -1"),
            ("查找大于 100MB 的文件", "find . -type f -size +100M"),
            ("找出空目录", "find . -type d -empty"),
        ],
        [("-name 模式", "按文件名匹配，支持通配符"), ("-type f/d", "只找文件（f）或目录（d）"), ("-size +100M", "按大小过滤"), ("-mtime -1", "最近 1 天内修改过"), ("-delete", "删除匹配项，风险高")],
        caution="find 的条件顺序会影响结果；-delete 会直接删除且不可恢复。先去掉动作预览结果，再把 | xargs rm 或 -delete 投入使用。",
        related=("locate", "grep", "xargs", "which"),
        danger="caution",
    ),
    C(
        "locate", "快速按文件名查找", "查找与搜索",
        "locate [选项] 关键词...",
        "locate 查询预建的文件名数据库，速度比 find 快很多，但数据库不是实时的。刚创建的文件可能查不到，可以先用 sudo updatedb 更新索引。",
        "快速 查找 文件名 数据库 索引 搜索 位置",
        [
            ("查找包含 nginx 的路径", "locate nginx.conf"),
            ("忽略大小写查找", "locate -i readme"),
            ("更新文件索引数据库", "sudo updatedb"),
        ],
        [("-i", "忽略大小写"), ("-c", "只输出匹配数量"), ("-r", "把关键词当作正则表达式"), ("-l 数量", "限制结果条数")],
        caution="locate 的结果来自数据库，可能包含已删除文件或漏掉新文件。需要实时准确结果时用 find。",
        related=("find", "which", "whereis"),
    ),
    C(
        "which", "查找命令的可执行文件位置", "查找与搜索",
        "which [选项] 命令...",
        "which 按 PATH 环境变量查找命令实际执行的是哪个文件。排查「为什么运行的是旧版本」或确认某个工具是否安装时非常有用。",
        "命令 位置 路径 可执行 安装 哪个 版本",
        [
            ("查看 python3 的位置", "which python3"),
            ("显示 PATH 中所有同名命令", "which -a python"),
            ("确认某个工具是否存在", "which curl git docker"),
        ],
        [("-a", "显示所有匹配项，而不只第一个"), ("-s", "静默模式，仅用退出码表示是否存在")],
        related=("whereis", "type", "man"),
    ),
    C(
        "whereis", "查找程序、源码和手册位置", "查找与搜索",
        "whereis [选项] 名称...",
        "whereis 不只找可执行文件，还会找对应的源码和手册页位置。它查询标准系统目录，不依赖当前 PATH 里的别名。",
        "程序 位置 手册 源码 路径 在哪",
        [
            ("查看 ssh 相关文件位置", "whereis ssh"),
            ("只找可执行文件", "whereis -b python3"),
            ("只找手册页", "whereis -m tar"),
        ],
        [("-b", "只查找可执行文件"), ("-m", "只查找手册页"), ("-s", "只查找源码")],
        related=("which", "type", "man"),
    ),
    C(
        "xargs", "把输入转换成命令参数", "查找与搜索",
        "命令 | xargs [选项] 命令",
        "xargs 把标准输入的一行行内容拼成后续命令的参数，常和 find、grep 配合批量处理文件。文件名里有空格时要用 -0 配合 find -print0。",
        "批量 参数 管道 处理 文件 组合 删除",
        [
            ("批量删除 .tmp 文件", "find . -name '*.tmp' -print0 | xargs -0 rm -f"),
            ("每个文件单独执行一次命令", "find . -name '*.log' -print0 | xargs -0 -n1 gzip"),
            ("用占位符放置参数", "echo image.png | xargs -I{} cp {} backup/"),
        ],
        [("-0", "用 NUL 分隔输入，正确处理含空格的文件名"), ("-n 数量", "每次最多传几个参数"), ("-I {}", "用 {} 指定参数插入位置"), ("-p", "执行前询问")],
        caution="xargs 默认按空白切分参数，文件名有空格时会拆错；与 find 配合时务必用 -print0 | xargs -0。组合 rm 前先打印结果确认。",
        related=("find", "grep", "rm"),
        danger="caution",
    ),

    # ---------------- 压缩归档 ----------------
    C(
        "tar", "打包与解包归档文件", "压缩归档",
        "tar [选项] [归档文件] [文件...]",
        "tar 把多个文件打成一个归档包，再配合 gzip 压缩成常见的 .tar.gz。备份目录、迁移项目、下载源码包都离不开它。",
        "压缩 解压 打包 归档 tar.gz tgz 备份 目录",
        [
            ("把目录打包成 tar.gz", "tar -czf backup.tar.gz project/"),
            ("解压 tar.gz 到当前目录", "tar -xzf backup.tar.gz"),
            ("不解压，先查看包内文件", "tar -tzf backup.tar.gz"),
            ("解压到指定目录", "tar -xzf backup.tar.gz -C /opt/"),
        ],
        [("-c", "创建归档"), ("-x", "解包/提取"), ("-z", "用 gzip 压缩或解压"), ("-f 文件", "指定归档文件名，必须紧跟文件名"), ("-t", "列出归档内容"), ("-v", "显示处理过程")],
        caution="选项 f 后面必须紧跟归档文件名，例如 -czf backup.tar.gz。解压前可先用 -tzf 查看内容，避免覆盖当前目录文件。",
        related=("zip", "unzip", "gzip", "file"),
    ),
    C(
        "zip", "创建 ZIP 压缩包", "压缩归档",
        "zip [选项] 压缩包.zip 文件...",
        "zip 创建兼容 Windows/macOS 的 .zip 压缩包。压缩目录需要 -r；和 tar 不同，zip 默认会往已有压缩包里追加/更新文件。",
        "压缩 打包 zip 目录 加密 跨平台",
        [
            ("压缩整个目录", "zip -r site.zip site/"),
            ("压缩时设置密码", "zip -e secret.zip report.pdf"),
            ("最高压缩率", "zip -9 archive.zip data.csv"),
        ],
        [("-r", "递归压缩目录"), ("-e", "设置打开密码（交互输入）"), ("-9", "最高压缩级别"), ("-x 模式", "排除文件，如 -x '*.log'")],
        caution="向已有 zip 包再次执行 zip 时是更新内容而不是重新创建；需要干净压缩包时先删除旧包。",
        related=("unzip", "tar", "gzip"),
    ),
    C(
        "unzip", "解压 ZIP 文件", "压缩归档",
        "unzip [选项] 文件.zip [指定文件...]",
        "unzip 解开 .zip 压缩包，可以只解压其中几个文件，也可以指定输出目录。解压前用 -l 查看内容，避免覆盖现有文件。",
        "解压 zip 压缩包 提取 文件 查看 内容",
        [
            ("解压到当前目录", "unzip site.zip"),
            ("先查看包内文件列表", "unzip -l site.zip"),
            ("解压到指定目录", "unzip site.zip -d /tmp/site"),
        ],
        [("-l", "只列出内容，不解压"), ("-d 目录", "指定解压目标目录"), ("-o", "覆盖已有文件且不询问"), ("-n", "不覆盖已有文件")],
        caution="默认遇到同名文件会询问；批量脚本里 -o 会直接覆盖，使用前确认目标目录。",
        related=("zip", "tar", "file"),
    ),
    C(
        "gzip", "压缩单个文件", "压缩归档",
        "gzip [选项] 文件...",
        "gzip 把单个文件压成 .gz，默认会删除原文件。它不负责打包多个文件；打包目录请用 tar -z。解压可用 gzip -d 或 gunzip。",
        "压缩 解压 gz 单文件 归档",
        [
            ("压缩文件并保留原文件", "gzip -k app.log"),
            ("解压 .gz 文件", "gzip -d app.log.gz"),
            ("最高压缩率", "gzip -9 backup.sql"),
        ],
        [("-k", "保留原始文件"), ("-d", "解压"), ("-9", "最高压缩级别"), ("-l", "查看压缩率信息")],
        caution="gzip 默认压缩后删除原文件；想保留请加 -k。压缩多个文件请改用 tar。",
        related=("tar", "zip", "file"),
    ),
];
