
import sqlite3
from database_schema import create_tables

def populate_data(db_name='wholesaler_bot.db'):
    create_tables(db_name) # Ensure tables are created
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    sample_products = [
        ('Organic Apples', 'Fresh, crisp organic apples (per kg)', 'Fruits', 3.50, 100),
        ('Bananas', 'Sweet and ripe bananas (per kg)', 'Fruits', 2.00, 150),
        ('Carrots', 'Locally sourced fresh carrots (per kg)', 'Vegetables', 1.80, 200),
        ('Potatoes', 'Versatile russet potatoes (per kg)', 'Vegetables', 1.20, 300),
        ('Milk (1L)', 'Full cream dairy milk', 'Dairy', 2.80, 50),
        ('Cheddar Cheese (250g)', 'Aged sharp cheddar cheese', 'Dairy', 5.00, 30),
        ('Whole Wheat Bread', 'Freshly baked whole wheat loaf', 'Bakery', 3.20, 40),
        ('Eggs (Dozen)', 'Farm fresh large eggs', 'Pantry', 4.00, 60),
        ('Rice (5kg)', 'Premium long-grain rice', 'Pantry', 8.00, 70),
        ('Chicken Breast (1kg)', 'Boneless, skinless chicken breast', 'Meat', 12.00, 25)
    ]

    cursor.executemany(
        "INSERT INTO products (name, description, category, price, stock) VALUES (?, ?, ?, ?, ?)",
        sample_products
    )

    conn.commit()
    conn.close()
    print("Sample data populated successfully.")

if __name__ == '__main__':
    populate_data()
