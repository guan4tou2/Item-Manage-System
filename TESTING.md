# 測試說明

本專案包含完整的單元測試套件，涵蓋服務層、驗證器和路由層的功能測試。

## 測試結構

```
tests/
├── __init__.py
├── test_items.py          # 物品服務測試
├── test_user_service.py   # 使用者服務測試
├── test_location_service.py  # 位置服務測試
├── test_type_service.py   # 類型服務測試
├── test_validators.py     # 驗證器測試
└── test_routes.py         # 路由層測試
```

## 執行測試

### 方法 1: 使用 run_tests.py

```bash
python3 run_tests.py
```

### 方法 2: 使用 unittest

```bash
python3 -m unittest discover tests
```

### 方法 3: 執行單個測試文件

```bash
python3 -m unittest tests.test_items
python3 -m unittest tests.test_user_service
python3 -m unittest tests.test_location_service
python3 -m unittest tests.test_type_service
python3 -m unittest tests.test_validators
python3 -m unittest tests.test_routes
```

### 方法 4: 執行特定測試案例

```bash
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

## 測試設計原則

1. **隔離性**: 每個測試都是獨立的，使用模擬的 repository 避免依賴真實資料庫
2. **可重複性**: 測試可以在任何環境中執行，不依賴外部狀態
3. **完整性**: 涵蓋正常流程、邊界情況和錯誤處理
4. **可讀性**: 測試名稱清楚描述測試目的，使用中文註解

## 注意事項

1. 測試不需要真實的 MongoDB 連接，所有資料庫操作都被模擬
2. 路由測試需要 Flask 應用程式上下文，已在 setUp 中處理
3. CSRF 保護在測試中被禁用（`WTF_CSRF_ENABLED = False`）
4. 測試使用 `unittest.mock.patch` 來模擬外部依賴

## 持續整合

建議在 CI/CD 流程中加入測試執行：

```yaml
# 範例 GitHub Actions
- name: Run tests
  run: python3 run_tests.py
```

