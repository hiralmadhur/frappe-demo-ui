import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import nowdate, getdate, fmt_money, format_date

# ============================================
# ROLE & CONTEXT METHODS
# ============================================

@frappe.whitelist(allow_guest=True)
def get_current_user_role():
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
def get_seller_context():
    seller = frappe.db.get_value(
        "Company", {"custom_seller": 1},
        ["name", "company_name"], as_dict=True
    )
    if not seller:
        frappe.log_error("No company found with custom_seller=1", "Seller Context Error")
        return {"pincodes": [], "company": None}

    pincodes = frappe.db.sql_list("""
        SELECT DISTINCT a.pincode
        FROM `tabAddress` a
        JOIN `tabDynamic Link` dl ON a.name = dl.parent
        WHERE dl.link_name = %s
        AND a.pincode IS NOT NULL AND a.pincode != ''
    """, (seller.name,))

    return {
        "company": seller,
        "pincodes": [{"label": p, "value": p} for p in pincodes]
    }


# ============================================
# SELLER PORTAL METHODS
# ============================================

@frappe.whitelist()
def get_filtered_options(pincode):
    if not pincode:
        return {"societies": [], "customers": []}

    societies = frappe.db.sql("""
        SELECT DISTINCT c.name AS value, c.company_name AS label
        FROM `tabCompany` c
        JOIN `tabDynamic Link` dl ON dl.link_name = c.name
        JOIN `tabAddress` a ON a.name = dl.parent
        WHERE c.custom_society = 1 AND a.pincode = %s
    """, (pincode,), as_dict=True)

    customers = frappe.db.sql("""
        SELECT DISTINCT c.name AS value, c.customer_name AS label
        FROM `tabCustomer` c
        JOIN `tabDynamic Link` dl ON dl.link_name = c.name
        JOIN `tabAddress` a ON a.name = dl.parent
        WHERE a.pincode = %s
    """, (pincode,), as_dict=True)

    return {"societies": societies, "customers": customers}


@frappe.whitelist()
def get_item_categories():
    return frappe.db.sql("""
        SELECT name AS value, item_group_name AS label
        FROM `tabItem Group`
        WHERE is_group = 0
        ORDER BY item_group_name
    """, as_dict=True)


# ============================================
# CUSTOMER SIDEBAR DATA
# ============================================

@frappe.whitelist()
def get_customer_sidebar_data():
    try:
        user_email = frappe.session.user

        customer = frappe.db.get_value(
            "Customer", {"email_id": user_email},
            ["name", "customer_name"], as_dict=True
        ) or frappe.db.get_value(
            "Customer", {"user": user_email},
            ["name", "customer_name"], as_dict=True
        )

        if not customer and user_email != "Administrator":
            frappe.log_error(f"No Customer found for email: {user_email}", "Customer Sidebar Error")

        final_pincode_list = []

        if customer:
            addresses = frappe.db.sql("""
                SELECT a.pincode, a.is_primary_address
                FROM `tabAddress` a
                JOIN `tabDynamic Link` dl ON a.name = dl.parent
                WHERE dl.link_doctype = 'Customer' AND dl.link_name = %s
            """, (customer.name,), as_dict=True)

            primary = [a.pincode for a in addresses if a.is_primary_address and a.pincode]
            others  = [a.pincode for a in addresses if not a.is_primary_address and a.pincode]
            final_pincode_list = (
                sorted(list(set(primary)), reverse=True) +
                sorted(list(set(others) - set(primary)))
            )

        if not final_pincode_list and user_email == "Administrator":
            final_pincode_list = ["388001"]

        categories = frappe.db.sql("""
            SELECT DISTINCT ig.name as value, ig.item_group_name as label
            FROM `tabItem Group` ig
            INNER JOIN `tabItem` i ON i.item_group = ig.name
            WHERE ig.is_group = 0 AND i.disabled = 0 AND i.is_sales_item = 1
            ORDER BY ig.item_group_name ASC
        """, as_dict=True)

        pincode_map = {}
        if final_pincode_list:
            all_companies = frappe.db.sql("""
                SELECT DISTINCT a.pincode, c.name, c.company_name,
                    c.custom_society, c.custom_seller
                FROM `tabCompany` c
                JOIN `tabDynamic Link` dl ON dl.link_name = c.name
                JOIN `tabAddress` a ON a.name = dl.parent
                WHERE a.pincode IN %s
                AND (c.custom_society = 1 OR c.custom_seller = 1)
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


# ============================================
# TERRITORY HELPER
# Debug confirmed: Daily Item Price territory = city name (e.g. "Anand")
# ============================================

def get_seller_territory(seller):
    """
    Seller company ke address ki city se Territory fetch karo.
    Fallback: "Anand" (teri setup ka confirmed default)
    """
    if not seller:
        return "Anand"

    addresses = frappe.db.sql("""
        SELECT a.city, a.pincode, a.is_primary_address
        FROM `tabAddress` a
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
        territory = frappe.db.sql("""
            SELECT name FROM `tabTerritory`
            WHERE LOWER(name) = LOWER(%s) LIMIT 1
        """, (city,), pluck=True)
        if territory:
            return territory[0]

    return "Anand"


# ============================================
# PRICE LOOKUP
#
# IMPORTANT BUSINESS RULE:
# Agar seller ne aaj ke liye koi valid Daily Item Price set nahi ki
# (ya end_date expire ho gayi jaise 15-Feb ke baad),
# to item "unavailable" dikhni chahiye customer ko.
# Standard Selling price fallback NAHI hogi - kyunki wo misleading hai.
#
# Return format:
#   price          : float  (0.0 agar unavailable)
#   price_available: bool   (False agar koi valid rule nahi)
#   price_reason   : str    (human-readable reason for UI)
# ============================================

def find_price_recursive(item_code, current_territory, day, target_date):
    """
    Daily Item Price se aaj ki price dhundho - territory hierarchy ke saath.

    Returns dict:
        {
            "price": 23.0,
            "price_available": True,
            "price_reason": ""
        }
    OR agar unavailable:
        {
            "price": 0.0,
            "price_available": False,
            "price_reason": "Price not set by seller for Monday"
        }

    NO standard price fallback - agar seller ne price set nahi ki to
    customer ko clearly "unavailable" dikhao.
    """
    temp_territory = current_territory
    checked_territories = []

    while temp_territory:
        checked_territories.append(temp_territory)

        # Is territory ke liye Daily Item Price rules fetch karo
        rules = frappe.db.get_all(
            "Daily Item Price",
            filters={"item_code": item_code, "territory": temp_territory},
            fields=["name", "start_date", "end_date"],
            order_by="start_date desc"
        )

        for r in rules:
            if not r.start_date:
                continue

            # Rule start hona chahiye aaj ya pehle
            if getdate(r.start_date) > getdate(target_date):
                continue

            # end_date check:
            # - None/null = no expiry, valid forever
            # - end_date >= today = still valid
            # - end_date < today = EXPIRED (seller ne band kar diya)
            if r.end_date and getdate(r.end_date) < getdate(target_date):
                # Ye rule expire ho gaya hai (e.g. end_date: 15-Feb, today: 16-Feb)
                # Agle rule try karo same territory mein
                continue

            # Valid rule mila - ab is din ki price fetch karo
            price = frappe.db.get_value(
                "Daily Price Detail",
                {"parent": r.name, "day": day},
                "price"
            )

            if price and float(price) > 0:
                # Price mili!
                return {
                    "price": float(price),
                    "price_available": True,
                    "price_reason": ""
                }
            else:
                # Rule hai but is din ke liye price 0 ya set nahi
                return {
                    "price": 0.0,
                    "price_available": False,
                    "price_reason": f"Price not set by seller for {day}"
                }

        # Is territory mein koi valid rule nahi mila - parent territory try karo
        parent = frappe.db.get_value("Territory", temp_territory, "parent_territory")
        temp_territory = parent

    # Koi bhi territory mein valid rule nahi mila
    # Standard price fallback NAHI - seller ne price hi set nahi ki
    return {
        "price": 0.0,
        "price_available": False,
        "price_reason": f"No price set by seller for {day}"
    }


# ============================================
# ITEM FETCHING WITH PRICING
# ============================================

@frappe.whitelist()
def get_seller_items(category=None, seller=None):
    """
    Items fetch karo with day-wise pricing from Daily Item Price.
    Agar price unavailable hai (end_date expire, ya set nahi),
    to item mein price_available=False aata hai - customer ko clearly dikhao.
    """
    filters = {"disabled": 0, "is_sales_item": 1}
    if category:
        filters["item_group"] = category

    items = frappe.get_all(
        "Item",
        filters=filters,
        fields=[
            "name", "item_code", "item_name", "item_group",
            "image", "standard_rate", "description", "stock_uom"
        ]
    )

    seller_territory = get_seller_territory(seller)
    target_date = nowdate()
    day = frappe.utils.get_datetime(target_date).strftime("%A")

    for item in items:
        result = find_price_recursive(item.item_code, seller_territory, day, target_date)

        item["price"]           = result["price"]
        item["price_available"] = result["price_available"]
        item["price_reason"]    = result["price_reason"]

        # formatted_price sirf tab dikhao jab available ho
        if result["price_available"]:
            item["formatted_price"] = fmt_money(result["price"], currency="INR")
        else:
            item["formatted_price"] = ""

    return items


# ============================================
# CUSTOMER: PLACE ORDER
# Cart mein unavailable items nahi hone chahiye - double check karo
# ============================================

@frappe.whitelist()
def place_order(cart_data, customer, seller, pincode, society=None, delivery_address=None):
    """
    Place order - Daily Item Price se territory-based pricing.
    Unavailable items order mein nahi jayenge.
    """
    try:
        import json
        if isinstance(cart_data, str):
            cart_data = json.loads(cart_data)

        if not cart_data:
            return {"status": "error", "message": _("Cart is empty")}

        seller_territory = get_seller_territory(seller)
        target_date = nowdate()
        day = frappe.utils.get_datetime(target_date).strftime("%A")

        so = frappe.new_doc("Sales Order")
        so.customer          = customer
        so.company           = seller
        so.transaction_date  = nowdate()
        so.delivery_date     = frappe.utils.add_days(nowdate(), 1)
        so.territory         = seller_territory

        if delivery_address:
            so.customer_address = delivery_address
        if hasattr(so, 'custom_pincode'):
            so.custom_pincode = pincode
        if hasattr(so, 'custom_society') and society:
            so.custom_society = society

        unavailable_items = []

        for item_code, qty in cart_data.items():
            result = find_price_recursive(item_code, seller_territory, day, target_date)

            if not result["price_available"]:
                # Item unavailable hai aaj - order mein mat dalo
                item_name = frappe.db.get_value("Item", item_code, "item_name") or item_code
                unavailable_items.append(item_name)
                continue

            so.append("items", {
                "item_code":          item_code,
                "qty":                qty,
                "rate":               result["price"],
                "ignore_pricing_rule": 1,
                "delivery_date":      so.delivery_date
            })

        # Agar saare items unavailable hain
        if not so.items:
            return {
                "status": "error",
                "message": _("No items available for today. Seller has not set prices for {0}.").format(day)
            }

        so.insert(ignore_permissions=True)

        # Agar kuch items unavailable the
        warning = ""
        if unavailable_items:
            warning = _(" Note: {0} item(s) were skipped as price not set for today: {1}").format(
                len(unavailable_items), ", ".join(unavailable_items)
            )

        return {
            "status":          "success",
            "message":         _("Order placed successfully! Order ID: {0}{1}").format(so.name, warning),
            "order_id":        so.name,
            "order_name":      so.name,
            "grand_total":     so.grand_total,
            "formatted_total": fmt_money(so.grand_total, currency="INR"),
            "skipped_items":   unavailable_items
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Place Order Error")
        return {"status": "error", "message": str(e)}


# ============================================
# CUSTOMER: ORDER HISTORY
# ============================================

@frappe.whitelist()
def get_customer_orders(customer=None):
    try:
        if not customer:
            user_email = frappe.session.user
            customer = frappe.db.get_value(
                "Customer", {"email_id": user_email}, "name"
            ) or frappe.db.get_value(
                "Customer", {"user": user_email}, "name"
            )

        if not customer:
            return {"status": "error", "message": _("Customer not found")}

        orders = frappe.db.sql("""
            SELECT so.name, so.transaction_date, so.delivery_date,
                so.grand_total, so.docstatus, so.status,
                so.company as seller, so.per_delivered, so.per_billed
            FROM `tabSales Order` so
            WHERE so.customer = %s
            ORDER BY so.creation DESC
        """, (customer,), as_dict=True)

        for order in orders:
            if order.docstatus == 0:
                order.display_status = "Pending Acceptance"
                order.can_cancel     = True
                order.status_color   = "orange"
            elif order.docstatus == 1:
                order.can_cancel = False
                if order.status == "To Deliver and Bill":
                    order.display_status = "Accepted - Pending Delivery"
                    order.status_color   = "blue"
                elif order.status == "To Bill":
                    order.display_status = "Delivered - Payment Due (Month End)"
                    order.status_color   = "blue"
                elif order.status == "Completed":
                    order.display_status = "Completed"
                    order.status_color   = "green"
                else:
                    order.display_status = order.status
                    order.status_color   = "gray"
            else:
                order.display_status = "Cancelled"
                order.status_color   = "red"
                order.can_cancel     = False

            order.formatted_total = fmt_money(order.grand_total, currency="INR")
            order.formatted_date  = format_date(order.transaction_date)

        return {"status": "success", "orders": orders}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Customer Orders Error")
        return {"status": "error", "message": str(e)}


# ============================================
# CUSTOMER: ORDER DETAILS
# ============================================

@frappe.whitelist()
def get_order_details(order_id):
    try:
        doc = frappe.get_doc("Sales Order", order_id)
        items = []
        for item in doc.items:
            items.append({
                "item_code":        item.item_code,
                "item_name":        item.item_name,
                "qty":              item.qty,
                "rate":             item.rate,
                "amount":           item.amount,
                "uom":              item.uom,
                "formatted_rate":   fmt_money(item.rate,   currency="INR"),
                "formatted_amount": fmt_money(item.amount, currency="INR")
            })

        if doc.docstatus == 0:
            display_status = "Pending Acceptance"
            can_cancel = True
        elif doc.docstatus == 1:
            can_cancel = False
            if doc.status == "To Deliver and Bill":
                display_status = "Accepted - Pending Delivery"
            elif doc.status == "To Bill":
                display_status = "Delivered - Pending Invoice"
            elif doc.status == "Completed":
                display_status = "Completed"
            else:
                display_status = doc.status
        else:
            display_status = "Cancelled"
            can_cancel = False

        return {
            "status": "success",
            "order": {
                "name":            doc.name,
                "transaction_date":format_date(doc.transaction_date),
                "delivery_date":   format_date(doc.delivery_date),
                "customer":        doc.customer,
                "customer_name":   doc.customer_name,
                "seller":          doc.company,
                "total":           doc.grand_total,
                "formatted_total": fmt_money(doc.grand_total, currency="INR"),
                "docstatus":       doc.docstatus,
                "display_status":  display_status,
                "can_cancel":      can_cancel,
                "items":           items
            }
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Order Details Error")
        return {"status": "error", "message": str(e)}


# ============================================
# CUSTOMER: CANCEL ORDER
# ============================================

@frappe.whitelist()
def cancel_order(order_id):
    try:
        doc = frappe.get_doc("Sales Order", order_id)
        user_email = frappe.session.user
        customer = frappe.db.get_value(
            "Customer", {"email_id": user_email}, "name"
        ) or frappe.db.get_value(
            "Customer", {"user": user_email}, "name"
        )

        if doc.customer != customer and user_email != "Administrator":
            return {"status": "error", "message": _("You can only cancel your own orders")}

        if doc.docstatus == 0:
            frappe.delete_doc("Sales Order", order_id, ignore_permissions=True)
            return {"status": "success", "message": _("Order cancelled successfully")}
        else:
            return {"status": "error", "message": _("Cannot cancel accepted orders. Please contact seller.")}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Cancel Order Error")
        return {"status": "error", "message": str(e)}


# ============================================
# SELLER: GET ORDERS
# ============================================

@frappe.whitelist()
def get_seller_orders(seller=None, status_filter=None):
    try:
        if not seller:
            seller = frappe.db.get_value("Company", {"custom_seller": 1}, "name")
        if not seller:
            return {"status": "error", "message": _("Seller company not found")}

        filters = {"company": seller}
        if status_filter == "pending":
            filters["docstatus"] = 0
        elif status_filter == "accepted":
            filters["docstatus"] = 1

        orders = frappe.get_all(
            "Sales Order",
            filters=filters,
            fields=["name", "customer", "customer_name", "transaction_date",
                    "grand_total", "docstatus", "status", "per_delivered", "per_billed"],
            order_by="creation desc"
        )

        for order in orders:
            order.display_status  = "Pending" if order.docstatus == 0 else \
                                    order.status if order.docstatus == 1 else "Cancelled"
            order.formatted_total = fmt_money(order.grand_total, currency="INR")
            order.formatted_date  = format_date(order.transaction_date)

        return {"status": "success", "orders": orders}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Seller Orders Error")
        return {"status": "error", "message": str(e)}


# ============================================
# SELLER: ORDER WORKFLOW
# ============================================

@frappe.whitelist()
def process_order_workflow(order_id, action):
    try:
        doc = frappe.get_doc("Sales Order", order_id)

        if action == "accept":
            if doc.docstatus == 1:
                return {"status": "error", "message": _("Order is already accepted.")}
            doc.submit()
            return {"status": "success", "message": _("Order {0} accepted successfully").format(doc.name)}

        elif action == "reject":
            if doc.docstatus == 0:
                frappe.delete_doc("Sales Order", order_id, ignore_permissions=True)
                return {"status": "success", "message": _("Order rejected and deleted")}
            return {"status": "error", "message": _("Cannot reject accepted orders")}

        elif action == "deliver":
            if doc.docstatus == 0:
                return {"status": "error", "message": _("Please accept the order first")}
            if doc.per_delivered >= 100:
                return {"status": "error", "message": _("Order is already fully delivered")}
            dn = get_mapped_doc("Sales Order", order_id, {
                "Sales Order":      {"doctype": "Delivery Note", "validation": {"docstatus": ["=", 1]}},
                "Sales Order Item": {"doctype": "Delivery Note Item",
                                     "field_map": {"name": "so_detail", "parent": "against_sales_order"}}
            })
            dn.insert(ignore_permissions=True)
            dn.submit()
            return {"status": "success", "message": _("Delivery Note {0} created successfully").format(dn.name)}

        elif action == "invoice":
            if doc.docstatus == 0:
                return {"status": "error", "message": _("Please accept the order first")}
            if doc.per_billed >= 100:
                return {"status": "error", "message": _("Order is already fully billed")}
            sinv = get_mapped_doc("Sales Order", order_id, {
                "Sales Order":      {"doctype": "Sales Invoice", "validation": {"docstatus": ["=", 1]}},
                "Sales Order Item": {"doctype": "Sales Invoice Item",
                                     "field_map": {"name": "so_detail", "parent": "against_sales_order"}}
            })
            sinv.insert(ignore_permissions=True)
            sinv.submit()
            return {"status": "success", "message": _("Invoice {0} created successfully").format(sinv.name)}

        return {"status": "error", "message": _("Unknown action: {0}").format(action)}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Order Workflow Error")
        return {"status": "error", "message": str(e)}


# ============================================
# DEBUG (production mein remove kar dena)
# ============================================

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
        result["seller_company"]    = frappe.db.get_value("Company", seller, ["name", "company_name"], as_dict=True)
        result["seller_addresses"]  = frappe.db.sql("""
            SELECT a.name, a.city, a.pincode, a.is_primary_address
            FROM `tabAddress` a JOIN `tabDynamic Link` dl ON a.name = dl.parent
            WHERE dl.link_doctype = 'Company' AND dl.link_name = %s
        """, (seller,), as_dict=True)
        result["resolved_territory"] = get_seller_territory(seller)

    result["all_territories"] = frappe.db.sql(
        "SELECT name, parent_territory FROM `tabTerritory` ORDER BY name", as_dict=True
    )
    daily_prices = frappe.db.sql("""
        SELECT dip.name, dip.item_code, dip.territory, dip.start_date, dip.end_date
        FROM `tabDaily Item Price` dip ORDER BY dip.start_date DESC LIMIT 20
    """, as_dict=True)
    for dp in daily_prices:
        dp["prices"] = frappe.db.sql("""
            SELECT day, price FROM `tabDaily Price Detail`
            WHERE parent = %s ORDER BY idx ASC
        """, (dp["name"],), as_dict=True)
    result["daily_item_prices"] = daily_prices

    today = nowdate()
    result["today"]     = today
    result["today_day"] = frappe.utils.get_datetime(today).strftime("%A")

    return result