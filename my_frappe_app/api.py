import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import nowdate, getdate, fmt_money, format_date, add_months, get_datetime

DAY_QTY_FIELD = {
    "Monday":    "monday_qty",
    "Tuesday":   "tuesday_qty",
    "Wednesday": "wednesday_qty",
    "Thursday":  "thursday_qty",
    "Friday":    "friday_qty",
    "Saturday":  "saturday_qty",
    "Sunday":    "sunday_qty",
}

ALL_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@frappe.whitelist(allow_guest=True)
def get_current_user_role():
    frappe.local.no_cookie_check = True
    user = frappe.session.user
    if user == "Administrator":
        return {"role": "Administrator"}
    roles = frappe.get_roles(user)
    if "Customer" in roles:
        return {"role": "Customer"}
    elif "Seller" in roles:
        return {"role": "Seller"}
    return {"role": "Guest"}

@frappe.whitelist()
def get_customer_sidebar_data():
    try:
        user_email = frappe.session.user
        customer = (
            frappe.db.get_value("Customer", {"email_id": user_email}, ["name", "customer_name"], as_dict=True)
            or frappe.db.get_value("Customer", {"user": user_email}, ["name", "customer_name"], as_dict=True)
        )

        if not customer and user_email != "Administrator":
            frappe.log_error(f"No Customer found for email: {user_email}", "Customer Sidebar Error")

        final_pincode_list = []
        if customer:
            addresses = frappe.db.sql("""
                SELECT a.pincode, a.is_primary_address FROM `tabAddress` a
                JOIN `tabDynamic Link` dl ON a.name = dl.parent
                WHERE dl.link_doctype = 'Customer' AND dl.link_name = %s
            """, (customer.name,), as_dict=True)
            primary = [a.pincode for a in addresses if a.is_primary_address and a.pincode]
            others  = [a.pincode for a in addresses if not a.is_primary_address and a.pincode]
            final_pincode_list = (
                sorted(list(set(primary)), reverse=True)
                + sorted(list(set(others) - set(primary)))
            )

        if not final_pincode_list and user_email == "Administrator":
            final_pincode_list = ["388001"]

        categories = frappe.db.sql("""
            SELECT DISTINCT ig.name as value, ig.item_group_name as label FROM `tabItem Group` ig
            INNER JOIN `tabItem` i ON i.item_group = ig.name
            WHERE ig.is_group = 0 AND i.disabled = 0 AND i.is_sales_item = 1
            ORDER BY ig.item_group_name ASC
        """, as_dict=True)

        pincode_map = {}
        if final_pincode_list:
            all_companies = frappe.db.sql("""
                SELECT DISTINCT a.pincode, c.name, c.company_name, c.custom_society, c.custom_seller
                FROM `tabCompany` c
                JOIN `tabDynamic Link` dl ON dl.link_name = c.name
                JOIN `tabAddress` a ON a.name = dl.parent
                WHERE a.pincode IN %s AND (c.custom_society = 1 OR c.custom_seller = 1)
            """, (final_pincode_list,), as_dict=True)
            for pin in final_pincode_list:
                pincode_map[pin] = {
                    "societies": [
                        {"value": c.name, "label": c.company_name}
                        for c in all_companies if c.pincode == pin and c.custom_society
                    ],
                    "sellers": [
                        {"value": c.name, "label": c.company_name}
                        for c in all_companies if c.pincode == pin and c.custom_seller
                    ]
                }
        return {
            "status": "success",
            "customer": customer,
            "pincode_list": [{"label": p, "value": p} for p in final_pincode_list],
            "pincode_map": pincode_map,
            "all_categories": categories
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Customer Sidebar Error")
        return {"status": "error", "message": str(e)}

def get_seller_territory(seller):
    if not seller:
        return "Anand"
    addresses = frappe.db.sql("""
        SELECT a.city, a.pincode, a.is_primary_address FROM `tabAddress` a
        JOIN `tabDynamic Link` dl ON a.name = dl.parent
        WHERE dl.link_doctype = 'Company' AND dl.link_name = %s
        ORDER BY a.is_primary_address DESC
    """, (seller,), as_dict=True)
    if not addresses:
        return "Anand"
    for addr in addresses:
        city = (addr.get("city") or "").strip()
        if not city:
            continue
        territory = frappe.db.get_value("Territory", {"name": city}, "name")
        if territory:
            return territory
        territory = frappe.db.sql(
            "SELECT name FROM `tabTerritory` WHERE LOWER(name) = LOWER(%s) LIMIT 1",
            (city,), pluck=True
        )
        if territory:
            return territory[0]
    return "Anand"

def _is_subscription_category(item_group_value):
    if not item_group_value:
        return False
    ig_name = frappe.db.get_value("Item Group", item_group_value, "item_group_name") or ""
    ig_lower = ig_name.lower()
    iv_lower = str(item_group_value).lower()
    for keyword in ["newspaper", "magazine", "news paper", "paper"]:
        if keyword in ig_lower or keyword in iv_lower:
            return True
    return False


def find_price_recursive(item_code, current_territory, day, target_date):
    temp_territory = current_territory
    while temp_territory:
        rules = frappe.db.get_all(
            "Daily Item Price",
            filters={"item_code": item_code, "territory": temp_territory},
            fields=["name", "start_date", "end_date"],
            order_by="start_date desc"
        )
        for r in rules:
            if not r.start_date:
                continue
            if getdate(r.start_date) > getdate(target_date):
                continue
            if r.end_date and getdate(r.end_date) < getdate(target_date):
                continue
            price = frappe.db.get_value(
                "Daily Price Detail",
                {"parent": r.name, "day": day},
                "price"
            )
            if price and float(price) > 0:
                return {"price": float(price), "price_available": True, "price_reason": ""}
            else:
                return {
                    "price": 0.0,
                    "price_available": False,
                    "price_reason": f"Price not set by seller for {day}"
                }
        parent = frappe.db.get_value("Territory", temp_territory, "parent_territory")
        temp_territory = parent
    return {
        "price": 0.0,
        "price_available": False,
        "price_reason": f"No price rule found for {day}"
    }

@frappe.whitelist()
def get_customer_subscription_status(customer, seller):
    if not customer or not seller:
        return {"active": {}, "pending": {}, "schedule": {}}

    today = nowdate()

    subs = frappe.db.sql("""
        SELECT name, status FROM `tabNewspaper Subscription`
        WHERE customer = %s AND seller = %s
          AND status IN ('Active', 'Accept Pending')
          AND start_date <= %s AND end_date >= %s
    """, (customer, seller, today, today), as_dict=True)

    active_map   = {}
    pending_map  = {}
    schedule_map = {}

    for sub in subs:
        schedule_items = frappe.db.get_all(
            "Newspaper Subscription Item",
            filters={"parent": sub.name},
            fields=[
                "item_code", "is_primary_item",
                "monday_qty", "tuesday_qty", "wednesday_qty",
                "thursday_qty", "friday_qty", "saturday_qty", "sunday_qty"
            ]
        )
        for si in schedule_items:
            ic = si.item_code
            if not ic:
                continue

            schedule_map[ic] = {
                "Monday":    int(si.monday_qty or 0),
                "Tuesday":   int(si.tuesday_qty or 0),
                "Wednesday": int(si.wednesday_qty or 0),
                "Thursday":  int(si.thursday_qty or 0),
                "Friday":    int(si.friday_qty or 0),
                "Saturday":  int(si.saturday_qty or 0),
                "Sunday":    int(si.sunday_qty or 0),
                "sub_name":  sub.name
            }

            if sub.status == "Active":
                active_map[ic] = sub.name
            elif sub.status == "Accept Pending":
                pending_map[ic] = sub.name

    return {
        "active":   active_map,
        "pending":  pending_map,
        "schedule": schedule_map
    }

@frappe.whitelist()
def get_seller_items(category=None, seller=None):
    if not category:
        return []
    items = frappe.get_all(
        "Item",
        filters={"disabled": 0, "is_sales_item": 1, "item_group": category},
        fields=["name", "item_code", "item_name", "item_group",
                "image", "standard_rate", "description", "stock_uom"]
    )
    category_is_subscription = _is_subscription_category(category)
    seller_territory = get_seller_territory(seller)
    target_date = nowdate()
    day = get_datetime(target_date).strftime("%A")

    for item in items:
        item["is_subscription_item"] = category_is_subscription

        result = find_price_recursive(item.item_code, seller_territory, day, target_date)
        item["price"]           = result["price"]
        item["price_available"] = result["price_available"]
        item["price_reason"]    = result["price_reason"]
        item["formatted_price"] = fmt_money(result["price"], currency="INR") if result["price_available"] else ""

        day_prices = {}
        for d in ALL_DAYS:
            pr = find_price_recursive(item.item_code, seller_territory, d, target_date)
            day_prices[d] = pr["price"] if pr["price_available"] else 0.0
        item["day_prices"] = day_prices

    return items

@frappe.whitelist()
def create_subscription(
    customer, seller,
    schedule_items,
    start_date=None,
    months=1
):
    try:
        import json

        if isinstance(schedule_items, str):
            try:
                schedule_items = json.loads(schedule_items)
            except Exception:
                schedule_items = []

        if not schedule_items:
            return {"status": "error", "message": "No schedule items provided"}

        today    = nowdate()
        start_dt = getdate(start_date) if start_date else getdate(today)
        end_dt   = add_months(start_dt, int(months))

        primary_items = [s for s in schedule_items if s.get("is_primary_item")]
        if not primary_items:
            schedule_items[0]["is_primary_item"] = 1
            primary_items = [schedule_items[0]]

        primary_item_code = primary_items[0].get("item_code")

        primary = primary_items[0]
        has_any_day = any(
            int(primary.get(DAY_QTY_FIELD[d], 0) or 0) > 0
            for d in ALL_DAYS
        )
        if not has_any_day:
            return {"status": "error", "message": "Please select at least one day for delivery."}

        existing = frappe.db.sql("""
            SELECT ns.name, ns.status
            FROM `tabNewspaper Subscription` ns
            JOIN `tabNewspaper Subscription Item` nsi ON nsi.parent = ns.name
            WHERE ns.customer = %s AND ns.seller = %s
              AND nsi.item_code = %s AND nsi.is_primary_item = 1
              AND ns.status IN ('Active', 'Accept Pending')
              AND ns.end_date >= %s
        """, (customer, seller, primary_item_code, today), as_dict=True)

        if existing:
            return {
                "status": "error",
                "message": (
                    f"Subscription already exists with status '{existing[0].status}' "
                    f"({existing[0].name}). Wait for seller to accept or subscription to expire."
                )
            }

        doc = frappe.new_doc("Newspaper Subscription")
        doc.customer   = customer
        doc.seller     = seller
        doc.start_date = start_dt
        doc.end_date   = end_dt
        doc.status     = "Accept Pending"
        doc.territory  = get_seller_territory(seller)

        for si in schedule_items:
            ic = si.get("item_code")
            if not ic:
                continue
            item_name_val = frappe.db.get_value("Item", ic, "item_name") or ic
            child_row = doc.append("schedule_items", {})
            child_row.item_code       = ic
            child_row.item_name       = item_name_val
            child_row.is_primary_item = 1 if si.get("is_primary_item") else 0
            for d in ALL_DAYS:
                qty_field = DAY_QTY_FIELD[d]
                try:
                    qty = max(0, min(int(si.get(qty_field, 0) or 0), 99))
                except (ValueError, TypeError):
                    qty = 0
                setattr(child_row, qty_field, qty)

        doc.flags.ignore_permissions = True
        doc.insert()
        frappe.db.commit()

        primary_item_name = frappe.db.get_value("Item", primary_item_code, "item_name") or primary_item_code
        msg = f"Subscription request sent for '{primary_item_name}'. Waiting for seller approval."

        return {
            "status": "success",
            "message": msg,
            "subscription_id": doc.name
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Subscription Creation Error")
        return {"status": "error", "message": str(e)}

@frappe.whitelist()
def get_seller_subscriptions(seller=None, status_filter=None):
    try:
        if not seller:
            seller = frappe.db.get_value("Company", {"custom_seller": 1}, "name")
        if not seller:
            return {"status": "error", "message": "Seller not found"}

        filters = {"seller": seller}
        if status_filter:
            filters["status"] = status_filter
        else:
            filters["status"] = ["in", ["Accept Pending", "Active"]]

        subs = frappe.get_all(
            "Newspaper Subscription",
            filters=filters,
            fields=["name", "customer", "status", "start_date", "end_date", "territory", "creation"],
            order_by="creation desc"
        )

        for sub in subs:
            sub.customer_name = frappe.db.get_value("Customer", sub.customer, "customer_name") or sub.customer

            schedule_items = frappe.db.get_all(
                "Newspaper Subscription Item",
                filters={"parent": sub.name},
                fields=["item_code", "item_name", "is_primary_item",
                        "monday_qty", "tuesday_qty", "wednesday_qty",
                        "thursday_qty", "friday_qty", "saturday_qty", "sunday_qty"]
            )
            sub.schedule_items = schedule_items

            primary = next((s for s in schedule_items if s.is_primary_item), None)
            sub.primary_item_name = primary.item_name if primary else ""

            sub.formatted_start = format_date(sub.start_date)
            sub.formatted_end   = format_date(sub.end_date)

        return {"status": "success", "subscriptions": subs}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Seller Subscriptions Error")
        return {"status": "error", "message": str(e)}


# ─── HELPER: Customer ka email nikalo ───────────────────────────────────────
def _get_customer_email(customer_name):
    """Customer ka email ya user field se email lo."""
    return (
        frappe.db.get_value("Customer", customer_name, "email_id")
        or frappe.db.get_value("Customer", customer_name, "user")
        or None
    )


@frappe.whitelist()
def process_subscription(sub_name, action):
    """
    action: 'accept' or 'reject'
    - accept: sets status=Active
    - reject: sets status=Cancelled
    Dono cases me customer ka frontend realtime se auto-refresh hoga.
    """
    try:
        sub = frappe.get_doc("Newspaper Subscription", sub_name)
        customer_email = _get_customer_email(sub.customer)

        if action == "accept":
            if sub.status != "Accept Pending":
                return {"status": "error", "message": f"Cannot accept — status is '{sub.status}'"}

            sub.status = "Active"
            sub.flags.ignore_permissions = True
            sub.save()
            frappe.db.commit()

            # ✅ FIX 1: Custom realtime event — frontend ka subscription_update handler trigger hoga
            if customer_email:
                frappe.publish_realtime(
                    event='subscription_update',
                    message={
                        'sub_name': sub_name,
                        'action': 'accepted',
                        'customer': customer_email
                    },
                    user=customer_email
                )

            # Existing: msgprint + Notification Log (bhi trigger hoga — double refresh safe hai)
            _notify_customer_subscription(
                customer=sub.customer,
                sub_name=sub.name,
                action="accepted"
            )

            return {
                "status": "success",
                "message": f"Subscription {sub.name} activated! Daily orders will generate from tomorrow via cron."
            }

        elif action == "reject":
            if sub.status not in ("Accept Pending", "Active"):
                return {"status": "error", "message": f"Cannot reject — status is '{sub.status}'"}

            sub.status = "Cancelled"
            sub.flags.ignore_permissions = True
            sub.save()
            frappe.db.commit()

            # ✅ FIX 2: Reject pe bhi realtime event
            if customer_email:
                frappe.publish_realtime(
                    event='subscription_update',
                    message={
                        'sub_name': sub_name,
                        'action': 'rejected',
                        'customer': customer_email
                    },
                    user=customer_email
                )

            _notify_customer_subscription(
                customer=sub.customer,
                sub_name=sub.name,
                action="rejected"
            )

            return {
                "status": "success",
                "message": f"Subscription {sub.name} cancelled."
            }

        return {"status": "error", "message": "Unknown action"}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Process Subscription Error")
        return {"status": "error", "message": str(e)}


def _run_daily_orders(override_day=None, test_mode=False):
    today    = nowdate()
    day_name = override_day if override_day else get_datetime(today).strftime("%A")
    qty_field = DAY_QTY_FIELD.get(day_name, "monday_qty")

    if test_mode:
        date_condition = "AND start_date <= %(today)s"
    else:
        date_condition = "AND start_date < %(today)s"

    active_subs = frappe.db.sql(f"""
        SELECT name, customer, seller, territory
        FROM `tabNewspaper Subscription`
        WHERE status = 'Active'
          {date_condition}
          AND end_date >= %(today)s
    """, {"today": today}, as_dict=True)

    total = len(active_subs)
    created = skipped = dn_created = 0
    failed = []

    for sub in active_subs:
        try:
            already = frappe.db.get_value("Sales Order", {
                "custom_subscription_refereance": sub.name,
                "transaction_date": today,
                "docstatus": ["!=", 2]
            }, "name")
            if already:
                skipped += 1
                continue

            schedule_items = frappe.db.get_all(
                "Newspaper Subscription Item",
                filters={"parent": sub.name},
                fields=["item_code", "item_name"] + list(DAY_QTY_FIELD.values())
            )

            items_to_order = []
            for si in schedule_items:
                qty = int(getattr(si, qty_field, 0) or 0)
                if qty > 0:
                    items_to_order.append({"item_code": si.item_code, "qty": qty})

            if not items_to_order:
                skipped += 1
                continue

            item_prices  = []
            price_failed = False
            for entry in items_to_order:
                price_result = find_price_recursive(
                    entry["item_code"], sub.territory, day_name, today
                )
                if not price_result["price_available"]:
                    failed.append({
                        "subscription": sub.name,
                        "customer":     sub.customer,
                        "item":         entry["item_code"],
                        "reason":       price_result["price_reason"]
                    })
                    price_failed = True
                    break
                item_prices.append({
                    "item_code": entry["item_code"],
                    "qty":       entry["qty"],
                    "price":     price_result["price"]
                })

            if price_failed:
                continue

            so = frappe.new_doc("Sales Order")
            so.customer                       = sub.customer
            so.company                        = sub.seller
            so.transaction_date               = today
            so.delivery_date                  = today
            so.territory                      = sub.territory
            so.custom_subscription_refereance = sub.name

            for ip in item_prices:
                so.append("items", {
                    "item_code":           ip["item_code"],
                    "qty":                 ip["qty"],
                    "rate":                ip["price"],
                    "delivery_date":       today,
                    "ignore_pricing_rule": 1
                })

            so.flags.ignore_permissions = True
            _insert_sales_order_with_warehouse_fallback(so, sub.seller)
            so.reload()
            so.submit()
            created += 1

            try:
                dn = get_mapped_doc("Sales Order", so.name, {
                    "Sales Order": {
                        "doctype": "Delivery Note",
                        "validation": {"docstatus": ["=", 1]}
                    },
                    "Sales Order Item": {
                        "doctype": "Delivery Note Item",
                        "field_map": {
                            "name":   "so_detail",
                            "parent": "against_sales_order"
                        }
                    }
                })

                for item in dn.items:
                    item.warehouse = None

                dn.flags.ignore_permissions        = True
                dn.flags.ignore_mandatory          = True
                dn.flags.ignore_stock_validation   = True
                dn.flags.ignore_validate_link      = True

                dn.insert(ignore_mandatory=True)

                dn.flags.ignore_permissions        = True
                dn.flags.ignore_stock_validation   = True
                frappe.flags.ignore_stock_ledger   = True
                dn.submit()

                frappe.flags.ignore_stock_ledger   = False
                dn_created += 1

            except Exception as dn_err:
                frappe.log_error(frappe.get_traceback(), f"Auto DN Error: {so.name}")
                failed.append({
                    "subscription": sub.name,
                    "so":           so.name,
                    "reason":       f"SO created but DN failed: {str(dn_err)}"
                })

        except Exception as e:
            failed.append({"subscription": sub.name, "reason": str(e)})
            frappe.log_error(frappe.get_traceback(), f"Daily Order Error: {sub.name}")

    summary = (
        f"Date:{today} Day:{day_name} Mode:{'TEST' if test_mode else 'PROD'} "
        f"Total:{total} Created:{created} DN:{dn_created} "
        f"Skipped:{skipped} Failed:{len(failed)}"
    )
    if failed:
        frappe.log_error(f"{summary}\n{failed}", "Daily Order Generation")
    else:
        frappe.logger().info(summary)

    return {
        "date":       today,
        "day":        day_name,
        "total":      total,
        "created":    created,
        "dn_created": dn_created,
        "skipped":    skipped,
        "failed":     failed
    }


@frappe.whitelist()
def generate_daily_orders():
    """Production cron — start_date < today (next day se orders shuru)"""
    return _run_daily_orders(test_mode=False)


@frappe.whitelist()
def generate_daily_orders_test(test_day=None):
    """Test mode — start_date <= today (same day bhi chalega)"""
    return _run_daily_orders(override_day=test_day, test_mode=True)

def _insert_sales_order_with_warehouse_fallback(so, seller_company):
    try:
        so.insert()
    except frappe.exceptions.ValidationError as ve:
        if "warehouse" in str(ve).lower():
            wh = (
                frappe.db.get_value("Warehouse", {"company": seller_company, "is_group": 0}, "name")
                or frappe.db.get_value("Warehouse", {"is_group": 0}, "name")
            )
            if wh:
                for row in so.items:
                    if not row.get("warehouse"):
                        row.warehouse = wh
                so.insert()
            else:
                raise
        else:
            raise

@frappe.whitelist()
def expire_old_subscriptions():
    today = nowdate()
    expired = frappe.db.sql("""
        SELECT name FROM `tabNewspaper Subscription`
        WHERE status IN ('Active', 'Accept Pending') AND end_date < %(today)s
    """, {"today": today}, pluck=True)
    for name in expired:
        frappe.db.set_value("Newspaper Subscription", name, "status", "Expired")
    if expired:
        frappe.db.commit()
    return {"expired_count": len(expired)}

@frappe.whitelist()
def place_order(cart_data, customer, seller, pincode, society=None, delivery_address=None):
    try:
        import json
        if isinstance(cart_data, str):
            cart_data = json.loads(cart_data)
        if not cart_data:
            return {"status": "error", "message": _("Cart is empty")}

        seller_territory = get_seller_territory(seller)
        target_date = nowdate()
        day = get_datetime(target_date).strftime("%A")

        so = frappe.new_doc("Sales Order")
        so.customer         = customer
        so.company          = seller
        so.transaction_date = nowdate()
        so.delivery_date    = frappe.utils.add_days(nowdate(), 1)
        so.territory        = seller_territory

        if delivery_address:
            so.customer_address = delivery_address
        if hasattr(so, "custom_pincode"):
            so.custom_pincode = pincode
        if hasattr(so, "custom_society") and society:
            so.custom_society = society

        unavailable_items = []
        for item_code, qty in cart_data.items():
            result = find_price_recursive(item_code, seller_territory, day, target_date)
            if not result["price_available"]:
                unavailable_items.append(
                    frappe.db.get_value("Item", item_code, "item_name") or item_code
                )
                continue
            so.append("items", {
                "item_code": item_code,
                "qty": qty,
                "rate": result["price"],
                "ignore_pricing_rule": 1,
                "delivery_date": so.delivery_date
            })

        if not so.items:
            return {
                "status": "error",
                "message": _("No items available for today. Seller has not set prices for {0}.").format(day)
            }

        so.flags.ignore_permissions = True
        so.insert()

        return {
            "status": "success",
            "message": _("Order placed! ID: {0}").format(so.name),
            "order_id": so.name,
            "order_name": so.name,
            "grand_total": so.grand_total,
            "formatted_total": fmt_money(so.grand_total, currency="INR"),
            "skipped_items": unavailable_items
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Place Order Error")
        return {"status": "error", "message": str(e)}

@frappe.whitelist()
def get_customer_orders(customer=None):
    try:
        if not customer:
            user_email = frappe.session.user
            customer = (
                frappe.db.get_value("Customer", {"email_id": user_email}, "name")
                or frappe.db.get_value("Customer", {"user": user_email}, "name")
            )
        if not customer:
            return {"status": "error", "message": _("Customer not found")}

        orders = frappe.db.sql("""
            SELECT so.name, so.transaction_date, so.delivery_date, so.grand_total,
                   so.docstatus, so.status, so.company as seller,
                   so.per_delivered, so.per_billed,
                   so.custom_subscription_refereance
            FROM `tabSales Order` so
            WHERE so.customer = %s
            ORDER BY so.creation DESC
        """, (customer,), as_dict=True)

        for order in orders:
            order.is_subscription_order = bool(order.custom_subscription_refereance)

            if order.docstatus == 0:
                order.display_status = "Pending Acceptance"
                order.can_cancel     = True
                order.status_color   = "orange"
            elif order.docstatus == 1:
                order.can_cancel     = False
                order.display_status = {
                    "To Deliver and Bill": "Accepted - Pending Delivery",
                    "To Bill":             "Delivered - Payment Due",
                    "Completed":           "Completed"
                }.get(order.status, order.status)
                order.status_color = "green" if order.status == "Completed" else "blue"
            else:
                order.display_status = "Cancelled"
                order.status_color   = "red"
                order.can_cancel     = False

            order.formatted_total = fmt_money(order.grand_total, currency="INR")
            order.formatted_date  = format_date(order.transaction_date)

        subs = frappe.db.sql("""
            SELECT name, status, start_date, end_date, seller, creation
            FROM `tabNewspaper Subscription`
            WHERE customer = %s
            ORDER BY creation DESC
        """, (customer,), as_dict=True)

        for sub in subs:
            sub.schedule_items = frappe.db.get_all(
                "Newspaper Subscription Item",
                filters={"parent": sub.name},
                fields=["item_code", "item_name", "is_primary_item",
                        "monday_qty", "tuesday_qty", "wednesday_qty",
                        "thursday_qty", "friday_qty", "saturday_qty", "sunday_qty"]
            )
            sub.formatted_start = format_date(sub.start_date)
            sub.formatted_end   = format_date(sub.end_date)

        return {"status": "success", "orders": orders, "subscriptions": subs}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Customer Orders Error")
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def cancel_order(order_id):
    try:
        doc = frappe.get_doc("Sales Order", order_id)
        user_email = frappe.session.user
        customer = (
            frappe.db.get_value("Customer", {"email_id": user_email}, "name")
            or frappe.db.get_value("Customer", {"user": user_email}, "name")
        )
        if doc.customer != customer and user_email != "Administrator":
            return {"status": "error", "message": _("You can only cancel your own orders")}
        if doc.docstatus == 0:
            frappe.delete_doc("Sales Order", order_id, ignore_permissions=True)
            return {"status": "success", "message": _("Order cancelled successfully")}
        return {"status": "error", "message": _("Cannot cancel accepted orders. Please contact seller.")}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Cancel Order Error")
        return {"status": "error", "message": str(e)}

@frappe.whitelist()
def process_order_workflow(order_id, action):
    try:
        doc = frappe.get_doc("Sales Order", order_id)
        customer_email = _get_customer_email(doc.customer)

        if action == "accept":
            if doc.docstatus == 1:
                return {"status": "error", "message": _("Already accepted.")}
            doc.submit()

            # ✅ FIX 3: Order accept pe customer ko notify karo
            if customer_email:
                frappe.publish_realtime(
                    event='order_update',
                    message={
                        'order_id': doc.name,
                        'action': 'accepted',
                        'customer': customer_email
                    },
                    user=customer_email
                )

            return {
                "status": "success",
                "message": _("Order {0} accepted").format(doc.name)
            }

        elif action == "reject":
            if doc.docstatus != 0:
                return {"status": "error", "message": _("Cannot reject accepted orders")}
            frappe.delete_doc("Sales Order", order_id, ignore_permissions=True)

            # ✅ FIX 4: Order reject pe bhi notify karo
            if customer_email:
                frappe.publish_realtime(
                    event='order_update',
                    message={
                        'order_id': order_id,
                        'action': 'rejected',
                        'customer': customer_email
                    },
                    user=customer_email
                )

            return {"status": "success", "message": _("Order rejected")}

        elif action == "deliver":
            if doc.docstatus == 0:
                return {"status": "error", "message": _("Accept the order first")}
            if doc.per_delivered >= 100:
                return {"status": "error", "message": _("Already fully delivered")}
            dn = get_mapped_doc("Sales Order", order_id, {
                "Sales Order": {
                    "doctype": "Delivery Note",
                    "validation": {"docstatus": ["=", 1]}
                },
                "Sales Order Item": {
                    "doctype": "Delivery Note Item",
                    "field_map": {
                        "name": "so_detail",
                        "parent": "against_sales_order"
                    }
                }
            })
            dn.insert(ignore_permissions=True)
            dn.submit()

            # ✅ FIX 5: Delivery pe bhi customer notify karo
            if customer_email:
                frappe.publish_realtime(
                    event='order_update',
                    message={
                        'order_id': order_id,
                        'action': 'delivered',
                        'customer': customer_email
                    },
                    user=customer_email
                )

            return {
                "status": "success",
                "message": _("Delivery Note {0} created").format(dn.name)
            }

        elif action == "invoice":
            if doc.docstatus == 0:
                return {"status": "error", "message": _("Accept the order first")}
            if doc.per_billed >= 100:
                return {"status": "error", "message": _("Already fully billed")}
            sinv = get_mapped_doc("Sales Order", order_id, {
                "Sales Order": {
                    "doctype": "Sales Invoice",
                    "validation": {"docstatus": ["=", 1]}
                },
                "Sales Order Item": {
                    "doctype": "Sales Invoice Item",
                    "field_map": {
                        "name": "so_detail",
                        "parent": "against_sales_order"
                    }
                }
            })
            sinv.insert(ignore_permissions=True)
            sinv.submit()
            return {
                "status": "success",
                "message": _("Invoice {0} created").format(sinv.name)
            }

        return {"status": "error", "message": _("Unknown action")}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Order Workflow Error")
        return {"status": "error", "message": str(e)}


def _notify_customer_subscription(customer, sub_name, action):
    try:
        user_email = _get_customer_email(customer)
        if not user_email:
            return

        if action == "accepted":
            subject = f"✅ Subscription {sub_name} Activated!"
            message = (
                f"Great news! Your subscription plan <b>{sub_name}</b> has been "
                f"<b>accepted and activated</b> by the seller. "
                f"Daily newspaper delivery will start automatically from tomorrow."
            )
        else:
            subject = f"❌ Subscription {sub_name} Rejected"
            message = (
                f"Your subscription plan <b>{sub_name}</b> has been "
                f"<b>rejected</b> by the seller. "
                f"Please contact the seller or create a new subscription."
            )

        frappe.publish_realtime(
            event="msgprint",
            message=message,
            user=user_email
        )

        note = frappe.new_doc("Notification Log")
        note.subject          = subject
        note.email_content    = message
        note.for_user         = user_email
        note.type             = "Alert"
        note.document_type    = "Newspaper Subscription"
        note.document_name    = sub_name
        note.flags.ignore_permissions = True
        note.insert()
        frappe.db.commit()

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Subscription Notification Error")

@frappe.whitelist()
def get_seller_orders(seller=None, status_filter=None):
    try:
        if not seller:
            seller = frappe.db.get_value("Company", {"custom_seller": 1}, "name")
        if not seller:
            return {"status": "error", "message": _("Seller company not found")}

        filters = {"company": seller}
        if status_filter == "pending":    filters["docstatus"] = 0
        elif status_filter == "accepted": filters["docstatus"] = 1

        orders = frappe.get_all(
            "Sales Order",
            filters=filters,
            fields=[
                "name", "customer", "customer_name", "transaction_date",
                "grand_total", "docstatus", "status", "per_delivered", "per_billed",
                "custom_subscription_refereance", "currency"
            ],
            order_by="creation desc"
        )

        for o in orders:
            o.display_status     = "Pending" if o.docstatus == 0 else (
                "Cancelled" if o.docstatus == 2 else o.status
            )
            o.formatted_total    = fmt_money(o.grand_total, currency="INR")
            o.formatted_date     = format_date(o.transaction_date)
            o.is_subscription_order = bool(o.custom_subscription_refereance)

            o.items = frappe.db.get_all(
                "Sales Order Item",
                filters={"parent": o.name},
                fields=["item_code", "item_name", "qty", "rate", "delivered_qty", "uom"]
            )

        return {"status": "success", "orders": orders}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Seller Orders Error")
        return {"status": "error", "message": str(e)}

@frappe.whitelist()
def debug_price_setup(seller=None):
    result = {}
    if not seller:
        seller_company = frappe.db.get_value(
            "Company", {"custom_seller": 1}, ["name", "company_name"], as_dict=True
        )
        result["auto_detected_seller"] = seller_company
        if seller_company:
            seller = seller_company.name
    if seller:
        result["seller_company"]     = frappe.db.get_value(
            "Company", seller, ["name", "company_name"], as_dict=True
        )
        result["resolved_territory"] = get_seller_territory(seller)
    result["today"]     = nowdate()
    result["today_day"] = get_datetime(nowdate()).strftime("%A")
    result["active_subscriptions"] = frappe.db.sql("""
        SELECT name, customer, seller, territory, start_date, end_date, status
        FROM `tabNewspaper Subscription`
        WHERE status IN ('Active', 'Accept Pending')
        ORDER BY creation DESC
    """, as_dict=True)
    return result


@frappe.whitelist()
def get_seller_sidebar_data():
    try:
        seller = frappe.db.get_value(
            "Company", {"custom_seller": 1},
            ["name", "company_name"], as_dict=True
        )
        if not seller:
            return {"status": "error", "message": "No seller company found"}

        pincodes = frappe.db.sql("""
            SELECT DISTINCT a.pincode FROM `tabAddress` a
            JOIN `tabDynamic Link` dl ON a.name = dl.parent
            WHERE dl.link_doctype = 'Company' AND dl.link_name = %s
              AND a.pincode IS NOT NULL AND a.pincode != ''
            ORDER BY a.pincode
        """, (seller.name,), pluck=True)

        if not pincodes:
            return {
                "status": "success",
                "seller": seller,
                "pincode_list": [],
                "pincode_map": {},
                "all_categories": []
            }

        pincode_map = {}

        all_companies = frappe.db.sql("""
            SELECT DISTINCT a.pincode, c.name, c.company_name, c.custom_society
            FROM `tabCompany` c
            JOIN `tabDynamic Link` dl ON dl.link_name = c.name AND dl.link_doctype = 'Company'
            JOIN `tabAddress` a ON a.name = dl.parent
            WHERE a.pincode IN %s AND c.custom_society = 1
        """, (pincodes,), as_dict=True)

        all_customers = frappe.db.sql("""
            SELECT DISTINCT a.pincode, c.name, c.customer_name FROM `tabCustomer` c
            JOIN `tabDynamic Link` dl ON dl.link_name = c.name AND dl.link_doctype = 'Customer'
            JOIN `tabAddress` a ON a.name = dl.parent
            WHERE a.pincode IN %s
            ORDER BY c.customer_name
        """, (pincodes,), as_dict=True)

        for pin in pincodes:
            pincode_map[pin] = {
                "societies": [
                    {"value": c.name, "label": c.company_name}
                    for c in all_companies if c.pincode == pin
                ],
                "customers": [
                    {"value": c.name, "label": c.customer_name}
                    for c in all_customers if c.pincode == pin
                ]
            }

        categories = frappe.db.sql("""
            SELECT DISTINCT ig.name as value, ig.item_group_name as label
            FROM `tabItem Group` ig
            INNER JOIN `tabItem` i ON i.item_group = ig.name
            WHERE ig.is_group = 0 AND i.disabled = 0 AND i.is_sales_item = 1
            ORDER BY ig.item_group_name ASC
        """, as_dict=True)

        return {
            "status": "success",
            "seller": seller,
            "pincode_list": [{"label": p, "value": p} for p in pincodes],
            "pincode_map": pincode_map,
            "all_categories": categories
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Seller Sidebar Error")
        return {"status": "error", "message": str(e)}

@frappe.whitelist()
def get_customers_by_pincode_society(pincode, society=None):
    try:
        if society:
            customers = frappe.db.sql("""
                SELECT DISTINCT c.name AS value, c.customer_name AS label
                FROM `tabCustomer` c
                JOIN `tabDynamic Link` dl ON dl.link_name = c.name AND dl.link_doctype = 'Customer'
                JOIN `tabAddress` a ON a.name = dl.parent
                WHERE a.pincode = %s
                ORDER BY c.customer_name
            """, (pincode,), as_dict=True)
        else:
            customers = frappe.db.sql("""
                SELECT DISTINCT c.name AS value, c.customer_name AS label
                FROM `tabCustomer` c
                JOIN `tabDynamic Link` dl ON dl.link_name = c.name AND dl.link_doctype = 'Customer'
                JOIN `tabAddress` a ON a.name = dl.parent
                WHERE a.pincode = %s
                ORDER BY c.customer_name
            """, (pincode,), as_dict=True)
        return {"status": "success", "customers": customers}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@frappe.whitelist()
def get_seller_customers(seller=None):
    try:
        if not seller:
            seller = frappe.db.get_value("Company", {"custom_seller": 1}, "name")
        if not seller:
            return {"status": "error", "message": "Seller not found"}

        customer_names_from_orders = frappe.db.sql_list("""
            SELECT DISTINCT customer FROM `tabSales Order`
            WHERE company = %s AND docstatus != 2
        """, (seller,))

        customer_names_from_subs = frappe.db.sql_list("""
            SELECT DISTINCT customer FROM `tabNewspaper Subscription`
            WHERE seller = %s
        """, (seller,))

        all_customer_names = list(set(customer_names_from_orders + customer_names_from_subs))

        if not all_customer_names:
            return {
                "status": "success",
                "customers": [],
                "pincodes": []
            }

        customers_info = frappe.db.sql("""
            SELECT c.name, c.customer_name, c.email_id as email,
                   c.mobile_no as mobile
            FROM `tabCustomer` c
            WHERE c.name IN %s
            ORDER BY c.customer_name ASC
        """, (all_customer_names,), as_dict=True)

        customer_pincodes = frappe.db.sql("""
            SELECT dl.link_name as customer, a.pincode
            FROM `tabAddress` a
            JOIN `tabDynamic Link` dl ON a.name = dl.parent
            WHERE dl.link_doctype = 'Customer'
              AND dl.link_name IN %s
              AND a.pincode IS NOT NULL
            ORDER BY a.is_primary_address DESC
        """, (all_customer_names,), as_dict=True)

        pincode_map = {}
        for cp in customer_pincodes:
            if cp.customer not in pincode_map:
                pincode_map[cp.customer] = cp.pincode

        all_pincodes = list(set(p.pincode for p in customer_pincodes if p.pincode))

        order_stats = frappe.db.sql("""
            SELECT customer,
                   COUNT(*) as total_orders,
                   SUM(grand_total) as total_revenue
            FROM `tabSales Order`
            WHERE company = %s AND docstatus != 2
            GROUP BY customer
        """, (seller,), as_dict=True)

        order_stats_map = {o.customer: o for o in order_stats}

        sub_counts = frappe.db.sql("""
            SELECT customer, status, COUNT(*) as cnt
            FROM `tabNewspaper Subscription`
            WHERE seller = %s
            GROUP BY customer, status
        """, (seller,), as_dict=True)

        active_subs_map  = {}
        pending_subs_map = {}
        for sc in sub_counts:
            if sc.status == 'Active':
                active_subs_map[sc.customer] = sc.cnt
            elif sc.status == 'Accept Pending':
                pending_subs_map[sc.customer] = sc.cnt

        all_subs = frappe.db.sql("""
            SELECT name, customer, status, start_date, end_date
            FROM `tabNewspaper Subscription`
            WHERE seller = %s AND status IN ('Active', 'Accept Pending')
            ORDER BY creation DESC
        """, (seller,), as_dict=True)

        for sub in all_subs:
            sub.schedule_items = frappe.db.get_all(
                "Newspaper Subscription Item",
                filters={"parent": sub.name},
                fields=["item_code", "item_name", "is_primary_item",
                        "monday_qty", "tuesday_qty", "wednesday_qty",
                        "thursday_qty", "friday_qty", "saturday_qty", "sunday_qty"]
            )
            sub.formatted_start = format_date(sub.start_date)
            sub.formatted_end   = format_date(sub.end_date)

        subs_by_customer = {}
        for sub in all_subs:
            subs_by_customer.setdefault(sub.customer, []).append(sub)

        recent_orders = frappe.db.sql("""
            SELECT name, customer, transaction_date, grand_total,
                   docstatus, status, custom_subscription_refereance
            FROM `tabSales Order`
            WHERE company = %s AND docstatus != 2
            ORDER BY creation DESC
            LIMIT 500
        """, (seller,), as_dict=True)

        recent_orders_by_customer = {}
        for o in recent_orders:
            recent_orders_by_customer.setdefault(o.customer, [])
            if len(recent_orders_by_customer[o.customer]) < 5:
                recent_orders_by_customer[o.customer].append(o)

        result = []
        for c in customers_info:
            stats_obj = order_stats_map.get(c.name, {})
            result.append({
                "name":           c.name,
                "customer_name":  c.customer_name,
                "email":          c.email or "",
                "mobile":         c.mobile or "",
                "pincode":        pincode_map.get(c.name, ""),
                "active_subs":    active_subs_map.get(c.name, 0),
                "pending_subs":   pending_subs_map.get(c.name, 0),
                "total_orders":   int(stats_obj.get("total_orders", 0) or 0),
                "total_revenue":  float(stats_obj.get("total_revenue", 0) or 0),
                "subscriptions":  subs_by_customer.get(c.name, []),
                "recent_orders":  recent_orders_by_customer.get(c.name, []),
            })

        return {
            "status":    "success",
            "customers": result,
            "pincodes":  sorted(all_pincodes)
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Seller Customers Error")
        return {"status": "error", "message": str(e)}


import json
import frappe
from frappe import _
from frappe.utils import nowdate, flt

@frappe.whitelist()
def create_invoice_from_sales_orders(sales_orders):
    if isinstance(sales_orders, str):
        sales_orders = json.loads(sales_orders)

    if not sales_orders or not isinstance(sales_orders, list):
        frappe.throw(_("No Sales Order selected."))

    first_so = frappe.get_doc("Sales Order", sales_orders[0])
    _validate_so(first_so)

    for so_name in sales_orders[1:]:
        so = frappe.get_doc("Sales Order", so_name)
        _validate_so(so)
        if so.customer != first_so.customer:
            frappe.throw(_(
                f"All Sales Orders must belong to the same customer. "
                f"'{sales_orders[0]}' has customer '{first_so.customer}' "
                f"but '{so_name}' has customer '{so.customer}'."
            ))

    sinv = frappe.new_doc("Sales Invoice")
    sinv.customer            = first_so.customer
    sinv.company             = first_so.company
    sinv.currency            = first_so.currency
    sinv.conversion_rate     = first_so.conversion_rate or 1
    sinv.selling_price_list  = first_so.selling_price_list
    sinv.price_list_currency = first_so.price_list_currency
    sinv.plc_conversion_rate = first_so.plc_conversion_rate or 1
    sinv.posting_date        = nowdate()
    sinv.set_posting_time    = 1

    fully_billed_orders = []

    for so_name in sales_orders:
        so = frappe.get_doc("Sales Order", so_name)

        if _is_fully_billed(so):
            fully_billed_orders.append(so_name)
            continue

        dn_map = _get_delivery_note_map(so_name)

        for item in so.items:
            rate = flt(item.rate)
            if not rate:
                continue

            already_billed_qty = round(flt(item.billed_amt) / rate, 9)
            qty_to_bill = round(flt(item.delivered_qty) - already_billed_qty, 9)

            if qty_to_bill <= 0:
                continue

            dn_name, dn_detail = dn_map.get(item.name, (None, None))

            sinv.append("items", {
                "item_code":              item.item_code,
                "item_name":              item.item_name,
                "description":            item.description or item.item_name,
                "qty":                    qty_to_bill,
                "uom":                    item.uom,
                "stock_uom":              item.stock_uom,
                "conversion_factor":      item.conversion_factor or 1,
                "rate":                   rate,
                "amount":                 round(qty_to_bill * rate, 9),
                "warehouse":              item.warehouse,
                "cost_center":            item.cost_center,
                "income_account":         _get_income_account(item, sinv.company),
                "sales_order":            so_name,
                "so_detail":              item.name,
                "delivery_note":          dn_name,
                "dn_detail":              dn_detail,
            })

    if fully_billed_orders and len(fully_billed_orders) == len(sales_orders):
        if len(fully_billed_orders) == 1:
            frappe.throw(_(
                f"Sales Order '{fully_billed_orders[0]}' has already been fully billed. "
                f"Please select a different order."
            ))
        else:
            frappe.throw(_(
                f"All selected Sales Orders have already been fully billed: "
                f"{', '.join(fully_billed_orders)}. Please select different orders."
            ))

    if fully_billed_orders and len(fully_billed_orders) < len(sales_orders):
        frappe.log_error(
            message=f"Already fully billed orders skipped during invoice creation: {fully_billed_orders}",
            title="Invoice Creation: Orders Skipped"
        )

    if not sinv.items:
        frappe.throw(_(
            "No items available to bill. All items are either already billed or not yet delivered."
        ))

    if first_so.taxes_and_charges:
        sinv.taxes_and_charges = first_so.taxes_and_charges

    for tax in first_so.taxes:
        sinv.append("taxes", {
            "charge_type":  tax.charge_type,
            "account_head": tax.account_head,
            "description":  tax.description,
            "rate":         tax.rate,
            "cost_center":  tax.cost_center,
        })

    sinv.set_missing_values()
    sinv.calculate_taxes_and_totals()
    sinv.flags.ignore_permissions = True
    sinv.insert()
    frappe.db.commit()

    skipped_note = ""
    if fully_billed_orders:
        skipped_note = f" ({len(fully_billed_orders)} already-billed order(s) were skipped: {', '.join(fully_billed_orders)})"

    return {
        "invoice_name":   sinv.name,
        "customer":       sinv.customer,
        "grand_total":    sinv.grand_total,
        "skipped_orders": fully_billed_orders,
        "message":        f"Draft Sales Invoice '{sinv.name}' created successfully!{skipped_note}",
    }


def _is_fully_billed(so_doc) -> bool:
    if flt(so_doc.per_billed) >= 100:
        return True
    if so_doc.billing_status == "Fully Billed":
        return True
    has_billable_item = False
    for item in so_doc.items:
        rate = flt(item.rate)
        if not rate:
            continue
        delivered_qty = flt(item.delivered_qty)
        if delivered_qty <= 0:
            continue
        already_billed_qty = round(flt(item.billed_amt) / rate, 9)
        qty_to_bill = round(delivered_qty - already_billed_qty, 9)
        if qty_to_bill > 0:
            has_billable_item = True
            break
    return not has_billable_item


def _get_delivery_note_map(so_name: str) -> dict:
    try:
        rows = frappe.db.sql("""
            SELECT dni.so_detail, dni.parent, dni.name
            FROM `tabDelivery Note Item` dni
            INNER JOIN `tabDelivery Note` dn ON dn.name = dni.parent
            WHERE dni.against_sales_order = %s AND dn.docstatus = 1
        """, so_name, as_dict=True)
    except Exception:
        return {}
    result = {}
    for r in rows:
        if r.so_detail and r.so_detail not in result:
            result[r.so_detail] = (r.parent, r.name)
    return result


def _validate_so(so_doc):
    if so_doc.docstatus != 1:
        frappe.throw(_(f"Sales Order {so_doc.name} is not submitted. Only submitted orders can be invoiced."))
    if so_doc.status in ("Closed", "Cancelled"):
        frappe.throw(_(f"Sales Order {so_doc.name} is {so_doc.status} — invoice cannot be created."))

def _get_income_account(item, company: str) -> str:
    if getattr(item, "income_account", None):
        return item.income_account
    try:
        for d in frappe.get_cached_doc("Item", item.item_code).item_defaults:
            if d.company == company and d.income_account:
                return d.income_account
    except Exception:
        pass
    try:
        acc = frappe.get_cached_doc("Company", company).default_income_account
        if acc:
            return acc
    except Exception:
        pass
    return ""


@frappe.whitelist()
def get_sales_order_items(order_names):
    if isinstance(order_names, str):
        order_names = json.loads(order_names)

    if not order_names:
        return []

    rows = frappe.db.sql("""
        SELECT
            soi.parent,
            soi.item_code,
            soi.item_name,
            soi.qty,
            soi.delivered_qty,
            soi.billed_amt,
            soi.rate,
            soi.amount,
            soi.uom
        FROM `tabSales Order Item` soi
        WHERE soi.parent IN %s
        ORDER BY soi.parent, soi.idx
    """, [tuple(order_names)], as_dict=True)

    return rows