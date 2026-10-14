#!/usr/bin/env python3
"""Ohio Steak 'n Shake Store Exchange - supply request board."""
import os
import sqlite3
import time
from flask import Flask, request, jsonify, Response

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "exchange.db")
PORT = int(os.environ.get("PORT", "8471"))

app = Flask(__name__)

def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = db()
    c.execute("""CREATE TABLE IF NOT EXISTS requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        store_number TEXT NOT NULL,
        item TEXT NOT NULL,
        quantity TEXT NOT NULL DEFAULT '1',
        needed_by TEXT DEFAULT '',
        contact_name TEXT DEFAULT '',
        contact_phone TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'open',
        claimed_by_store TEXT DEFAULT '',
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL
    )""")
    c.commit()
    c.close()

def row_to_dict(r):
    return dict(r)

@app.route("/api/requests", methods=["GET"])
def list_requests():
    c = db()
    rows = c.execute("SELECT * FROM requests ORDER BY created_at DESC").fetchall()
    c.close()
    return jsonify([row_to_dict(r) for r in rows])

@app.route("/api/requests", methods=["POST"])
def create_request():
    d = request.get_json(force=True) or {}
    store = (d.get("store_number") or "").strip()
    item = (d.get("item") or "").strip()
    if not store or not item:
        return jsonify({"error": "Store number and item are required."}), 400
    now = int(time.time())
    c = db()
    cur = c.execute("""INSERT INTO requests
        (store_number, item, quantity, needed_by, contact_name, contact_phone, notes, status, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,'open',?,?)""",
        (store[:20], item[:200], (d.get("quantity") or "1").strip()[:20],
         (d.get("needed_by") or "").strip()[:40], (d.get("contact_name") or "").strip()[:60],
         (d.get("contact_phone") or "").strip()[:30], (d.get("notes") or "").strip()[:500],
         now, now))
    c.commit()
    rid = cur.lastrowid
    row = c.execute("SELECT * FROM requests WHERE id=?", (rid,)).fetchone()
    c.close()
    return jsonify(row_to_dict(row)), 201

def _get(rid):
    c = db()
    row = c.execute("SELECT * FROM requests WHERE id=?", (rid,)).fetchone()
    c.close()
    return row

@app.route("/api/requests/<int:rid>/claim", methods=["POST"])
def claim(rid):
    d = request.get_json(force=True) or {}
    store = (d.get("store_number") or "").strip()
    if not store:
        return jsonify({"error": "Store number is required."}), 400
    r = _get(rid)
    if not r:
        return jsonify({"error": "Request not found."}), 404
    if r["status"] != "open":
        return jsonify({"error": "Request is no longer open."}), 409
    now = int(time.time())
    c = db()
    c.execute("UPDATE requests SET status='claimed', claimed_by_store=?, updated_at=? WHERE id=?",
              (store[:20], now, rid))
    c.commit()
    row = c.execute("SELECT * FROM requests WHERE id=?", (rid,)).fetchone()
    c.close()
    return jsonify(row_to_dict(row))

@app.route("/api/requests/<int:rid>/unclaim", methods=["POST"])
def unclaim(rid):
    r = _get(rid)
    if not r:
        return jsonify({"error": "Request not found."}), 404
    if r["status"] != "claimed":
        return jsonify({"error": "Request is not claimed."}), 409
    now = int(time.time())
    c = db()
    c.execute("UPDATE requests SET status='open', claimed_by_store='', updated_at=? WHERE id=?", (now, rid))
    c.commit()
    row = c.execute("SELECT * FROM requests WHERE id=?", (rid,)).fetchone()
    c.close()
    return jsonify(row_to_dict(row))

@app.route("/api/requests/<int:rid>/fulfill", methods=["POST"])
def fulfill(rid):
    r = _get(rid)
    if not r:
        return jsonify({"error": "Request not found."}), 404
    if r["status"] not in ("open", "claimed"):
        return jsonify({"error": "Request is already closed."}), 409
    now = int(time.time())
    c = db()
    c.execute("UPDATE requests SET status='fulfilled', updated_at=? WHERE id=?", (now, rid))
    c.commit()
    row = c.execute("SELECT * FROM requests WHERE id=?", (rid,)).fetchone()
    c.close()
    return jsonify(row_to_dict(row))

@app.route("/api/requests/<int:rid>/cancel", methods=["POST"])
def cancel(rid):
    r = _get(rid)
    if not r:
        return jsonify({"error": "Request not found."}), 404
    if r["status"] not in ("open", "claimed"):
        return jsonify({"error": "Request is already closed."}), 409
    now = int(time.time())
    c = db()
    c.execute("UPDATE requests SET status='cancelled', updated_at=? WHERE id=?", (now, rid))
    c.commit()
    row = c.execute("SELECT * FROM requests WHERE id=?", (rid,)).fetchone()
    c.close()
    return jsonify(row_to_dict(row))

@app.route("/healthz")
def healthz():
    return jsonify({"ok": True})

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ohio Store Exchange &mdash; Steak 'n Shake</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;background:#f4f4f4;color:#222;line-height:1.45}
header{background:#111;color:#fff;padding:18px 16px;text-align:center;border-bottom:5px solid #d8232a}
header h1{font-size:22px;letter-spacing:.5px}
header h1 span{color:#d8232a}
header p{color:#bbb;font-size:13px;margin-top:4px}
.wrap{max-width:720px;margin:0 auto;padding:14px 12px 60px}
.card{background:#fff;border-radius:10px;padding:16px;margin-bottom:14px;box-shadow:0 1px 4px rgba(0,0,0,.08)}
.card h2{font-size:17px;margin-bottom:12px;color:#111}
label{display:block;font-size:13px;font-weight:600;margin:10px 0 4px;color:#444}
input,textarea,select{width:100%;padding:10px;border:1px solid #ccc;border-radius:8px;font-size:15px}
textarea{resize:vertical;min-height:56px}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
button{cursor:pointer;border:none;border-radius:8px;font-size:15px;font-weight:700;padding:11px 16px}
.btn-red{background:#d8232a;color:#fff;width:100%;margin-top:14px}
.btn-red:active{background:#b31b21}
.btn-dark{background:#222;color:#fff}
.btn-sm{padding:7px 12px;font-size:13px;margin-right:6px;margin-top:8px}
.btn-outline{background:#fff;border:2px solid #d8232a;color:#d8232a}
.req{border-left:5px solid #d8232a}
.req.claimed{border-left-color:#e6a817}
.req.done{border-left-color:#999;opacity:.75}
.req .top{display:flex;justify-content:space-between;align-items:baseline;gap:8px}
.req .item{font-size:17px;font-weight:700}
.badge{font-size:11px;font-weight:800;text-transform:uppercase;padding:3px 9px;border-radius:20px;white-space:nowrap}
.b-open{background:#ffe1e3;color:#b31b21}
.b-claimed{background:#fff3d6;color:#8a6400}
.b-fulfilled{background:#e2f2e2;color:#1e6b1e}
.b-cancelled{background:#eee;color:#666}
.meta{font-size:13px;color:#666;margin-top:6px}
.meta b{color:#333}
.notes{font-size:14px;margin-top:8px;background:#fafafa;border-radius:6px;padding:8px}
.empty{text-align:center;color:#888;padding:26px 10px;font-size:14px}
h3.sec{font-size:15px;text-transform:uppercase;letter-spacing:.6px;color:#666;margin:20px 0 10px}
#err{display:none;background:#ffe1e3;color:#b31b21;border-radius:8px;padding:10px;margin-bottom:12px;font-size:14px}
.search{margin-bottom:4px}
footer{text-align:center;color:#999;font-size:12px;margin-top:30px}
</style>
</head>
<body>
<header>
<h1>OHIO STORE <span>EXCHANGE</span></h1>
<p>Steak 'n Shake &mdash; borrow &amp; request supplies between Ohio stores</p>
</header>
<div class="wrap">
<div id="err"></div>
<div class="card">
<h2>Request an item</h2>
<form id="reqForm">
<div class="row2">
<div><label>Your store number *</label><input id="f_store" required inputmode="numeric" placeholder="e.g. 1234"></div>
<div><label>Quantity</label><input id="f_qty" value="1"></div>
</div>
<label>Item needed *</label><input id="f_item" required placeholder="e.g. 10 lb ground beef patties">
<div class="row2">
<div><label>Needed by</label><input id="f_needed" placeholder="e.g. Tomorrow AM"></div>
<div><label>Your name</label><input id="f_name" placeholder="Manager on duty"></div>
</div>
<label>Phone</label><input id="f_phone" inputmode="tel" placeholder="So the other store can reach you">
<label>Notes</label><textarea id="f_notes" placeholder="Brand, size, or anything that helps"></textarea>
<button class="btn-red" type="submit">Post request</button>
</form>
</div>
<div class="card search">
<input id="q" placeholder="Search items or store numbers&hellip;">
</div>
<h3 class="sec">Open requests</h3>
<div id="open"></div>
<h3 class="sec">Claimed &mdash; being picked up</h3>
<div id="claimed"></div>
<h3 class="sec">Recently closed</h3>
<div id="closed"></div>
<footer>Ohio Store Exchange &middot; for Steak 'n Shake Ohio region stores</footer>
</div>
<script>
const $=id=>document.getElementById(id);
function showErr(m){const e=$('err');e.textContent=m;e.style.display='block';setTimeout(()=>e.style.display='none',5000);}
function esc(s){return String(s==null?'':s);}
function fmtTime(ts){const d=new Date(ts*1000);return d.toLocaleString();}
function badge(st){const m={open:['b-open','Open'],claimed:['b-claimed','Claimed'],fulfilled:['b-fulfilled','Fulfilled'],cancelled:['b-cancelled','Cancelled']};const b=m[st]||m.open;return '<span class="badge '+b[0]+'">'+b[1]+'</span>';}
let all=[];
async function load(){
  const r=await fetch('/api/requests');
  all=await r.json();
  render();
}
function card(r){
  const cls=r.status==='open'?'':(r.status==='claimed'?'claimed':'done');
  let h='<div class="card req '+cls+'"><div class="top"><div class="item"></div>'+badge(r.status)+'</div>';
  h+='<div class="meta">Store <b class="st"></b> &middot; Qty <b class="qt"></b>';
  if(r.needed_by)h+=' &middot; Needed <b class="nb"></b>';
  h+=' &middot; <span class="tm"></span></div>';
  if(r.claimed_by_store)h+='<div class="meta">Claimed by store <b class="cb"></b></div>';
  if(r.contact_name||r.contact_phone)h+='<div class="meta">Contact: <b class="cn"></b> <span class="cp"></span></div>';
  if(r.notes)h+='<div class="notes"></div>';
  h+='<div class="acts"></div></div>';
  const t=document.createElement('template');t.innerHTML=h.trim();
  const el=t.content.firstChild;
  el.querySelector('.item').textContent=r.item;
  el.querySelector('.st').textContent=r.store_number;
  el.querySelector('.qt').textContent=r.quantity;
  if(r.needed_by)el.querySelector('.nb').textContent=r.needed_by;
  el.querySelector('.tm').textContent=fmtTime(r.created_at);
  if(r.claimed_by_store)el.querySelector('.cb').textContent=r.claimed_by_store;
  if(r.contact_name||r.contact_phone){
    el.querySelector('.cn').textContent=r.contact_name||'';
    el.querySelector('.cp').textContent=r.contact_phone?('('+r.contact_phone+')'):'';
  }
  if(r.notes)el.querySelector('.notes').textContent=r.notes;
  const acts=el.querySelector('.acts');
  function btn(label,cls,fn){const b=document.createElement('button');b.className='btn-sm '+cls;b.textContent=label;b.onclick=fn;acts.appendChild(b);}
  if(r.status==='open'){
    btn('We have it', 'btn-dark', async()=>{
      const s=prompt('Your store number:');
      if(!s||!s.trim())return;
      const res=await fetch('/api/requests/'+r.id+'/claim',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({store_number:s.trim()})});
      if(!res.ok){showErr((await res.json()).error||'Could not claim.');return;}
      load();
    });
    btn('Fulfilled','btn-outline',async()=>{await fetch('/api/requests/'+r.id+'/fulfill',{method:'POST'});load();});
    btn('Cancel','btn-outline',async()=>{if(confirm('Cancel this request?')){await fetch('/api/requests/'+r.id+'/cancel',{method:'POST'});load();}});
  }else if(r.status==='claimed'){
    btn('Mark fulfilled','btn-dark',async()=>{await fetch('/api/requests/'+r.id+'/fulfill',{method:'POST'});load();});
    btn('Release claim','btn-outline',async()=>{await fetch('/api/requests/'+r.id+'/unclaim',{method:'POST'});load();});
  }
  return el;
}
function render(){
  const q=$('q').value.trim().toLowerCase();
  const f=r=>!q||(r.item+' '+r.store_number+' '+(r.notes||'')).toLowerCase().includes(q);
  const open=all.filter(r=>r.status==='open'&&f(r));
  const claimed=all.filter(r=>r.status==='claimed'&&f(r));
  const closed=all.filter(r=>(r.status==='fulfilled'||r.status==='cancelled')&&f(r)).slice(0,20);
  const put=(id,list,msg)=>{const e=$(id);e.innerHTML='';if(!list.length){e.innerHTML='<div class="card empty">'+msg+'</div>';return;}list.forEach(r=>e.appendChild(card(r)));};
  put('open',open,'No open requests. All stocked up.');
  put('claimed',claimed,'Nothing claimed right now.');
  put('closed',closed,'Nothing closed yet.');
}
$('q').addEventListener('input',render);
$('reqForm').addEventListener('submit',async e=>{
  e.preventDefault();
  const body={store_number:$('f_store').value,quantity:$('f_qty').value,item:$('f_item').value,
    needed_by:$('f_needed').value,contact_name:$('f_name').value,contact_phone:$('f_phone').value,notes:$('f_notes').value};
  const res=await fetch('/api/requests',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  if(!res.ok){showErr((await res.json()).error||'Could not post.');return;}
  e.target.reset();$('f_qty').value='1';
  load();
  window.scrollTo({top:0,behavior:'smooth'});
});
load();
setInterval(load,30000);
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return Response(PAGE, mimetype="text/html")

if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=PORT)
