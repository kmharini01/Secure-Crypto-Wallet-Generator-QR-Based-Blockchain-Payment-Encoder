import re
import json
import qrcode
import mysql.connector
from tkinter import Tk, Label, Entry, Button, StringVar, OptionMenu, filedialog, messagebox

# Optional libs for wallet generation
try:
    from eth_account import Account
except Exception:
    Account = None

try:
    from bitcoinlib.keys import Key as BTCKey
except Exception:
    BTCKey = None

# --------------------
# MySQL Save Function
# --------------------
def save_wallet_to_mysql(name, wallet_type, address, private_key, qr_file_path):
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="system",
            database="walletdb"
        )
        cursor = conn.cursor()

        query = """
        INSERT INTO wallets (name, wallet_type, address, private_key, qr_file)
        VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (name, wallet_type, address, private_key, qr_file_path))
        conn.commit()

        print("✅ Wallet saved to MySQL successfully.")

    except Exception as e:
        print("❌ Error saving to MySQL:", e)

    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass

# --------------------
# Regex validation
# --------------------
# Bitcoin: legacy (1,3), or bech32 (bc1...)
BTC_REGEX = re.compile(r'^(?:[13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[ac-hj-np-z02-9]{11,71})$')
# Litecoin: legacy (L, M), P2SH (3), or bech32 (ltc1...)
LTC_REGEX = re.compile(r'^(?:[LM3][a-km-zA-HJ-NP-Z1-9]{25,34}|ltc1[ac-hj-np-z02-9]{11,71})$')
# Ethereum / ERC-20 style
ETH_REGEX = re.compile(r'^0x[a-fA-F0-9]{40}$')

def is_valid_btc(addr): return bool(BTC_REGEX.match(addr))
def is_valid_ltc(addr): return bool(LTC_REGEX.match(addr))
def is_valid_eth(addr): return bool(ETH_REGEX.match(addr))
def is_valid_amount(amount_str):
    if not amount_str: return True
    try:
        return float(amount_str) > 0
    except ValueError:
        return False

# --------------------
# Wallet Generation
# --------------------
def generate_eth_wallet():
    if Account is None:
        raise RuntimeError("eth-account library not available. Install with: pip install eth-account")
    acct = Account.create()
    # private key hex string (0x...)
    return {"crypto": "Ethereum", "address": acct.address, "private_key": "0x" + acct.key.hex()}

def generate_btc_wallet():
    if BTCKey is None:
        raise RuntimeError("bitcoinlib library not available. Install with: pip install bitcoinlib")
    k = BTCKey(network='bitcoin')
    return {"crypto": "Bitcoin", "address": k.address(), "private_key": k.wif()}

def generate_ltc_wallet():
    if BTCKey is None:
        raise RuntimeError("bitcoinlib library not available. Install with: pip install bitcoinlib")
    # bitcoinlib Key supports different networks; use litecoin
    k = BTCKey(network='litecoin')
    return {"crypto": "Litecoin", "address": k.address(), "private_key": k.wif()}

def generate_usdt_wallet():
    # We'll create an Ethereum address and treat USDT as ERC-20 (most common)
    if Account is None:
        raise RuntimeError("eth-account library not available. Install with: pip install eth-account")
    acct = Account.create()
    return {"crypto": "USDT (ERC20)", "address": acct.address, "private_key": "0x" + acct.key.hex()}

# --------------------
# QR Code Function
# --------------------
def generate_qr():
    address = address_var.get().strip()
    amount = amount_var.get().strip()
    crypto = crypto_var.get()

    if not address:
        messagebox.showwarning("Input Missing", "Enter wallet address!")
        return

    # Validate by crypto
    if crypto == "Bitcoin" and not is_valid_btc(address):
        messagebox.showwarning("Invalid BTC", "Invalid Bitcoin address!")
        return
    if crypto == "Litecoin" and not is_valid_ltc(address):
        messagebox.showwarning("Invalid LTC", "Invalid Litecoin address!")
        return
    if crypto in ("Ethereum", "USDT (ERC20)") and not is_valid_eth(address):
        messagebox.showwarning("Invalid ETH/USDT", "Invalid Ethereum-style address!")
        return

    if not is_valid_amount(amount):
        messagebox.showwarning("Invalid Amount", "Enter valid numeric amount!")
        return

    # Create a simple URI string for QR. Note: token QR schemes vary by wallet app.
    # For USDT (ERC20) we prefix with 'usdt:' for clarity, but many wallets expect 'ethereum:' with token info.
    coin_key = crypto.lower().split()[0]  # e.g. 'bitcoin', 'ethereum', 'usdt'
    # Build URI: e.g. bitcoin:addr?amount=1.23
    uri = f"{coin_key}:{address}"
    if amount:
        uri += f"?amount={amount}"

    qr = qrcode.QRCode()
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image()

    file_path = filedialog.asksaveasfilename(defaultextension=".png")
    if file_path:
        img.save(file_path)
        messagebox.showinfo("Saved", f"QR saved at {file_path}")

        # ✅ Save wallet to MySQL with QR path (address & key already in fields)
        save_wallet_to_mysql(
            name="User",
            wallet_type=crypto,
            address=address,
            private_key=private_key_temp.get(),  # stored during wallet creation
            qr_file_path=file_path
        )

# --------------------
# Wallet Button Action
# --------------------
def on_generate_wallet():
    crypto = crypto_var.get()

    try:
        if crypto == "Ethereum":
            info = generate_eth_wallet()
        elif crypto == "Bitcoin":
            info = generate_btc_wallet()
        elif crypto == "Litecoin":
            info = generate_ltc_wallet()
        elif crypto == "USDT (ERC20)":
            info = generate_usdt_wallet()
        else:
            raise RuntimeError("Unsupported cryptocurrency selected.")
    except Exception as e:
        messagebox.showerror("Generation Error", str(e))
        return

    address_var.set(info["address"])
    private_key_temp.set(info["private_key"])  # store temporarily for DB insert

    messagebox.showinfo("Wallet Generated", f"{crypto} Address:\n{info['address']}")

    save_choice = messagebox.askyesno("Save Key?", "Save private key to JSON file?")
    if save_choice:
        path = filedialog.asksaveasfilename(defaultextension=".json")
        if path:
            with open(path, "w") as f:
                json.dump(info, f, indent=4)
            messagebox.showinfo("Saved", "Private key saved")

# --------------------
# UI Setup
# --------------------
root = Tk()
root.title("Crypto Wallet + QR Generator (BTC, ETH, LTC, USDT)")
root.geometry("520x380")

private_key_temp = StringVar()

Label(root, text="Select Cryptocurrency:").pack(pady=(8,0))
crypto_var = StringVar(value="Bitcoin")
OptionMenu(root, crypto_var, "Bitcoin", "Ethereum", "Litecoin", "USDT (ERC20)").pack()

Label(root, text="Wallet Address:").pack(pady=(10,0))
address_var = StringVar()
Entry(root, textvariable=address_var, width=64).pack()

Label(root, text="Amount (Optional):").pack(pady=(8,0))
amount_var = StringVar()
Entry(root, textvariable=amount_var, width=64).pack()

Button(root, text="Generate Wallet", bg="blue", fg="white", command=on_generate_wallet).pack(pady=8)
Button(root, text="Generate QR Code", bg="green", fg="white", command=generate_qr).pack(pady=4)

Label(root, text="⚠️ Private keys control funds. Store securely.").pack(pady=12)

root.mainloop()
