"""
专利撰写助手启动脚本
"""

import subprocess
import sys
import os


def install_requirements():
    """安装依赖"""
    print("正在安装依赖...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ 依赖安装完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖安装失败: {e}")
        return False


def run_app():
    """运行应用"""
    print("正在启动专利撰写助手...")
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py", "--server.port=8501"])
    except KeyboardInterrupt:
        print("\n👋 应用已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")


def main():
    print("🚀 专利撰写助手")
    print("=" * 50)
    
    # 检查是否需要安装依赖
    if not os.path.exists("requirements.txt"):
        print("❌ 未找到 requirements.txt 文件")
        return
    
    # 安装依赖
    if not install_requirements():
        return
    
    print("\n" + "=" * 50)
    print("🌐 应用将在浏览器中打开: http://localhost:8501")
    print("💡 使用 Ctrl+C 停止应用")
    print("=" * 50 + "\n")
    
    # 运行应用
    run_app()


if __name__ == "__main__":
    main() 