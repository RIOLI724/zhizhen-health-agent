"""启动入口：预检端口占用，用中文给出可执行的解决方案，再拉起服务。"""

import socket

import uvicorn

HOST = "127.0.0.1"
PORT = 8000


def port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        return sock.connect_ex((host, port)) == 0


def main() -> int:
    if port_in_use(HOST, PORT):
        print("⚠️  启动失败：端口 8000 已被占用。")
        print("    这几乎总是因为上一个后端还在运行。两种解决：")
        print("    1. VS Code 里找到之前的后端终端，点红色方块停止后重试；")
        print("    2. 或按 Ctrl+C 退出本程序后，重启电脑再试。")
        return 1

    print(f"智诊后端启动中：http://{HOST}:{PORT}")
    print("健康检查：http://127.0.0.1:8000/api/health")
    uvicorn.run("app.main:app", host=HOST, port=PORT, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
