### 开发

dev 启动命令
```
uv run uvicorn opentask.main:app --port=7377 --host=0.0.0.0
```

测试命令
```
cd backend && uv run pytest tests/ -v
```

## 注意
- 禁止修改后端服务端口，固定保持7377
- 如果7377端口被占用，你要先关闭占用端口的服务

## 规范
- api的实现放到 backend\opentask\api , 数据库操作不要放在api层
- service层在 backend\opentask\services
- 同一个模块的代码要内聚，比如issue相关的评论等功能都要放在issue模块内