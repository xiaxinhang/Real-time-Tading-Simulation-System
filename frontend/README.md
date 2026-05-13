# Frontend Tester

这是一个用于联调后端的轻量前端测试页（无 Node 依赖）。

## 启动方式
在项目根目录执行：

```powershell
# 启动后端
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# 新开终端启动前端静态服务
.\.venv\Scripts\python.exe -m http.server 5500 --directory frontend
```

浏览器打开：
`http://127.0.0.1:5500`

## 可测功能
- 后端健康检查
- WebSocket 实时行情展示
- 下单（buy/sell）
- 持仓查询
- 用户分析与市场分析查询

