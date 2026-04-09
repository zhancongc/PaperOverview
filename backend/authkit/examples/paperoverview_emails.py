"""
AutoOverview 专属邮件模板
"""
from jinja2 import Template


# 验证码邮件模板
VERIFICATION_CODE_TEMPLATE = Template("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; background: #FFFBF5; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; }
        .header { background: linear-gradient(135deg, #D63031 0%, #B71C1C 100%); color: white; padding: 40px 30px; text-align: center; border-radius: 12px 12px 0 0; }
        .header h1 { margin: 0; font-size: 24px; font-weight: 600; }
        .content { background: white; padding: 40px 30px; border-radius: 0 0 12px 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        .greeting { font-size: 16px; margin-bottom: 20px; }
        .code-box { background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%); border: 2px dashed #667eea; padding: 25px; text-align: center; margin: 25px 0; border-radius: 8px; }
        .code { font-size: 36px; font-weight: 700; color: #667eea; letter-spacing: 8px; font-family: 'Courier New', monospace; }
        .expire-notice { color: #666; font-size: 14px; text-align: center; }
        .warning { background: #fff3cd; color: #856404; padding: 15px; border-radius: 6px; font-size: 14px; margin-top: 20px; border-left: 4px solid #ffc107; }
        .footer { text-align: center; margin-top: 30px; color: #999; font-size: 12px; }
        .footer a { color: #667eea; text-decoration: none; }
        .logo { font-size: 32px; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">📚</div>
            <h1>论文综述生成器</h1>
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
                <p>此邮件由 <a href="https://autooverview.com">AutoOverview</a> 自动发送，请勿直接回复</p>
                <p>如有疑问，请联系我们：service@snappicker.com</p>
            </div>
        </div>
    </div>
</body>
</html>
""")


# 欢迎邮件模板
WELCOME_TEMPLATE = Template("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; background: #FFFBF5; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; }
        .header { background: linear-gradient(135deg, #D63031 0%, #B71C1C 100%); color: white; padding: 40px 30px; text-align: center; border-radius: 12px 12px 0 0; }
        .header h1 { margin: 0; font-size: 24px; font-weight: 600; }
        .content { background: white; padding: 40px 30px; border-radius: 0 0 12px 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        .welcome-text { font-size: 16px; margin-bottom: 20px; }
        .feature-list { list-style: none; padding: 0; margin: 25px 0; }
        .feature-item { padding: 15px; margin-bottom: 10px; background: #f8f9fa; border-radius: 8px; display: flex; align-items: center; }
        .feature-icon { font-size: 24px; margin-right: 15px; }
        .feature-text { flex: 1; }
        .feature-title { font-weight: 600; color: #333; margin-bottom: 4px; }
        .feature-desc { font-size: 14px; color: #666; }
        .cta-button { display: inline-block; padding: 15px 40px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; border-radius: 8px; font-weight: 600; margin: 20px 0; }
        .footer { text-align: center; margin-top: 30px; color: #999; font-size: 12px; }
        .footer a { color: #667eea; text-decoration: none; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎉 欢迎加入 AutoOverview！</h1>
        </div>
        <div class="content">
            <p class="welcome-text">
                {% if nickname %}
                亲爱的 <strong>{{ nickname }}</strong>，
                {% else %}
                您好！
                {% endif %}
            </p>
            <p>感谢您注册论文综述生成器！您的账号已成功创建。</p>
            <p>现在您可以开始使用我们的服务，一键生成专业的文献综述。</p>

            <ul class="feature-list">
                <li class="feature-item">
                    <span class="feature-icon">🔍</span>
                    <div class="feature-text">
                        <div class="feature-title">智能检索</div>
                        <div class="feature-desc">自动检索相关文献</div>
                    </div>
                </li>
                <li class="feature-item">
                    <span class="feature-icon">📊</span>
                    <div class="feature-text">
                        <div class="feature-title">智能分析</div>
                        <div class="feature-desc">AI 分析文献内容</div>
                    </div>
                </li>
                <li class="feature-item">
                    <span class="feature-icon">✨</span>
                    <div class="feature-text">
                        <div class="feature-title">自动生成</div>
                        <div class="feature-desc">一键生成专业综述</div>
                    </div>
                </li>
            </ul>

            <div style="text-align: center;">
                <a href="https://autooverview.com" class="cta-button">开始使用</a>
            </div>

            <p style="color: #666; font-size: 14px; margin-top: 25px;">
                如有任何问题，欢迎随时联系我们。
            </p>

            <div class="footer">
                <p>此邮件由 <a href="https://autooverview.com">AutoOverview</a> 自动发送，请勿直接回复</p>
                <p>联系我们：service@snappicker.com</p>
            </div>
        </div>
    </div>
</body>
</html>
""")


# 密码重置邮件模板
PASSWORD_RESET_TEMPLATE = Template("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; background: #FFFBF5; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; }
        .header { background: linear-gradient(135deg, #D63031 0%, #B71C1C 100%); color: white; padding: 40px 30px; text-align: center; border-radius: 12px 12px 0 0; }
        .content { background: white; padding: 40px 30px; border-radius: 0 0 12px 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        .code-box { background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%); border: 2px dashed #667eea; padding: 25px; text-align: center; margin: 25px 0; border-radius: 8px; }
        .code { font-size: 36px; font-weight: 700; color: #667eea; letter-spacing: 8px; font-family: 'Courier New', monospace; }
        .steps { background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .steps ol { margin: 0; padding-left: 20px; }
        .steps li { margin-bottom: 10px; }
        .warning { background: #fff3cd; color: #856404; padding: 15px; border-radius: 6px; font-size: 14px; margin-top: 20px; border-left: 4px solid #ffc107; }
        .footer { text-align: center; margin-top: 30px; color: #999; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 重置密码</h1>
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
                <p>此邮件由 AutoOverview 自动发送，请勿直接回复</p>
                <p>如有疑问，请联系：service@snappicker.com</p>
            </div>
        </div>
    </div>
</body>
</html>
""")


def get_verification_code_email(code: str, purpose: str = "登录", expire_minutes: int = 10) -> str:
    """获取验证码邮件 HTML"""
    purpose_map = {
        "login": "登录",
        "register": "注册",
        "reset_password": "重置密码"
    }
    purpose_text = purpose_map.get(purpose, purpose)

    return VERIFICATION_CODE_TEMPLATE.render(
        code=code,
        purpose=purpose_text,
        expire_minutes=expire_minutes
    )


def get_welcome_email(nickname: str = None) -> str:
    """获取欢迎邮件 HTML"""
    return WELCOME_TEMPLATE.render(nickname=nickname or "用户")


def get_password_reset_email(code: str, expire_minutes: int = 10) -> str:
    """获取密码重置邮件 HTML"""
    return PASSWORD_RESET_TEMPLATE.render(
        code=code,
        expire_minutes=expire_minutes
    )
