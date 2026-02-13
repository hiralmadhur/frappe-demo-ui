app_name = "my_frappe_app"
app_title = "my_frappe_app"
app_publisher = "uvtechglobal@gmail.com"
app_description = "my_frappe_app"
app_email = "uvtechglobal@gmail.com"
app_license = "mit"

app_include_js = "/assets/my_frappe_app/frontend/index.js"
app_include_css = "/assets/my_frappe_app/frontend/index.css"

# Website route rules
website_route_rules = [
    {"from_route": "/frontend/<path:app_path>", "to_route": "frontend"},
]

# Login redirect hook
on_session_creation = "my_frappe_app.utils.login_redirect"

# Role-based home page — both Seller and Customer go to /frontend
# Vue app (App.vue) then reads frappe.boot.user.roles and routes to
# /seller or /customer accordingly
role_home_page = {
    "Seller":   "/frontend",
    "Customer": "/frontend",
}