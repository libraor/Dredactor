"""Dredactor Web 界面启动脚本"""

import os
import sys
import subprocess
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def main():
    """启动 Streamlit 应用"""
    print("🔒 Dredactor Web 界面启动中...")
    print(f"项目根目录: {project_root}")

    # 检查依赖
    try:
        import streamlit
        print(f"✅ Streamlit 版本: {streamlit.__version__}")
    except ImportError:
        print("❌ Streamlit 未安装")
        print("请运行: pip install streamlit")
        sys.exit(1)

    # 检查 dredactor 模块
    try:
        import dredactor
        print("✅ Dredactor 模块已加载")
    except ImportError:
        print("❌ Dredactor 模块未找到")
        sys.exit(1)

    # 启动 Streamlit
    app_path = Path(__file__).parent / "app.py"
    print(f"🚀 启动应用: {app_path}")
    print("=" * 60)
    print("访问地址: http://localhost:8501")
    print("=" * 60)

    # 运行 streamlit
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(app_path), "--browser.gatherUsageStats=false"],
        cwd=str(project_root),
    )


if __name__ == "__main__":
    main()
