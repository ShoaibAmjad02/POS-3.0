from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CashHandlingConfig(AppConfig):
    name = "cash_handling"
    verbose_name = _("Cash Handling")

    def ready(self):
        import cash_handling.signals
        cash_handling.signals.register_signal_handlers()
