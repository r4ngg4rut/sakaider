import os
import time
import threading
from fastapi import FastAPI
from web3 import Web3
from decimal import Decimal

# Load environment variables
PRIVATE_KEYS = os.getenv("PRIVATE_KEYS").split(",")  # Pisahkan jadi list
NEW_WALLET_ADDRESS = os.getenv("NEW_WALLET_ADDRESS")

# Daftar RPC untuk berbagai jaringan EVM
NETWORKS = {
    "Ethereum": os.getenv("ETHEREUM_RPC"),
    "Binance Smart Chain": os.getenv("BSC_RPC"),
    "Polygon": os.getenv("POLYGON_RPC"),
    "Base": os.getenv("BASE_RPC"),
    "Arbitrum": os.getenv("ARBITRUM_RPC"),
    "Optimism": os.getenv("OPTIMISM_RPC"),
    "ETH Sepolia": os.getenv("ETHSEPOLIA_RPC"),
    "ETH Holesky": os.getenv("ETHHOLESKY_RPC"),
    "Linea": os.getenv("LINEA_RPC"),
    "Linea Sepolia": os.getenv("LINEASEPO_RPC"),
    "Polygon Amoy": os.getenv("AMOY_RPC"),
    "Base Sepolia": os.getenv("BASESEPO_RPC"),
    "Blast": os.getenv("BLAST_RPC"),
    "Optimism Sepolia": os.getenv("OPSEPO_RPC"),
    "ARB Sepolia": os.getenv("ARBSEPO"),
    "Palm": os.getenv("PALM_RPC"),
    "Palm test": os.getenv("PALMTEST_RPC"),
    "AVAX Fuji": os.getenv("AVAXFUJI_RPC"),
    "AVAX": os.getenv("AVAX_RPC"),
    "Celo Alfa": os.getenv("CELOALFA_RPC"),
    "Celo": os.getenv("CELO_ROC"),
    "Zksync": os.getenv("ZKSYNC_RPC"),
    "Zsync Sepo": os.getenv("ZKSYNCSEPO_RPC"),
    "Bsc Test": os.getenv("BSCTEST_RPC"),
    "Mantle": os.getenv("MANTLE_RPC"),
    "Mantle Sepo": os.getenv("MANTLESEPO_RPC"),
    "opBNB": os.getenv("opBNB_RPC"),
    "opBNB Test": os.getenv("opBNBTEST_RPC"),
    "Scroll": os.getenv("SCROLL_RPC"),
    "Scroll test": os.getenv("SCROLLTEST_RPC"),
    "Swellchain": os.getenv("SWELLCHAIN_RPC"),
    "Swell test": os.getenv("SWELLTEST_RPC"),
    "Unichain Sepo": os.getenv("UNICHAINSEPO_RPC"),
    "VANA": os.getenv("VANA_RPC"),
    "OKT": os.getenv("OKT_RPC"),
    "KCC": os.getenv("KCC_RPC"),
}

# Inisialisasi Web3 untuk semua jaringan dan wallet
wallets = []
for private_key in PRIVATE_KEYS:
    for network_name, rpc_url in NETWORKS.items():
        if rpc_url:
            try:
                w3 = Web3(Web3.HTTPProvider(rpc_url))
                if not w3.is_connected():
                    print(f"Failed to connect to {network_name} RPC: {rpc_url}")
                    continue
                account = w3.eth.account.from_key(private_key)
                wallets.append({
                    "network": network_name,
                    "web3": w3,
                    "address": account.address,
                    "private_key": private_key
                })
            except Exception as e:
                print(f"Error connecting to {network_name} RPC: {e}")
        else:
            print(f"RPC untuk {network_name} tidak ditemukan, melewati...")

app = FastAPI()
drain_running = False  # Status monitoring

# Fungsi cek saldo ETH/token di jaringan tertentu
def get_eth_balance(w3, address):
    return w3.from_wei(w3.eth.get_balance(address), "ether")

# Fungsi transfer ETH/token di jaringan tertentu
def transfer_eth(w3, network_name, from_address, private_key):
    balance = get_eth_balance(w3, from_address)
    if balance > 0.0005:
        nonce = w3.eth.get_transaction_count(from_address)
        to_address = Web3.to_checksum_address(NEW_WALLET_ADDRESS)

        try:
            tx = {
                "to": to_address,
                "value": w3.to_wei(balance - Decimal("0.0005"), "ether"),
                "gas": 21000,
                "gasPrice": w3.eth.gas_price,
                "nonce": nonce,
                "chainId": w3.eth.chain_id,
            }

            signed_tx = w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            print(f"[{network_name}] ETH dari {from_address} dikirim! TX Hash: {w3.to_hex(tx_hash)}")
        except ValueError as e:
            print(f"Invalid transaction parameters: {e}")
        except Exception as e:
            print(f"Unexpected error during transaction: {e}")

# Fungsi monitoring semua wallet di semua jaringan
def monitor_wallets():
    global drain_running
    while drain_running:
        for wallet in wallets:
            network_name = wallet["network"]
            w3 = wallet["web3"]
            address = wallet["address"]
            private_key = wallet["private_key"]

            eth_balance = get_eth_balance(w3, address)
            print(f"[{network_name}] Wallet: {address}, Saldo: {eth_balance} ETH")

            if eth_balance > 0.0005:
                transfer_eth(w3, network_name, address, private_key)

        time.sleep(10)

# Endpoint API untuk memulai auto-drain
@app.post("/start-drain")
def start_drain():
    global drain_running
    with drain_lock:
        if not drain_running:
            drain_running = True
            threading.Thread(target=monitor_wallets).start()
            return {"status": "Auto-drain dimulai untuk semua wallet di semua jaringan!"}
        else:
            return {"status": "Auto-drain sudah berjalan!"}

# Endpoint API untuk menghentikan auto-drain
@app.post("/stop-drain")
def stop_drain():
    global drain_running
    with drain_lock:
        if drain_running:
            drain_running = False
            return {"status": "Auto-drain dihentikan untuk semua wallet!"}
        else:
            return {"status": "Auto-drain tidak berjalan!"}

# Cek status monitoring
@app.get("/status")
def status():
    return {"running": drain_running}
