#!/usr/bin/env python
"""
用于自动修复导入路径的工具脚本。

将项目中的相对导入转换为绝对导入，例如：
- from utils.xxx 变为 from src.utils.xxx
- from graph.xxx 变为 from src.graph.xxx
- from tools.xxx 变为 from src.tools.xxx
- from data.xxx 变为 from src.data.xxx
- from agents.xxx 变为 from src.agents.xxx

使用方法：python fix_imports.py
"""

import os
import re
import sys
from pathlib import Path


def fix_imports_in_file(file_path):
    """修复单个文件中的导入路径"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 定义需要修复的模块路径
    modules_to_fix = ['utils', 'graph', 'tools', 'data', 'agents', 'llm']
    
    # 定义导入模式
    patterns = []
    for module in modules_to_fix:
        # 模式 1: from module.xxx import ...
        patterns.append((
            re.compile(fr'from\s+({module}\.[^\s]+)\s+import', re.MULTILINE),
            fr'from src.\1 import'
        ))
        # 模式 2: import module.xxx ...
        patterns.append((
            re.compile(fr'import\s+({module}\.[^\s]+)(\s|,|$)', re.MULTILINE),
            fr'import src.\1\2'
        ))
        # 模式 3: from module import xxx
        patterns.append((
            re.compile(fr'from\s+({module})\s+import', re.MULTILINE),
            fr'from src.\1 import'
        ))
    
    # 应用所有模式
    modified = False
    new_content = content
    for pattern, replacement in patterns:
        if re.search(pattern, new_content):
            new_content = re.sub(pattern, replacement, new_content)
            modified = True
    
    # 如果内容被修改，写回文件
    if modified:
        print(f"修复导入: {file_path}")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False


def scan_and_fix_directory(directory):
    """遍历目录，修复所有 .py 文件中的导入"""
    fixed_count = 0
    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.endswith('.py'):
                file_path = os.path.join(root, filename)
                if fix_imports_in_file(file_path):
                    fixed_count += 1
    return fixed_count


if __name__ == "__main__":
    src_dir = Path("src")
    if not src_dir.exists() or not src_dir.is_dir():
        print("错误: 未找到 src 目录。请在项目根目录下运行此脚本。")
        sys.exit(1)
    
    fixed_count = scan_and_fix_directory(src_dir)
    print(f"完成! 已修复 {fixed_count} 个文件的导入路径。") 