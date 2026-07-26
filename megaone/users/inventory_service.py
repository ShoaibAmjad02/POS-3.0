from decimal import Decimal
from django.db.models import F, Sum
from django.utils import timezone
from menu.models import Food
from .models import InventoryBatch, SaleItemCost


class InventoryValuationService:
    """
    Reusable service for inventory costing and valuation.
    Supports FIFO and Weighted Average Cost methods per product.
    """

    def __init__(self, costing_method=None):
        self.costing_method = costing_method or 'fifo'

    def _get_method(self, product):
        if hasattr(product, 'costing_method') and product.costing_method:
            return product.costing_method
        return self.costing_method

    # ──────────────────────────────────────────────
    # Batch Management
    # ──────────────────────────────────────────────

    def create_batch(self, food, quantity, unit_cost, purchase_date=None, supplier='', purchase_reference='', notes='', selling_price=0, wholesale_price=0):
        """Create a new inventory batch for a stock purchase and update AVCO if applicable."""
        unit_cost = Decimal(str(unit_cost))
        total_cost = unit_cost * quantity
        batch = InventoryBatch.objects.create(
            food=food,
            purchase_date=purchase_date or timezone.now(),
            quantity=quantity,
            remaining_quantity=quantity,
            unit_cost=unit_cost,
            total_cost=total_cost,
            selling_price=Decimal(str(selling_price)),
            wholesale_price=Decimal(str(wholesale_price)),
            supplier=supplier or '',
            purchase_reference=purchase_reference or '',
            notes=notes,
        )
        if self._get_method(food) == 'average':
            self._update_average_cost(food, quantity, unit_cost)
        return batch

    def _update_average_cost(self, product, new_qty, new_unit_cost):
        """Update the current_average_cost on the product for perpetual AVCO."""
        new_qty = Decimal(str(new_qty))
        new_unit_cost = Decimal(str(new_unit_cost))
        old_qty = Decimal(str(self.get_total_remaining_qty(product) - int(new_qty)))
        old_avg = Decimal(str(product.current_average_cost or 0))
        if old_qty > 0 and old_avg > 0:
            new_avg = (old_avg * old_qty + new_unit_cost * new_qty) / (old_qty + new_qty)
        else:
            new_avg = new_unit_cost
        Food.objects.filter(pk=product.pk).update(current_average_cost=new_avg)
        product.current_average_cost = new_avg

    def get_remaining_batches(self, product):
        return InventoryBatch.objects.filter(
            food=product,
            remaining_quantity__gt=0
        ).order_by('purchase_date', 'id')

    def get_total_remaining_qty(self, product):
        result = InventoryBatch.objects.filter(
            food=product,
            remaining_quantity__gt=0
        ).aggregate(total=Sum('remaining_quantity'))
        return result['total'] or 0

    # ──────────────────────────────────────────────
    # FIFO
    # ──────────────────────────────────────────────

    def _consume_fifo(self, product, quantity):
        needed = int(quantity)
        if needed <= 0:
            return []
        batches = self.get_remaining_batches(product)
        consumption = []
        for batch in batches:
            if needed <= 0:
                break
            take = min(needed, batch.remaining_quantity)
            consumption.append((batch, take, batch.unit_cost))
            needed -= take
        if needed > 0:
            raise ValueError(
                f"Insufficient stock for '{product.name}': need {quantity}, "
                f"only {self.get_total_remaining_qty(product)} available"
            )
        return consumption

    # ──────────────────────────────────────────────
    # Average Cost
    # ──────────────────────────────────────────────

    def _get_current_average_cost(self, product):
        """Get the current perpetual average cost for a product."""
        avg = Decimal(str(product.current_average_cost or 0))
        if avg > 0:
            return avg
        return Decimal(str(product.default_purchase_cost or 0))

    def _consume_average(self, product, quantity):
        needed = int(quantity)
        if needed <= 0:
            return []
        batches = self.get_remaining_batches(product)
        avg_cost = self._get_current_average_cost(product)
        consumption = []
        for batch in batches:
            if needed <= 0:
                break
            take = min(needed, batch.remaining_quantity)
            consumption.append((batch, take, avg_cost))
            needed -= take
        if needed > 0:
            raise ValueError(
                f"Insufficient stock for '{product.name}': need {quantity}, "
                f"only {self.get_total_remaining_qty(product)} available"
            )
        return consumption

    # ──────────────────────────────────────────────
    # Public API - Stock Movements
    # ──────────────────────────────────────────────

    def consume(self, product, quantity):
        """
        Consume inventory using the product's costing method.
        Returns list of (batch, qty_consumed, unit_cost).
        Updates remaining_quantity in the database.
        """
        method = self._get_method(product)
        if method == 'average':
            consumption = self._consume_average(product, quantity)
        else:
            consumption = self._consume_fifo(product, quantity)

        for batch, take, unit_cost in consumption:
            InventoryBatch.objects.filter(pk=batch.pk).update(
                remaining_quantity=F('remaining_quantity') - take
            )
        return consumption

    def consume_and_record_costs(self, product, quantity, invoice_item=None, wholesale_invoice_item=None):
        consumption = self.consume(product, quantity)
        costs = []
        for batch, take, unit_cost in consumption:
            SaleItemCost.objects.create(
                inventory_batch=batch,
                invoice_item=invoice_item,
                wholesale_invoice_item=wholesale_invoice_item,
                quantity=take,
                unit_cost=unit_cost,
            )
            costs.append((batch, take, unit_cost))
        return costs

    def return_to_stock(self, product, quantity, unit_cost=None):
        if unit_cost is not None:
            cost = Decimal(str(unit_cost))
        else:
            cost = Decimal(str(product.default_purchase_cost or 0))
        batch = self.create_batch(
            food=product,
            quantity=quantity,
            unit_cost=cost,
            notes='Stock return'
        )
        return batch

    # ──────────────────────────────────────────────
    # Valuation
    # ──────────────────────────────────────────────

    def get_inventory_value(self, product=None):
        """
        Calculate total inventory value for a product or all products.
        Uses each product's configured costing method.
        """
        batches = InventoryBatch.objects.filter(remaining_quantity__gt=0)
        if product is not None:
            batches = batches.filter(food=product)

        if not batches:
            return Decimal('0')

        if product is not None:
            method = self._get_method(product)
            if method == 'average':
                avg = self._get_current_average_cost(product)
                total_qty = self.get_total_remaining_qty(product)
                return Decimal(str(total_qty)) * avg

        total = Decimal('0')
        for batch in batches:
            total += Decimal(str(batch.remaining_quantity)) * batch.unit_cost
        return total

    def get_product_inventory_value(self, product):
        return self.get_inventory_value(product=product)

    # ──────────────────────────────────────────────
    # COGS
    # ──────────────────────────────────────────────

    def get_cogs_for_item(self, item, item_type='retail'):
        if item_type == 'retail':
            costs = SaleItemCost.objects.filter(invoice_item=item)
        else:
            costs = SaleItemCost.objects.filter(wholesale_invoice_item=item)
        return costs.aggregate(
            total=Sum(F('quantity') * F('unit_cost'))
        )['total'] or Decimal('0')

    def get_cogs_for_invoice(self, invoice, invoice_type='retail'):
        total = Decimal('0')
        if invoice_type == 'retail':
            for item in invoice.items.all():
                total += self.get_cogs_for_item(item, 'retail')
        else:
            for item in invoice.items.all():
                total += self.get_cogs_for_item(item, 'wholesale')
        return total

    def get_recent_cogs(self, start_dt=None, end_dt=None, invoice_type=None):
        total = Decimal('0')
        cost_qs = SaleItemCost.objects.all()
        if start_dt and end_dt:
            if invoice_type in (None, 'retail'):
                retail_costs = cost_qs.filter(
                    invoice_item__isnull=False,
                    invoice_item__invoice__created_at__range=[start_dt, end_dt]
                )
                total += retail_costs.aggregate(
                    total=Sum(F('quantity') * F('unit_cost'))
                )['total'] or Decimal('0')
            if invoice_type in (None, 'wholesale'):
                ws_costs = cost_qs.filter(
                    wholesale_invoice_item__isnull=False,
                    wholesale_invoice_item__wholesale_invoice__created_at__range=[start_dt, end_dt]
                )
                total += ws_costs.aggregate(
                    total=Sum(F('quantity') * F('unit_cost'))
                )['total'] or Decimal('0')
        else:
            if invoice_type:
                if invoice_type == 'retail':
                    cost_qs = cost_qs.filter(invoice_item__isnull=False)
                else:
                    cost_qs = cost_qs.filter(wholesale_invoice_item__isnull=False)
            total = cost_qs.aggregate(
                total=Sum(F('quantity') * F('unit_cost'))
            )['total'] or Decimal('0')
        return total

    # ──────────────────────────────────────────────
    # Summary
    # ──────────────────────────────────────────────

    def get_inventory_summary(self):
        active_products = Food.objects.filter(available=True)
        total_products = active_products.count()
        total_stock_qty = 0
        total_value = Decimal('0')

        for p in active_products:
            batches = list(InventoryBatch.objects.filter(food=p, remaining_quantity__gt=0))
            qty = sum(b.remaining_quantity for b in batches)
            total_stock_qty += qty
            method = self._get_method(p)
            if method == 'average':
                total_value += Decimal(str(qty)) * self._get_current_average_cost(p)
            else:
                total_value += sum(Decimal(str(b.remaining_quantity)) * b.unit_cost for b in batches)

        return {
            'total_products': total_products,
            'total_stock_quantity': total_stock_qty,
            'total_inventory_value': total_value,
        }
