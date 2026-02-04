# 測試快速開始指南

本指南幫助你快速開始測試物品管理系統。

## 🚀 快速開始

### 選項 1: Docker（推薦用於 CI/CD）

```bash
# 執行完整測試套件
make test-docker

# 或直接使用腳本
./run_tests.sh
```

### 選項 2: uv（推薦用於本地開發）

```bash
# 快速執行測試
make test-uv

# 或直接使用腳本
./run_tests_uv.sh
```

### 選項 3: 傳統方式

```bash
# 安裝依賴
make install

# 執行測試
make test

# 執行測試並查看覆蓋率
make test-cov
```

## 📊 測試覆蓋率

執行測試後，打開覆蓋率報告：

```bash
# macOS
open htmlcov/index.html

# Linux
xdg-open htmlcov/index.html

# Windows
start htmlcov/index.html
```

## 🔍 執行特定測試

```bash
# 只測試通知模組
pytest tests/test_notifications.py -v

# 只測試旅行模組
pytest tests/test_travel.py -v

# 測試特定功能
pytest tests/test_notifications.py::NotificationsTestCase::test_get_settings_authenticated -v
```

## 🐛 開發模式

開發新功能時，使用監視模式自動執行測試：

```bash
make test-watch
```

## 📝 測試清單

- ✅ **test_items.py** - 物品管理
- ✅ **test_user_service.py** - 使用者服務
- ✅ **test_location_service.py** - 位置管理
- ✅ **test_type_service.py** - 類型管理
- ✅ **test_validators.py** - 資料驗證
- ✅ **test_routes.py** - 路由與認證
- ✅ **test_notifications.py** - 通知系統
- ✅ **test_travel.py** - 旅行管理
- ✅ **test_api.py** - API 文檔

## 🛠️ 疑難排解

### 問題：測試失敗找不到模組

```bash
# 重新安裝依賴
make clean
make install
```

### 問題：Docker 測試無法啟動

```bash
# 清理並重建
docker-compose -f docker-compose.test.yml down -v
docker-compose -f docker-compose.test.yml build --no-cache
```

### 問題：權限錯誤

```bash
# 給予執行權限
chmod +x run_tests.sh run_tests_uv.sh
```

## 📚 更多資訊

詳細測試文檔請參閱 [TESTING.md](TESTING.md)

## 🎯 測試目標

- 單元測試覆蓋率 > 80%
- 所有 API 端點有測試
- 所有服務層有測試
- 關鍵業務邏輯有測試

## 🤝 貢獻

新增功能時請同時新增測試：

1. 在 `tests/` 目錄新增測試文件
2. 遵循現有測試的命名和結構
3. 使用中文註解說明測試目的
4. 確保測試通過後再提交

## ⚙️ CI/CD 整合

測試已配置可直接用於 CI/CD：

```yaml
# GitHub Actions 範例
- name: Run tests
  run: make test-docker
```

## 📞 需要幫助？

查看完整文檔：
- [TESTING.md](TESTING.md) - 完整測試說明
- [README.md](README.md) - 專案說明
- [SETUP.md](SETUP.md) - 環境設置

---

**快速命令參考**

| 命令 | 說明 |
|------|------|
| `make test` | 本地執行測試 |
| `make test-cov` | 測試 + 覆蓋率報告 |
| `make test-docker` | Docker 中執行測試 |
| `make test-uv` | 使用 uv 快速測試 |
| `make test-watch` | 監視模式自動測試 |
