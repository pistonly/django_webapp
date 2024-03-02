from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext as _


class LoginForm(AuthenticationForm):
    # You can customize the form here if needed
    error_messages = {
        'invalid_login': _(
            "用户名或密码错误"
        ),
        'inactive': _("此用户名不存在"),
    }

