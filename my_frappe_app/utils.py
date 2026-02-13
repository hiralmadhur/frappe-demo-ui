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

    if "Seller" in roles or "Customer" in roles:
        frappe.local.response["home_page"] = "/frontend"
        frappe.db.commit()