from django.db import models


class Category(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ("percentage", "Percentage"),
        ("fixed", "Fixed Amount"),
    ]
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    discount_type = models.CharField(
        max_length=20, choices=DISCOUNT_TYPE_CHOICES, blank=True, null=True
    )
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return self.name


class Food(models.Model):
    COSTING_METHOD_CHOICES = [
        ('fifo', 'FIFO (First In, First Out)'),
        ('average', 'Average Cost (AVCO)'),
    ]

    DISCOUNT_TYPE_CHOICES = [
        ("percentage", "Percentage"),
        ("fixed", "Fixed Amount"),
    ]
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="foods"
    )
    name = models.CharField(max_length=200)
    company_name = models.CharField(max_length=200, blank=True, default='')
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    default_purchase_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Default cost for future purchases")
    costing_method = models.CharField(max_length=10, choices=COSTING_METHOD_CHOICES, default='fifo', help_text="Inventory costing method")
    current_average_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Current weighted average cost (AVCO)")
    wholesale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Wholesale selling price")
    wholesale_discount_type = models.CharField(
        max_length=20, choices=DISCOUNT_TYPE_CHOICES, blank=True, null=True
    )
    wholesale_discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock = models.IntegerField(default=0)
    sku = models.CharField(max_length=100, blank=True, null=True)
    reward_points = models.IntegerField(
        default=0, help_text="Points earned when customer orders this item"
    )
    barcode = models.CharField(max_length=20, unique=True, blank=True, null=True)
    product_code = models.CharField(max_length=20, unique=True, blank=True, null=True)
    image = models.ImageField(upload_to="foods/", blank=True, null=True)
    available = models.BooleanField(default=True)
    is_popular = models.BooleanField(default=False)
    discount_type = models.CharField(
        max_length=20, choices=DISCOUNT_TYPE_CHOICES, blank=True, null=True
    )
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def _next_barcode(self):
        last = Food.objects.filter(barcode__regex=r"^\d{5}$").order_by("-barcode").first()
        if last:
            return str(int(last.barcode) + 1).zfill(5)
        return "10001"

    def _next_product_code(self):
        last = Food.objects.filter(product_code__regex=r"^\d{5}$").order_by("-product_code").first()
        if last:
            return str(int(last.product_code) + 1).zfill(5)
        return "50001"

    def save(self, *args, **kwargs):
        if not self.barcode:
            self.barcode = self._next_barcode()
            while Food.objects.filter(barcode=self.barcode).exclude(pk=self.pk).exists():
                self.barcode = str(int(self.barcode) + 1).zfill(5)
        if not self.product_code:
            self.product_code = self._next_product_code()
            while Food.objects.filter(product_code=self.product_code).exclude(pk=self.pk).exists():
                self.product_code = str(int(self.product_code) + 1).zfill(5)
        if not self.default_purchase_cost:
            self.default_purchase_cost = self.cost_price
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
