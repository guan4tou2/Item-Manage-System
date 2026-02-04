#!/bin/bash

echo "=========================================="
echo "驗證測試環境設置"
echo "=========================================="
echo ""

# 檢查必要文件
echo "✓ 檢查測試文件..."
files=(
    "tests/test_notifications.py"
    "tests/test_travel.py"
    "tests/test_api.py"
    "pyproject.toml"
    "docker-compose.test.yml"
    "Dockerfile.test"
    "run_tests.sh"
    "run_tests_uv.sh"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ✗ $file (缺失)"
    fi
done

echo ""
echo "✓ 檢查測試腳本權限..."
if [ -x "run_tests.sh" ]; then
    echo "  ✓ run_tests.sh 可執行"
else
    echo "  ✗ run_tests.sh 不可執行"
fi

if [ -x "run_tests_uv.sh" ]; then
    echo "  ✓ run_tests_uv.sh 可執行"
else
    echo "  ✗ run_tests_uv.sh 不可執行"
fi

echo ""
echo "✓ 檢查測試案例數量..."
test_count=$(find tests -name "test_*.py" | wc -l)
echo "  找到 $test_count 個測試文件"

echo ""
echo "✓ 列出所有測試文件:"
find tests -name "test_*.py" | sort | sed 's/^/  - /'

echo ""
echo "✓ 檢查 Docker 配置..."
if command -v docker &> /dev/null; then
    echo "  ✓ Docker 已安裝"
    if command -v docker-compose &> /dev/null; then
        echo "  ✓ Docker Compose 已安裝"
    else
        echo "  ✗ Docker Compose 未安裝"
    fi
else
    echo "  ✗ Docker 未安裝"
fi

echo ""
echo "✓ 檢查 Python 環境..."
if command -v python3 &> /dev/null; then
    python_version=$(python3 --version)
    echo "  ✓ $python_version"
else
    echo "  ✗ Python 3 未安裝"
fi

echo ""
echo "✓ 檢查 uv..."
if command -v uv &> /dev/null; then
    uv_version=$(uv --version 2>&1 || echo "unknown")
    echo "  ✓ uv 已安裝 ($uv_version)"
else
    echo "  ⚠ uv 未安裝（可選）"
fi

echo ""
echo "✓ 檢查 pytest..."
if python3 -c "import pytest" 2>/dev/null; then
    pytest_version=$(python3 -c "import pytest; print(pytest.__version__)")
    echo "  ✓ pytest $pytest_version"
else
    echo "  ✗ pytest 未安裝"
fi

echo ""
echo "=========================================="
echo "設置驗證完成！"
echo "=========================================="
echo ""
echo "快速開始:"
echo "  本地測試: make test"
echo "  覆蓋率:   make test-cov"
echo "  Docker:   make test-docker"
echo "  uv 快速:  make test-uv"
echo ""
echo "詳細說明請參閱:"
echo "  - TESTING_QUICK_START.md"
echo "  - TESTING.md"
echo "  - TEST_SETUP_SUMMARY.md"
echo ""
