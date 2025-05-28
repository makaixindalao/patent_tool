@echo off
echo ========================================
echo        专利撰写助手 v2.0 启动器
echo ========================================
echo.

echo [1/3] 正在停止现有的Python进程...
taskkill /f /im python.exe >nul 2>&1
echo      完成！

echo [2/3] 等待进程完全停止...
timeout /t 2 >nul
echo      完成！

echo [3/3] 正在启动专利撰写助手...
echo.
echo ========================================
echo  🌐 应用地址: http://localhost:8501
echo  💡 使用 Ctrl+C 停止应用
echo  📋 在浏览器中打开上述地址使用应用
echo  🚀 新功能: 支持多厂商API和多线程处理
echo ========================================
echo.

python -m streamlit run app.py --server.port=8501

echo.
echo 应用已停止，按任意键退出...
pause >nul 