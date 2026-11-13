# IMS v2：Python 3.13、Node.js 22、pnpm 9.12.0、uv、Docker Compose
.DEFAULT_GOAL := help
.PHONY: help install dev up down logs migrate gen-types test test-api test-web typecheck lint e2e audit

help: ## 顯示可用指令
	@awk 'BEGIN {FS = ":.*## "} /^[a-z0-9-]+:.*## / {printf "  %-14s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## 依 lockfile 安裝 API 測試依賴與 workspace 依賴
	cd apps/api && uv sync --frozen --extra test
	pnpm install --frozen-lockfile

dev: ## 啟動 Web 開發伺服器（API 需另開終端啟動）
	pnpm --filter @ims/web dev

up: gen-types ## 產生型別並建置、啟動 Compose 服務
	docker compose up -d --build

down: ## 停止 Compose 服務（保留 volumes）
	docker compose down

logs: ## 追蹤 Compose 服務日誌
	docker compose logs -f

migrate: ## 將本機 API 資料庫遷移至 head
	cd apps/api && .venv/bin/alembic upgrade head

gen-types: ## 匯出 OpenAPI 並產生 TypeScript 型別
	cd apps/api && .venv/bin/python scripts/export_openapi.py > ../../packages/api-types/openapi.json
	pnpm --filter @ims/api-types gen:types

test: test-api test-web ## 執行 API 與 Web 單元測試

test-api: ## 使用既有 API 虛擬環境執行 pytest
	cd apps/api && .venv/bin/python -m pytest -q

test-web: ## 執行 Web Vitest 測試
	pnpm --filter @ims/web test

typecheck: ## 檢查 workspace TypeScript 型別
	pnpm typecheck

lint: ## 執行 API ruff 與 workspace lint
	cd apps/api && .venv/bin/ruff check .
	pnpm lint

e2e: ## 執行 Playwright（需已啟動完整服務與安裝瀏覽器）
	pnpm --filter @ims/web test:e2e

audit: ## 稽核鎖定的 Python 與正式 Node 依賴（需網路）
	@audit_file=$$(mktemp); trap 'rm -f "$$audit_file"' EXIT; \
	cd apps/api && uv lock --check && \
	uv export --extra test --no-hashes --no-emit-project -q > "$$audit_file" && \
	uvx pip-audit -r "$$audit_file" --no-deps --disable-pip
	pnpm audit --prod --audit-level=high
