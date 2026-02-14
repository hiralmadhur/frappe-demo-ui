import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import nowdate, getdate, fmt_money, format_date

# ============================================
# ROLE & CONTEXT METHODS
# ============================================

@frappe.whitelist(allow_guest=True)
def get_current_user_role():
    """Get current user's role"""
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
    """Seller portal context - company and pincodes"""
    seller = frappe.db.get_value(
        "Company", 
        {"custom_seller": 1}, 
        ["name", "company_name"], 
        as_dict=True
    )
    
    if not seller: 
        frappe.log_error("No company found with custom_seller=1", "Seller Context Error")
        return {"pincodes": [], "company": None}

    pincodes = frappe.db.sql_list("""
        SELECT DISTINCT a.pincode 
        FROM `tabAddress` a 
        JOIN `tabDynamic Link` dl ON a.name = dl.parent 
        WHERE dl.link_name = %s 
        AND a.pincode IS NOT NULL 
        AND a.pincode != ''
    """, (seller.name,))

    if not pincodes:
        frappe.log_error(f"No addresses linked to company {seller.name} or pincodes missing", "Seller Context Error")

    return {
        "company": seller,
        "pincodes": [{"label": p, "value": p} for p in pincodes]
    }

# ============================================
# SELLER PORTAL METHODS
# ============================================

@frappe.whitelist()
def get_filtered_options(pincode):
    """Get societies and customers filtered by pincode"""
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
    """Get all item categories for filtering"""
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
    """Customer portal sidebar data - comprehensive"""
    try:
        user_email = frappe.session.user
        
        # Find customer
        customer = frappe.db.get_value(
            "Customer", 
            {"email_id": user_email}, 
            ["name", "customer_name"], 
            as_dict=True
        ) or frappe.db.get_value(
            "Customer", 
            {"user": user_email}, 
            ["name", "customer_name"], 
            as_dict=True
        )

        if not customer and user_email != "Administrator":
            frappe.log_error(f"No Customer found for email: {user_email}", "Customer Sidebar Error")

        final_pincode_list = []
        
        if customer:
            # Get customer addresses
            addresses = frappe.db.sql("""
                SELECT a.pincode, a.is_primary_address 
                FROM `tabAddress` a
                JOIN `tabDynamic Link` dl ON a.name = dl.parent
                WHERE dl.link_doctype = 'Customer' 
                AND dl.link_name = %s
            """, (customer.name,), as_dict=True)
            
            if not addresses:
                frappe.log_error(f"No addresses linked to customer {customer.name}", "Customer Sidebar Error")

            # Primary addresses first
            primary = [a.pincode for a in addresses if a.is_primary_address and a.pincode]
            others = [a.pincode for a in addresses if not a.is_primary_address and a.pincode]
            final_pincode_list = sorted(list(set(primary)), reverse=True) + \
                                 sorted(list(set(others) - set(primary)))

        # Fallback for Administrator
        if not final_pincode_list and user_email == "Administrator":
            final_pincode_list = ["388001"]
            frappe.logger().debug("Using fallback pincode 388001 for Administrator")

        # Get active categories
        categories = frappe.db.sql("""
            SELECT DISTINCT ig.name as value, ig.item_group_name as label
            FROM `tabItem Group` ig
            INNER JOIN `tabItem` i ON i.item_group = ig.name
            WHERE ig.is_group = 0 
            AND i.disabled = 0 
            AND i.is_sales_item = 1
            ORDER BY ig.item_group_name ASC
        """, as_dict=True)

        # Build pincode map
        pincode_map = {}
        if final_pincode_list:
            all_companies = frappe.db.sql("""
                SELECT DISTINCT 
                    a.pincode, 
                    c.name, 
                    c.company_name, 
                    c.custom_society, 
                    c.custom_seller
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
                        for c in all_companies 
                        if c.pincode == pin and c.custom_society
                    ],
                    "sellers": [
                        {"value": c.name, "label": c.company_name} 
                        for c in all_companies 
                        if c.pincode == pin and c.custom_seller
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
# ITEM FETCHING WITH PRICING
# ============================================

@frappe.whitelist()
def get_seller_items(category=None, seller=None):
    """Get items with dynamic pricing"""
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

    # Get seller pincode
    seller_pincode = None
    if seller:
        seller_pincode_list = frappe.db.sql("""
            SELECT a.pincode 
            FROM `tabAddress` a
            JOIN `tabDynamic Link` dl ON a.name = dl.parent
            WHERE dl.link_doctype = 'Company' 
            AND dl.link_name = %s
            ORDER BY a.is_primary_address DESC 
            LIMIT 1
        """, (seller,), pluck=True)
        
        if seller_pincode_list:
            seller_pincode = seller_pincode_list[0]

    target_date = nowdate()
    day = frappe.utils.get_datetime(target_date).strftime("%A")

    # Add pricing to each item
    for item in items:
        price = find_price_recursive(item.item_code, seller_pincode, day, target_date)
        item["price"] = price
        item["formatted_price"] = fmt_money(price, currency="INR")

    return items

def find_price_recursive(item_code, current_territory, day, target_date):
    """Recursive price lookup with territory hierarchy"""
    temp_territory = current_territory
    
    # Try Daily Item Price
    while temp_territory:
        rules = frappe.get_all(
            "Daily Item Price", 
            filters={"item_code": item_code, "territory": temp_territory}, 
            fields=["name", "start_date"], 
            order_by="start_date desc"
        )
        
        for r in rules:
            if getdate(r.start_date) <= getdate(target_date):
                price = frappe.db.get_value(
                    "Daily Price Detail", 
                    {"parent": r.name, "day": day}, 
                    "price"
                )
                if price: 
                    return float(price)
        
        # Move to parent territory
        temp_territory = frappe.db.get_value(
            "Territory", 
            temp_territory, 
            "parent_territory"
        )

    # Fallback to standard price
    standard_price = frappe.db.get_value(
        "Item Price", 
        {"item_code": item_code, "price_list": "Standard Selling"}, 
        "price_list_rate"
    )
    
    return float(standard_price) if standard_price else 0.0

# ============================================
# CUSTOMER: PLACE ORDER
# ============================================

@frappe.whitelist()
def place_order(cart_data, customer, seller, pincode, society=None, delivery_address=None):
    """
    Place order from cart - creates Draft Sales Order
    
    Args:
        cart_data: JSON string of {item_code: qty, ...}
        customer: Customer ID
        seller: Seller Company ID
        pincode: Delivery pincode
        society: Optional society
        delivery_address: Optional address ID
    """
    try:
        import json
        if isinstance(cart_data, str):
            cart_data = json.loads(cart_data)
        
        if not cart_data:
            return {"status": "error", "message": _("Cart is empty")}
        
        # Create Sales Order
        so = frappe.new_doc("Sales Order")
        so.customer = customer
        so.company = seller
        so.transaction_date = nowdate()
        so.delivery_date = frappe.utils.add_days(nowdate(), 1)
        
        # Set address
        if delivery_address:
            so.customer_address = delivery_address
        
        # Custom fields (if exist)
        if hasattr(so, 'custom_pincode'):
            so.custom_pincode = pincode
        if hasattr(so, 'custom_society') and society:
            so.custom_society = society
        
        # Add items with pricing
        target_date = nowdate()
        day = frappe.utils.get_datetime(target_date).strftime("%A")
        
        for item_code, qty in cart_data.items():
            price = find_price_recursive(item_code, pincode, day, target_date)
            so.append("items", {
                "item_code": item_code,
                "qty": qty,
                "rate": price,
                "delivery_date": so.delivery_date
            })
        
        so.insert(ignore_permissions=True)
        
        return {
            "status": "success",
            "message": _("Order placed successfully! Order ID: {0}").format(so.name),
            "order_id": so.name,
            "order_name": so.name,
            "grand_total": so.grand_total,
            "formatted_total": fmt_money(so.grand_total, currency="INR")
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Place Order Error")
        return {"status": "error", "message": str(e)}

# ============================================
# CUSTOMER: ORDER HISTORY
# ============================================

@frappe.whitelist()
def get_customer_orders(customer=None):
    """Get customer order history with status"""
    try:
        # Auto-detect customer if not provided
        if not customer:
            user_email = frappe.session.user
            customer = frappe.db.get_value(
                "Customer", 
                {"email_id": user_email}, 
                "name"
            ) or frappe.db.get_value(
                "Customer", 
                {"user": user_email}, 
                "name"
            )
        
        if not customer:
            return {"status": "error", "message": _("Customer not found")}
        
        orders = frappe.db.sql("""
            SELECT 
                so.name, 
                so.transaction_date, 
                so.delivery_date,
                so.grand_total, 
                so.docstatus, 
                so.status,
                so.company as seller,
                so.per_delivered, 
                so.per_billed
            FROM `tabSales Order` so
            WHERE so.customer = %s
            ORDER BY so.creation DESC
        """, (customer,), as_dict=True)
        
        for order in orders:
            # Readable status
            if order.docstatus == 0:
                order.display_status = "Pending Acceptance"
                order.can_cancel = True
                order.status_color = "orange"
            elif order.docstatus == 1:
                if order.status == "To Deliver and Bill":
                    order.display_status = "Accepted - Pending Delivery"
                    order.status_color = "blue"
                elif order.status == "To Bill":
                    order.display_status = "Delivered - Payment Due (Month End)"
                    order.status_color = "blue"
                elif order.status == "Completed":
                    order.display_status = "Completed"
                    order.status_color = "green"
                else:
                    order.display_status = order.status
                    order.status_color = "gray"
                order.can_cancel = False
            else:
                order.display_status = "Cancelled"
                order.status_color = "red"
                order.can_cancel = False
            
            order.formatted_total = fmt_money(order.grand_total, currency="INR")
            order.formatted_date = format_date(order.transaction_date)
            
        return {"status": "success", "orders": orders}
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Customer Orders Error")
        return {"status": "error", "message": str(e)}

# ============================================
# CUSTOMER: ORDER DETAILS
# ============================================

@frappe.whitelist()
def get_order_details(order_id):
    """Get detailed order information"""
    try:
        doc = frappe.get_doc("Sales Order", order_id)
        
        items = []
        for item in doc.items:
            items.append({
                "item_code": item.item_code,
                "item_name": item.item_name,
                "qty": item.qty,
                "rate": item.rate,
                "amount": item.amount,
                "uom": item.uom,
                "formatted_rate": fmt_money(item.rate, currency="INR"),
                "formatted_amount": fmt_money(item.amount, currency="INR")
            })
        
        # Status info
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
                "name": doc.name,
                "transaction_date": format_date(doc.transaction_date),
                "delivery_date": format_date(doc.delivery_date),
                "customer": doc.customer,
                "customer_name": doc.customer_name,
                "seller": doc.company,
                "total": doc.grand_total,
                "formatted_total": fmt_money(doc.grand_total, currency="INR"),
                "docstatus": doc.docstatus,
                "display_status": display_status,
                "can_cancel": can_cancel,
                "items": items
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
    """Cancel order - only works for draft orders"""
    try:
        doc = frappe.get_doc("Sales Order", order_id)
        
        # Check permissions
        user_email = frappe.session.user
        customer = frappe.db.get_value(
            "Customer", 
            {"email_id": user_email}, 
            "name"
        ) or frappe.db.get_value(
            "Customer", 
            {"user": user_email}, 
            "name"
        )
        
        if doc.customer != customer and user_email != "Administrator":
            return {
                "status": "error", 
                "message": _("You can only cancel your own orders")
            }
        
        if doc.docstatus == 0:
            frappe.delete_doc("Sales Order", order_id, ignore_permissions=True)
            return {
                "status": "success", 
                "message": _("Order cancelled successfully")
            }
        else:
            return {
                "status": "error", 
                "message": _("Cannot cancel accepted orders. Please contact seller.")
            }
            
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Cancel Order Error")
        return {"status": "error", "message": str(e)}

# ============================================
# SELLER: GET ORDERS
# ============================================

@frappe.whitelist()
def get_seller_orders(seller=None, status_filter=None):
    """Get seller's orders"""
    try:
        # Auto-detect seller if not provided
        if not seller:
            seller = frappe.db.get_value(
                "Company", 
                {"custom_seller": 1}, 
                "name"
            )
        
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
            fields=[
                "name", "customer", "customer_name", "transaction_date", 
                "grand_total", "docstatus", "status", "per_delivered", "per_billed"
            ],
            order_by="creation desc"
        )
        
        for order in orders:
            if order.docstatus == 0:
                order.display_status = "Pending"
            elif order.docstatus == 1:
                order.display_status = order.status
            else:
                order.display_status = "Cancelled"
            
            order.formatted_total = fmt_money(order.grand_total, currency="INR")
            order.formatted_date = format_date(order.transaction_date)
        
        return {"status": "success", "orders": orders}
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Seller Orders Error")
        return {"status": "error", "message": str(e)}

# ============================================
# SELLER: ORDER WORKFLOW
# ============================================

@frappe.whitelist()
def process_order_workflow(order_id, action):
    """
    Process order workflow actions
    
    Actions:
        - accept: Submit draft order
        - reject: Delete draft order
        - deliver: Create delivery note
        - invoice: Create sales invoice
    """
    try:
        doc = frappe.get_doc("Sales Order", order_id)
        
        # 1. ACCEPT
        if action == "accept":
            if doc.docstatus == 1: 
                return {
                    "status": "error", 
                    "message": _("Order is already accepted.")
                }
            doc.submit()
            return {
                "status": "success", 
                "message": _("Order {0} accepted successfully").format(doc.name)
            }
        
        # 2. REJECT
        elif action == "reject":
            if doc.docstatus == 0:
                frappe.delete_doc("Sales Order", order_id, ignore_permissions=True)
                return {
                    "status": "success", 
                    "message": _("Order rejected and deleted")
                }
            return {
                "status": "error", 
                "message": _("Cannot reject accepted orders")
            }
            
        # 3. DELIVER
        elif action == "deliver":
            if doc.docstatus == 0: 
                return {
                    "status": "error", 
                    "message": _("Please accept the order first")
                }
            if doc.per_delivered >= 100: 
                return {
                    "status": "error", 
                    "message": _("Order is already fully delivered")
                }

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
            
            return {
                "status": "success", 
                "message": _("Delivery Note {0} created successfully").format(dn.name)
            }
            
        # 4. INVOICE
        elif action == "invoice":
            if doc.docstatus == 0: 
                return {
                    "status": "error", 
                    "message": _("Please accept the order first")
                }
            if doc.per_billed >= 100: 
                return {
                    "status": "error", 
                    "message": _("Order is already fully billed")
                }

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
                "message": _("Invoice {0} created successfully").format(sinv.name)
            }
            
        return {
            "status": "error", 
            "message": _("Unknown action: {0}").format(action)
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Order Workflow Error")
        return {"status": "error", "message": str(e)}