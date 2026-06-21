import aiosqlite
import json
from config import DATABASE_PATH

async def get_db():
    return await aiosqlite.connect(DATABASE_PATH)

async def init_db():
    db = await get_db()
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            full_name TEXT,
            phone TEXT,
            country TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            sort_order INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            benefits TEXT,
            usage_info TEXT,
            price REAL NOT NULL,
            image_url TEXT,
            in_stock INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );

        CREATE TABLE IF NOT EXISTS package_options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS cart_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            package_option_id INTEGER,
            quantity INTEGER DEFAULT 1,
            UNIQUE(telegram_id, product_id, package_option_id)
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            full_name TEXT,
            phone TEXT,
            address TEXT,
            delivery_method TEXT,
            delivery_fee REAL DEFAULT 0,
            subtotal REAL NOT NULL,
            total REAL NOT NULL,
            payment_method TEXT,
            payment_status TEXT DEFAULT 'pending',
            order_status TEXT DEFAULT 'pending',
            items_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
        );

        CREATE TABLE IF NOT EXISTS faqs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            sort_order INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS enquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            status TEXT DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS broadcasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT NOT NULL,
            sent_to INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    await db.commit()
    await db.close()

async def seed_demo_data():
    db = await get_db()
    count = await db.execute("SELECT COUNT(*) FROM categories")
    row = await count.fetchone()
    if row[0] > 0:
        await db.close()
        return

    await db.executemany("INSERT INTO categories (name, description, sort_order) VALUES (?, ?, ?)", [
        ("Vitamins & Supplements", "Essential vitamins and daily supplements", 1),
        ("Herbal & Natural", "Natural herbal remedies and wellness products", 2),
        ("Protein & Fitness", "Protein powders and fitness supplements", 3),
        ("Skin & Beauty", "Skincare and beauty wellness products", 4),
    ])

    await db.executemany(
        "INSERT INTO products (category_id, name, description, benefits, usage_info, price, image_url) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (1, "Multivitamin Daily Complex",
             "Complete daily multivitamin with 23 essential vitamins and minerals.",
             "Supports immune system, energy levels, and overall health. Contains Vitamins A, C, D, E, K, B-complex, Iron, Zinc, and more.",
             "Take 1 tablet daily with food. Best taken in the morning.",
             29.90, ""),
            (1, "Vitamin D3 5000 IU",
             "High-potency Vitamin D3 supplement for bone and immune health.",
             "Supports calcium absorption, bone strength, immune function, and mood regulation.",
             "Take 1 softgel daily with a meal containing fat for best absorption.",
             19.90, ""),
            (2, "Turmeric Curcumin Extract",
             "Organic turmeric extract with BioPerine for enhanced absorption.",
             "Powerful anti-inflammatory and antioxidant properties. Supports joint health and digestion.",
             "Take 2 capsules daily with meals. Can be taken morning and evening.",
             34.90, ""),
            (2, "Ashwagandha Root Extract",
             "Premium KSM-66 Ashwagandha for stress relief and vitality.",
             "Reduces cortisol levels, improves sleep quality, boosts energy, and supports cognitive function.",
             "Take 1 capsule twice daily. Best taken with warm milk before bed.",
             24.90, ""),
            (3, "Whey Protein Isolate - Vanilla",
             "Pure whey protein isolate, 25g protein per serving, low carb.",
             "Supports muscle recovery, lean muscle growth, and workout performance. 90% protein content.",
             "Mix 1 scoop (30g) with 250ml water or milk. Take post-workout or between meals.",
             59.90, ""),
            (3, "Plant-Based Protein - Chocolate",
             "Organic plant-based protein blend from pea, rice, and hemp.",
             "Complete amino acid profile. Dairy-free, soy-free, suitable for vegans. Easy to digest.",
             "Mix 1 scoop with 300ml water, plant milk, or add to smoothies.",
             54.90, ""),
            (4, "Collagen Peptides Powder",
             "Hydrolyzed marine collagen peptides for skin, hair, and nails.",
             "Improves skin elasticity, reduces wrinkles, strengthens hair and nails, supports joint health.",
             "Mix 1 scoop (10g) into coffee, tea, smoothies, or water daily.",
             44.90, ""),
            (4, "Hyaluronic Acid + Vitamin C Serum",
             "Advanced hydrating serum with hyaluronic acid and vitamin C.",
             "Deep hydration, brightens skin tone, reduces fine lines, and protects against free radicals.",
             "Apply 3-4 drops to clean face and neck morning and evening before moisturizer.",
             39.90, ""),
        ]
    )

    await db.executemany(
        "INSERT INTO package_options (product_id, name, price) VALUES (?, ?, ?)",
        [
            (1, "1 Bottle (60 tablets)", 29.90),
            (1, "2 Bottles Bundle", 54.90),
            (1, "3 Bottles Bundle", 79.90),
            (5, "1kg Bag", 59.90),
            (5, "2kg Bag", 109.90),
            (6, "1kg Bag", 54.90),
            (6, "2kg Bag", 99.90),
            (7, "150g Pouch", 44.90),
            (7, "300g Tub", 79.90),
        ]
    )

    await db.executemany("INSERT INTO faqs (question, answer, sort_order) VALUES (?, ?, ?)", [
        ("What payment methods do you accept?", "We accept PayNow (Singapore) and credit/debit cards via Stripe.", 1),
        ("How long does delivery take?", "Standard delivery takes 3-5 business days. Express delivery takes 1-2 business days.", 2),
        ("Can I return a product?", "Yes, we accept returns within 14 days of delivery if the product is unopened and in original packaging.", 3),
        ("Do you ship internationally?", "Currently we only ship within Singapore. International shipping coming soon.", 4),
        ("How do I track my order?", "Use the 'My Orders' option in the bot menu to check your order status anytime.", 5),
    ])

    await db.commit()
    await db.close()
