# ============================================================
# 物品管理系統 Makefile
# ============================================================
#
# 常用命令:
#   make install    安裝依賴
#   make run        啟動應用程式
#   make setup      初始化資料庫
#   make docker-up  Docker 啟動
#   make help       顯示說明
#
# ============================================================

.PHONY: help install run setup docker-up docker-down docker-logs docker-build clean test lint check

# 預設目標
.DEFAULT_GOAL := help

# 顏色定義
BLUE := \033[34m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
NC := \033[0m # No Color

# ============================================================
# 說明
# ============================================================

help: ## 顯示此說明
	@echo ""
	@echo "$(BLUE)🏠 物品管理系統 - 可用命令$(NC)"
	@echo "$(BLUE)================================================$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-18s$(NC) %s\n", $$1, $$2}'
	@echo ""

# ============================================================
# 本地開發
# ============================================================

install: ## 安裝 Python 依賴
	@echo "$(BLUE)📦 安裝依賴...$(NC)"
	@if command -v uv >/dev/null 2>&1; then \
		echo "使用 uv 安裝..."; \
		uv venv venv 2>/dev/null || true; \
		. venv/bin/activate && uv pip install -r requirements.txt; \
	else \
		echo "使用 pip 安裝..."; \
		python3 -m venv venv 2>/dev/null || true; \
		. venv/bin/activate && pip install -r requirements.txt; \
	fi
	@echo "$(GREEN)✓ 安裝完成$(NC)"

run: ## 啟動應用程式（本地）
	@echo "$(BLUE)🚀 啟動應用程式...$(NC)"
	@. venv/bin/activate && python run.py

setup: ## 初始化資料庫（索引、管理員、範例資料）
	@echo "$(BLUE)🔧 初始化資料庫...$(NC)"
	@. venv/bin/activate && python scripts/setup.py all

setup-indexes: ## 只建立資料庫索引
	@. venv/bin/activate && python scripts/setup.py indexes

setup-admin: ## 只建立管理員帳號
	@. venv/bin/activate && python scripts/setup.py admin

setup-sample: ## 建立範例資料
	@. venv/bin/activate && python scripts/setup.py sample

check: ## 檢查系統狀態
	@. venv/bin/activate && python scripts/setup.py check

# ============================================================
# Docker 操作
# ============================================================

docker-build: ## 建置 Docker 映像
	@echo "$(BLUE)🐳 建置 Docker 映像...$(NC)"
	docker-compose build

docker-up: ## 啟動 Docker 容器
	@echo "$(BLUE)🐳 啟動 Docker 容器...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ 容器已啟動$(NC)"
	@echo ""
	@echo "$(YELLOW)🌐 訪問: http://localhost:8080$(NC)"
	@echo "$(YELLOW)👤 登入: admin / admin$(NC)"

docker-down: ## 停止 Docker 容器
	@echo "$(BLUE)🐳 停止 Docker 容器...$(NC)"
	docker-compose down

docker-restart: ## 重啟 Docker 容器
	@echo "$(BLUE)🐳 重啟 Docker 容器...$(NC)"
	docker-compose restart

docker-logs: ## 查看 Docker 日誌
	docker-compose logs -f

docker-logs-app: ## 查看應用程式日誌
	docker-compose logs -f app

docker-shell: ## 進入應用程式容器
	docker-compose exec app /bin/sh

docker-mongo: ## 進入 MongoDB shell
	docker-compose exec mongo mongosh myDB

docker-setup: ## 在 Docker 中初始化資料庫
	@echo "$(BLUE)🔧 在 Docker 中初始化資料庫...$(NC)"
	docker-compose exec app python scripts/init_db.py

docker-rebuild: ## 重建並重啟 Docker 容器
	@echo "$(BLUE)🐳 重建 Docker 容器...$(NC)"
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d
	@echo "$(GREEN)✓ 重建完成$(NC)"

# ============================================================
# 測試與品質
# ============================================================

test: ## 執行測試
	@echo "$(BLUE)🧪 執行測試...$(NC)"
	@. venv/bin/activate && python -m pytest tests/ -v

lint: ## 程式碼檢查
	@echo "$(BLUE)🔍 程式碼檢查...$(NC)"
	@. venv/bin/activate && python -m flake8 app/ --max-line-length=100 || true

# ============================================================
# 清理
# ============================================================

clean: ## 清理暫存檔案
	@echo "$(BLUE)🧹 清理暫存檔案...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name ".DS_Store" -delete 2>/dev/null || true
	@echo "$(GREEN)✓ 清理完成$(NC)"

clean-all: clean ## 清理所有（包含 venv）
	@echo "$(RED)⚠️  刪除虛擬環境...$(NC)"
	rm -rf venv/
	@echo "$(GREEN)✓ 完全清理完成$(NC)"

# ============================================================
# 快捷命令
# ============================================================

dev: install setup run ## 完整開發環境設置並啟動

prod: docker-build docker-up docker-setup ## 生產環境部署

