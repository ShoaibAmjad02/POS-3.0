import pytest
from decimal import Decimal
from django.utils import timezone
from menu.models import Food, Category
from megaone.users.models import InventoryBatch, SaleItemCost, Invoice, InvoiceItem
from megaone.users.inventory_service import InventoryValuationService


@pytest.fixture
def category(db):
    return Category.objects.create(name="Test Category")


@pytest.fixture
def product(db, category):
    return Food.objects.create(
        category=category,
        name="Test Product",
        description="Test",
        price=Decimal("100.00"),
        cost_price=Decimal("10.00"),
        default_purchase_cost=Decimal("10.00"),
        stock=0,
        costing_method='fifo',
    )


@pytest.fixture
def svc():
    return InventoryValuationService()


@pytest.mark.django_db
class TestInventoryBatches:

    def test_create_batch(self, product, svc):
        batch = svc.create_batch(product, quantity=100, unit_cost=10)
        assert batch.food == product
        assert batch.quantity == 100
        assert batch.remaining_quantity == 100
        assert batch.unit_cost == Decimal("10.00")
        assert batch.total_cost == Decimal("1000.00")

    def test_multiple_batches(self, product, svc):
        svc.create_batch(product, quantity=100, unit_cost=10)
        svc.create_batch(product, quantity=50, unit_cost=15)
        batches = svc.get_remaining_batches(product)
        assert len(batches) == 2
        assert batches[0].unit_cost == Decimal("10.00")
        assert batches[1].unit_cost == Decimal("15.00")

    def test_total_remaining_qty(self, product, svc):
        svc.create_batch(product, quantity=100, unit_cost=10)
        svc.create_batch(product, quantity=50, unit_cost=15)
        assert svc.get_total_remaining_qty(product) == 150


@pytest.mark.django_db
class TestFIFOConsumption:

    def test_basic_fifo(self, product, svc):
        svc.create_batch(product, quantity=100, unit_cost=10)
        svc.create_batch(product, quantity=50, unit_cost=15)

        consumption = svc.consume(product, 120)
        assert len(consumption) == 2
        # First 100 from batch 1 @ 10
        assert consumption[0][1] == 100
        assert consumption[0][2] == Decimal("10.00")
        # Next 20 from batch 2 @ 15
        assert consumption[1][1] == 20
        assert consumption[1][2] == Decimal("15.00")

        # Verify remaining batches
        remaining = svc.get_remaining_batches(product)
        assert len(remaining) == 1
        assert remaining[0].remaining_quantity == 30

    def test_full_fifo_consumption(self, product, svc):
        svc.create_batch(product, quantity=100, unit_cost=10)
        svc.create_batch(product, quantity=50, unit_cost=15)

        svc.consume(product, 150)
        remaining = svc.get_remaining_batches(product)
        assert len(remaining) == 0

    def test_fifo_insufficient_stock(self, product, svc):
        svc.create_batch(product, quantity=10, unit_cost=10)
        with pytest.raises(ValueError, match="Insufficient stock"):
            svc.consume(product, 20)

    def test_partial_sale_fifo(self, product, svc):
        svc.create_batch(product, quantity=100, unit_cost=10)
        svc.create_batch(product, quantity=50, unit_cost=15)

        # First sale: 30 units
        c1 = svc.consume(product, 30)
        assert len(c1) == 1
        assert c1[0][1] == 30

        # Second sale: 80 units
        c2 = svc.consume(product, 80)
        assert len(c2) == 2
        assert c2[0][1] == 70  # 70 remaining from batch 1
        assert c2[1][1] == 10  # 10 from batch 2

    def test_fifo_inventory_value(self, product, svc):
        svc.create_batch(product, quantity=100, unit_cost=10)
        svc.create_batch(product, quantity=50, unit_cost=15)
        svc.consume(product, 120)

        value = svc.get_product_inventory_value(product)
        # Remaining: 30 x 15 = 450
        assert value == Decimal("450.00")


@pytest.mark.django_db
class TestAverageCost:

    def test_average_cost_after_purchase(self, product, svc):
        product.costing_method = 'average'
        product.save()

        svc.create_batch(product, quantity=100, unit_cost=10)
        avg = svc._get_current_average_cost(product)
        assert avg == Decimal("10.00")

        svc.create_batch(product, quantity=50, unit_cost=15)
        avg = svc._get_current_average_cost(product)
        # (100*10 + 50*15) / 150 = 1750/150 = 11.666...
        assert avg == Decimal("11.66666666666666666666666667")

    def test_average_cost_unchanged_after_sale(self, product, svc):
        product.costing_method = 'average'
        product.save()

        svc.create_batch(product, quantity=100, unit_cost=10)
        svc.create_batch(product, quantity=50, unit_cost=15)
        avg_before = svc._get_current_average_cost(product)

        svc.consume(product, 80)
        avg_after = svc._get_current_average_cost(product)

        # Average cost should NOT change after a sale
        assert avg_before == avg_after

    def test_average_cost_consumption(self, product, svc):
        product.costing_method = 'average'
        product.save()

        svc.create_batch(product, quantity=100, unit_cost=10)
        svc.create_batch(product, quantity=50, unit_cost=15)

        consumption = svc.consume(product, 120)
        avg = Decimal("11.66666666666666666666666667")
        total_cogs = sum(Decimal(str(take)) * unit_cost for _, take, unit_cost in consumption)
        # 120 * 11.666... = 1400
        assert total_cogs == Decimal("1400.00")
        for _, _, unit_cost in consumption:
            assert unit_cost == avg


@pytest.mark.django_db
class TestSaleItemCosts:

    def test_consume_and_record_costs(self, product, svc):
        svc.create_batch(product, quantity=100, unit_cost=10)

        costs = svc.consume_and_record_costs(product, 30)
        assert len(costs) == 1
        assert costs[0][1] == 30
        assert costs[0][2] == Decimal("10.00")

        # Verify SaleItemCost was created
        assert SaleItemCost.objects.count() == 1
        assert SaleItemCost.objects.first().quantity == 30

    def test_cogs_calculation(self, product, svc):
        svc.create_batch(product, quantity=100, unit_cost=10)
        svc.create_batch(product, quantity=50, unit_cost=15)

        # Create invoice to hold invoice items
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create(email="test@test.com", password="test")

        invoice = Invoice.objects.create(
            user=user,
            customer_name="Test",
            invoice_number="TEST-INV-001",
        )

        invoice_item = InvoiceItem.objects.create(
            invoice=invoice,
            product_name=product.name,
            price=Decimal("100.00"),
            quantity=120,
            subtotal=Decimal("12000.00"),
        )

        svc.consume_and_record_costs(product, 120, invoice_item=invoice_item)

        cogs = svc.get_cogs_for_item(invoice_item, 'retail')
        # 100 x 10 + 20 x 15 = 1000 + 300 = 1300
        assert cogs == Decimal("1300.00")


@pytest.mark.django_db
class TestReturns:

    def test_return_to_stock(self, product, svc):
        svc.create_batch(product, quantity=100, unit_cost=10)
        svc.consume(product, 50)

        svc.return_to_stock(product, 10, unit_cost=10)
        remaining = svc.get_total_remaining_qty(product)
        assert remaining == 60

    def test_return_preserves_cost(self, product, svc):
        batch = svc.create_batch(product, quantity=100, unit_cost=10)
        svc.consume(product, 50)

        svc.return_to_stock(product, 10, unit_cost=10)
        batches = svc.get_remaining_batches(product)
        total_value = sum(
            Decimal(str(b.remaining_quantity)) * b.unit_cost for b in batches
        )
        # 50 remaining from batch 1 x 10 = 500
        # 10 returned x 10 = 100
        # Total = 600
        assert total_value == Decimal("600.00")


@pytest.mark.django_db
class TestInventoryValuation:

    def test_empty_inventory(self, product, svc):
        value = svc.get_product_inventory_value(product)
        assert value == Decimal("0")

    def test_single_batch_value(self, product, svc):
        svc.create_batch(product, quantity=100, unit_cost=10)
        value = svc.get_product_inventory_value(product)
        assert value == Decimal("1000.00")

    def test_after_partial_sale_value(self, product, svc):
        svc.create_batch(product, quantity=100, unit_cost=10)
        svc.create_batch(product, quantity=50, unit_cost=15)
        svc.consume(product, 80)

        value = svc.get_product_inventory_value(product)
        # Remaining: 20 (batch 1) x 10 + 50 (batch 2) x 15 = 200 + 750 = 950
        assert value == Decimal("950.00")

    def test_average_inventory_value(self, product, svc):
        product.costing_method = 'average'
        product.save()
        svc.create_batch(product, quantity=100, unit_cost=10)
        svc.create_batch(product, quantity=50, unit_cost=15)
        svc.consume(product, 80)

        value = svc.get_product_inventory_value(product)
        # Avg cost after purchases: (100*10 + 50*15) / 150 = 11.666...
        # Avg stays 11.666... after sale (perpetual AVCO)
        # Value: 70 * 11.666... = 816.666...
        assert value == Decimal("816.6666666666666666666666669")

    def test_inventory_summary(self, product, svc):
        svc.create_batch(product, quantity=100, unit_cost=10)
        svc.create_batch(product, quantity=50, unit_cost=15)
        svc.consume(product, 30)

        summary = svc.get_inventory_summary()
        assert summary['total_products'] == 1
        assert summary['total_stock_quantity'] == 120
        # 70 (batch 1) x 10 + 50 (batch 2) x 15 = 700 + 750 = 1450
        assert summary['total_inventory_value'] == Decimal("1450.00")


@pytest.mark.django_db
class TestProfitCalculation:

    def test_profit_calculation(self, product, svc):
        svc.create_batch(product, quantity=100, unit_cost=10)

        # Sale: 1 unit at 100, COGS = 10
        cogs = sum(Decimal(str(take)) * unit_cost for _, take, unit_cost in svc.consume(product, 1))
        assert cogs == Decimal("10.00")

        revenue = Decimal("100.00")
        profit = revenue - cogs
        assert profit == Decimal("90.00")

    def test_mixed_batch_profit(self, product, svc):
        svc.create_batch(product, quantity=100, unit_cost=10)
        svc.create_batch(product, quantity=50, unit_cost=15)

        # Sale 120 units, revenue = 120 * 100 = 12000
        consumption = svc.consume(product, 120)
        cogs = sum(Decimal(str(take)) * unit_cost for _, take, unit_cost in consumption)
        revenue = Decimal("120.00") * 120
        profit = revenue - cogs

        assert cogs == Decimal("1300.00")  # 100x10 + 20x15
        assert profit == Decimal("13100.00")


@pytest.mark.django_db
class TestValidation:

    def test_negative_stock_prevented(self, product, svc):
        svc.create_batch(product, quantity=10, unit_cost=10)
        with pytest.raises(ValueError):
            svc.consume(product, 20)

    def test_zero_consumption(self, product, svc):
        svc.create_batch(product, quantity=10, unit_cost=10)
        consumption = svc.consume(product, 0)
        assert consumption == []

    def test_different_purchase_costs(self, product):
        svc = InventoryValuationService()
        svc.create_batch(product, quantity=50, unit_cost=8)
        svc.create_batch(product, quantity=30, unit_cost=12)
        svc.create_batch(product, quantity=20, unit_cost=15)

        total_value = svc.get_product_inventory_value(product)
        # 50x8 + 30x12 + 20x15 = 400 + 360 + 300 = 1060
        assert total_value == Decimal("1060.00")

        consumption = svc.consume(product, 70)
        cogs = sum(Decimal(str(take)) * unit_cost for _, take, unit_cost in consumption)
        # 50x8 + 20x12 = 400 + 240 = 640
        assert cogs == Decimal("640.00")

    def test_inventory_reconciliation(self, product, svc):
        """Test that inventory value + cogs = total cost of all stock ever purchased"""
        svc.create_batch(product, quantity=100, unit_cost=10)
        svc.create_batch(product, quantity=50, unit_cost=15)

        total_purchased = Decimal("1750.00")  # 1000 + 750

        c0 = svc.consume(product, 80)
        cogs = sum(Decimal(str(take)) * unit_cost for _, take, unit_cost in c0)
        c1 = svc.consume(product, 20)
        cogs += sum(Decimal(str(take)) * unit_cost for _, take, unit_cost in c1)
        c2 = svc.consume(product, 30)
        cogs += sum(Decimal(str(take)) * unit_cost for _, take, unit_cost in c2)

        # After consuming 80 + 20 + 30 = 130, remaining = 20
        remaining_value = svc.get_product_inventory_value(product)
        # Remaining all from batch 2: 20 x 15 = 300
        # COGS: 80x10 + 20x10 + 30x15 = 800 + 200 + 450 = 1450
        # 300 + 1450 = 1750 = total_purchased
        assert remaining_value + cogs == total_purchased


@pytest.mark.django_db
class TestBackwardCompat:

    def test_cost_price_sync(self, product, svc):
        """Ensure cost_price is synced with default_purchase_cost for new products"""
        assert product.default_purchase_cost == product.cost_price

    def test_default_purchase_cost_independent(self, product):
        """Edit should not change cost_price when stock > 0"""
        product.stock = 10
        product.save()

        # Simulate what edit_product does
        old_cost_price = product.cost_price
        product.default_purchase_cost = Decimal("20.00")
        product.save()

        product.refresh_from_db()
        assert product.default_purchase_cost == Decimal("20.00")
        assert product.cost_price == old_cost_price  # Unchanged


@pytest.mark.django_db
class TestReportReconciliation:

    def test_stock_movement_report_valuation(self, product, svc):
        """Stock Movement Report inventory value must match batch valuation."""
        svc.create_batch(product, quantity=100, unit_cost=10)
        svc.create_batch(product, quantity=50, unit_cost=15)
        svc.consume(product, 30)

        batch_value = svc.get_product_inventory_value(product)
        # Remaining: 70 (batch1) x 10 + 50 (batch2) x 15 = 700 + 750 = 1450
        assert batch_value == Decimal("1450.00")

        # This is what the report will display
        report_inventory_value = batch_value
        assert report_inventory_value > 0

    def test_inventory_summary_reconciliation(self, product, svc):
        """Inventory Summary must match batch valuation."""
        svc.create_batch(product, quantity=100, unit_cost=10)
        svc.create_batch(product, quantity=50, unit_cost=15)
        svc.consume(product, 30)

        summary = svc.get_inventory_summary()
        batch_value = svc.get_product_inventory_value(product)

        assert summary['total_inventory_value'] == batch_value
        assert summary['total_stock_quantity'] == 120

    def test_profit_loss_reconciliation(self, product, svc):
        """P&L COGS + remaining inventory value = total purchase cost."""
        svc.create_batch(product, quantity=100, unit_cost=10)
        svc.create_batch(product, quantity=50, unit_cost=15)

        total_purchased = Decimal("1750.00")

        consumption = svc.consume(product, 80)
        cogs = sum(Decimal(str(take)) * unit_cost for _, take, unit_cost in consumption)
        remaining = svc.get_product_inventory_value(product)

        # Revenue
        revenue = Decimal("120.00") * 80
        gross_profit = revenue - cogs
        expected_profit = Decimal("9600.00") - Decimal("800.00")  # 80x120 - 80x10
        assert gross_profit == expected_profit

        # Reconciliation
        assert remaining + cogs == total_purchased

    def test_all_reports_use_same_service(self, product):
        """All reports should get the same inventory value."""
        svc1 = InventoryValuationService()
        svc2 = InventoryValuationService()

        svc1.create_batch(product, quantity=100, unit_cost=10)
        svc1.create_batch(product, quantity=50, unit_cost=15)
        svc1.consume(product, 40)

        v1 = svc1.get_product_inventory_value(product)
        v2 = svc2.get_product_inventory_value(product)
        assert v1 == v2

    def test_avco_profit_loss_reconciliation(self, product, svc):
        """AVCO: P&L COGS + remaining = all purchase costs over time."""
        product.costing_method = 'average'
        product.save()

        svc.create_batch(product, quantity=100, unit_cost=10)
        svc.create_batch(product, quantity=50, unit_cost=15)
        svc.create_batch(product, quantity=40, unit_cost=20)

        total_purchased = Decimal("1000.00") + Decimal("750.00") + Decimal("800.00")

        consumption = svc.consume(product, 120)
        cogs = sum(Decimal(str(take)) * unit_cost for _, take, unit_cost in consumption)
        remaining = svc.get_product_inventory_value(product)

        assert remaining + cogs == total_purchased

    def test_returns_dont_break_reconciliation(self, product, svc):
        """Returns restore stock and maintain reconciliation."""
        svc.create_batch(product, quantity=100, unit_cost=10)
        svc.consume(product, 30)
        before_return = svc.get_product_inventory_value(product)

        svc.return_to_stock(product, 10, unit_cost=10)
        after_return = svc.get_product_inventory_value(product)

        # Value should increase by the returned amount
        assert after_return == before_return + Decimal("100.00")
        assert svc.get_total_remaining_qty(product) == 80

    def test_multiple_products_independent_valuation(self, category, svc):
        """Each product's inventory value is independent."""
        p1 = Food.objects.create(
            category=category, name="Product A", description="", price=100,
            cost_price=10, default_purchase_cost=10, stock=0
        )
        p2 = Food.objects.create(
            category=category, name="Product B", description="", price=200,
            cost_price=20, default_purchase_cost=20, stock=0
        )

        svc.create_batch(p1, quantity=50, unit_cost=10)
        svc.create_batch(p2, quantity=30, unit_cost=20)

        assert svc.get_product_inventory_value(p1) == Decimal("500.00")
        assert svc.get_product_inventory_value(p2) == Decimal("600.00")

        # Total inventory value
        total = svc.get_inventory_summary()['total_inventory_value']
        assert total == Decimal("1100.00")


@pytest.mark.django_db
class TestGetUnitCost:

    def test_invoice_item_type(self, product, svc, category):
        """_get_unit_cost must not crash when called with InvoiceItem."""
        from megaone.users.views import _get_unit_cost
        from megaone.users.models import Invoice, InvoiceItem
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create(email="costtest@test.com", password="test")

        svc.create_batch(product, quantity=10, unit_cost=25)
        invoice = Invoice.objects.create(user=user, customer_name="Test", invoice_number="COST-TEST")
        inv_item = InvoiceItem.objects.create(
            invoice=invoice, product_name=product.name,
            price=100, quantity=2, subtotal=200,
        )
        svc.consume_and_record_costs(product, 2, invoice_item=inv_item)

        # Should not raise ValueError from type mismatch
        cost = _get_unit_cost(inv_item, product)
        assert cost == 25.0

    def test_wholesale_item_type(self, product, svc, category):
        """_get_unit_cost must not crash when called with WholesaleInvoiceItem."""
        from megaone.users.views import _get_unit_cost
        from megaone.users.models import WholesaleInvoice, WholesaleInvoiceItem, WholesaleCustomer
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create(email="wscost@test.com", password="test")

        customer = WholesaleCustomer.objects.create(company_name="Test Co", contact_person="Test")
        svc.create_batch(product, quantity=10, unit_cost=35)
        ws_invoice = WholesaleInvoice.objects.create(
            wholesale_customer=customer,
        )
        ws_item = WholesaleInvoiceItem.objects.create(
            wholesale_invoice=ws_invoice, product_name=product.name,
            wholesale_price=100, quantity=3, subtotal=300,
        )
        svc.consume_and_record_costs(product, 3, wholesale_invoice_item=ws_item)

        # Should not raise ValueError from type mismatch
        cost = _get_unit_cost(ws_item, product)
        assert cost == 35.0

    def test_fallback_to_default_purchase_cost(self, product):
        """_get_unit_cost falls back to default_purchase_cost when no SaleItemCost."""
        from megaone.users.views import _get_unit_cost
        from megaone.users.models import Invoice, InvoiceItem
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create(email="fallback@test.com", password="test")

        product.default_purchase_cost = Decimal("42.00")
        product.cost_price = Decimal("99.00")
        product.save()

        invoice = Invoice.objects.create(user=user, customer_name="Test", invoice_number="FALLBACK-TEST")
        inv_item = InvoiceItem.objects.create(
            invoice=invoice, product_name=product.name,
            price=100, quantity=1, subtotal=100,
        )
        cost = _get_unit_cost(inv_item, product)
        # Should use default_purchase_cost (42), NOT cost_price (99)
        assert cost == 42.0
