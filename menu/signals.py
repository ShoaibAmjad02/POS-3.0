import logging

from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from menu.models import Food

logger = logging.getLogger(__name__)


@receiver(post_delete, sender=Food)
def delete_food_image_on_delete(sender, instance, **kwargs):
    if instance.image and instance.image.name:
        try:
            instance.image.storage.delete(instance.image.name)
        except Exception as e:
            logger.error(f"Failed to delete image for product {instance.pk}: {e}")


@receiver(pre_save, sender=Food)
def delete_old_food_image_on_update(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = Food.objects.get(pk=instance.pk)
    except Food.DoesNotExist:
        return
    if old.image and old.image.name and old.image != instance.image:
        try:
            old.image.storage.delete(old.image.name)
        except Exception as e:
            logger.error(f"Failed to delete old image for product {instance.pk}: {e}")
