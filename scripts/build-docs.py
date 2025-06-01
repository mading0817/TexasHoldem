#!/usr/bin/env python3
"""
文档生成脚本 - Texas Hold'em Poker Game v2

使用pdoc生成API文档，采用模块化方式避免双层v2目录结构。
支持GitHub Pages发布。

使用方法:
    python scripts/build-docs.py
    python scripts/build-docs.py --check  # 检查文档是否需要更新
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

def run_command(cmd, check=True):
    """运行命令并返回结果"""
    print(f"运行命令: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"命令执行失败: {result.stderr}")
        sys.exit(1)
    return result

def clean_docs():
    """清理旧的文档目录"""
    docs_dir = Path("docs")
    
    # 保留conf.py和.nojekyll
    preserve_files = ["conf.py", ".nojekyll"]
    preserved_content = {}
    
    for file in preserve_files:
        file_path = docs_dir / file
        if file_path.exists():
            preserved_content[file] = file_path.read_text(encoding='utf-8')
    
    # 清理v2目录和其他生成的文件
    v2_dir = docs_dir / "v2"
    if v2_dir.exists():
        shutil.rmtree(v2_dir)
    
    # 清理其他pdoc生成的文件
    for file in ["index.html", "search.js"]:
        file_path = docs_dir / file
        if file_path.exists():
            file_path.unlink()
    
    # 恢复保留的文件
    for file, content in preserved_content.items():
        (docs_dir / file).write_text(content, encoding='utf-8')
    
    print("✅ 清理旧文档完成")

def generate_docs():
    """生成新的文档"""
    # 确保docs目录存在
    Path("docs").mkdir(exist_ok=True)
    
    # 生成文档
    cmd = [
        sys.executable, "-m", "pdoc",
        "-o", "docs",
        "-d", "google",
        "v2.core", "v2.controller", "v2.ui"
    ]
    
    run_command(cmd)
    print("✅ 文档生成完成")

def ensure_github_pages_ready():
    """确保GitHub Pages配置正确"""
    docs_dir = Path("docs")
    
    # 创建.nojekyll文件
    nojekyll_path = docs_dir / ".nojekyll"
    if not nojekyll_path.exists():
        nojekyll_path.touch()
        print("✅ 创建.nojekyll文件")
    
    print("✅ GitHub Pages配置完成")

def check_git_status():
    """检查git状态，确认文档是否有变更"""
    result = run_command(["git", "diff", "--exit-code", "docs/"], check=False)
    if result.returncode == 0:
        print("✅ 文档无变更")
        return True
    else:
        print("⚠️  文档有变更，需要提交")
        return False

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="生成v2项目API文档")
    parser.add_argument("--check", action="store_true", 
                       help="检查文档是否需要更新（用于CI）")
    
    args = parser.parse_args()
    
    print("🚀 开始生成Texas Hold'em Poker v2文档...")
    
    # 切换到项目根目录
    os.chdir(Path(__file__).parent.parent)
    
    if args.check:
        # CI模式：生成文档并检查是否有变更
        clean_docs()
        generate_docs()
        ensure_github_pages_ready()
        
        if not check_git_status():
            print("❌ 文档不是最新的，请运行 'python scripts/build-docs.py' 更新文档")
            sys.exit(1)
        else:
            print("✅ 文档检查通过")
    else:
        # 正常模式：生成文档
        clean_docs()
        generate_docs()
        ensure_github_pages_ready()
        
        print("\n🎉 文档生成完成！")
        print("📁 文档位置: docs/")
        print("🌐 本地预览: 打开 docs/index.html")
        print("📚 GitHub Pages: 推送到main分支后自动发布")
        
        # 显示文档结构
        print("\n📋 生成的文档结构:")
        docs_dir = Path("docs")
        for item in sorted(docs_dir.rglob("*.html")):
            print(f"   {item.relative_to(docs_dir)}")

if __name__ == "__main__":
    main() 