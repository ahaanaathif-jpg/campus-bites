# Campus Bites

A beginner-friendly College Canteen Pre-Order System built with Python, Flask, SQLite, HTML, CSS, and JavaScript. Students can browse and search a sample menu, build a cart, select a pickup time, and place a demo order. The admin desk manages menu prices, availability, and order statuses. There is no online payment processing; the demo records payment as pending for pay-at-pickup.

## Run in GitHub Codespaces

1. Open this repository in a Codespace.
2. In the terminal, install Flask and start the app:

    ```bash
    python -m pip install -r requirements.txt
    python app.py
    ```

3. Open port `5000` from the Ports tab when Codespaces prompts. The SQLite database is created automatically at `instance/campus_bites.db` and seeded with sample categories and food items on first run.
4. Open **Admin** in the top navigation to manage the menu and order statuses.

Stop the server with `Ctrl+C`. To start with a clean database, stop the server and delete `instance/campus_bites.db`; the next start recreates it. Do not delete the database while the server is running.

## Pages

- `/` menu, categories, search, item availability, and add-to-cart
- `/cart` quantity controls, remove, and live total
- `/checkout` student details and pickup-time selection
- `/order/<id>` order receipt and confirmation
- `/orders` order history lookup by the student's checkout email
- `/admin` add food items, update price/availability, and manage order status

## Database design

The app creates the six requested tables with primary keys and foreign keys: `STUDENT`, `CATEGORY`, `FOOD_ITEM`, `ORDERS`, `ORDER_ITEM`, and `PAYMENT`. A student can have multiple orders; categories contain multiple food items; `ORDER_ITEM` connects orders and food items; and `PAYMENT.Order_ID` is unique, so an order has at most one payment record. SQLite foreign-key enforcement is enabled on each connection. Checkout uses parameterized SQL, validates submitted values, obtains authoritative prices from the database, and commits the order, line items, and demo payment together.

For a classroom demo, `/admin` is intentionally simple and has no login. Keep it local; do not deploy it publicly without adding authentication and CSRF protection. The app uses sample remote Unsplash images and Google Fonts, so the first render needs internet access for those assets; the menu and ordering functionality itself is local.

## Optional database command

```bash
flask --app app init-db
```

This creates the schema and sample menu without starting the development server. To use a different SQLite location, set `CAMPUS_BITES_DB` before starting the app. Set `SECRET_KEY` to a random value if you adapt the project beyond a local demo.
