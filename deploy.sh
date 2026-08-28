#!/usr/bin/env bash
# ============================================================
# wjw2 部署脚本
# 用法：远程 git pull 之后，在项目根目录执行：
#     bash deploy.sh
# 脚本会自动完成：依赖安装 → 配置检查 → 数据库迁移 → 静态文件收集 → 重启应用
# 兼容：本地开发机（wjw2-env）与 PythonAnywhere（~/.virtualenvs/wjw2-env）
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"

echo "==> [1/5] 定位虚拟环境"
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

echo "==> [2/5] 安装 / 更新依赖"
"$PIP" install -r requirements.txt

echo "==> [3/5] 配置检查 (manage.py check)"
"$PY" manage.py check

echo "==> [4/5] 数据库迁移"
"$PY" manage.py migrate

echo "==> [5/5] 收集静态文件"
"$PY" manage.py collectstatic --noinput

# PythonAnywhere 通过 touch 其 WSGI 文件来重启应用
if ls /var/www/*_wsgi.py >/dev/null 2>&1; then
    echo "==> 检测到 PythonAnywhere，正在重启应用"
    touch /var/www/*_wsgi.py
fi

echo ""
echo "部署完成。"
