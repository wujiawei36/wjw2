#!/usr/bin/env bash
# ============================================================
# wjw2 部署脚本
# 用法：远程 git pull 之后，在项目根目录执行：
#     bash deploy.sh
# 脚本会自动完成：备份数据库 → 依赖安装 → 配置检查 → 数据库迁移
#                 → 清理过期访问记录 → 静态文件收集 → 重启应用
# 兼容：本地开发机（wjw2-env）与 PythonAnywhere（~/.virtualenvs/wjw2-env）
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"

echo "==> [1/6] 定位虚拟环境"
if [ -x "./wjw2-env/bin/python" ]; then
    PY="./wjw2-env/bin/python"
    PIP="./wjw2-env/bin/pip"
elif [ -x "$HOME/.virtualenvs/wjw2-env/bin/python" ]; then
    PY="$HOME/.virtualenvs/wjw2-env/bin/python"
    PIP="$HOME/.virtualenvs/wjw2-env/bin/pip"
else
    echo "错误：未找到虚拟环境（./wjw2-env 或 ~/.virtualenvs/wjw2-env）"
    echo "请先创建：python3 -m venv wjw2-env"
    exit 1
fi
echo "    使用: $PY"

echo "==> [2/6] 备份数据库"
BACKUP_DIR="$PWD/backups"
mkdir -p "$BACKUP_DIR"
if [ -f "$PWD/db.sqlite3" ]; then
    BACKUP_FILE="$BACKUP_DIR/db-$(date +%Y%m%d-%H%M%S).sqlite3"
    cp "$PWD/db.sqlite3" "$BACKUP_FILE"
    echo "    已备份 → $BACKUP_FILE"
    # 只保留最近 7 份，更早的自动删除（兼容 macOS 无 xargs -r）
    ls -1t "$BACKUP_DIR"/db-*.sqlite3 2>/dev/null | tail -n +8 | while IFS= read -r old; do
        rm -f "$old"
        echo "    清理旧备份 → $old"
    done
else
    echo "    未发现 db.sqlite3（首次部署？跳过备份）"
fi

echo "==> [3/6] 安装 / 更新依赖"
"$PIP" install -r requirements.txt

echo "==> [4/6] 配置检查 (manage.py check)"
"$PY" manage.py check

echo "==> [5/7] 数据库迁移"
"$PY" manage.py migrate

echo "==> [6/7] 清理过期访问记录（只保留今日，完整历史见 django.log）"
"$PY" manage.py cleanup_page_visits --days 1

echo "==> [7/7] 收集静态文件"
"$PY" manage.py collectstatic --noinput

# PythonAnywhere 通过 touch 其 WSGI 文件来重启应用
if ls /var/www/*_wsgi.py >/dev/null 2>&1; then
    echo "==> 检测到 PythonAnywhere，正在重启应用"
    touch /var/www/*_wsgi.py
fi

echo ""
echo "部署完成。数据库备份目录: $BACKUP_DIR（保留最近 7 份）"
