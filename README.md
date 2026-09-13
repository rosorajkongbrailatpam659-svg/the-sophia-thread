# The Sophia Thread

A starter full-stack embroidery business website built with Flask and SQLite.

## Features

- Customer-facing homepage
- Product gallery
- Product detail pages
- Customer order form
- Admin login
- Add products with photo, price, description and quantity
- Edit/delete products
- Order dashboard
- Order status updates
- SQLite database
- Responsive styling

## Run locally

1. Install Python 3.10+.
2. Open a terminal in this folder.
3. Create a virtual environment:

   Windows:
   `python -m venv venv`
   `venv\Scripts\activate`

   macOS/Linux:
   `python3 -m venv venv`
   `source venv/bin/activate`

4. Install dependencies:

   `pip install -r requirements.txt`

5. Set admin credentials.

   Windows PowerShell:
   `$env:ADMIN_USERNAME="admin"`
   `$env:ADMIN_PASSWORD="your-strong-password"`
   `$env:SECRET_KEY="your-long-random-secret"`

   macOS/Linux:
   `export ADMIN_USERNAME="admin"`
   `export ADMIN_PASSWORD="your-strong-password"`
   `export SECRET_KEY="your-long-random-secret"`

   If you skip this step, the default password is intentionally set to `change-me`; change it before use.

6. Run:

   `python app.py`

7. Open:
   `http://127.0.0.1:5000`

8. Admin:
   `http://127.0.0.1:5000/admin/login`

## Important before publishing

- Set a strong SECRET_KEY.
- Set a strong admin password.
- Use HTTPS.
- Configure production hosting rather than Flask's debug server.
- Add CSRF protection and rate limiting before accepting real public orders.
- Configure a production database and image storage if the business grows.

## Suggested next upgrades

- WhatsApp order button
- Instagram link
- Custom embroidery request with customer image upload
- Search/filter products
- Categories
- Payment gateway
- Email/order notifications
- Customer order tracking
- Professional logo and branding
