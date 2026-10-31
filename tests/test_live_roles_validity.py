"""End-to-end multi-role data flow and validity test for Brightloop.

Validates the complete propagation of business data across roles:
  Customer  <--->  Staff  <--->  Admin
Also verifies data isolation, role-based access boundaries, tax & discount
math, invoice PDF rendering, payment settlement, and executive dashboard metrics.
"""

import sys
from datetime import date, timedelta
from decimal import Decimal
import requests

BASE_URL = "http://127.0.0.1:8001"
PROXIED_URL = "http://localhost:5173/api"


def print_step(step_num: int, title: str):
    print(f"\n{'='*70}")
    print(f" STEP {step_num}: {title.upper()}")
    print(f"{'='*70}")


def check(assertion: bool, message: str):
    if assertion:
        print(f"  [PASS] {message}")
    else:
        print(f"  [FAIL] {message}")
        raise AssertionError(f"Validation failed: {message}")


def run_validity_test():
    session = requests.Session()
    # Test via proxied URL to also validate Vite frontend proxy routing!
    api_url = PROXIED_URL

    # --------------------------------------------------------------------------
    # 0. Health check
    # --------------------------------------------------------------------------
    print_step(0, "System Health & Proxy Connectivity Check")
    health = session.get(f"{api_url}/health", timeout=5).json()
    check(health.get("status") == "ok", "Backend health status is 'ok'")
    check(health.get("database") == "ok", "Database connection is operational")

    # --------------------------------------------------------------------------
    # 1. Admin Authentication & Catalog Setup
    # --------------------------------------------------------------------------
    print_step(1, "Admin Authentication & Product / Variant / Plan Setup")
    admin_login = session.post(
        f"{api_url}/auth/login",
        json={"email": "admin@example.com", "password": "Admin!Brightloop2026"},
    )
    check(admin_login.status_code == 200, "Admin login succeeded")
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Verify Admin profile
    admin_me = session.get(f"{api_url}/auth/me", headers=admin_headers).json()
    check(admin_me["role"] == "admin", "Admin role confirmed on profile")

    # Ensure Staff exists
    staff_user = session.post(
        f"{api_url}/staff/users",
        headers=admin_headers,
        json={
            "email": "staff_ops@brightloop.com",
            "full_name": "Operations Specialist",
            "password": "Staff!Brightloop2026",
            "role": "staff",
        },
    )
    if staff_user.status_code == 201:
        print("  [PASS] Created new Staff user 'staff_ops@brightloop.com'")
    elif staff_user.status_code == 409:
        print("  [PASS] Staff user 'staff_ops@brightloop.com' already exists")
    else:
        raise AssertionError(f"Unexpected status creating staff user: {staff_user.status_code} {staff_user.text}")

    import time
    run_id = int(time.time() * 1000) % 1_000_000

    # Create distinct Product for this validity test
    prod_resp = session.post(
        f"{api_url}/products",
        headers=admin_headers,
        json={
            "name": f"Brightloop Suite {run_id}",
            "product_type": "software",
            "sales_price": "1000.00",
            "cost_price": "300.00",
            "notes": "End-to-end multi-tier test product",
        },
    )
    check(prod_resp.status_code == 201, f"Admin created product 'Brightloop Suite {run_id}'")
    product = prod_resp.json()

    # Add Variant "Odoo brand" (+560.00)
    variant_resp = session.post(
        f"{api_url}/products/{product['id']}/variants",
        headers=admin_headers,
        json={"name": "Odoo brand", "additional_price": "560.00"},
    )
    check(variant_resp.status_code == 201, "Admin created variant 'Odoo brand' (+560.00)")
    variant = variant_resp.json()

    # Create Plan
    plan_resp = session.post(
        f"{api_url}/plans",
        headers=admin_headers,
        json={
            "product_id": product["id"],
            "name": f"Enterprise Monthly {run_id}",
            "amount": "1000.00",
            "billing_interval": "monthly",
            "minimum_quantity": 2,
            "allow_renew": True,
            "allow_pause": True,
            "allow_early_close": True,
        },
    )
    check(plan_resp.status_code == 201, "Admin created monthly recurring plan")
    plan = plan_resp.json()

    # Create Tax Rule 18%
    tax_resp = session.post(
        f"{api_url}/tax-rules",
        headers=admin_headers,
        json={"name": f"Standard GST 18% {run_id}", "rate": "18.00"},
    )
    check(tax_resp.status_code == 201, "Admin created tax rule 'Standard GST 18%'")
    tax = tax_resp.json()

    # Create Discount Rule TEAM10 (10% off for 2+ units)
    disc_resp = session.post(
        f"{api_url}/discounts",
        headers=admin_headers,
        json={
            "code": f"PROMO10_{run_id}",
            "discount_type": "percentage",
            "value": "10.00",
            "minimum_purchase": "2000.00",
            "minimum_quantity": 2,
            "usage_limit": 5,
            "product_id": product["id"],
        },
    )
    check(disc_resp.status_code == 201, f"Admin created discount rule 'PROMO10_{run_id}'")
    discount = disc_resp.json()

    # --------------------------------------------------------------------------
    # 2. Customer Registration & Security Policy Verification
    # --------------------------------------------------------------------------
    print_step(2, "Customer Registration & Password Policy Validation")

    # Verify that weak passwords fail policy check
    weak_reg = session.post(
        f"{api_url}/users",
        json={
            "email": "weak@brightloop.com",
            "full_name": "Weak Pass User",
            "password": "simplepassword",
            "role": "customer",
        },
    )
    check(weak_reg.status_code == 422, "Weak password correctly rejected by API validation (HTTP 422)")

    # Attempting to register as 'staff' publicly must be blocked (HTTP 403)
    escalate_reg = session.post(
        f"{api_url}/users",
        json={
            "email": "hacker@brightloop.com",
            "full_name": "Privilege Escalation",
            "password": "Strong!Pass2026",
            "role": "staff",
        },
    )
    check(escalate_reg.status_code == 403, "Public user attempting to register as 'staff' blocked with HTTP 403")

    # Valid Customer Registration
    customer_email = f"client_{product['id']}@cloudcorp.com"
    cust_reg = session.post(
        f"{api_url}/users",
        json={
            "email": customer_email,
            "full_name": "CloudCorp Global Inc",
            "password": "Customer!Brightloop2026",
            "role": "customer",
        },
    )
    check(cust_reg.status_code == 201, f"Customer successfully registered: '{customer_email}'")
    customer = cust_reg.json()

    # Customer Login
    cust_login = session.post(
        f"{api_url}/auth/login",
        json={"email": customer_email, "password": "Customer!Brightloop2026"},
    )
    check(cust_login.status_code == 200, "Customer logged in successfully")
    customer_token = cust_login.json()["access_token"]
    customer_headers = {"Authorization": f"Bearer {customer_token}"}

    # Verify Customer Access Boundary: Customer cannot create products or plans
    unauth_prod = session.post(
        f"{api_url}/products",
        headers=customer_headers,
        json={"name": "Hacked Product", "sales_price": "1"},
    )
    check(unauth_prod.status_code == 403, "Customer cannot create products (HTTP 403 Forbidden)")

    # Customer initially has 0 subscriptions and 0 invoices
    cust_subs = session.get(f"{api_url}/subscriptions", headers=customer_headers).json()
    check(len(cust_subs) == 0, "Customer portal initially shows 0 subscriptions")

    # --------------------------------------------------------------------------
    # 3. Staff Creates Quotation for Customer & Converts to Subscription
    # --------------------------------------------------------------------------
    print_step(3, "Staff Prepares Quote for Customer & Converts to Subscription")
    staff_login = session.post(
        f"{api_url}/auth/login",
        json={"email": "staff_ops@brightloop.com", "password": "Staff!Brightloop2026"},
    )
    check(staff_login.status_code == 200, "Staff logged in successfully")
    staff_token = staff_login.json()["access_token"]
    staff_headers = {"Authorization": f"Bearer {staff_token}"}

    # Staff creates Quotation targeting Customer
    today = date.today()
    unit_price = Decimal("1000.00") + Decimal("560.00")  # Base + Odoo brand variant
    quote_payload = {
        "customer_id": customer["id"],
        "plan_id": plan["id"],
        "discount_id": discount["id"],
        "tax_rule_id": tax["id"],
        "expires_on": (today + timedelta(days=30)).isoformat(),
        "payment_terms": "Net 15 Days",
        "payment_due_days": 15,
        "lines": [
            {
                "product_id": product["id"],
                "variant_id": variant["id"],
                "product_name": product["name"],
                "variant_name": variant["name"],
                "quantity": 2,
                "unit_price": str(unit_price),
            }
        ],
    }
    quote_resp = session.post(f"{api_url}/quotations", headers=staff_headers, json=quote_payload)
    check(quote_resp.status_code == 201, "Staff successfully created quotation for customer")
    quotation = quote_resp.json()
    check(quotation["status"] == "draft", "Quotation initialized in 'draft' status")

    # Customer checks Quotations: now sees this quotation!
    cust_quotes = session.get(f"{api_url}/quotations", headers=customer_headers).json()
    check(any(q["id"] == quotation["id"] for q in cust_quotes), "Customer sees the newly issued quotation in their portal")

    # Staff progresses Quote: draft -> quotation -> confirmed
    for next_status in ("quotation", "confirmed"):
        patch_resp = session.patch(
            f"{api_url}/quotations/{quotation['id']}/status",
            headers=staff_headers,
            json={"status": next_status},
        )
        check(patch_resp.status_code == 200, f"Quotation status progressed to '{next_status}'")

    # Staff converts confirmed Quote into Subscription
    convert_resp = session.post(
        f"{api_url}/quotations/{quotation['id']}/convert",
        headers=staff_headers,
        json={
            "starts_on": today.isoformat(),
            "expires_on": (today + timedelta(days=365)).isoformat(),
        },
    )
    check(convert_resp.status_code == 201, "Staff converted confirmed quotation into a subscription")
    sub = convert_resp.json()
    sub_id = sub["id"]

    # Staff progresses Subscription: draft -> quotation -> confirmed -> activate
    for action in ("mark-quotation", "confirm", "activate"):
        act_resp = session.post(f"{api_url}/subscriptions/{sub_id}/{action}", headers=staff_headers)
        check(act_resp.status_code == 200, f"Subscription progressed via action: '{action}'")
    active_sub = act_resp.json()
    check(active_sub["status"] == "active", "Subscription is now 'active'")
    billing_date = active_sub["next_billing_on"]
    print(f"  [INFO] Subscription Next Billing Date: {billing_date}")

    # --------------------------------------------------------------------------
    # 4. Customer Portal Check on Active Subscription
    # --------------------------------------------------------------------------
    print_step(4, "Customer Portal Verification of Active Subscription")
    cust_subs_after = session.get(f"{api_url}/subscriptions", headers=customer_headers).json()
    check(len(cust_subs_after) >= 1, "Customer portal now shows active subscription")
    client_sub = next(s for s in cust_subs_after if s["id"] == sub_id)
    check(client_sub["status"] == "active", "Customer confirms subscription status is 'active'")
    check(client_sub["customer_id"] == customer["id"], "Customer ID strictly matches current user")

    # Verify Customer CANNOT trigger billing engine (Admin only)
    cust_billing = session.post(f"{api_url}/billing/run", headers=customer_headers)
    check(cust_billing.status_code == 403, "Customer attempting to trigger billing engine is blocked (HTTP 403)")

    # --------------------------------------------------------------------------
    # 5. Billing Engine Execution & Invoicing
    # --------------------------------------------------------------------------
    print_step(5, "Admin Runs Billing Engine & Validates Math (Discounts + Taxes)")
    bill_run = session.post(
        f"{api_url}/billing/run",
        headers=admin_headers,
        params={"billing_date": billing_date},
    )
    check(bill_run.status_code == 200, "Admin executed billing run successfully")
    generated_invoices = bill_run.json()
    target_invoice = next((inv for inv in generated_invoices if inv["subscription_id"] == sub_id), None)
    check(target_invoice is not None, "Billing engine created invoice for the active customer subscription")

    # Mathematical Verification:
    # 2 units * 1,560.00 = 3,120.00 subtotal
    # TEAM10 (10% discount applied BEFORE tax): 3,120.00 * 0.10 = 312.00
    # Taxable Base: 3,120.00 - 312.00 = 2,808.00
    # GST 18%: 2,808.00 * 0.18 = 505.44
    # Total Due: 2,808.00 + 505.44 = 3,313.44
    expected_subtotal = Decimal("3120.00")
    expected_discount = Decimal("312.00")
    expected_tax = Decimal("505.44")
    expected_total = Decimal("3313.44")

    actual_subtotal = Decimal(target_invoice["subtotal"])
    actual_discount = Decimal(target_invoice["discount_amount"])
    actual_tax = Decimal(target_invoice["tax_amount"])
    actual_total = Decimal(target_invoice["amount"])

    check(actual_subtotal == expected_subtotal, f"Subtotal is exactly ₹{expected_subtotal} (Got: ₹{actual_subtotal})")
    check(actual_discount == expected_discount, f"Discount is exactly ₹{expected_discount} (Got: ₹{actual_discount})")
    check(actual_tax == expected_tax, f"GST 18% is exactly ₹{expected_tax} (Got: ₹{actual_tax})")
    check(actual_total == expected_total, f"Total Amount is exactly ₹{expected_total} (Got: ₹{actual_total})")

    # Anti-Duplicate Billing Check: Running billing engine again immediately must not produce duplicate invoices!
    second_run = session.post(
        f"{api_url}/billing/run",
        headers=admin_headers,
        params={"billing_date": billing_date},
    ).json()
    check(not any(inv["subscription_id"] == sub_id for inv in second_run), "No duplicate invoice created for the same billing period")

    # --------------------------------------------------------------------------
    # 6. Staff Invoicing, PDF Print & Payment Settlement
    # --------------------------------------------------------------------------
    print_step(6, "Staff Confirms Invoice, Customer Downloads PDF, Payment Settled")
    inv_id = target_invoice["id"]

    # Staff confirms Draft invoice -> Confirmed
    conf_inv = session.post(f"{api_url}/invoices/{inv_id}/confirm", headers=staff_headers)
    check(conf_inv.status_code == 200, "Staff confirmed draft invoice")
    check(conf_inv.json()["status"] == "confirmed", "Invoice status is now 'confirmed'")

    # Customer logs in and views the confirmed invoice
    cust_invoices = session.get(f"{api_url}/invoices", headers=customer_headers).json()
    check(any(i["id"] == inv_id for i in cust_invoices), "Customer sees the invoice in their portal")

    # Customer downloads formatted PDF invoice
    pdf_resp = session.get(f"{api_url}/invoices/{inv_id}/print", headers=customer_headers)
    check(pdf_resp.status_code == 200, "Customer downloaded invoice PDF successfully")
    check(pdf_resp.content.startswith(b"%PDF-"), "Generated document has valid PDF magic header (%PDF-)")
    print(f"  [INFO] PDF Invoice Size: {len(pdf_resp.content)} bytes")

    # Customer isolation test: Another customer cannot access or print this invoice!
    other_cust_login = session.post(
        f"{api_url}/auth/login",
        json={"email": "customer@example.com", "password": "Customer!Brightloop2026"},
    ).json()
    other_headers = {"Authorization": f"Bearer {other_cust_login['access_token']}"}
    unauthorized_pdf = session.get(f"{api_url}/invoices/{inv_id}/print", headers=other_headers)
    check(unauthorized_pdf.status_code == 403, "Other customer cannot view/print this invoice (HTTP 403 Forbidden)")

    # Staff records customer payment
    pay_resp = session.post(
        f"{api_url}/invoices/{inv_id}/payments",
        headers=staff_headers,
        json={
            "amount": str(expected_total),
            "method": "bank_transfer",
            "status": "success",
            "note": "Wire settlement ref: WIRE-2026-CCG",
        },
    )
    check(pay_resp.status_code == 201, "Staff successfully recorded customer payment")

    # Verify Invoice is now PAID with 0.00 outstanding balance
    settled_inv = session.get(f"{api_url}/invoices/{inv_id}", headers=staff_headers).json()
    check(settled_inv["status"] == "paid", "Invoice status moved to 'paid'")
    check(Decimal(settled_inv["outstanding_balance"]) == Decimal("0.00"), "Invoice outstanding balance is ₹0.00")

    # Customer portal also sees the invoice as Paid
    cust_settled_inv = session.get(f"{api_url}/invoices/{inv_id}", headers=customer_headers).json()
    check(cust_settled_inv["status"] == "paid", "Customer portal confirms invoice is 'paid'")

    # --------------------------------------------------------------------------
    # 7. Finance Executive Dashboard Real-Time Reflection
    # --------------------------------------------------------------------------
    print_step(7, "Admin Reviews Finance Executive Dashboard")
    dash = session.get(f"{api_url}/finance/dashboard", headers=admin_headers).json()
    check("active_subscriptions" in dash, "Dashboard returns active subscriptions count")
    check(dash["active_subscriptions"] >= 1, f"Active subscriptions count: {dash['active_subscriptions']}")
    check("revenue" in dash, "Dashboard returns revenue")
    check(Decimal(str(dash["revenue"])) >= expected_total, f"Revenue contains recorded transaction (Total: ₹{dash['revenue']})")
    print(f"  [INFO] Dashboard Total Revenue: ₹{dash.get('revenue')}")
    print(f"  [INFO] Dashboard Total Payments Settled: ₹{dash.get('payments')}")
    print(f"  [INFO] Dashboard Outstanding Balance: ₹{dash.get('outstanding_balance')}")
    print(f"  [INFO] Dashboard Overdue Invoices Count: {dash.get('overdue_invoices')}")

    # --------------------------------------------------------------------------
    # 8. Access Control & Security Matrix Summary
    # --------------------------------------------------------------------------
    print_step(8, "Role-Based Access Control (RBAC) Matrix Verification")

    # Staff cannot create staff
    staff_create_staff = session.post(
        f"{api_url}/staff/users",
        headers=staff_headers,
        json={"email": "s2@brightloop.com", "full_name": "S2", "password": "Staff!Brightloop2026", "role": "staff"},
    )
    check(staff_create_staff.status_code == 403, "Staff cannot create other staff members (HTTP 403)")

    # Staff cannot run billing engine
    staff_run_billing = session.post(f"{api_url}/billing/run", headers=staff_headers)
    check(staff_run_billing.status_code == 403, "Staff cannot trigger billing engine (HTTP 403)")

    # Customer cannot view finance dashboard
    cust_view_dash = session.get(f"{api_url}/finance/dashboard", headers=customer_headers)
    check(cust_view_dash.status_code == 403, "Customer cannot access executive finance dashboard (HTTP 403)")

    print(f"\n{'='*70}")
    print(" ALL 33 MULTI-ROLE VALIDITY TESTS PASSED WITH 100% SUCCESS! ")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    try:
        run_validity_test()
    except Exception as exc:
        print(f"\n[FATAL ERROR] {exc}", file=sys.stderr)
        sys.exit(1)
