import tkinter as tk
from tkinter import filedialog, messagebox
import os
import sys
import zipfile
import py7zr
import rarfile
from pathlib import Path
import threading
import tarfile  # 添加顶部导入
import shutil


def set_unrar_path():
    if getattr(sys, 'frozen', False):
        # 打包后路径（PyInstaller 生成的临时目录）
        unrar_path = os.path.join(sys._MEIPASS, "unrar.exe")
    else:
        # 开发时路径（当前目录下的 unrar.exe）
        unrar_path = "unrar.exe"

    rarfile.UNRAR_TOOL = unrar_path
    os.environ["PATH"] += os.pathsep + os.path.dirname(unrar_path)


# 在 GUI 初始化时调用
set_unrar_path()


class ConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("压缩包格式转换工具")
        self.root.geometry("600x300")

        # 文件选择区域
        self.frame = tk.Frame(root)
        self.frame.pack(pady=20)

        self.file_label = tk.Label(self.frame, text="选择文件:")
        self.file_label.grid(row=0, column=0, padx=5)

        self.file_entry = tk.Entry(self.frame, width=50)
        self.file_entry.grid(row=0, column=1, padx=5)

        self.browse_btn = tk.Button(self.frame, text="浏览", command=self.select_files)
        self.browse_btn.grid(row=0, column=2, padx=5)

        # 转换按钮
        self.convert_btn = tk.Button(root, text="开始转换", command=self.start_conversion)
        self.convert_btn.pack(pady=10)

        # 状态显示
        self.status_text = tk.Text(root, height=5)
        self.status_text.pack(pady=10)

        # 设置 unrar 路径 ===
        self.set_unrar_path()

    def set_unrar_path(self):
        """根据运行环境动态设置 unrar 路径"""
        if getattr(sys, 'frozen', False):
            # 打包后的路径（PyInstaller 生成的临时目录）
            unrar_path = os.path.join(sys._MEIPASS, "unrar.exe")
        else:
            # 开发时路径（当前目录下的 unrar.exe）
            unrar_path = os.path.abspath("unrar.exe")
        # 设置 unrar 路径
        rarfile.UNRAR_TOOL = unrar_path
        # 将路径添加到系统环境变量（兼容某些系统配置）
        os.environ["PATH"] += os.pathsep + os.path.dirname(unrar_path)

    def select_files(self):
        files = filedialog.askopenfilenames(
            filetypes=[("支持格式", "*.7z *.rar *.zip *.tar")]
        )
        if files:
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, "; ".join([str(Path(f)) for f in files]))

    def convert_file(self, input_path, output_zip):
        temp_dir = input_path.parent / f"temp_{input_path.stem}"
        try:
            # 创建临时目录
            temp_dir.mkdir(exist_ok=True)

            # 根据后缀解压
            suffix = input_path.suffix.lower()
            if suffix == ".7z":
                with py7zr.SevenZipFile(input_path, mode='r') as archive:
                    archive.extractall(temp_dir)
            elif suffix == ".rar":
                with rarfile.RarFile(input_path) as archive:
                     archive.extractall(temp_dir)
            elif suffix == ".zip":
                with zipfile.ZipFile(input_path) as archive:
                    archive.extractall(temp_dir)
            elif suffix == ".tar":
                with tarfile.open(input_path) as archive:
                    archive.extractall(temp_dir)
            else:
                raise ValueError("不支持的格式")

            # 打包为ZIP
            with zipfile.ZipFile(output_zip, "w") as zipf:
                for root_dir, _, files in os.walk(temp_dir):
                    for file in files:
                        file_path = Path(root_dir) / file
                        arcname = file_path.relative_to(temp_dir)
                        zipf.write(file_path, arcname)
            return True
        except Exception as e:
            import traceback
            traceback.print_exc()  # 打印完整错误堆栈
            return str(e)
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    def start_conversion(self):
        files = self.file_entry.get().split("; ")
        if not files or files == ['']:
            messagebox.showwarning("警告", "请先选择文件！")
            return

        # 禁用按钮避免重复点击
        self.convert_btn.config(state=tk.DISABLED)
        self.status_text.delete(1.0, tk.END)
        self.status_text.insert(tk.END, "开始转换...\n")

        def task():
            success = 0
            failed = 0
            for file_path in files:
                file = Path(file_path.strip())
                if not file.exists():
                    self.root.after(0, self.status_text.insert, tk.END, f"文件 {file} 不存在！\n")
                    failed += 1
                    continue

                # 处理输出文件名冲突
                output_zip = file.parent / f"{file.stem}_converted.zip"
                if output_zip.exists():
                    # 自动重命名
                    count = 1
                    while output_zip.exists():
                        output_zip = file.parent / f"{file.stem}_converted_{count}.zip"
                        count += 1

                result = self.convert_file(file, output_zip)
                if result is True:
                    self.root.after(0, self.status_text.insert, tk.END, f"✅ {file} 转换成功: {output_zip}\n")
                    success += 1
                else:
                    self.root.after(0, self.status_text.insert, tk.END, f"❌ {file} 转换失败: {result}\n")
                    failed += 1

            self.root.after(0, self.status_text.insert, tk.END, f"\n转换完成！成功: {success}, 失败: {failed}\n")
            # 恢复按钮状态
            self.root.after(0, lambda: self.convert_btn.config(state=tk.NORMAL))

        # 启动线程
        threading.Thread(target=task, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    app = ConverterApp(root)
    root.mainloop()