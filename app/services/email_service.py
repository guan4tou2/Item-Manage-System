"""Email 通知服務模組"""
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

# Email 設定 (從環境變數讀取)
MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "")


def is_email_configured() -> bool:
    """檢查 Email 是否已設定"""
    return bool(MAIL_USERNAME and MAIL_PASSWORD)


def send_expiry_notification(
    to_email: str,
    expired_items: List[Dict[str, Any]],
    near_expiry_items: List[Dict[str, Any]],
    replacement_due: Optional[List[Dict[str, Any]]] = None,
    replacement_upcoming: Optional[List[Dict[str, Any]]] = None,
) -> bool:
    """
    發送到期提醒 Email
    
    參數:
        to_email: 收件人 Email
        expired_items: 已過期物品列表
        near_expiry_items: 即將到期物品列表
    
    回傳:
        是否發送成功
    """
    if not is_email_configured():
        print("⚠️ Email 未設定，跳過發送")
        return False
    
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # 建立郵件
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🔔 物品到期提醒 - {datetime.now().strftime('%Y-%m-%d')}"
        msg["From"] = MAIL_DEFAULT_SENDER or MAIL_USERNAME
        msg["To"] = to_email
        
        # 純文字版本
        text_content = generate_text_content(
            expired_items,
            near_expiry_items,
            replacement_due=replacement_due,
            replacement_upcoming=replacement_upcoming,
        )
        
        # HTML 版本
        html_content = generate_html_content(
            expired_items,
            near_expiry_items,
            replacement_due=replacement_due,
            replacement_upcoming=replacement_upcoming,
        )
        
        msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))
        
        # 發送郵件
        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as server:
            if MAIL_USE_TLS:
                server.starttls()
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.send_message(msg)
        
        print(f"✅ Email 發送成功: {to_email}")
        return True
        
    except Exception as e:
        print(f"❌ Email 發送失敗: {e}")
        return False


def generate_text_content(
    expired_items: List[Dict[str, Any]],
    near_expiry_items: List[Dict[str, Any]],
    replacement_due: Optional[List[Dict[str, Any]]] = None,
    replacement_upcoming: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """產生純文字內容"""
    lines = [
        "物品提醒",
        "=" * 40,
        "",
    ]
    
    if expired_items:
        lines.append(f"⚠️ 已過期物品 ({len(expired_items)} 項):")
        lines.append("-" * 30)
        for item in expired_items:
            lines.append(f"  • {item.get('ItemName', '未知物品')}")
            if item.get("WarrantyExpiry"):
                lines.append(f"    保固到期: {item['WarrantyExpiry']}")
            if item.get("UsageExpiry"):
                lines.append(f"    使用期限: {item['UsageExpiry']}")
            lines.append("")
    
    if near_expiry_items:
        lines.append(f"⏰ 即將到期物品 ({len(near_expiry_items)} 項):")
        lines.append("-" * 30)
        for item in near_expiry_items:
            lines.append(f"  • {item.get('ItemName', '未知物品')}")
            if item.get("WarrantyExpiry"):
                lines.append(f"    保固到期: {item['WarrantyExpiry']}")
            if item.get("UsageExpiry"):
                lines.append(f"    使用期限: {item['UsageExpiry']}")
            lines.append("")

    if replacement_due:
        lines.append(f"🧺 需要更換 ({len(replacement_due)} 項):")
        lines.append("-" * 30)
        for item in replacement_due:
            lines.append(f"  • {item.get('ItemName', '未知物品')} (規則: {item.get('rule_name','')}, 已 {item.get('days_since',0)} 天)")
        lines.append("")

    if replacement_upcoming:
        lines.append(f"⏳ 即將更換 ({len(replacement_upcoming)} 項):")
        lines.append("-" * 30)
        for item in replacement_upcoming:
            lines.append(f"  • {item.get('ItemName', '未知物品')} (剩餘 {item.get('days_remaining',0)} 天，規則: {item.get('rule_name','')})")
        lines.append("")
    
    lines.extend([
        "",
        "請登入系統查看詳情並進行處理。",
        "",
        "---",
        "此郵件由物品管理系統自動發送",
    ])
    
    return "\n".join(lines)


def generate_html_content(
    expired_items: List[Dict[str, Any]],
    near_expiry_items: List[Dict[str, Any]],
    replacement_due: Optional[List[Dict[str, Any]]] = None,
    replacement_upcoming: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """產生 HTML 內容"""
    expired_rows = ""
    replacement_due = replacement_due or []
    replacement_upcoming = replacement_upcoming or []
    for item in expired_items:
        expired_rows += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #eee;">
                <strong>{item.get('ItemName', '未知物品')}</strong>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #eee;">
                {item.get('WarrantyExpiry', '-')}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #eee;">
                {item.get('UsageExpiry', '-')}
            </td>
        </tr>
        """
    
    near_rows = ""
    for item in near_expiry_items:
        near_rows += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #eee;">
                <strong>{item.get('ItemName', '未知物品')}</strong>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #eee;">
                {item.get('WarrantyExpiry', '-')}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #eee;">
                {item.get('UsageExpiry', '-')}
            </td>
        </tr>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
    </head>
    <body style="font-family: 'Noto Sans TC', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
            <h1 style="margin: 0; font-size: 24px;">🔔 物品到期提醒</h1>
            <p style="margin: 10px 0 0; opacity: 0.9;">{datetime.now().strftime('%Y年%m月%d日')}</p>
        </div>
        
        <div style="background: #fff; padding: 30px; border: 1px solid #eee; border-top: none; border-radius: 0 0 10px 10px;">
    """
    
    if expired_items:
        html += f"""
            <div style="margin-bottom: 30px;">
                <h2 style="color: #dc3545; font-size: 18px; margin-bottom: 15px;">
                    ⚠️ 已過期物品 ({len(expired_items)} 項)
                </h2>
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: #fef2f2;">
                            <th style="padding: 12px; text-align: left; border-bottom: 2px solid #dc3545;">物品名稱</th>
                            <th style="padding: 12px; text-align: left; border-bottom: 2px solid #dc3545;">保固到期</th>
                            <th style="padding: 12px; text-align: left; border-bottom: 2px solid #dc3545;">使用期限</th>
                        </tr>
                    </thead>
                    <tbody>
                        {expired_rows}
                    </tbody>
                </table>
            </div>
        """
    
    if near_expiry_items:
        html += f"""
            <div style="margin-bottom: 30px;">
                <h2 style="color: #ffc107; font-size: 18px; margin-bottom: 15px;">
                    ⏰ 即將到期物品 ({len(near_expiry_items)} 項)
                </h2>
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: #fffbeb;">
                            <th style="padding: 12px; text-align: left; border-bottom: 2px solid #ffc107;">物品名稱</th>
                            <th style="padding: 12px; text-align: left; border-bottom: 2px solid #ffc107;">保固到期</th>
                            <th style="padding: 12px; text-align: left; border-bottom: 2px solid #ffc107;">使用期限</th>
                        </tr>
                    </thead>
                    <tbody>
                        {near_rows}
                    </tbody>
                </table>
            </div>
        """

    if replacement_due:
        due_rows = "".join(
            f"""
            <tr>
                <td style=\"padding: 12px; border-bottom: 1px solid #eee;\">{item.get('ItemName','未知物品')}</td>
                <td style=\"padding: 12px; border-bottom: 1px solid #eee;\">{item.get('rule_name','')}</td>
                <td style=\"padding: 12px; border-bottom: 1px solid #eee;\">已 {item.get('days_since',0)} 天</td>
            </tr>
            """
            for item in replacement_due
        )
        html += f"""
            <div style="margin-bottom: 30px;">
                <h2 style="color: #0d6efd; font-size: 18px; margin-bottom: 15px;">
                    🧺 需要更換 ({len(replacement_due)} 項)
                </h2>
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: #eef4ff;">
                            <th style="padding: 12px; text-align: left; border-bottom: 2px solid #0d6efd;">物品名稱</th>
                            <th style="padding: 12px; text-align: left; border-bottom: 2px solid #0d6efd;">規則</th>
                            <th style="padding: 12px; text-align: left; border-bottom: 2px solid #0d6efd;">已使用天數</th>
                        </tr>
                    </thead>
                    <tbody>
                        {due_rows}
                    </tbody>
                </table>
            </div>
        """

    if replacement_upcoming:
        upcoming_rows = "".join(
            f"""
            <tr>
                <td style=\"padding: 12px; border-bottom: 1px solid #eee;\">{item.get('ItemName','未知物品')}</td>
                <td style=\"padding: 12px; border-bottom: 1px solid #eee;\">{item.get('rule_name','')}</td>
                <td style=\"padding: 12px; border-bottom: 1px solid #eee;\">剩餘 {item.get('days_remaining',0)} 天</td>
            </tr>
            """
            for item in replacement_upcoming
        )
        html += f"""
            <div style="margin-bottom: 30px;">
                <h2 style="color: #20c997; font-size: 18px; margin-bottom: 15px;">
                    ⏳ 即將更換 ({len(replacement_upcoming)} 項)
                </h2>
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: #e8fff6;">
                            <th style="padding: 12px; text-align: left; border-bottom: 2px solid #20c997;">物品名稱</th>
                            <th style="padding: 12px; text-align: left; border-bottom: 2px solid #20c997;">規則</th>
                            <th style="padding: 12px; text-align: left; border-bottom: 2px solid #20c997;">剩餘天數</th>
                        </tr>
                    </thead>
                    <tbody>
                        {upcoming_rows}
                    </tbody>
                </table>
            </div>
        """
    
    html += """
            <div style="text-align: center; margin-top: 30px;">
                <p style="color: #666;">請登入系統查看詳情並進行處理</p>
            </div>
        </div>
        
        <div style="text-align: center; padding: 20px; color: #999; font-size: 12px;">
            <p>此郵件由物品管理系統自動發送</p>
        </div>
    </body>
    </html>
    """
    
    return html


def send_test_email(to_email: str) -> bool:
    """發送測試 Email"""
    if not is_email_configured():
        return False
    
    try:
        import smtplib
        from email.mime.text import MIMEText
        
        msg = MIMEText("這是一封測試郵件，用於確認 Email 設定是否正確。")
        msg["Subject"] = "🔔 物品管理系統 - 測試郵件"
        msg["From"] = MAIL_DEFAULT_SENDER or MAIL_USERNAME
        msg["To"] = to_email
        
        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as server:
            if MAIL_USE_TLS:
                server.starttls()
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.send_message(msg)
        
        return True
    except Exception as e:
        print(f"❌ 測試郵件發送失敗: {e}")
        return False

