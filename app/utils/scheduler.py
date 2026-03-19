"""通知任務調度模組"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

from app.services import notification_service


scheduler = None


def init_scheduler():
    """初始化定時任務調度器"""
    if scheduler is not None and scheduler.running:
        return

    current_scheduler = BackgroundScheduler()

    # 每小時檢查一次（可以根據需要調整）
    current_scheduler.add_job(
        func=check_notifications_job,
        trigger=CronTrigger(minute="0"),
        id="check_notifications",
        name="檢查並發送到期通知",
        replace_existing=True,
    )

    # 每日 09:00 檢查逾期借出
    current_scheduler.add_job(
        func=check_overdue_loans_job,
        trigger=CronTrigger(hour="9", minute="0"),
        id="check_overdue_loans",
        name="檢查逾期借出提醒",
        replace_existing=True,
    )

    current_scheduler.start()
    globals()["scheduler"] = current_scheduler
    print(f"✅ 通知調度器已啟動 - {datetime.now()}")


def shutdown_scheduler():
    """關閉定時任務調度器"""
    if scheduler and scheduler.running:
        scheduler.shutdown()
        print("✅ 通知調度器已關閉")


def check_notifications_job():
    """檢查並發送通知的定時任務"""
    try:
        results = notification_service.check_and_send_notifications()

        if results["total_notifications"] > 0:
            print(f"📧 通知任務執行完成: 發送 {results['total_notifications']} 個通知給 {results['success_users']} 個使用者")

    except Exception as e:
        print(f"❌ 通知任務執行失敗: {e}")


def check_overdue_loans_job():
    """每日檢查逾期借出並發出提醒"""
    try:
        from app.services.loan_service import check_and_notify_overdue
        check_and_notify_overdue()
    except Exception as e:
        print(f"❌ 逾期借出檢查任務失敗: {e}")
