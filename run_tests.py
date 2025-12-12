#!/usr/bin/env python3
"""執行所有測試的腳本"""
import unittest
import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 發現並執行所有測試
loader = unittest.TestLoader()
suite = loader.discover('tests', pattern='test_*.py')

runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)

# 如果有測試失敗，以非零狀態碼退出
sys.exit(0 if result.wasSuccessful() else 1)

