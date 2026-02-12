import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc

# --- Existing Functions (Context & Options) ---
@frappe.whitelist()
def get_seller_context():
    seller = frappe.db.get_value("Company", {"custom_seller": 1}, ["name", "company_name"], as_dict=True)
    if not seller: return {"pincodes": [], "company": None}

    pincodes = frappe.db.sql_list("""
        SELECT DISTINCT a.pincode FROM `tabAddress` a 
        JOIN `tabDynamic Link` dl ON a.name = dl.parent 
        WHERE dl.link_name = %s AND a.pincode IS NOT NULL AND a.pincode != ''
    """, (seller.name))

    return {
        "company": seller,
        "pincodes": [{"label": p, "value": p} for p in pincodes]
    }

@frappe.whitelist()
def get_filtered_options(pincode):
    if not pincode: return {"societies": [], "customers": []}

    societies = frappe.db.sql("""
        SELECT DISTINCT c.name as value, c.company_name as label FROM `tabCompany` c
        JOIN `tabDynamic Link` dl ON dl.link_name = c.name
        JOIN `tabAddress` a ON a.name = dl.parent
        WHERE c.custom_society = 1 AND a.pincode = %s
    """, (pincode), as_dict=True)

    customers = frappe.db.sql("""
        SELECT DISTINCT c.name as value, c.customer_name as label FROM `tabCustomer` c
        JOIN `tabDynamic Link` dl ON dl.link_name = c.name
        JOIN `tabAddress` a ON a.name = dl.parent
        WHERE a.pincode = %s
    """, (pincode), as_dict=True)

    return {"societies": societies, "customers": customers}

# --- UPDATED WORKFLOW FUNCTION WITH ERROR LOGGING ---
@frappe.whitelist()
def process_order_workflow(order_id, action):
    try:
        doc = frappe.get_doc("Sales Order", order_id)
        
        # 1. ACCEPT ACTION
        if action == "accept":
            if doc.docstatus == 1:
                return {"status": "error", "message": _("Order is already accepted.")}
            
            doc.submit()
            return {"status": "success", "message": _("Order Accepted Successfully")}
            
        # 2. DELIVER ACTION
        elif action == "deliver":
            if doc.docstatus == 0:
                return {"status": "error", "message": _("Please accept the order first.")}
            
            if doc.per_delivered >= 100:
                return {"status": "error", "message": _("Order is already fully delivered.")}

            # CHANGE 2: Yahan 'get_mapped_doc' use karein
            dn = get_mapped_doc("Sales Order", order_id, {
                "Sales Order": {
                    "doctype": "Delivery Note",
                    "validation": {
                        "docstatus": ["=", 1]
                    }
                },
                "Sales Order Item": {
                    "doctype": "Delivery Note Item",
                    "field_map": {
                        "name": "so_detail", 
                        "parent": "against_sales_order",
                    },
                }
            })
            
            dn.insert()
            dn.submit()

            return {"status": "success", "message": _("Delivery Note {0} Created").format(dn.name)}
            
        # 3. INVOICE ACTION
        elif action == "invoice":
            if doc.docstatus == 0:
                return {"status": "error", "message": _("Please accept the order first.")}
                
            if doc.per_billed >= 100:
                return {"status": "error", "message": _("Order is already billed.")}

            # CHANGE 3: Yahan bhi 'get_mapped_doc' karein
            sinv = get_mapped_doc("Sales Order", order_id, {
                "Sales Order": { 
                    "doctype": "Sales Invoice", 
                    "validation": { "docstatus": ["=", 1] } 
                },
                "Sales Order Item": { 
                    "doctype": "Sales Invoice Item", 
                    "field_map": { "name": "so_detail", "parent": "against_sales_order" } 
                }
            })
            
            sinv.insert()
            sinv.submit()

            return {"status": "success", "message": _("Invoice {0} Created").format(sinv.name)}
            
        return {"status": "error", "message": _("Unknown Action: {0}").format(action)}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Order Workflow Error")
        return {
            "status": "error", 
            "message": str(e),
            "traceback": frappe.get_traceback()
        }
# my_frappe_app/api.py

@frappe.whitelist()
def get_customer_context():
    """Logged in customer ke details aur unke address ke pincodes fetch karega"""
    user = frappe.session.user
    customer = frappe.db.get_value("Customer", {"user": user}, ["name", "customer_name"], as_dict=True)
    
    if not customer:
        return {"pincodes": [], "customer": None}

    # Customer ke linked addresses se Pincodes nikalein
    pincodes = frappe.db.sql_list("""
        SELECT DISTINCT a.pincode FROM `tabAddress` a
        JOIN `tabDynamic Link` dl ON a.name = dl.parent
        WHERE dl.link_doctype='Customer' AND dl.link_name=%s 
        AND a.pincode IS NOT NULL
        ORDER BY a.is_primary_address DESC
    """, (customer.name))

    return {
        "customer": customer,
        "pincodes": [{"label": p, "value": p} for p in pincodes]
    }

@frappe.whitelist()
def get_sellers_for_customer(pincode=None, society=None):
    """
    1. Pincode hai -> Societies return karo.
    2. Society hai -> Sellers (Companies) return karo.
    """
    data = {"societies": [], "sellers": []}

    if pincode:
        # Pincode ke basis par Societies (Companies marked as society context)
        # Note: Aapke logic ke hisab se Society kaise define hai, main assume kar raha hu Company doctype use ho raha hai
        # Ya agar Society alag doctype hai to table name change karein.
        # Yahan hum maan rahe hai Society ek Address/Area hai.
        
        # Scenario: Pincode -> Society List
        # Assuming 'Address' has Society field or strictly Pincode mapping
        pass 
        # (Implementation depends on your specific Society doctype structure. 
        #  Simple rakhte hai: Pincode -> Sellers in that area)
    
    return data

# Simplified version for your specific Sidebar flow:
@frappe.whitelist()
def get_societies_by_pincode(pincode):
    # Fetch distinct societies linked to addresses in this pincode
    # Adjust logic based on where you store "Society" name (e.g., Address Line 2 or Custom Field)
    societies = frappe.db.sql("""
        SELECT DISTINCT address_line2 as label, address_line2 as value 
        FROM `tabAddress` WHERE pincode=%s AND address_line2 IS NOT NULL
    """, (pincode), as_dict=True)
    return societies

@frappe.whitelist()
def get_sellers_by_society(society):
    # Fetch Sellers (Companies) that have addresses in this Society
    sellers = frappe.db.sql("""
        SELECT DISTINCT c.name as value, c.company_name as label 
        FROM `tabCompany` c
        JOIN `tabDynamic Link` dl ON dl.link_name = c.name
        JOIN `tabAddress` a ON a.name = dl.parent
        WHERE c.is_seller = 1 AND a.address_line2 = %s
    """, (society), as_dict=True)
    return sellers

@frappe.whitelist()
def get_seller_items(seller):
    # Fetch Items sold by this Seller
    items = frappe.db.get_list("Item", 
        filters={"disabled": 0, "is_sales_item": 1}, # Add filter to link item to seller if applicable
        fields=["name", "item_name", "item_code", "standard_rate", "image"]
    )
    return items