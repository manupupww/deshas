#!/usr/bin/env python3
import http.server
import socketserver
import json
import pandas as pd
from datetime import datetime
import pytz
import os

# Configuration
PORT = 8080
DIRECTORY = "dashboard_web"
SWEEPS_CSV_FILE = "data/sweeps_database.csv"

class SweepsAPIHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        if self.path == '/api/sweeps':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            try:
                if os.path.exists(SWEEPS_CSV_FILE):
                    df = pd.read_csv(SWEEPS_CSV_FILE)
                    
                    # Ensure timestamp and amounts are numeric
                    if 'timestamp' in df.columns:
                        df['timestamp'] = pd.to_numeric(df['timestamp'], errors='coerce')
                    
                    if 'usd_amount' not in df.columns:
                        df['usd_amount'] = pd.to_numeric(df.get('size', 0), errors='coerce') * pd.to_numeric(df.get('price', 0), errors='coerce')
                    else:
                        df['usd_amount'] = pd.to_numeric(df['usd_amount'], errors='coerce')
                    
                    # Sort newest first
                    if 'timestamp' in df.columns:
                        df = df.sort_values('timestamp', ascending=False)
                        
                    # Calculate time ago and clean up data for frontend
                    current_time = datetime.now(pytz.UTC).timestamp()
                    sweeps_data = []
                    
                    for idx, row in df.iterrows():
                        # Extract side (outcome)
                        outcome = str(row.get('outcome', 'Unknown'))
                        side_text = 'Yes' if outcome.upper() == 'YES' else 'No' if outcome.upper() == 'NO' else outcome[:3].capitalize()
                        
                        # Extract price formatting
                        price = row.get('price', row.get('avg_price', 0))
                        try:
                            price_formatted = f"{float(price) * 100:.1f}%" if pd.notna(price) and float(price) > 0 else "-"
                        except (ValueError, TypeError):
                            price_formatted = "-"
                            
                        # Format Time
                        ts = row.get('timestamp')
                        time_ago = "---"
                        if pd.notna(ts):
                            diff = current_time - float(ts)
                            if diff < 60:
                                time_ago = f"{int(diff)}s ago"
                            elif diff < 3600:
                                time_ago = f"{int(diff // 60)}m ago"
                            elif diff < 86400:
                                time_ago = f"{int(diff // 3600)}h ago"
                            else:
                                time_ago = f"{int(diff // 86400)}d ago"
                                
                        # Extract End Date for "Closing Soon" tab
                        end_date = row.get('endDate', row.get('end_date_iso', row.get('end_date', None)))
                        expires_in_hours = -1
                        if pd.notna(end_date):
                            try:
                                # Try parsing ISO format
                                ed_dt = pd.to_datetime(end_date)
                                if ed_dt.tzinfo is None:
                                    ed_dt = ed_dt.replace(tzinfo=pytz.UTC)
                                diff_hours = (ed_dt.timestamp() - current_time) / 3600
                                expires_in_hours = diff_hours
                            except Exception:
                                pass
                                
                        sweeps_data.append({
                            "amount": float(row.get('usd_amount', 0)),
                            "side": side_text,
                            "price": price_formatted,
                            "market": str(row.get('title', row.get('market_name', 'Unknown Market'))),
                            "time": time_ago,
                            "timestamp": float(ts) if pd.notna(ts) else 0,
                            "expires_in_hours": expires_in_hours
                        })
                        
                    # Limit to top 150 for performance
                    response_data = sweeps_data[:150]
                    self.wfile.write(json.dumps(response_data).encode())
                else:
                    self.wfile.write(json.dumps([]).encode())
            except Exception as e:
                print(f"Error serving sweeps: {e}")
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        else:
            # Serve files from directory
            return super().do_GET()

if __name__ == '__main__':
    with socketserver.TCPServer(("", PORT), SweepsAPIHandler) as httpd:
        print(f"Serving at port {PORT}. Open http://localhost:{PORT} in your browser.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")
            httpd.server_close()
