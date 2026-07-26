from django.db.models.signals import post_save
from django.contrib.auth import get_user_model
from django.dispatch import receiver
from .models import LoyaltyCard, OperatorPermission

User = get_user_model()


@receiver(post_save, sender=User)
def create_loyalty_card_for_user(sender, instance, created, **kwargs):
    if instance.is_staff or instance.is_superuser or getattr(instance, 'is_operator', False):
        return

    card, was_created = LoyaltyCard.objects.get_or_create(
        user=instance,
        defaults={'status': 'ACTIVE'}
    )

    if was_created or not card.card_pdf or not card.qr_code_image:
        from .loyalty_utils import generate_qr_code_image, generate_loyalty_card_pdf, generate_loyalty_card_image
        try:
            generate_qr_code_image(card)
            generate_loyalty_card_pdf(card)
            generate_loyalty_card_image(card)
        except Exception:
            pass


@receiver(post_save, sender=User)
def create_operator_permissions(sender, instance, **kwargs):
    if instance.is_operator or instance.is_staff:
        perms, created = OperatorPermission.objects.get_or_create(user=instance)
        if instance.is_staff:
            needs_update = False
            for f in OperatorPermission._meta.get_fields():
                name = f.name
                if not (name.startswith('can_') or name.startswith('cash_')):
                    continue
                if not hasattr(f, 'get_internal_type'):
                    continue
                if f.get_internal_type() == 'BooleanField' and not getattr(perms, name):
                    setattr(perms, name, True)
                    needs_update = True
            if needs_update:
                perms.save()
