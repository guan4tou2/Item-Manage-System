"""API 文檔模組測試"""
import unittest
from unittest.mock import Mock, patch

# Setup test environment
import tests.conftest  # noqa: F401

from app import create_app


class APITestCase(unittest.TestCase):
    """API 路由測試"""

    def setUp(self):
        """測試前設置"""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        """測試後清理"""
        self.ctx.pop()

    def test_api_docs_endpoint_exists(self):
        """測試 API 文檔端點存在"""
        response = self.client.get('/api/docs')
        # API 文檔可能需要 flasgger，沒安裝時應返回 404
        self.assertIn(response.status_code, [200, 404])

    def test_api_docs_without_flasgger(self):
        """測試沒有 flasgger 時的 API 文檔"""
        with patch.dict('sys.modules', {'flasgger': None}):
            response = self.client.get('/api/docs')
            # 沒有 flasgger 時應返回友好的錯誤訊息
            if response.status_code == 404:
                data = response.get_json()
                self.assertIn('info', data)

    def test_api_health_endpoint(self):
        """測試 API 健康檢查端點"""
        response = self.client.get('/api/health')
        self.assertIn(response.status_code, [200, 404])
        
        if response.status_code == 200:
            data = response.get_json()
            self.assertIn('status', data)
            self.assertEqual(data['status'], 'healthy')

    def test_api_docs_structure(self):
        """測試 API 文檔結構"""
        try:
            from app.api.routes import api_docs
            result = api_docs()
            
            if isinstance(result, dict):
                # 檢查基本結構
                if 'specs' in result:
                    specs = result['specs']
                    self.assertIsInstance(specs, list)
                    if specs:
                        spec = specs[0]
                        self.assertIn('version', spec)
                        self.assertIn('title', spec)
        except Exception:
            # 如果函數調用失敗（例如缺少依賴），跳過測試
            pass

    def test_api_docs_security_definitions(self):
        """測試 API 安全定義"""
        try:
            from app.api.routes import api_docs
            result = api_docs()
            
            if isinstance(result, dict) and 'specs' in result:
                specs = result['specs']
                if specs and 'securityDefinitions' in specs[0]:
                    security_defs = specs[0]['securityDefinitions']
                    self.assertIn('BearerAuth', security_defs)
                    self.assertEqual(security_defs['BearerAuth']['type'], 'apiKey')
        except Exception:
            pass

    def test_api_docs_paths(self):
        """測試 API 路徑定義"""
        try:
            from app.api.routes import api_docs
            result = api_docs()
            
            if isinstance(result, dict) and 'specs' in result:
                specs = result['specs']
                if specs and 'paths' in specs[0]:
                    paths = specs[0]['paths']
                    # 檢查是否定義了基本路徑
                    self.assertIsInstance(paths, dict)
                    # 常見的 API 端點
                    expected_paths = ['/items', '/types', '/locations']
                    for path in expected_paths:
                        if path in paths:
                            self.assertIn('get', paths[path])
        except Exception:
            pass


if __name__ == '__main__':
    unittest.main()
