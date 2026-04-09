"""
通用邮件模板系统
支持自定义品牌信息
"""
from jinja2 import Template
from typing import Optional
import os


class EmailTemplateConfig:
    """邮件模板配置"""

    def __init__(self):
        # 从环境变量读取配置
        self.app_name = os.getenv("AUTH_EMAIL_APP_NAME", "AutoOverview")
        self.app_url = os.getenv("AUTH_EMAIL_APP_URL", "#")
        self.logo_emoji = os.getenv("AUTH_EMAIL_LOGO_EMOJI", "📚")
        self.contact_email = os.getenv("AUTH_EMAIL_CONTACT_EMAIL", "support@example.com")
        self.primary_color = os.getenv("AUTH_EMAIL_PRIMARY_COLOR", "#C0392B")
        self.secondary_color = os.getenv("AUTH_EMAIL_SECONDARY_COLOR", "#8E1A1A")

    @property
    def gradient(self):
        return f"linear-gradient(135deg, {self.primary_color} 0%, {self.secondary_color} 100%)"


# 全局配置实例
email_config = EmailTemplateConfig()


# 通用验证码邮件模板
VERIFICATION_CODE_TEMPLATE = Template("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; background: #FFFBF5; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; }
        .header { background: {{ gradient }}; padding: 40px 30px; text-align: center; border-radius: 12px 12px 0 0; }
        .header h1 { margin: 10px 0 0 0; font-size: 24px; font-weight: 600; color: #ffffff !important; }
        .logo { font-size: 32px; margin-bottom: 10px; }
        .content { background: white; padding: 40px 30px; border-radius: 0 0 12px 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); color: #333; }
        .greeting { font-size: 16px; margin-bottom: 20px; }
        .code-box { background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%); border: 2px dashed {{ primary_color }}; padding: 25px; text-align: center; margin: 25px 0; border-radius: 8px; }
        .code { font-size: 36px; font-weight: 700; color: {{ primary_color }} !important; letter-spacing: 8px; font-family: 'Courier New', monospace; }
        .expire-notice { color: #666; font-size: 14px; text-align: center; }
        .warning { background: #fff3cd; color: #856404; padding: 15px; border-radius: 6px; font-size: 14px; margin-top: 20px; border-left: 4px solid #ffc107; }
        .footer { text-align: center; margin-top: 30px; color: #999; font-size: 12px; }
        .footer a { color: {{ primary_color }}; text-decoration: none; }
        @media (prefers-color-scheme: dark) {
            .content { background: #1a1a1a; color: #e0e0e0; }
            .code-box { background: #2a2a2a; }
            .expire-notice { color: #aaa; }
            .footer { color: #777; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">{{ logo_emoji }}</div>
            <h1>{{ app_name }}</h1>
        </div>
        <div class="content">
            <p class="greeting">您好！</p>
            <p>您正在进行 <strong>{{ purpose }}</strong> 操作，验证码如下：</p>
            <div class="code-box">
                <div class="code">{{ code }}</div>
            </div>
            <p class="expire-notice">
                验证码有效期为 <strong>{{ expire_minutes }}</strong> 分钟，请尽快完成验证。
            </p>
            <div class="warning">
                ⚠️ 如果这不是您的操作，请忽略此邮件，您的账号安全不会受到影响。
            </div>
            <div class="footer">
                <p>此邮件由 <a href="{{ app_url }}">{{ app_name }}</a> 自动发送，请勿直接回复</p>
                <p>如有疑问，请联系我们：{{ contact_email }}</p>
            </div>
        </div>
    </div>
</body>
</html>
""")


# 通用欢迎邮件模板
WELCOME_TEMPLATE = Template("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; background: #FFFBF5; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; }
        .header { background: {{ gradient }}; padding: 40px 30px; text-align: center; border-radius: 12px 12px 0 0; }
        .header h1 { margin: 10px 0 0 0; font-size: 24px; font-weight: 600; color: #ffffff !important; }
        .logo { font-size: 32px; margin-bottom: 10px; }
        .content { background: white; padding: 40px 30px; border-radius: 0 0 12px 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); color: #333; }
        .welcome-text { font-size: 16px; margin-bottom: 20px; }
        .cta-button { display: inline-block; padding: 15px 40px; background: {{ gradient }}; color: #ffffff !important; text-decoration: none; border-radius: 8px; font-weight: 600; margin: 20px 0; }
        .footer { text-align: center; margin-top: 30px; color: #999; font-size: 12px; }
        .footer a { color: {{ primary_color }}; text-decoration: none; }
        @media (prefers-color-scheme: dark) {
            .content { background: #1a1a1a; color: #e0e0e0; }
            .footer { color: #777; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">🎉</div>
            <h1>欢迎注册 {{ app_name }}！</h1>
        </div>
        <div class="content">
            <p class="welcome-text">
                {% if nickname %}
                亲爱的 <strong>{{ nickname }}</strong>，
                {% else %}
                您好！
                {% endif %}
            </p>
            <p>感谢您注册！您的账号已成功创建。</p>
            <p>现在您可以开始使用我们的服务了。</p>

            <div style="text-align: center;">
                <a href="{{ app_url }}" class="cta-button">开始使用</a>
            </div>

            <p style="color: #666; font-size: 14px; margin-top: 25px;">
                如有任何问题，欢迎随时联系我们。
            </p>

            <div class="footer">
                <p>此邮件由 <a href="{{ app_url }}">{{ app_name }}</a> 自动发送，请勿直接回复</p>
                <p>联系我们：{{ contact_email }}</p>
            </div>
        </div>
    </div>
</body>
</html>
""")


# 通用密码重置邮件模板
PASSWORD_RESET_TEMPLATE = Template("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; background: #FFFBF5; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; }
        .header { background: {{ gradient }}; padding: 40px 30px; text-align: center; border-radius: 12px 12px 0 0; }
        .header h1 { color: #ffffff !important; }
        .logo { font-size: 32px; margin-bottom: 10px; }
        .content { background: white; padding: 40px 30px; border-radius: 0 0 12px 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); color: #333; }
        .code-box { background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%); border: 2px dashed {{ primary_color }}; padding: 25px; text-align: center; margin: 25px 0; border-radius: 8px; }
        .code { font-size: 36px; font-weight: 700; color: {{ primary_color }} !important; letter-spacing: 8px; font-family: 'Courier New', monospace; }
        .steps { background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .steps ol { margin: 0; padding-left: 20px; }
        .steps li { margin-bottom: 10px; }
        .warning { background: #fff3cd; color: #856404; padding: 15px; border-radius: 6px; font-size: 14px; margin-top: 20px; border-left: 4px solid #ffc107; }
        .footer { text-align: center; margin-top: 30px; color: #999; font-size: 12px; }
        @media (prefers-color-scheme: dark) {
            .content { background: #1a1a1a; color: #e0e0e0; }
            .code-box { background: #2a2a2a; }
            .footer { color: #777; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">🔐</div>
            <h1>重置密码</h1>
        </div>
        <div class="content">
            <p>您好！</p>
            <p>我们收到了您的密码重置请求，验证码如下：</p>

            <div class="code-box">
                <div class="code">{{ code }}</div>
            </div>

            <p>验证码有效期为 <strong>{{ expire_minutes }}</strong> 分钟。</p>

            <div class="steps">
                <strong>重置步骤：</strong>
                <ol>
                    <li>复制上面的验证码</li>
                    <li>返回应用，输入验证码</li>
                    <li>设置您的新密码</li>
                </ol>
            </div>

            <div class="warning">
                ⚠️ 如果这不是您的操作，请忽略此邮件，您的账号安全不会受到影响。
            </div>

            <div class="footer">
                <p>此邮件由 {{ app_name }} 自动发送，请勿直接回复</p>
                <p>如有疑问，请联系：{{ contact_email }}</p>
            </div>
        </div>
    </div>
</body>
</html>
""")


def get_verification_code_email(code: str, purpose: str = "登录", expire_minutes: int = 10) -> str:
    """获取验证码邮件 HTML"""
    return VERIFICATION_CODE_TEMPLATE.render(
        code=code,
        purpose=purpose,
        expire_minutes=expire_minutes,
        **email_config.__dict__
    )


def get_welcome_email(nickname: Optional[str] = None) -> str:
    """获取欢迎邮件 HTML"""
    return WELCOME_TEMPLATE.render(
        nickname=nickname or "用户",
        **email_config.__dict__
    )


def get_password_reset_email(code: str, expire_minutes: int = 10) -> str:
    """获取密码重置邮件 HTML"""
    return PASSWORD_RESET_TEMPLATE.render(
        code=code,
        expire_minutes=expire_minutes,
        **email_config.__dict__
    )
