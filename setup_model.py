"""
环境安装脚本：下载 MediaPipe 手部关键点模型文件。

在新机器上部署时，安装完依赖后运行一次即可：
    pip install mediapipe opencv-python pynput numpy
    python setup_model.py
"""
import ssl
import sys
import urllib.request
from pathlib import Path
import certifi

MODEL_URL  = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
MODEL_PATH = Path(__file__).parent / "src" / "hand_landmarker.task"


def download(url: str, dest: Path) -> None:
    ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    opener  = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl_ctx))

    print(f"下载中：{url}")
    print(f"保存至：{dest}")

    with opener.open(url) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        chunk = 65536
        with open(dest, "wb") as f:
            while True:
                data = resp.read(chunk)
                if not data:
                    break
                f.write(data)
                downloaded += len(data)
                if total:
                    pct = downloaded / total * 100
                    print(f"\r  {downloaded // 1024} / {total // 1024} KB  ({pct:.1f}%)", end="", flush=True)
    print("\n完成。")


def main() -> None:
    if MODEL_PATH.exists():
        print(f"模型文件已存在：{MODEL_PATH}，无需重新下载。")
        print("若需强制重新下载，请先删除该文件后再运行本脚本。")
        return

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        download(MODEL_URL, MODEL_PATH)
    except Exception as e:
        # 下载失败时清理残留文件
        if MODEL_PATH.exists():
            MODEL_PATH.unlink()
        print(f"\n下载失败：{e}", file=sys.stderr)
        print(f"请手动下载并放入 src/ 目录：\n  {MODEL_URL}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
