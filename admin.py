import json
import asyncio
import aiosqlite
from fastapi import FastAPI, Request, Form, Depends, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from config import ADMIN_USERNAME, ADMIN_PASSWORD, DATABASE_PATH, BOT_TOKEN
from database import init_db, seed_demo_data

app = FastAPI(title="Health & Wellness Admin")
app.add_middleware(SessionMiddleware, secret_key="hw-admin-secret-key-change-in-prod")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


async def get_db():
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    return db


def require_login(request: Request):
    if not request.session.get("logged_in"):
        raise HTTPException(status_code=303, headers={"Location": "/login"})


@app.on_event("startup")
async def startup():
    await init_db()
    await seed_demo_data()


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        request.session["logged_in"] = True
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login", status_code=303)
    db = await get_db()
    stats = {}
    for query_name, query in [
        ("total_orders", "SELECT COUNT(*) FROM orders"),
        ("pending_orders", "SELECT COUNT(*) FROM orders WHERE order_status = 'pending'"),
        ("total_revenue", "SELECT COALESCE(SUM(total), 0) FROM orders WHERE payment_status = 'completed'"),
        ("total_customers", "SELECT COUNT(*) FROM users"),
        ("total_products", "SELECT COUNT(*) FROM products"),
        ("open_enquiries", "SELECT COUNT(*) FROM enquiries WHERE status = 'open'"),
    ]:
        cursor = await db.execute(query)
        row = await cursor.fetchone()
        stats[query_name] = row[0]

    cursor = await db.execute(
        "SELECT o.id, u.full_name, o.total, o.order_status, o.payment_status, o.created_at "
        "FROM orders o LEFT JOIN users u ON o.telegram_id = u.telegram_id "
        "ORDER BY o.created_at DESC LIMIT 10"
    )
    recent_orders = await cursor.fetchall()
    await db.close()

    return templates.TemplateResponse("dashboard.html", {
        "request": request, "stats": stats, "recent_orders": recent_orders
    })


@app.get("/orders", response_class=HTMLResponse)
async def orders_page(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login", status_code=303)
    db = await get_db()
    cursor = await db.execute(
        "SELECT o.*, u.full_name as customer_name, u.phone as customer_phone "
        "FROM orders o LEFT JOIN users u ON o.telegram_id = u.telegram_id "
        "ORDER BY o.created_at DESC"
    )
    orders = await cursor.fetchall()
    await db.close()
    return templates.TemplateResponse("orders.html", {"request": request, "orders": orders})


@app.post("/orders/{order_id}/status")
async def update_order_status(request: Request, order_id: int, status: str = Form(...)):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login", status_code=303)
    db = await get_db()
    await db.execute("UPDATE orders SET order_status = ? WHERE id = ?", (status, order_id))
    await db.commit()

    cursor = await db.execute("SELECT telegram_id FROM orders WHERE id = ?", (order_id,))
    order = await cursor.fetchone()
    await db.close()

    if order and BOT_TOKEN != "YOUR_BOT_TOKEN_HERE":
        try:
            from telegram import Bot
            bot = Bot(token=BOT_TOKEN)
            status_labels = {
                "pending": "Pending", "processing": "Processing",
                "shipped": "Shipped", "completed": "Completed"
            }
            await bot.send_message(
                chat_id=order[0],
                text=f"Order #{order_id} Update\n\nYour order status has been updated to: {status_labels.get(status, status)}"
            )
        except Exception:
            pass

    return RedirectResponse("/orders", status_code=303)


@app.post("/orders/{order_id}/payment")
async def update_payment_status(request: Request, order_id: int, status: str = Form(...)):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login", status_code=303)
    db = await get_db()
    await db.execute("UPDATE orders SET payment_status = ? WHERE id = ?", (status, order_id))
    await db.commit()
    await db.close()
    return RedirectResponse("/orders", status_code=303)


@app.get("/products", response_class=HTMLResponse)
async def products_page(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login", status_code=303)
    db = await get_db()
    cursor = await db.execute(
        "SELECT p.*, c.name as cat_name FROM products p "
        "LEFT JOIN categories c ON p.category_id = c.id ORDER BY p.id"
    )
    products = await cursor.fetchall()
    cat_cursor = await db.execute("SELECT id, name FROM categories ORDER BY sort_order")
    categories = await cat_cursor.fetchall()
    await db.close()
    return templates.TemplateResponse("products.html", {
        "request": request, "products": products, "categories": categories
    })


@app.post("/products/add")
async def add_product(
    request: Request,
    name: str = Form(...), category_id: int = Form(...),
    description: str = Form(""), benefits: str = Form(""),
    usage_info: str = Form(""), price: float = Form(...),
):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login", status_code=303)
    db = await get_db()
    await db.execute(
        "INSERT INTO products (category_id, name, description, benefits, usage_info, price) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (category_id, name, description, benefits, usage_info, price)
    )
    await db.commit()
    await db.close()
    return RedirectResponse("/products", status_code=303)


@app.post("/products/{product_id}/delete")
async def delete_product(request: Request, product_id: int):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login", status_code=303)
    db = await get_db()
    await db.execute("DELETE FROM package_options WHERE product_id = ?", (product_id,))
    await db.execute("DELETE FROM products WHERE id = ?", (product_id,))
    await db.commit()
    await db.close()
    return RedirectResponse("/products", status_code=303)


@app.post("/products/{product_id}/toggle")
async def toggle_product(request: Request, product_id: int):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login", status_code=303)
    db = await get_db()
    await db.execute("UPDATE products SET in_stock = NOT in_stock WHERE id = ?", (product_id,))
    await db.commit()
    await db.close()
    return RedirectResponse("/products", status_code=303)


@app.get("/categories", response_class=HTMLResponse)
async def categories_page(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login", status_code=303)
    db = await get_db()
    cursor = await db.execute("SELECT * FROM categories ORDER BY sort_order")
    categories = await cursor.fetchall()
    await db.close()
    return templates.TemplateResponse("categories.html", {"request": request, "categories": categories})


@app.post("/categories/add")
async def add_category(request: Request, name: str = Form(...), description: str = Form("")):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login", status_code=303)
    db = await get_db()
    await db.execute("INSERT INTO categories (name, description) VALUES (?, ?)", (name, description))
    await db.commit()
    await db.close()
    return RedirectResponse("/categories", status_code=303)


@app.post("/categories/{cat_id}/delete")
async def delete_category(request: Request, cat_id: int):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login", status_code=303)
    db = await get_db()
    await db.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
    await db.commit()
    await db.close()
    return RedirectResponse("/categories", status_code=303)


@app.get("/customers", response_class=HTMLResponse)
async def customers_page(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login", status_code=303)
    db = await get_db()
    cursor = await db.execute("SELECT * FROM users ORDER BY created_at DESC")
    users = await cursor.fetchall()
    await db.close()
    return templates.TemplateResponse("customers.html", {"request": request, "users": users})


@app.get("/enquiries", response_class=HTMLResponse)
async def enquiries_page(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login", status_code=303)
    db = await get_db()
    cursor = await db.execute(
        "SELECT e.*, u.full_name, u.phone FROM enquiries e "
        "LEFT JOIN users u ON e.telegram_id = u.telegram_id "
        "ORDER BY e.created_at DESC"
    )
    enquiries = await cursor.fetchall()
    await db.close()
    return templates.TemplateResponse("enquiries.html", {"request": request, "enquiries": enquiries})


@app.post("/enquiries/{enq_id}/close")
async def close_enquiry(request: Request, enq_id: int):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login", status_code=303)
    db = await get_db()
    await db.execute("UPDATE enquiries SET status = 'closed' WHERE id = ?", (enq_id,))
    await db.commit()
    await db.close()
    return RedirectResponse("/enquiries", status_code=303)


@app.get("/broadcast", response_class=HTMLResponse)
async def broadcast_page(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login", status_code=303)
    db = await get_db()
    cursor = await db.execute("SELECT * FROM broadcasts ORDER BY created_at DESC LIMIT 20")
    broadcasts = await cursor.fetchall()
    user_count_cursor = await db.execute("SELECT COUNT(*) FROM users")
    user_count = (await user_count_cursor.fetchone())[0]
    await db.close()
    return templates.TemplateResponse("broadcast.html", {
        "request": request, "broadcasts": broadcasts, "user_count": user_count
    })


@app.post("/broadcast/send")
async def send_broadcast(request: Request, message: str = Form(...)):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login", status_code=303)

    db = await get_db()
    cursor = await db.execute("SELECT telegram_id FROM users")
    users = await cursor.fetchall()
    sent = 0

    if BOT_TOKEN != "YOUR_BOT_TOKEN_HERE":
        from telegram import Bot
        bot = Bot(token=BOT_TOKEN)
        for user in users:
            try:
                await bot.send_message(chat_id=user[0], text=message)
                sent += 1
            except Exception:
                pass

    await db.execute(
        "INSERT INTO broadcasts (message, sent_to) VALUES (?, ?)",
        (message, sent)
    )
    await db.commit()
    await db.close()
    return RedirectResponse("/broadcast", status_code=303)


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login", status_code=303)
    from config import DELIVERY_OPTIONS
    return templates.TemplateResponse("settings.html", {
        "request": request, "delivery_options": DELIVERY_OPTIONS
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
