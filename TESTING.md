# 測試說明

本專案包含完整的單元測試套件，涵蓋服務層、驗證器和路由層的功能測試。

## 測試結構

```
tests/
├── __init__.py
├── conftest.py                # 測試配置和 fixtures
├── fixtures_env.py            # 環境設置
├── test_items.py              # 物品服務測試
├── test_user_service.py       # 使用者服務測試
├── test_location_service.py   # 位置服務測試
├── test_type_service.py       # 類型服務測試
├── test_validators.py         # 驗證器測試
├── test_routes.py             # 路由層測試
├── test_notifications.py      # 通知模組測試 (NEW)
├── test_travel.py             # 旅行模組測試 (NEW)
└── test_api.py                # API 文檔測試 (NEW)
```

## 執行測試

### 方法 1: 使用 Makefile（推薦）

```bash
# 本地執行測試
make test

# 執行測試並生成覆蓋率報告
make test-cov

# 在 Docker 中執行測試
make test-docker

# 使用 uv 執行測試（快速）
make test-uv

# 監視模式（自動重新執行）
make test-watch
```

### 方法 2: 使用 Docker Compose

```bash
# 使用 Docker Compose 執行完整測試環境
docker-compose -f docker-compose.test.yml build
docker-compose -f docker-compose.test.yml run --rm test

# 執行特定測試
docker-compose -f docker-compose.test.yml run --rm test pytest tests/test_notifications.py -v
```

### 方法 3: 使用 uv（本地快速執行）

```bash
# 執行腳本
./run_tests_uv.sh

# 或手動執行
uv pip install pytest pytest-cov pytest-mock pytest-flask pytest-env
pytest -v --cov=app --cov-report=html
```

### 方法 4: 使用 pytest 直接執行

```bash
# 啟動虛擬環境
source venv/bin/activate

# 執行所有測試
pytest -v

# 執行特定測試文件
pytest tests/test_notifications.py -v

# 執行特定測試案例
pytest tests/test_notifications.py::NotificationsTestCase::test_get_settings_authenticated -v

# 執行測試並生成覆蓋率
pytest --cov=app --cov-report=html --cov-report=term-missing

# 執行測試並顯示詳細輸出
pytest -vv -s
```

### 方法 5: 使用傳統 unittest

```bash
python3 -m unittest discover tests
python3 -m unittest tests.test_items
python3 -m unittest tests.test_items.ItemServiceTestCase.test_search_by_name
```

## 測試覆蓋範圍

### 1. 物品服務測試 (test_items.py)
- ✅ 依名稱、位置、類型搜尋
- ✅ 依樓層、房間、區域搜尋
- ✅ 依保固期限、使用期限、名稱排序
- ✅ 分頁功能
- ✅ 取得單個物品
- ✅ 建立、更新、刪除物品
- ✅ 過期狀態註解

### 2. 使用者服務測試 (test_user_service.py)
- ✅ 使用雜湊密碼認證
- ✅ 明文密碼自動升級為雜湊
- ✅ 使用者不存在的情況
- ✅ 錯誤密碼處理
- ✅ 建立使用者（成功/重複）
- ✅ 建立管理員使用者
- ✅ 取得使用者資訊
- ✅ 密碼雜湊功能

### 3. 位置服務測試 (test_location_service.py)
- ✅ 列出所有位置
- ✅ 列出選擇選項（樓層、房間、區域）
- ✅ 建立位置（成功/失敗/重複）
- ✅ 刪除位置
- ✅ 更新位置

### 4. 類型服務測試 (test_type_service.py)
- ✅ 列出所有類型
- ✅ 建立類型

### 5. 驗證器測試 (test_validators.py)
- ✅ 必填欄位驗證
- ✅ 物品類型驗證
- ✅ 位置欄位驗證（樓層、房間、區域）
- ✅ 日期格式驗證
- ✅ 可選欄位處理

### 6. 路由層測試 (test_routes.py)
- ✅ 登入頁面 GET/POST
- ✅ 登入成功/失敗處理
- ✅ 登出功能
- ✅ 需要登入的頁面保護
- ✅ 需要管理員權限的頁面保護

### 7. 通知模組測試 (test_notifications.py) 🆕
- ✅ 通知設定頁面認證保護
- ✅ 取得通知設定 API
- ✅ 更新通知設定 API
- ✅ 解析替換間隔字串
- ✅ 手動發送通知 API
- ✅ 通知摘要 API
- ✅ 成功/失敗情況處理

### 8. 旅行模組測試 (test_travel.py) 🆕
- ✅ 旅行列表頁面認證
- ✅ 建立/查看/更新旅行
- ✅ 新增/更新/刪除旅行分組
- ✅ 新增/更新/刪除旅行物品
- ✅ CSV 匯出功能
- ✅ 旅行提醒 API
- ✅ 購物清單管理
- ✅ 購物項目 CRUD
- ✅ 購物清單摘要

### 9. API 文檔測試 (test_api.py) 🆕
- ✅ API 文檔端點測試
- ✅ 健康檢查端點
- ✅ API 結構驗證
- ✅ 安全定義檢查
- ✅ 路徑定義檢查

## 測試設計原則

1. **隔離性**: 每個測試都是獨立的，使用模擬的 repository 避免依賴真實資料庫
2. **可重複性**: 測試可以在任何環境中執行，不依賴外部狀態
3. **完整性**: 涵蓋正常流程、邊界情況和錯誤處理
4. **可讀性**: 測試名稱清楚描述測試目的，使用中文註解

## 測試環境

### Docker 測試環境
使用 `docker-compose.test.yml` 配置獨立的測試環境：
- 獨立的 PostgreSQL 測試數據庫
- 獨立的 Redis 測試實例
- 獨立的 MongoDB 測試實例
- 使用 tmpfs 提高測試速度

### 本地測試環境
使用 pytest 配置在 `pyproject.toml` 中：
- 自動設置測試環境變數
- 自動生成覆蓋率報告
- 支援多種報告格式（term, html, xml）

## 覆蓋率報告

執行測試後查看覆蓋率：

```bash
# 終端顯示
pytest --cov=app --cov-report=term-missing

# HTML 報告（推薦）
pytest --cov=app --cov-report=html
open htmlcov/index.html

# XML 報告（用於 CI/CD）
pytest --cov=app --cov-report=xml
```

## 注意事項

1. 測試不需要真實的資料庫連接，所有資料庫操作都被模擬
2. 路由測試需要 Flask 應用程式上下文，已在 setUp 中處理
3. CSRF 保護在測試中被禁用（`WTF_CSRF_ENABLED = False`）
4. 測試使用 `unittest.mock.patch` 來模擬外部依賴
5. Docker 測試環境使用 tmpfs 提高測試速度

## 持續整合

### GitHub Actions 範例

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Build and run tests
      run: |
        docker-compose -f docker-compose.test.yml build
        docker-compose -f docker-compose.test.yml run --rm test
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        files: ./coverage.xml
```

## 開發測試流程

1. **開發新功能時**:
   ```bash
   # 使用監視模式，自動執行相關測試
   make test-watch
   ```

2. **提交前檢查**:
   ```bash
   # 執行完整測試和覆蓋率檢查
   make test-cov
   ```

3. **CI/CD 流程**:
   ```bash
   # 使用 Docker 確保環境一致
   make test-docker
   ```

## 疑難排解

### 測試失敗：ModuleNotFoundError

```bash
# 確保安裝了測試依賴
uv pip install pytest pytest-cov pytest-mock pytest-flask pytest-env
```

### Docker 測試無法啟動

```bash
# 清理並重建
docker-compose -f docker-compose.test.yml down -v
docker-compose -f docker-compose.test.yml build --no-cache
```

### 覆蓋率報告無法生成

```bash
# 確保安裝 pytest-cov
uv pip install pytest-cov

# 確保有寫入權限
chmod -R 755 htmlcov/
```

## 貢獻測試

新增測試時請遵循：
1. 使用描述性的測試名稱
2. 包含中文註解說明測試目的
3. 測試正常流程和錯誤情況
4. 使用 mock 隔離外部依賴
5. 保持測試獨立性


