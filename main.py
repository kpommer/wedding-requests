from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import sqlite3
import os
import uuid
from datetime import datetime
import base64

app = FastAPI()
# Use /tmp for Railway compatibility
DB_NAME = "/tmp/wedding_requests.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        song_name TEXT, 
        artist_name TEXT, 
        requester_name TEXT, 
        guest_id TEXT, 
        status TEXT DEFAULT 'pending',
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute("CREATE INDEX IF NOT EXISTS idx_requester ON requests(requester_name)")
    conn.commit()
    conn.close()

init_db()

@app.get("/")
async def home(request: Request):
    guest_id = request.cookies.get("guest_id")
    if not guest_id:
        guest_id = str(uuid.uuid4())
    
    content = """<!DOCTYPE html><html><head><script src="https://cdn.tailwindcss.com"></script>
    <meta name="viewport" content="width=device-width, initial-scale=1"></head>
    <body class="bg-pink-50 p-4"><div class="max-w-md mx-auto bg-white p-6 rounded-xl shadow-lg text-center">
    <h1 class="text-3xl font-bold text-pink-600 mb-2">Chloe & Alex 💍</h1>
    <p class="text-gray-600 mb-6">Request a song for our special day!</p>
    <form action="/submit" method="POST" class="space-y-4">
        <input type="text" name="song" placeholder="Song Name" class="w-full p-4 border rounded-lg text-lg" required>
        <input type="text" name="artist" placeholder="Artist" class="w-full p-4 border rounded-lg text-lg">
        <input type="text" name="name" placeholder="Your Name" class="w-full p-4 border rounded-lg text-lg" required>
        <button type="submit" class="w-full bg-pink-600 text-white p-4 rounded-lg font-bold text-xl shadow-md">🎵 Send Request</button>
    </form></div></body></html>"""
    
    response = HTMLResponse(content=content)
    response.set_cookie(key="guest_id", value=guest_id, httponly=True)
    return response

@app.post("/submit")
async def submit_request(request: Request, song: str = Form(...), artist: str = Form(...), name: str = Form(...)):
    guest_id = request.cookies.get("guest_id")
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO requests (song_name, artist_name, requester_name, guest_id) VALUES (?,?,?,?)", (song, artist, name, guest_id))
    conn.commit()
    conn.close()
    return HTMLResponse(content="""<!DOCTYPE html><html><head><script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-green-50 flex items-center justify-center min-h-screen"><div class="text-center p-6">
    <h1 class="text-4xl mb-4">🎉</h1><h2 class="text-2xl font-bold text-green-700">Request Sent!</h2>
    <p class="text-gray-600 mt-2">The DJ has your song. Time to hit the dance floor!</p>
    <a href="/" class="block mt-6 text-pink-600 underline">Request another</a></div></body></html>""")

@app.get("/dj")
async def dj_dashboard():
    conn = get_db()
    c = conn.cursor()
    
    # Get all requests
    c.execute("SELECT * FROM requests ORDER BY id DESC")
    rows = c.fetchall()
    
    # Get requester stats
    c.execute("SELECT requester_name, COUNT(*) as count FROM requests GROUP BY requester_name ORDER BY count DESC")
    stats = c.fetchall()
    
    conn.close()

    # Generate Request Table
    html_rows = ""
    for r in rows:
        html_rows += f"""<tr class="border-b border-gray-700">
            <td class="p-3 font-bold">{r['song_name']} <span class="text-sm text-gray-400 font-normal">{r['artist_name']}</span></td>
            <td class="p-3">{r['requester_name']}</td>
            <td class="p-3 text-xs text-gray-500">{r['timestamp'][11:16]}</td>
        </tr>"""

    # Generate Stats Table
    stats_rows = ""
    for s in stats:
        color = "text-red-400 font-bold" if s['count'] > 3 else "text-green-400"
        stats_rows += f"<tr><td class='p-2'>{s['requester_name']}</td><td class='p-2 text-right {color}'>{s['count']}</td></tr>"

    content = f"""<!DOCTYPE html><html><head><script src="https://cdn.tailwindcss.com"></script>
    <meta http-equiv="refresh" content="10"></head>
    <body class="bg-gray-900 text-white p-4"><div class="max-w-4xl mx-auto">
    <h1 class="text-2xl font-bold mb-4 text-center">🎧 DJ Dashboard - Chloe & Alex</h1>
    
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div class="md:col-span-2 bg-gray-800 rounded-lg overflow-hidden">
            <h2 class="p-3 bg-gray-700 font-bold">Latest Requests</h2>
            <table class="w-full">{html_rows}</table>
        </div>
        
        <div class="bg-gray-800 rounded-lg overflow-hidden">
            <h2 class="p-3 bg-gray-700 font-bold">Requester Stats</h2>
            <table class="w-full text-sm">{stats_rows}</table>
            <p class="p-2 text-xs text-gray-500">⚠️ Red = High volume</p>
        </div>
    </div>
    </div></body></html>"""
    return HTMLResponse(content=content)

@app.get("/qr")
async def qr_info():
    # Read and encode the QR image as base64
    qr_path = os.path.join(os.path.dirname(__file__), "wedding_qr.png")
    qr_b64 = ""
    if os.path.exists(qr_path):
        with open(qr_path, "rb") as f:
            qr_b64 = base64.b64encode(f.read()).decode("utf-8")
    
    img_tag = f'<img src="data:image/png;base64,{qr_b64}" alt="Song Request QR" class="w-64 h-64 mx-auto mb-6 border-4 border-pink-200 rounded-lg">' if qr_b64 else '<div class="w-64 h-64 mx-auto mb-6 border-4 border-pink-200 rounded-lg flex items-center justify-center text-gray-400">QR Loading...</div>'
    
    content = f"""<!DOCTYPE html><html><head><script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-pink-50 min-h-screen flex items-center justify-center flex-col text-center p-4">
    <div class="bg-white p-6 rounded-2xl shadow-xl">
        <h1 class="text-2xl font-bold text-pink-600 mb-4">Chloe & Alex 💍</h1>
        {img_tag}
        <p class="text-gray-700 mb-2 text-lg">Scan to request a song!</p>
    </div></body></html>"""
    return HTMLResponse(content=content)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
