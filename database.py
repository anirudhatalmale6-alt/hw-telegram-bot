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

    # Category: Fat Loss & Weight Management
    await db.execute(
        "INSERT INTO categories (name, description, sort_order) VALUES (?, ?, ?)",
        ("Fat Loss & Weight Management", "Prescription peptides and compounds for weight management, metabolic health, and body composition", 1)
    )

    products = [
        # 1. Tirzepatide
        (1, "Tirzepatide (20mg)",
         "Tirzepatide is a prescription medicine given as a once-a-week shot under the skin. It acts like two natural gut hormones that control your metabolism. Sold under the name Mounjaro for type 2 diabetes and Zepbound for weight loss.",
         "Lowers blood sugar: Helps the body release insulin to keep blood sugar normal.\nKeeps you full: Slows down stomach emptying, making you feel full on much less food.\nImproves health: Helps lower blood pressure and cholesterol.",
         "Once-a-week injection under the skin. Most people lose between 15% and 22% of their body weight after about a year and a half.",
         179.00),
        # 2. Retatrutide
        (1, "Retatrutide (10mg)",
         "Retatrutide is a powerful new prescription medicine currently in advanced clinical trials. It is a triple agonist medication that mimics three different gut hormones at the same time: GLP-1, GIP, and glucagon.",
         "Accelerated Fat Breakdown: The third hormone (glucagon) assists the body in actively burning off stored body fat.\nDouble Appetite Control: Slows stomach emptying and signals the brain that the body is full.\nLiver & Blood Sugar Care: Reduces fat built up in the liver and clears excess sugar from the blood.",
         "Once-a-week injection under the skin. In clinical trials, people taking higher doses lost an average percentage of their total body weight over roughly a year.",
         180.00),
        # 3. Semaglutide
        (1, "Semaglutide (10mg)",
         "Semaglutide is a widely used prescription medicine given as a once-a-week shot under the skin. It is a GLP-1 receptor agonist. Sold under the brand name Ozempic for type 2 diabetes and Wegovy for chronic weight loss.",
         "Strong Blood Sugar Control: Signals your pancreas to create more insulin when you eat, preventing unhealthy blood sugar spikes.\nExtended Fullness: Delays how quickly your stomach empties food, meaning you stay full for longer.\nOrgan Protection: Offers protective benefits for kidneys, liver, and cardiovascular system.",
         "Once-a-week injection under the skin. On average, individuals taking the highest dose lose about 15% of their total body weight over a year to 15 months.",
         179.00),
        # 4. Cagrilintide
        (1, "Cagrilintide (5mg)",
         "Cagrilintide is a powerful new prescription medicine currently in advanced clinical trials. It is an amylin analogue that acts like a specific pancreatic hormone to slow digestion, stop sugar spikes, and signal fullness directly to your brain.",
         "Brain-Level Fullness: Directly strengthens the brain's natural sense of satisfaction and fullness after eating.\nSlowing Down the Stomach: Controls digestive speed, so food leaves your stomach much slower.\nSteadies Blood Sugar: Stops the liver from pumping out extra sugar right after meals.",
         "Once-a-week injection under the skin. Helps people lose a significant amount of weight over about a year. Even bigger results when combined with a GLP-1 drug.",
         119.00),
        # 5. Survodutide
        (1, "Survodutide (5mg)",
         "Survodutide is an advanced new prescription medicine currently in late-stage clinical trials. It is a dual glucagon and GLP-1 receptor agonist that acts like two different natural metabolic hormones to control appetite while forcing the liver to actively burn fat.",
         "Liver Cleansing: Dramatically lowers fat accumulation inside the liver and reduces inflammation.\nVisceral Fat Reduction: Directly reduces dangerous, deep abdominal fat that wraps around internal organs.\nStable Blood Sugar: The GLP-1 hormone component keeps insulin active, preventing spikes in blood glucose.",
         "Once-a-week injection under the skin. In advanced clinical trials, adults taking the highest dose lost up to 16.6% to 19% of their total body weight over 46 to 76 weeks.",
         139.00),
        # 6. Mazdutide
        (1, "Mazdutide (5mg)",
         "Mazdutide (sold under the brand name Xinermei in China) is a modern prescription medicine given as a once-a-week shot under the skin. It is a dual GLP-1 and glucagon receptor agonist that curbs hunger while prompting the liver to clear out fat and burn energy.",
         "Powerful Appetite Shield: Slows down stomach emptying and signals your brain that you are full to eliminate constant cravings.\nClears Liver Fat: Works heavily on the liver to drop fat accumulation, clear inflammation, and normalize liver enzymes.\nWipes Out Blood Sugar Spikes: Stimulates natural insulin release exactly when you eat.\nBroad Cardio Protection: Helps lower blood pressure, uric acid, and harmful cholesterol levels.",
         "Once-a-week injection under the skin. Adults lose an average of 14% to 20% of their total body weight over roughly a year of consistent treatment.",
         129.00),
        # 7. Semaglutide + Cagrilintide (CagriSema)
        (1, "Semaglutide + Cagrilintide (5mg+5mg)",
         "CagriSema is an advanced prescription combination medicine currently under regulatory review. It blends a GLP-1 receptor agonist (semaglutide) with an amylin analogue (Cagrilintide) to target appetite control through multiple pathways simultaneously.",
         "Amplified Brain-Level Fullness: Both hormones work in different areas of the brain to heavily multiply signals of satisfaction and fullness.\nMaximum Digestion Slowdown: Significantly delays how fast the stomach empties, keeping food there much longer.\nSupercharged Blood Sugar Control: Prevents liver sugar dumps while boosting natural insulin production.",
         "Once-a-week injection under the skin. In late-stage clinical trials, adults without diabetes lost an average of 20% to 22.7% of their total body weight over roughly 15 months.",
         279.00),
        # 8. Retatrutide + Cagrilintide
        (1, "Retatrutide + Cagrilintide (5mg+5mg)",
         "Retatrutide + Cagrilintide is an advanced combination of two next-generation metabolic medicines. It pairs a triple agonist (Retatrutide, targeting GLP-1, GIP, and glucagon) with an amylin analogue (Cagrilintide). Together, they interact with four separate hormonal pathways simultaneously.",
         "Quadruple Hormone Synergy: Targets four distinct pathways (GLP-1, GIP, glucagon, and amylin) to coordinate an unparalleled metabolic response.\nMaximum Fullness via the Brain: Forces the stomach to empty much slower while sending powerful fullness signals.\nAggressive Fat Oxidation: Glucagon forces the body to actively break down and burn off stored adipose tissue.\nDeep Internal Health Cleansing: Dramatically reduces dangerous fat surrounding internal organs and inside the liver.",
         "Once-a-week injection under the skin. Retatrutide alone drops an average of 24.2% of body weight in trials; combining it with Cagrilintide is expected to push average weight loss numbers even higher.",
         299.00),
        # 9. AOD9604
        (1, "AOD9604 (5mg)",
         "AOD9604 (Anti-Obesity Drug 9604) is a specialized prescription peptide typically taken as a daily shot under the skin or as a lozenge. It is a modified fragment of human growth hormone (HGH) that replicates the exact part that controls fat burning, without impacting height, bone growth, or blood sugar levels.",
         "Direct Fat Melting: Triggers lipolysis, the biological process where your body physically breaks down and unlocks stored fat cells for energy.\nStops Fat Storage: Simultaneously blocks lipogenesis, actively preventing your body from building and storing new fat cells.\nJoint and Cartilage Support: Derived from growth hormone, early research shows it can help heal worn-down cartilage and soothe joint pain.",
         "Daily injection under the skin. Targets stubborn belly fat specifically. Yields steady and moderate fat loss over 3 to 4 months. No appetite suppression - works entirely from your body burning fat cells more efficiently.",
         99.00),
        # 10. 5-Amino-1MQ
        (1, "5-Amino-1MQ (10mg)",
         "5-Amino-1MQ is formulated into a peptide form taken as a daily shot under the skin or used as a research compound. It functions as a highly targeted metabolic blocker that seeks out and shuts down NNMT, a stubborn enzyme inside your fat cells that stalls your metabolism.",
         "Unlocks Cellular Energy: By blocking the NNMT enzyme, it floods your cells with NAD+, which instantly jumpstarts a sluggish metabolism.\nShrinks Fat Cells: Stops existing fat cells from growing larger and blocks your body from making new fat tissue.\nSpeeds Up Healing: Reduces fat buildup inside your muscle fibres, allowing your muscles to repair and recover much faster.",
         "Daily injection under the skin. Users see a steady, visible reduction in body fat percentage over a 2 to 3-month period while keeping their muscle definition. Noticeable stamina boost within the first few weeks.",
         109.00),
        # 11. MOTS-C
        (1, "MOTS-C (10mg)",
         "MOTS-c is a unique prescription peptide given as an injection under the skin, usually taken 2 to 3 times a week. Known as a mitochondrial peptide, it is a tiny piece of DNA that comes directly from your cells' powerhouses (the mitochondria). It acts as a powerful metabolic signal to mimic the deep cellular benefits of intense physical exercise.",
         "Turns on Glucose Burning: Dramatically increases insulin sensitivity, forcing your muscles to rapidly pull sugar out of the bloodstream for instant energy.\nTriggers Fat Destruction: Stimulates your body to break down stored fatty acids, transforming stubborn fat into usable cellular fuel.\nSupercharges Mitochondria: Promotes the growth of brand new, healthy cell powerhouses, boosting baseline stamina and endurance.\nStrengthens Bones: Shown to support bone density and prevent bone thinning.",
         "Injection under the skin 2-3 times a week. Enhanced workout capacity within the first few weeks. Lean body recomposition over a 4 to 8-week cycle. Stable daily energy by smoothing out cellular fuel supply.",
         149.00),
        # 12. Tesamorelin
        (1, "Tesamorelin (10mg)",
         "Tesamorelin is an advanced prescription peptide given as a daily shot under the skin. It is a Growth Hormone-Releasing Hormone (GHRH) analogue that signals your brain's pituitary gland to naturally produce and release more of your body's own growth hormone, specifically targeting metabolic repair and fat breakdown.",
         "Destroys Visceral Fat: Aggressively breaks down the dangerous, hard fat that wraps around your internal organs.\nBoosts Lean Muscle: The natural rise in growth hormone levels helps your body repair tissue, leading to an increase in lean muscle mass.\nImproves Lipids: Helps clean up your bloodstream by lowering harmful triglycerides and improving cholesterol levels.\nSpeeds Up Recovery: Enhances cellular repair, allowing your muscles and joints to heal much faster after exercise.",
         "Daily injection under the skin. Noticeable reduction in deep belly fat and waist size over a 3 to 6-month period. Leaner physique as fat drops and muscle grows. Best taken at night on an empty stomach.",
         139.00),
        # 13. L-Carnitine
        (1, "L-Carnitine (600mg)",
         "L-Carnitine is a popular amino acid derivative frequently taken as an injection under the skin or into the muscle. It serves as an essential metabolic shuttle inside your body, responsible for transporting fat into your cell powerhouses so it can be burned for fuel.",
         "Accelerates Fat Burning: Forces your body to rely on stored fatty acids for energy, especially during cardiovascular exercise.\nBoosts Exercise Endurance: Feeds your muscles with fat fuel, sparing glycogen (stored sugar), allowing you to workout longer and harder.\nReduces Muscle Soreness: Improves blood flow to the muscles, significantly cutting down on post-exercise cellular damage.\nEnhances Brain Function: Certain forms cross into the brain to support focus, mental clarity, and protection against cognitive decline.",
         "Injectable form. Combined with exercise, users notice a faster drop in body fat percentage over a 4 to 8-week period. Noticeable push in cardiovascular endurance within the first week.",
         59.00),
        # 14. Lipo-C 120mg
        (1, "Lipo-C (120mg)",
         "Lipo-C is an advanced lipotropic (fat-burning) injection commonly referred to as a modified MIC or Lipo shot. Contains Methionine 15mg, Choline Chloride 50mg, Carnitine 50mg and Dexpanthenol 5mg. Given as a shot 1 to 2 times a week to help the liver process fat, break down energy, and speed up fat loss.",
         "Liver and Fat Synergy: Blends compounds that export fat from the liver with ingredients that immediately burn that fat for fuel.\nNo Jitters or Crashes: Increases daily physical energy and fat metabolism naturally at a cellular level.\nBypasses Weak Digestion: Taking these nutrients as an injection ensures 100% absorption into your system.",
         "Injection 1-2 times a week. Decreased liver and belly fat over a 4 to 8-week period. Noticeable energy boost and reduction in chronic physical fatigue within the first two weeks.",
         89.00),
        # 15. Lipo-C 216mg
        (1, "Lipo-C (216mg)",
         "Lipo-C 216mg is a highly advanced super-lipotropic (fat-burning) and energy injection, often called a Lipo-Plus or Super MIC blend. Contains L-Carnitine 20mg, L-Arginine 20mg, Methionine 25mg, Inositol 50mg, Choline 50mg, Vitamin B6 25mg, Vitamin B5 25mg, and Vitamin B12 1mg. Combines eight active ingredients for maximum fat breakdown and cellular energy.",
         "All-In-One Metabolic Powerhouse: Packs liver cleansers, fat burners, blood flow enhancers, and energy vitamins into a single formula.\nIntense, Stimulant-Free Energy: Provides a massive surge in daily stamina and workout endurance by fixing cellular pathways.\nTotal Nutrient Absorption: Delivered via injection, bypasses the stomach completely ensuring 100% utilization.",
         "Injection 1-2 times a week. Accelerated body fat drops with a smaller waistline over a 4 to 8-week cycle. Instant sustained energy within 24 to 48 hours. Enhanced muscle recovery.",
         99.00),
        # 16. Lipo-C Fat Blaster 526mg
        (1, "Lipo-C Fat Blaster (526mg)",
         "Lipo-C Fat Blaster is an elite cellular energy and fat-burning injection for advanced metabolic repair and anti-aging. Contains L-Carnitine 300mg, Methionine 25mg, Inositol 50mg, Choline 50mg, B12 1mg, B6 50mg and NADH 50mg. Combines ultra-high dose fat-shuttling carnitine with liver cleansers, essential B-vitamins, and NADH - a powerful coenzyme that acts as a direct spark plug for your cells' powerhouses.",
         "The High-Dose Carnitine Advantage: Packing 300mg of L-Carnitine floods your body with the exact transport molecule needed to move large amounts of fat into your cells to be burned.\nDirect Cellular Fuelling: NADH completely skips the middleman to deliver raw energy directly to your cells.\nTotal Metabolic Support: Addresses fat loss from three angles at once - exporting fat from the liver, physically shuttling it to the cellular furnace, and maximizing energy output.",
         "Injection 1-2 times a week. Accelerated slimming and toning over a 4 to 8-week period. Profound energy and mental clarity within hours. Drastic recovery improvements.",
         119.00),
        # 17. Super Shred
        (1, "Super Shred (553mg)",
         "Super Shred is an aggressive, high-strength fat-burning and thermogenic injection formulated to force immediate fat breakdown. Contains L-Carnitine 400mg, MIC Blend 100mg, ATP 50mg, Albuterol 2mg and B12 1mg. Combines ultra-high dose fat-shuttling carnitine and liver-cleansing nutrients with Albuterol (a stimulant that increases body temperature) and ATP (raw energy molecule).",
         "The Thermogenic Kick: Albuterol provides an immediate, intense physical kick that fires up your body's temperature and resting metabolic rate.\nDirect Physical Power: Includes raw ATP, which gives your muscles instant fuel, preventing the weakness or flat feeling when you cut calories.\nAggressive Fat Transport: Packing 400mg of L-Carnitine alongside MIC forces your body to un-trap stored fat and drive it straight into your cellular furnace.",
         "Injection 1-2 times a week. Rapid fat reduction with visible drop in body fat percentage over a 4 to 6-week cycle. Explosive workout stamina. Best taken in the morning before workouts. Must pair with heavy hydration and electrolytes.",
         129.00),
    ]

    for p in products:
        await db.execute(
            "INSERT INTO products (category_id, name, description, benefits, usage_info, price, image_url) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (p[0], p[1], p[2], p[3], p[4], p[5], "")
        )

    # Package options for all 17 products
    package_data = [
        (1, [("1 Bottle", 179.00), ("5 Bottles", 830.00), ("10 Bottles", 1540.00)]),
        (2, [("1 Bottle", 180.00), ("5 Bottles", 840.00), ("10 Bottles", 1540.00)]),
        (3, [("1 Bottle", 179.00), ("5 Bottles", 830.00), ("10 Bottles", 1540.00)]),
        (4, [("1 Bottle", 119.00), ("5 Bottles", 550.00), ("10 Bottles", 1020.00)]),
        (5, [("1 Bottle", 139.00), ("5 Bottles", 650.00), ("10 Bottles", 1200.00)]),
        (6, [("1 Bottle", 129.00), ("5 Bottles", 600.00), ("10 Bottles", 1110.00)]),
        (7, [("1 Bottle", 279.00), ("5 Bottles", 1300.00), ("10 Bottles", 2390.00)]),
        (8, [("1 Bottle", 299.00), ("5 Bottles", 1390.00), ("10 Bottles", 2560.00)]),
        (9, [("1 Bottle", 99.00), ("5 Bottles", 460.00), ("10 Bottles", 850.00)]),
        (10, [("1 Bottle", 109.00), ("5 Bottles", 510.00), ("10 Bottles", 940.00)]),
        (11, [("1 Bottle", 149.00), ("5 Bottles", 690.00), ("10 Bottles", 1270.00)]),
        (12, [("1 Bottle", 139.00), ("5 Bottles", 650.00), ("10 Bottles", 1200.00)]),
        (13, [("1 Bottle", 59.00), ("5 Bottles", 270.00), ("10 Bottles", 500.00)]),
        (14, [("1 Bottle", 89.00), ("5 Bottles", 410.00), ("10 Bottles", 760.00)]),
        (15, [("1 Bottle", 99.00), ("5 Bottles", 460.00), ("10 Bottles", 850.00)]),
        (16, [("1 Bottle", 119.00), ("5 Bottles", 550.00), ("10 Bottles", 1020.00)]),
        (17, [("1 Bottle", 129.00), ("5 Bottles", 600.00), ("10 Bottles", 1110.00)]),
    ]

    for prod_id, options in package_data:
        for opt_name, opt_price in options:
            await db.execute(
                "INSERT INTO package_options (product_id, name, price) VALUES (?, ?, ?)",
                (prod_id, opt_name, opt_price)
            )

    await db.executemany("INSERT INTO faqs (question, answer, sort_order) VALUES (?, ?, ?)", [
        ("What payment methods do you accept?", "We accept PayNow (Singapore) and credit/debit cards via Stripe.", 1),
        ("How long does delivery take?", "Standard delivery takes 3-5 business days. Express delivery takes 1-2 business days.", 2),
        ("Can I return a product?", "Yes, we accept returns within 14 days of delivery if the product is unopened and in original packaging.", 3),
        ("Do you ship internationally?", "Currently we only ship within Singapore. International shipping coming soon.", 4),
        ("How do I track my order?", "Use the 'My Orders' option in the bot menu to check your order status anytime.", 5),
        ("Are these products safe?", "All products are prescription-grade peptides and compounds. Please consult your healthcare provider before starting any new treatment.", 6),
        ("How should I store the products?", "Most peptides should be stored in a cool, dry place or refrigerated. Specific storage instructions are provided with each product.", 7),
    ])

    await db.commit()
    await db.close()
