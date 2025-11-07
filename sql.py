import mysql.connector

def save_wallet_to_mysql(name, wallet_type, address, private_key, qr_file_path):
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",  # or your MySQL username
            password="system",  # change this
            database="walletdb"
        )

        cursor = conn.cursor()

        query = """
        INSERT INTO wallets (name, wallet_type, address, private_key, qr_file)
        VALUES (%s, %s, %s, %s, %s)
        """
        values = (name, wallet_type, address, private_key, qr_file_path)

        cursor.execute(query, values)
        conn.commit()

        print("✅ Wallet saved to MySQL successfully.")

    except Exception as e:
        print("❌ Error saving to MySQL:", e)

    finally:
        cursor.close()
        conn.close()
