import frappe

def login_redirect():
    """
    Login ke baad role ke hisaab se redirect karo.
    Seller  → /frontend  (Vue app handles /seller route)
    Customer → /frontend  (Vue app handles /customer route)
    """
    if frappe.session.user == "Guest":
        return

    roles = frappe.get_roles(frappe.session.user)
    frappe.logger().debug(f"User {frappe.session.user} roles: {roles}")

    # Administrator should always go to Desk
    if frappe.session.user == "Administrator":
        return

    if "Seller" in roles:
        frappe.local.response["home_page"] = "/frontend/seller"
        frappe.db.commit()
    elif "Customer" in roles:
        frappe.local.response["home_page"] = "/frontend/customer"
        frappe.db.commit()

def get_home_page(user):
    """Bypass Desk for specific roles even for active sessions"""
    if user == "Administrator":
        return None # Defaults to Desk
        
    roles = frappe.get_roles(user)
    if "Seller" in roles:
        return "/frontend/seller"
    if "Customer" in roles:
        return "/frontend/customer"
    
    return None
