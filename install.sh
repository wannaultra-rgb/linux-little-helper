#!/usr/bin/env bash
set -euo pipefail

APP_NAME="linux-command-guide"
APP_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
TARGET_DIR="$DATA_HOME/$APP_NAME"
DESKTOP_DIR="$DATA_HOME/applications"
BIN_DIR="$HOME/.local/bin"
WRAPPER="$BIN_DIR/$APP_NAME"
DESKTOP_FILE="$DESKTOP_DIR/$APP_NAME.desktop"

if [[ "${1:-}" == "--uninstall" ]]; then
    rm -rf -- "$TARGET_DIR"
    rm -f -- "$DESKTOP_FILE" "$WRAPPER"
    command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
    echo "已卸载 Linux 命令指南。"
    exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "未找到 python3，请先安装 Python 3。" >&2
    exit 1
fi
if ! python3 -c "import tkinter" >/dev/null 2>&1; then
    echo "缺少 Tk 图形库。Debian/Ubuntu: sudo apt install python3-tk" >&2
    echo "Fedora: sudo dnf install python3-tkinter    Arch: sudo pacman -S tk" >&2
    exit 1
fi

mkdir -p "$TARGET_DIR" "$DESKTOP_DIR" "$BIN_DIR"
rm -rf -- "$TARGET_DIR"
mkdir -p "$TARGET_DIR"
cp -- "$APP_DIR/app.py" "$APP_DIR/icon.png" "$APP_DIR/README.md" "$TARGET_DIR/"
cp -R -- "$APP_DIR/guide" "$TARGET_DIR/"
find "$TARGET_DIR" -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
chmod +x "$TARGET_DIR/app.py"

cat > "$WRAPPER" <<EOF
#!/usr/bin/env bash
exec python3 "$TARGET_DIR/app.py" "\$@"
EOF
chmod +x "$WRAPPER"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Linux 命令指南
Comment=中文 ↔ 指令双向索引，快速找到合适的 Linux 命令
Exec="$WRAPPER"
Icon="$TARGET_DIR/icon.png"
Terminal=false
Categories=Utility;Education;
Keywords=linux;command;cheat;中文;命令;终端;
StartupNotify=true
EOF
chmod 644 "$DESKTOP_FILE"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
fi

echo "已安装到应用菜单：Linux 命令指南"
echo "启动器：$WRAPPER"
echo "如果终端提示找不到命令，把 ~/.local/bin 加入 PATH。"
