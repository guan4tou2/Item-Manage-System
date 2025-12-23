# 部署指南 (Deployment Guide)

本文件提供 **物品管理系統** 的詳細部署說明，包含「直接部署」、「Docker 部署」與「反向代理 (Proxy)」設定。

---

## 1. 直接部署 (Direct Deployment)

適用於 Linux 伺服器 (Ubuntu/Debian) 或 macOS 環境。

### 前置需求
*   Python 3.8+
*   MongoDB 4.4+ (需已安裝並啟動)

### 步驟

1.  **下載程式碼**
    ```bash
    git clone <repository-url>
    cd Item-Manage-System
    ```

2.  **建立虛擬環境**
    ```bash
    # 建立 venv
    python3 -m venv venv
    
    # 啟動 venv
    source venv/bin/activate
    ```

3.  **安裝依賴**
    ```bash
    pip install -r requirements.txt
    
    # 生產環境建議安裝 Gunicorn
    pip install gunicorn
    ```

4.  **設定環境變數**
    建立 `.env` 檔案或直接設定環境變數：
    ```bash
    export MONGO_URI="mongodb://localhost:27017/myDB"
    export SECRET_KEY="your-super-secret-key-change-this"
    ```

5.  **啟動服務 (Production)**
    使用 Gunicorn 啟動（建議 4 個 workers）：
    ```bash
    # 綁定 0.0.0.0:8080
    gunicorn -w 4 -b 0.0.0.0:8080 run:app
    ```
    現在，您可以通過 `http://你的IP:8080` 訪問系統。

---

## 2. Docker 部署

最簡單快速的部署方式，適合所有支援 Docker 的環境。

### 前置需求
*   Docker & Docker Compose

### 步驟

1.  **啟動容器**
    在專案根目錄執行：
    ```bash
    docker-compose up -d --build
    ```
    此命令會自動：
    *   建置應用程式映像檔
    *   啟動 MongoDB 資料庫容器
    *   建立應用程式容器並連接至資料庫

2.  **資料持久化**
    *   資料庫檔案預設儲存於 Docker Volume `mongo_data`，容器重啟或刪除後資料**不會**遺失。
    *   若需清除所有資料：`docker-compose down -v`

3.  **查看日誌**
    ```bash
    docker-compose logs -f
    ```

---

## 3. 反向代理設定 (Proxy Setup)

為了安全性與標準化，建議在 Flask/Gunicorn 前方架設 Nginx 反向代理，以提供 HTTPS 支援與標準 80/443 埠口訪問。

### Nginx 設定範例

1.  **安裝 Nginx**
    ```bash
    sudo apt update
    sudo apt install nginx
    ```

2.  **建立設定檔**
    編輯 `/etc/nginx/sites-available/item-system`：

    ```nginx
    server {
        listen 80;
        server_name your-domain.com;  # 請替換為您的域名或 IP

        location / {
            proxy_pass http://127.0.0.1:8080;  # 指向 Gunicorn 或 Docker 的埠口
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # 靜態檔案快取優化 (可選)
        location /static {
            alias /path/to/Item-Manage-System/static; # 若為直接部署
            expires 30d;
        }
    }
    ```

3.  **啟用設定並重啟**
    ```bash
    sudo ln -s /etc/nginx/sites-available/item-system /etc/nginx/sites-enabled/
    sudo nginx -t
    sudo systemctl restart nginx
    ```

### SSL 加密 (HTTPS)
強烈建議使用 Certbot 免費申請 SSL 憑證：
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## 4. 常見問題

*   **Q: 上傳的圖片在哪裡？**
    *   **直接部署**：在 `static/uploads/` 資料夾。
    *   **Docker**：在容器內的 `/workspace/static/uploads/`。若需備份圖片，建議修改 `docker-compose.yml` 將此目錄掛載出來。

*   **Q: 如何更改資料庫密碼？**
    *   請修改 `MONGO_URI` 環境變數，格式為 `mongodb://user:pass@host:port/dbname`。
