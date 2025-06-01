#!/usr/bin/env python3
"""
项目清理脚本。

自动删除项目中的临时文件、日志文件、调试文件等，保持项目目录整洁。
支持检查模式和实际删除模式。
"""

import os
import sys
import glob
import argparse
from pathlib import Path
from typing import List, Set


class ProjectCleaner:
    """项目清理器类。"""
    
    def __init__(self, project_root: Path):
        """
        初始化清理器。
        
        Args:
            project_root: 项目根目录路径
        """
        self.project_root = project_root
        self.deleted_files: List[Path] = []
        self.deleted_dirs: List[Path] = []
        
        # 定义要清理的文件模式
        self.file_patterns = [
            "*.log",           # 日志文件
            "*.tmp",           # 临时文件
            "*.temp",          # 临时文件
            "*.bak",           # 备份文件
            "*.swp",           # Vim交换文件
            "*.swo",           # Vim交换文件
            "*~",              # 编辑器备份文件
            ".DS_Store",       # macOS系统文件
            "Thumbs.db",       # Windows缩略图文件
            "desktop.ini",     # Windows桌面配置文件
            "*.pyc",           # Python字节码文件
            "*.pyo",           # Python优化字节码文件
            "*.pyd",           # Python扩展模块
            ".coverage",       # 覆盖率文件
            "coverage.xml",    # 覆盖率报告
            "*.cover",         # 覆盖率文件
            ".pytest_cache",   # pytest缓存目录
            ".mypy_cache",     # mypy缓存目录
            "__pycache__",     # Python缓存目录
            "*.egg-info",      # Python包信息目录
            ".tox",            # tox测试环境目录
            ".nox",            # nox测试环境目录
            "build",           # 构建目录
            "dist",            # 分发目录
            ".vscode/settings.json",  # VSCode用户设置（保留workspace设置）
        ]
        
        # 定义要清理的目录模式
        self.dir_patterns = [
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            "*.egg-info",
            ".tox",
            ".nox",
            "build",
            "dist",
        ]
        
        # 定义要保护的目录（不进入清理）
        self.protected_dirs = {
            ".git",
            ".venv",
            "venv",
            "env",
            "node_modules",
            ".idea",
            ".vscode",  # 保护整个.vscode目录，只清理特定文件
        }
        
        # 定义要保护的文件（不删除）
        self.protected_files = {
            ".gitignore",
            ".gitkeep",
            "README.md",
            "requirements.txt",
            "setup.py",
            "pyproject.toml",
            "Pipfile",
            "Pipfile.lock",
            "poetry.lock",
        }
    
    def find_files_to_clean(self) -> List[Path]:
        """
        查找需要清理的文件。
        
        Returns:
            需要清理的文件路径列表
        """
        files_to_clean = []
        
        for root, dirs, files in os.walk(self.project_root):
            root_path = Path(root)
            
            # 跳过受保护的目录
            if any(protected in root_path.parts for protected in self.protected_dirs):
                continue
            
            # 检查文件
            for file in files:
                file_path = root_path / file
                
                # 跳过受保护的文件
                if file in self.protected_files:
                    continue
                
                # 检查是否匹配清理模式
                for pattern in self.file_patterns:
                    if file_path.match(pattern) or file_path.name == pattern:
                        files_to_clean.append(file_path)
                        break
        
        return files_to_clean
    
    def find_dirs_to_clean(self) -> List[Path]:
        """
        查找需要清理的目录。
        
        Returns:
            需要清理的目录路径列表
        """
        dirs_to_clean = []
        
        for root, dirs, files in os.walk(self.project_root, topdown=False):
            root_path = Path(root)
            
            # 跳过受保护的目录
            if any(protected in root_path.parts for protected in self.protected_dirs):
                continue
            
            # 检查目录
            for dir_name in dirs:
                dir_path = root_path / dir_name
                
                # 检查是否匹配清理模式
                for pattern in self.dir_patterns:
                    if dir_path.match(pattern) or dir_path.name == pattern:
                        # 确保目录为空或只包含要清理的文件
                        if self._is_safe_to_remove_dir(dir_path):
                            dirs_to_clean.append(dir_path)
                        break
        
        return dirs_to_clean
    
    def _is_safe_to_remove_dir(self, dir_path: Path) -> bool:
        """
        检查目录是否可以安全删除。
        
        Args:
            dir_path: 目录路径
            
        Returns:
            如果可以安全删除则返回True
        """
        try:
            # 检查目录是否存在
            if not dir_path.exists() or not dir_path.is_dir():
                return False
            
            # 检查目录内容
            for item in dir_path.rglob("*"):
                if item.is_file():
                    # 如果包含不应该删除的文件，则不安全
                    if item.name in self.protected_files:
                        return False
                    
                    # 检查是否为可清理的文件
                    is_cleanable = False
                    for pattern in self.file_patterns:
                        if item.match(pattern) or item.name == pattern:
                            is_cleanable = True
                            break
                    
                    if not is_cleanable:
                        return False
            
            return True
        except (OSError, PermissionError):
            return False
    
    def clean_files(self, files: List[Path], dry_run: bool = False) -> int:
        """
        清理文件。
        
        Args:
            files: 要清理的文件列表
            dry_run: 是否为试运行模式
            
        Returns:
            成功删除的文件数量
        """
        deleted_count = 0
        
        for file_path in files:
            try:
                if file_path.exists():
                    if not dry_run:
                        file_path.unlink()
                        self.deleted_files.append(file_path)
                    deleted_count += 1
                    print(f"{'[DRY RUN] ' if dry_run else ''}删除文件: {file_path}")
            except (OSError, PermissionError) as e:
                print(f"无法删除文件 {file_path}: {e}")
        
        return deleted_count
    
    def clean_dirs(self, dirs: List[Path], dry_run: bool = False) -> int:
        """
        清理目录。
        
        Args:
            dirs: 要清理的目录列表
            dry_run: 是否为试运行模式
            
        Returns:
            成功删除的目录数量
        """
        deleted_count = 0
        
        for dir_path in dirs:
            try:
                if dir_path.exists() and dir_path.is_dir():
                    if not dry_run:
                        # 递归删除目录及其内容
                        import shutil
                        shutil.rmtree(dir_path)
                        self.deleted_dirs.append(dir_path)
                    deleted_count += 1
                    print(f"{'[DRY RUN] ' if dry_run else ''}删除目录: {dir_path}")
            except (OSError, PermissionError) as e:
                print(f"无法删除目录 {dir_path}: {e}")
        
        return deleted_count
    
    def clean_project(self, dry_run: bool = False, verbose: bool = False) -> dict:
        """
        清理整个项目。
        
        Args:
            dry_run: 是否为试运行模式
            verbose: 是否显示详细信息
            
        Returns:
            清理结果统计
        """
        print(f"开始清理项目: {self.project_root}")
        print(f"模式: {'试运行' if dry_run else '实际删除'}")
        print("-" * 50)
        
        # 查找要清理的文件和目录
        files_to_clean = self.find_files_to_clean()
        dirs_to_clean = self.find_dirs_to_clean()
        
        if verbose:
            print(f"找到 {len(files_to_clean)} 个文件需要清理")
            print(f"找到 {len(dirs_to_clean)} 个目录需要清理")
            print("-" * 50)
        
        # 清理文件
        deleted_files = self.clean_files(files_to_clean, dry_run)
        
        # 清理目录
        deleted_dirs = self.clean_dirs(dirs_to_clean, dry_run)
        
        # 统计结果
        result = {
            'files_found': len(files_to_clean),
            'dirs_found': len(dirs_to_clean),
            'files_deleted': deleted_files,
            'dirs_deleted': deleted_dirs,
            'dry_run': dry_run
        }
        
        print("-" * 50)
        print(f"清理完成:")
        print(f"  文件: {deleted_files}/{len(files_to_clean)}")
        print(f"  目录: {deleted_dirs}/{len(dirs_to_clean)}")
        
        return result
    
    def check_for_cleanup_needed(self) -> bool:
        """
        检查是否需要清理。
        
        Returns:
            如果发现需要清理的文件则返回True
        """
        files_to_clean = self.find_files_to_clean()
        dirs_to_clean = self.find_dirs_to_clean()
        
        return len(files_to_clean) > 0 or len(dirs_to_clean) > 0


def main():
    """主函数。"""
    parser = argparse.ArgumentParser(description="项目清理脚本")
    parser.add_argument(
        "--check", 
        action="store_true", 
        help="检查模式：只检查是否有需要清理的文件，不执行删除"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="试运行模式：显示将要删除的文件但不实际删除"
    )
    parser.add_argument(
        "--verbose", "-v", 
        action="store_true", 
        help="显示详细信息"
    )
    parser.add_argument(
        "--project-root", 
        type=Path, 
        default=Path.cwd(),
        help="项目根目录路径（默认为当前目录）"
    )
    
    args = parser.parse_args()
    
    # 确保项目根目录存在
    if not args.project_root.exists():
        print(f"错误: 项目根目录不存在: {args.project_root}")
        sys.exit(1)
    
    # 创建清理器
    cleaner = ProjectCleaner(args.project_root)
    
    # 检查模式
    if args.check:
        needs_cleanup = cleaner.check_for_cleanup_needed()
        if needs_cleanup:
            print("发现需要清理的文件")
            sys.exit(1)  # 非零退出码表示需要清理
        else:
            print("项目目录干净，无需清理")
            sys.exit(0)
    
    # 执行清理
    try:
        result = cleaner.clean_project(dry_run=args.dry_run, verbose=args.verbose)
        
        # 如果是试运行模式且发现需要清理的文件，返回非零退出码
        if args.dry_run and (result['files_found'] > 0 or result['dirs_found'] > 0):
            sys.exit(1)
        
        sys.exit(0)
        
    except KeyboardInterrupt:
        print("\n清理被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"清理过程中发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 