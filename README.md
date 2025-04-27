# 12306-stations
### 运行脚本

```shell
cd src/12306-mcp
mcpo --port 8000 -- uvicorn main:app
```

```shell
uvx mcpo --port 8000 -- uvicorn main:app
```
### 脚本

构建脚本
```shell
uv sync

uv build

yv publish -t <pypi-token>
```

```shell
mcpo --port 8000 -- uv tool run 12306-mcp
 OR
mcpo --port 8000 -- uvx 12306-mcp
```
