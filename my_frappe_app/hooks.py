app_name = "my_frappe_app"
app_title = "my_frappe_app"
app_publisher = "uvtechglobal@gmail.com"
app_description = "my_frappe_app"
app_email = "uvtechglobal@gmail.com"
app_license = "mit"

# Website route rules
website_route_rules = [
    {"from_route": "/frontend/<path:app_path>", "to_route": "frontend"},
]

# Login redirect hook
on_session_creation = "my_frappe_app.utils.login_redirect"
get_website_user_home_page = "my_frappe_app.utils.get_home_page"

# ── Doc Events ────────────────────────────────────────────────────
# Sales Invoice submit hone pe auto email bhejo
# on_invoice_submit_hook is defined in payment_utils.py (NOT api.py)
doc_events = {
    "Sales Invoice": {
        "on_submit": "my_frappe_app.payment_utils.on_invoice_submit_hook",
    },
}

scheduler_events = {
    "cron": {
        # Step 1: 11:58 PM IST — expire old subscriptions (UTC: 18:28)
        "28 18 * * *": [
            "my_frappe_app.api.expire_old_subscriptions",
        ],
        # Step 2: 12:05 AM IST — generate daily orders (UTC: 18:35)
        "35 18 * * *": [
            "my_frappe_app.api.generate_daily_orders",
        ],
    },
}

# Role-based home page
role_home_page = {
    "Seller": "/frontend/seller",
    "Customer": "/frontend/customer",
}

# ── Fixtures ──────────────────────────────────────────────────────
fixtures = [
    # 1. Custom DocTypes
    {
        "doctype": "DocType",
        "filters": [["module", "=", "my_frappe_app"]]
    },
    # 2. Company Custom Fields
    {
        "doctype": "Custom Field",
        "filters": [["dt", "=", "Company"]]
    },
    # 3. Sales Order Custom Fields
    {
        "doctype": "Custom Field",
        "filters": [["dt", "=", "Sales Order"]]
    },
    # 4. Property Setters
    {
        "doctype": "Property Setter",
        "filters": [["doc_type", "in", ["Company", "Sales Order"]]]
    },
    # 5. Print Formats
    {
        "doctype": "Print Format",
        "filters": [["module", "=", "my_frappe_app"]]
    },
]