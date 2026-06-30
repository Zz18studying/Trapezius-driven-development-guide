# -*- coding: utf-8 -*-
"""
一键设置脚本 - 按顺序运行所有数据处理脚本
"""

import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")

scripts = [
    "01_extract_and_merge_data.py",
    "02_generate_faq.py", 
    "03_build_vector_db.py",
    "04_test_retrieval.py"
]

def run_script(script_name):
    script_path = os.path.join(SCRIPT_DIR, script_name)
    print(f"\n{'='*60}")
    print(f"正在运行: {script_name}")
    print(f"{'='*60}")
    
    result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(f"stderr: {result.stderr}")
    
    return result.returncode == 0

def main():
    print("🚀 灵山胜境 - 一键设置脚本")
    print("="*60)
    
    success_count = 0
    for script in scripts:
        if run_script(script):
            success_count += 1
            print(f"✅ {script} 运行成功")
        else:
            print(f"❌ {script} 运行失败")
            print("⚠️ 后续脚本将跳过")
            break
    
    print(f"\n{'='*60}")
    if success_count == len(scripts):
        print("🎉 所有脚本运行成功！")
        print("现在可以启动后端服务了：")
        print(f"   cd {BACKEND_DIR}")
        print("   python main.py")
    else:
        print(f"⚠️ 部分脚本运行失败（{success_count}/{len(scripts)}）")
        print("请检查错误信息，修复后重新运行")

if __name__ == "__main__":
    main()