#!/usr/bin/env python3
"""
文档生成脚本 - Texas Hold'em Poker Game

使用pdoc生成API文档，支持v2和v3版本。
支持GitHub Pages发布。

使用方法:
    python scripts/build-docs.py
    python scripts/build-docs.py --version v3  # 生成v3文档
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

def clean_docs(version="v2"):
    """清理旧的文档目录"""
    docs_dir = Path("docs")
    
    # 保留conf.py和.nojekyll
    preserve_files = ["conf.py", ".nojekyll"]
    preserved_content = {}
    
    for file in preserve_files:
        file_path = docs_dir / file
        if file_path.exists():
            preserved_content[file] = file_path.read_text(encoding='utf-8')
    
    # 清理指定版本目录和其他生成的文件
    version_dir = docs_dir / version
    if version_dir.exists():
        shutil.rmtree(version_dir)
    
    # 清理其他pdoc生成的文件
    for file in ["index.html", "search.js"]:
        file_path = docs_dir / file
        if file_path.exists():
            file_path.unlink()
    
    # 恢复保留的文件
    for file, content in preserved_content.items():
        (docs_dir / file).write_text(content, encoding='utf-8')
    
    print(f"✅ 清理{version}旧文档完成")

def generate_docs(version="v2"):
    """生成新的文档"""
    # 确保docs目录存在
    Path("docs").mkdir(exist_ok=True)
    
    # 根据版本选择模块
    if version == "v2":
        modules = ["v2.core", "v2.controller", "v2.ui"]
    elif version == "v3":
        modules = ["v3.core", "v3.application"]
    else:
        raise ValueError(f"不支持的版本: {version}")
    
    # 生成文档
    cmd = [
        sys.executable, "-m", "pdoc",
        "-o", "docs",
        "-d", "google",
    ] + modules
    
    run_command(cmd)
    print(f"✅ {version}文档生成完成")

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
    
    parser = argparse.ArgumentParser(description="生成项目API文档")
    parser.add_argument("--version", choices=["v2", "v3"], default="v2",
                       help="指定要生成文档的版本 (默认: v2)")
    parser.add_argument("--check", action="store_true", 
                       help="检查文档是否需要更新（用于CI）")
    
    args = parser.parse_args()
    
    print(f"🚀 开始生成Texas Hold'em Poker {args.version}文档...")
    
    # 切换到项目根目录
    os.chdir(Path(__file__).parent.parent)
    
    if args.check:
        # CI模式：生成文档并检查是否有变更
        clean_docs(args.version)
        generate_docs(args.version)
        ensure_github_pages_ready()
        
        if not check_git_status():
            print("❌ 文档不是最新的，请运行 'python scripts/build-docs.py' 更新文档")
            sys.exit(1)
        else:
            print("✅ 文档检查通过")
    else:
        # 正常模式：生成文档
        clean_docs(args.version)
        generate_docs(args.version)
        ensure_github_pages_ready()
        
        print(f"\n🎉 {args.version}文档生成完成！")
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