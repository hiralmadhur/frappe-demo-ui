import frappe

def login_redirect():
    # Check if user is logged in and not Guest
    if frappe.session.user == "Guest":
        return

    # Check if user has 'Seller' role
    if "Seller" in frappe.get_roles(frappe.session.user):
        # Redirect specifically to the frontend route
        frappe.local.response["home_page"] = "/frontend"
        
        # Security: ensure session is saved before redirect
        frappe.db.commit()