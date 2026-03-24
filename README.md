# Telegram Wholesaler Bot

This is a sample Telegram bot for a wholesaler shop, built with Python and `python-telegram-bot` library, using SQLite for data storage. It demonstrates a product catalog, cart system, order placement, customer interaction, and basic admin features.

## Features

-   **Product Catalog**: Browse products by category with wholesale pricing.
-   **Cart System**: Add, update, and remove items from the cart.
-   **Order Placement**: Place orders with delivery details and receive confirmation.
-   **Customer Interaction**: Greetings, common queries (store hours, delivery info, payment methods).
-   **Admin Features**: Receive order notifications, view pending orders, mark orders as confirmed/delivered.
-   **SQLite Database**: Simple and efficient data storage.
-   **Inline Keyboards**: User-friendly navigation.

## Setup Instructions

Follow these steps to set up and run the bot:

### 1. Clone the Repository (or create files manually)

If you are setting this up in your local environment, first clone the repository:

```bash
git clone <repository_url>
cd telegram-wholesaler-bot
```

If you are manually creating the files, ensure you have the following structure in your `/home/ubuntu/telegram-wholesaler-bot/` directory:

```
telegram-wholesaler-bot/
├── bot.py
├── database_schema.py
├── populate_sample_data.py
└── requirements.txt
└── README.md
```

### 2. Get Your Bot Token

1.  Open Telegram and search for `@BotFather`.
2.  Start a chat with `@BotFather` and send the `/newbot` command.
3.  Follow the instructions to choose a name and a username for your bot. `@BotFather` will then provide you with an **HTTP API Token**.
4.  **Keep this token secure!** You will need it in the next step.

### 3. Find Your Telegram User ID (for Admin Features)

To use the admin features, you need to set your Telegram User ID as the `ADMIN_USER_ID` in `bot.py`.

1.  Open Telegram and search for `@userinfobot` or `@getidsbot`.
2.  Start a chat with the bot and send `/start`. It will reply with your User ID.
3.  Note down your User ID.

### 4. Install Dependencies

Navigate to the bot's directory in your terminal and install the required Python packages:

```bash
pip install -r requirements.txt
```

### 5. Configure the Bot

Open `bot.py` in a text editor and make the following changes:

1.  **Replace `YOUR_BOT_TOKEN`**: Locate the line `application = Application.builder().token("YOUR_BOT_TOKEN").build()` and replace `"YOUR_BOT_TOKEN"` with the HTTP API Token you obtained from `@BotFather`.

    ```python
    # Example:
    application = Application.builder().token("123456:ABC-DEF1234ghIkl-zyx57W2v1u1sa23b45").build()
    ```

2.  **Set `ADMIN_USER_ID`**: Locate the line `ADMIN_USER_ID = 123456789` and replace `123456789` with your actual Telegram User ID.

    ```python
    # Example:
    ADMIN_USER_ID = 1254321 # Your Telegram User ID
    ```

### 6. Initialize the Database and Populate Sample Data

Run the following commands in your terminal from the bot's directory to create the SQLite database and populate it with sample products:

```bash
python3 database_schema.py
python3 populate_sample_data.py
```

This will create a `wholesaler_bot.db` file in your project directory.

### 7. Run the Bot

Start the bot by running the `bot.py` script:

```bash
python3 bot.py
```

The bot should now be running and accessible via Telegram. Send `/start` to your bot to begin interacting with it.

## Usage

### User Commands

-   `/start`: Greets the user and displays the main menu.
-   **Browse Products**: View products by category.
-   **View Cart**: Check items in your cart, update quantities, or clear the cart.
-   **My Orders**: View your past order history.
-   **Help & Info**: Get information about store hours, delivery, and payment.

### Admin Commands

-   `/admin`: Access the admin menu (only for the configured `ADMIN_USER_ID`).
-   **View Pending Orders**: See orders awaiting confirmation or delivery.
-   **View All Orders**: See all orders.
-   **Manage Orders**: From pending orders, you can mark them as confirmed or delivered, or view detailed information.

## Customization

-   **Products**: Modify `populate_sample_data.py` to add, remove, or change sample products. For a live bot, you would implement an admin interface or a separate script to manage products dynamically.
-   **Responses**: Edit the text messages in `bot.py` to customize greetings, information, and confirmations.
-   **Admin Features**: Extend admin functionalities in `bot.py` to include more management options like editing product stock, viewing user details, etc.
-   **Database**: For larger scale applications, consider migrating from SQLite to a more robust database like PostgreSQL or MySQL.

Feel free to modify the code to suit your specific wholesaler shop's needs!
