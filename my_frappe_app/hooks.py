app_name = "my_frappe_app"
app_title = "my_frappe_app"
app_publisher = "uvtechglobal@gmail.com"
app_description = "my_frappe_app"
app_email = "uvtechglobal@gmail.com"
app_license = "mit"

# app_include_js = "/assets/my_frappe_app/frontend/index.js"
# app_include_css = "/assets/my_frappe_app/frontend/index.css"

# Website route rules
website_route_rules = [
    {"from_route": "/frontend/<path:app_path>", "to_route": "frontend"},
]

# Login redirect hook
on_session_creation = "my_frappe_app.utils.login_redirect"
get_website_user_home_page = "my_frappe_app.utils.get_home_page"

scheduler_events = {
    "cron": {
        # Step 1: 11:58 PM IST — expire purani subscriptions
        # UTC: 18:28
        "28 18 * * *": [
            "my_frappe_app.api.expire_old_subscriptions",
        ],
        # Step 2: 12:05 AM IST — naye din ke orders banao
        # UTC: 18:35
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

fixtures = [
    # ── 1. Saare Custom DocTypes jinka module = my_frappe_app ──
    {
        "doctype": "DocType",
        "filters": [
            ["module", "=", "my_frappe_app"]
        ]
    },

    # ── 2. Company ke saare Custom Fields ──────────────────────
    {
        "doctype": "Custom Field",
        "filters": [
            ["dt", "=", "Company"]
        ]
    },

    # ── 3. Sales Order ke saare Custom Fields ──────────────────
    {
        "doctype": "Custom Field",
        "filters": [
            ["dt", "=", "Sales Order"]
        ]
    },

    # ── 4. Property Setters (Company + Sales Order) ─────────────
    {
        "doctype": "Property Setter",
        "filters": [
            ["doc_type", "in", ["Company", "Sales Order"]]
        ]
    },
]