"""旅行模組測試"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Setup test environment
import tests.conftest  # noqa: F401

from app import create_app, db
from app.models import Travel, TravelGroup, TravelItem, ShoppingList, ShoppingItem


class TravelTestCase(unittest.TestCase):
    """旅行路由測試"""

    def setUp(self):
        """測試前設置"""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self):
        """測試後清理"""
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_list_page_requires_auth(self):
        """測試旅行列表頁面需要登入"""
        response = self.client.get('/travel/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/signin', response.location)

    def test_list_page_authenticated(self):
        """測試已登入用戶訪問旅行列表頁面"""
        with self.client.session_transaction() as sess:
            sess['UserID'] = 'testuser'

        response = self.client.get('/travel/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'testuser', response.data)

    def test_create_travel_requires_auth(self):
        """測試建立旅行需要登入"""
        response = self.client.post('/travel/create',
                                    data={'name': 'Test Travel'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('/signin', response.location)

    def test_create_travel_success(self):
        """測試成功建立旅行"""
        with self.client.session_transaction() as sess:
            sess['UserID'] = 'testuser'

        response = self.client.post('/travel/create',
                                    data={
                                        'name': 'Test Travel',
                                        'start_date': '2024-01-01',
                                        'end_date': '2024-01-07',
                                        'note': 'Test note'
                                    })
        self.assertEqual(response.status_code, 302)
        
        travel = Travel.query.filter_by(name='Test Travel').first()
        self.assertIsNotNone(travel)
        self.assertEqual(travel.owner, 'testuser')

    def test_create_travel_without_name(self):
        """測試建立旅行時沒有名稱"""
        with self.client.session_transaction() as sess:
            sess['UserID'] = 'testuser'

        response = self.client.post('/travel/create', data={})
        self.assertEqual(response.status_code, 302)
        self.assertIn('/travel/', response.location)

    def test_travel_detail_authenticated(self):
        """測試查看旅行詳情"""
        travel = Travel(name='Test Travel', owner='testuser')
        db.session.add(travel)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['UserID'] = 'testuser'

        response = self.client.get(f'/travel/{travel.id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Test Travel', response.data)

    def test_add_group_to_travel(self):
        """測試為旅行新增分組"""
        travel = Travel(name='Test Travel', owner='testuser')
        db.session.add(travel)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['UserID'] = 'testuser'

        response = self.client.post(f'/travel/{travel.id}/group',
                                    data={'name': 'Clothes', 'sort_order': 1})
        self.assertEqual(response.status_code, 302)

        group = TravelGroup.query.filter_by(travel_id=travel.id, name='Clothes').first()
        self.assertIsNotNone(group)

    def test_add_item_to_travel(self):
        """測試為旅行新增物品"""
        travel = Travel(name='Test Travel', owner='testuser')
        db.session.add(travel)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['UserID'] = 'testuser'

        response = self.client.post(f'/travel/{travel.id}/item',
                                    data={
                                        'name': 'Passport',
                                        'qty_required': 1,
                                        'qty_packed': 0
                                    })
        self.assertEqual(response.status_code, 302)

        item = TravelItem.query.filter_by(travel_id=travel.id, name='Passport').first()
        self.assertIsNotNone(item)

    def test_add_item_without_name(self):
        """測試新增物品時沒有名稱"""
        travel = Travel(name='Test Travel', owner='testuser')
        db.session.add(travel)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['UserID'] = 'testuser'

        response = self.client.post(f'/travel/{travel.id}/item', data={})
        self.assertEqual(response.status_code, 302)

    def test_update_travel_item(self):
        """測試更新旅行物品"""
        travel = Travel(name='Test Travel', owner='testuser')
        db.session.add(travel)
        db.session.flush()

        item = TravelItem(travel_id=travel.id, name='Passport',
                         qty_required=1, qty_packed=0, carried=False)
        db.session.add(item)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['UserID'] = 'testuser'

        response = self.client.post(f'/travel/{travel.id}/items/{item.id}/update',
                                    data={'toggle_carried': 'true'})
        self.assertEqual(response.status_code, 302)

        db.session.refresh(item)
        self.assertTrue(item.carried)

    def test_delete_travel_item(self):
        """測試刪除旅行物品"""
        travel = Travel(name='Test Travel', owner='testuser')
        db.session.add(travel)
        db.session.flush()

        item = TravelItem(travel_id=travel.id, name='Passport', qty_required=1)
        db.session.add(item)
        db.session.commit()

        item_id = item.id

        with self.client.session_transaction() as sess:
            sess['UserID'] = 'testuser'

        response = self.client.post(f'/travel/{travel.id}/items/{item_id}/delete')
        self.assertEqual(response.status_code, 302)

        deleted_item = TravelItem.query.get(item_id)
        self.assertIsNone(deleted_item)

    def test_list_travels_api(self):
        """測試 API 列出旅行"""
        travel = Travel(name='Test Travel', owner='testuser')
        db.session.add(travel)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['UserID'] = 'testuser'

        response = self.client.get('/travel/api')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('items', data)
        self.assertEqual(len(data['items']), 1)

    def test_create_travel_api(self):
        """測試 API 建立旅行"""
        with self.client.session_transaction() as sess:
            sess['UserID'] = 'testuser'

        response = self.client.post('/travel/api',
                                    json={'name': 'API Travel'})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])

    def test_create_travel_api_without_name(self):
        """測試 API 建立旅行時沒有名稱"""
        with self.client.session_transaction() as sess:
            sess['UserID'] = 'testuser'

        response = self.client.post('/travel/api', json={})
        self.assertEqual(response.status_code, 400)

    def test_export_travel_csv(self):
        """測試匯出旅行清單 CSV"""
        travel = Travel(name='Test Travel', owner='testuser')
        db.session.add(travel)
        db.session.flush()

        item = TravelItem(travel_id=travel.id, name='Passport',
                         qty_required=1, qty_packed=1, carried=True)
        db.session.add(item)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['UserID'] = 'testuser'

        response = self.client.get(f'/travel/api/{travel.id}/export')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertIn(b'Passport', response.data)

    def test_travel_reminder(self):
        """測試旅行提醒 API"""
        travel = Travel(name='Test Travel', owner='testuser')
        db.session.add(travel)
        db.session.flush()

        item1 = TravelItem(travel_id=travel.id, name='Item1',
                          qty_required=1, qty_packed=1, carried=True)
        item2 = TravelItem(travel_id=travel.id, name='Item2',
                          qty_required=1, qty_packed=0, carried=False)
        db.session.add_all([item1, item2])
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['UserID'] = 'testuser'

        response = self.client.get(f'/travel/api/{travel.id}/reminder')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['total'], 2)
        self.assertEqual(data['pending'], 1)


class ShoppingListTestCase(unittest.TestCase):
    """購物清單測試"""

    def setUp(self):
        """測試前設置"""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self):
        """測試後清理"""
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_list_shopping_lists(self):
        """測試列出購物清單"""
        shopping_list = ShoppingList(title='Test List', owner='testuser')
        db.session.add(shopping_list)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['UserID'] = 'testuser'

        response = self.client.get('/shopping/api/lists')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('items', data)

    def test_create_shopping_list(self):
        """測試建立購物清單"""
        with self.client.session_transaction() as sess:
            sess['UserID'] = 'testuser'

        response = self.client.post('/shopping/api',
                                    json={'title': 'New Shopping List'})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])

    def test_add_shopping_item(self):
        """測試新增購物項目"""
        shopping_list = ShoppingList(title='Test List', owner='testuser')
        db.session.add(shopping_list)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['UserID'] = 'testuser'

        response = self.client.post(f'/shopping/api/{shopping_list.id}/items',
                                    json={'name': 'Test Item', 'qty': 2})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])

    def test_update_shopping_item(self):
        """測試更新購物項目"""
        shopping_list = ShoppingList(title='Test List', owner='testuser')
        db.session.add(shopping_list)
        db.session.flush()

        item = ShoppingItem(list_id=shopping_list.id, name='Item',
                           qty=1, status='todo')
        db.session.add(item)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['UserID'] = 'testuser'

        response = self.client.patch(f'/shopping/api/items/{item.id}',
                                     json={'status': 'done'})
        self.assertEqual(response.status_code, 200)
        
        db.session.refresh(item)
        self.assertEqual(item.status, 'done')

    def test_shopping_summary(self):
        """測試購物清單摘要"""
        shopping_list = ShoppingList(title='Test List', owner='testuser')
        db.session.add(shopping_list)
        db.session.flush()

        item1 = ShoppingItem(list_id=shopping_list.id, name='Item1', status='done')
        item2 = ShoppingItem(list_id=shopping_list.id, name='Item2', status='todo')
        db.session.add_all([item1, item2])
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['UserID'] = 'testuser'

        response = self.client.get(f'/shopping/api/{shopping_list.id}/summary')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['done'], 1)
        self.assertEqual(data['todo'], 1)


if __name__ == '__main__':
    unittest.main()
