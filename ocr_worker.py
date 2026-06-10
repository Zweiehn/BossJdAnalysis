"""
PaddleOCR Worker - 被主程序通过 subprocess 调用
用法: python ocr_worker.py <image_path>
输出: stdout 输出识别文本，stderr 输出错误信息
"""

import sys
import os

# Windows 下输出 utf-8
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def main():
    if len(sys.argv) < 2:
        print("用法: python ocr_worker.py <image_path>", file=sys.stderr)
        sys.exit(1)

    image_path = sys.argv[1]
    if not os.path.exists(image_path):
        print(f"文件不存在: {image_path}", file=sys.stderr)
        sys.exit(1)

    try:
        from paddleocr import PaddleOCR

        ocr = PaddleOCR(
            use_angle_cls=True,
            lang="ch",
            show_log=False,
            use_gpu=False,
        )
        result = ocr.ocr(image_path, cls=True)

        if not result or not result[0]:
            print("")
            return

        lines = []
        for line in result[0]:
            text = line[1][0]
            if text and text.strip():
                lines.append(text.strip())

        print("\n".join(lines))

    except ImportError:
        print("请安装 PaddleOCR: pip install paddlepaddle paddleocr", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"OCR 错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
