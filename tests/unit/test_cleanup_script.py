"""
Tests for the project cleanup script.

This module tests the cleanup script functionality to ensure it correctly
identifies and removes temporary files while preserving important files.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch
import sys
import os

# Add scripts directory to path for importing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from cleanup import ProjectCleaner


class TestProjectCleaner:
    """Test the ProjectCleaner class."""
    
    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        
        # Create project structure
        (temp_dir / "src").mkdir()
        (temp_dir / "tests").mkdir()
        (temp_dir / "__pycache__").mkdir()
        (temp_dir / "src" / "__pycache__").mkdir()
        (temp_dir / ".pytest_cache").mkdir()
        
        # Create files to keep
        (temp_dir / "README.md").write_text("# Test Project")
        (temp_dir / "requirements.txt").write_text("pytest==7.0.0")
        (temp_dir / "src" / "main.py").write_text("print('hello')")
        (temp_dir / "tests" / "test_main.py").write_text("def test_main(): pass")
        
        # Create files to clean
        (temp_dir / "debug.log").write_text("debug info")
        (temp_dir / "temp.tmp").write_text("temporary data")
        (temp_dir / "backup.bak").write_text("backup data")
        (temp_dir / "src" / "module.pyc").write_text("bytecode")
        (temp_dir / "__pycache__" / "test.pyc").write_text("bytecode")
        (temp_dir / ".coverage").write_text("coverage data")
        
        yield temp_dir
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def test_find_files_to_clean(self, temp_project):
        """Test finding files that should be cleaned."""
        cleaner = ProjectCleaner(temp_project)
        files_to_clean = cleaner.find_files_to_clean()
        
        # Convert to relative paths for easier testing
        relative_files = [f.relative_to(temp_project) for f in files_to_clean]
        
        # Should find these files
        expected_files = {
            Path("debug.log"),
            Path("temp.tmp"),
            Path("backup.bak"),
            Path("src/module.pyc"),
            Path("__pycache__/test.pyc"),
            Path(".coverage")
        }
        
        assert len(relative_files) >= len(expected_files)
        for expected_file in expected_files:
            assert expected_file in relative_files
    
    def test_find_dirs_to_clean(self, temp_project):
        """Test finding directories that should be cleaned."""
        cleaner = ProjectCleaner(temp_project)
        dirs_to_clean = cleaner.find_dirs_to_clean()
        
        # Convert to relative paths for easier testing
        relative_dirs = [d.relative_to(temp_project) for d in dirs_to_clean]
        
        # Should find these directories
        expected_dirs = {
            Path("__pycache__"),
            Path("src/__pycache__"),
            Path(".pytest_cache")
        }
        
        for expected_dir in expected_dirs:
            assert expected_dir in relative_dirs
    
    def test_protected_files_not_cleaned(self, temp_project):
        """Test that protected files are not marked for cleaning."""
        cleaner = ProjectCleaner(temp_project)
        files_to_clean = cleaner.find_files_to_clean()
        
        # Convert to relative paths
        relative_files = [f.relative_to(temp_project) for f in files_to_clean]
        
        # These files should NOT be in the cleanup list
        protected_files = {
            Path("README.md"),
            Path("requirements.txt"),
            Path("src/main.py"),
            Path("tests/test_main.py")
        }
        
        for protected_file in protected_files:
            assert protected_file not in relative_files
    
    def test_clean_files_dry_run(self, temp_project):
        """Test cleaning files in dry run mode."""
        cleaner = ProjectCleaner(temp_project)
        files_to_clean = cleaner.find_files_to_clean()
        
        # Ensure we have files to clean
        assert len(files_to_clean) > 0
        
        # Run in dry run mode
        deleted_count = cleaner.clean_files(files_to_clean, dry_run=True)
        
        # Should report files as deleted but not actually delete them
        assert deleted_count > 0
        
        # Files should still exist
        for file_path in files_to_clean:
            assert file_path.exists(), f"File {file_path} should still exist in dry run"
    
    def test_clean_files_actual(self, temp_project):
        """Test actually cleaning files."""
        cleaner = ProjectCleaner(temp_project)
        files_to_clean = cleaner.find_files_to_clean()
        
        # Ensure we have files to clean
        assert len(files_to_clean) > 0
        
        # Store original file paths
        original_files = [f for f in files_to_clean if f.exists()]
        
        # Run actual cleanup
        deleted_count = cleaner.clean_files(files_to_clean, dry_run=False)
        
        # Should report files as deleted
        assert deleted_count == len(original_files)
        
        # Files should no longer exist
        for file_path in original_files:
            assert not file_path.exists(), f"File {file_path} should be deleted"
    
    def test_clean_dirs_actual(self, temp_project):
        """Test actually cleaning directories."""
        cleaner = ProjectCleaner(temp_project)
        dirs_to_clean = cleaner.find_dirs_to_clean()
        
        # Ensure we have directories to clean
        assert len(dirs_to_clean) > 0
        
        # Store original directory paths
        original_dirs = [d for d in dirs_to_clean if d.exists()]
        
        # Run actual cleanup
        deleted_count = cleaner.clean_dirs(dirs_to_clean, dry_run=False)
        
        # Should report directories as deleted
        assert deleted_count == len(original_dirs)
        
        # Directories should no longer exist
        for dir_path in original_dirs:
            assert not dir_path.exists(), f"Directory {dir_path} should be deleted"
    
    def test_check_for_cleanup_needed(self, temp_project):
        """Test checking if cleanup is needed."""
        cleaner = ProjectCleaner(temp_project)
        
        # Should need cleanup initially
        assert cleaner.check_for_cleanup_needed() is True
        
        # Clean the project
        cleaner.clean_project(dry_run=False, verbose=False)
        
        # Should not need cleanup after cleaning
        assert cleaner.check_for_cleanup_needed() is False
    
    def test_clean_project_integration(self, temp_project):
        """Test the full project cleaning integration."""
        cleaner = ProjectCleaner(temp_project)
        
        # Run full cleanup
        result = cleaner.clean_project(dry_run=False, verbose=True)
        
        # Should have found and cleaned files
        assert result['files_found'] > 0
        assert result['dirs_found'] > 0
        assert result['files_deleted'] == result['files_found']
        assert result['dirs_deleted'] == result['dirs_found']
        assert result['dry_run'] is False
        
        # Protected files should still exist
        assert (temp_project / "README.md").exists()
        assert (temp_project / "requirements.txt").exists()
        assert (temp_project / "src" / "main.py").exists()
        
        # Cleaned files should not exist
        assert not (temp_project / "debug.log").exists()
        assert not (temp_project / "temp.tmp").exists()
        assert not (temp_project / "__pycache__").exists()
    
    def test_safe_directory_removal(self, temp_project):
        """Test that directories are only removed if safe."""
        # Create a directory with protected content
        unsafe_dir = temp_project / "unsafe_cache"
        unsafe_dir.mkdir()
        (unsafe_dir / "important.txt").write_text("important data")
        
        cleaner = ProjectCleaner(temp_project)
        
        # Should not be marked for removal
        dirs_to_clean = cleaner.find_dirs_to_clean()
        relative_dirs = [d.relative_to(temp_project) for d in dirs_to_clean]
        
        assert Path("unsafe_cache") not in relative_dirs
        
        # Directory should still exist after cleanup
        cleaner.clean_project(dry_run=False)
        assert unsafe_dir.exists()
        assert (unsafe_dir / "important.txt").exists()


class TestCleanupScriptCLI:
    """Test the cleanup script command line interface."""
    
    @pytest.fixture
    def temp_project_with_cleanup(self):
        """Create a temporary project with files that need cleanup."""
        temp_dir = Path(tempfile.mkdtemp())
        
        # Create some files that need cleanup
        (temp_dir / "test.log").write_text("log data")
        (temp_dir / "temp.tmp").write_text("temp data")
        
        # Create some files that should be kept
        (temp_dir / "README.md").write_text("# Project")
        
        yield temp_dir
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def test_check_mode_with_cleanup_needed(self, temp_project_with_cleanup):
        """Test check mode when cleanup is needed."""
        from cleanup import main
        
        with patch('sys.argv', ['cleanup.py', '--check', '--project-root', str(temp_project_with_cleanup)]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            # Should exit with code 1 (cleanup needed)
            assert exc_info.value.code == 1
    
    def test_check_mode_no_cleanup_needed(self):
        """Test check mode when no cleanup is needed."""
        from cleanup import main
        
        # Create a clean temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "README.md").write_text("# Clean Project")
            
            with patch('sys.argv', ['cleanup.py', '--check', '--project-root', str(temp_path)]):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                
                # Should exit with code 0 (no cleanup needed)
                assert exc_info.value.code == 0 
 