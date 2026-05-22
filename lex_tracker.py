from flask import Flask, request, jsonify, render_template_string
import sqlite3, smtplib, threading, time
from datetime import datetime, date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

EMAIL_ORIGEN   = "miguelmartinezmarino2112@gmail.com"
EMAIL_PASSWORD = "vbya tefy biku rsxx"
EMAILS_DESTINO = [
    "miguelmartinezmarino2112@gmail.com",
    "nilamarino09@gmail.com",
    "adrian@nnlaw.com",
    "adry.navarro05@gmail.com",
]
HORA_ALERTA = "08:00"
app = Flask(__name__)
DB  = "lex_tracker.db"

def init_db():
    with sqlite3.connect(DB) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS plazos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            causa TEXT NOT NULL, expediente TEXT, tipo TEXT,
            fecha TEXT NOT NULL, responsable TEXT, notas TEXT,
            creado TEXT DEFAULT (date('now')))""")
        con.commit()

def get_all():
    with sqlite3.connect(DB) as con:
        con.row_factory = sqlite3.Row
        return [dict(r) for r in con.execute("SELECT * FROM plazos ORDER BY fecha ASC").fetchall()]

def insert(data):
    with sqlite3.connect(DB) as con:
        cur = con.execute("INSERT INTO plazos (causa,expediente,tipo,fecha,responsable,notas) VALUES (?,?,?,?,?,?)",
            (data['causa'],data.get('expediente',''),data.get('tipo',''),data['fecha'],data.get('responsable',''),data.get('notas','')))
        con.commit(); return cur.lastrowid

def update(id, data):
    with sqlite3.connect(DB) as con:
        con.execute("UPDATE plazos SET causa=?,expediente=?,tipo=?,fecha=?,responsable=?,notas=? WHERE id=?",
            (data['causa'],data.get('expediente',''),data.get('tipo',''),data['fecha'],data.get('responsable',''),data.get('notas',''),id))
        con.commit()

def delete(id):
    with sqlite3.connect(DB) as con:
        con.execute("DELETE FROM plazos WHERE id=?", (id,)); con.commit()

def dias_hasta(fecha_str):
    return (datetime.strptime(fecha_str, "%Y-%m-%d").date() - date.today()).days

def semaforo(dias):
    if dias <= 2: return "rojo"
    if dias <= 5: return "amarillo"
    return "verde"

def enriquecer(plazos):
    for p in plazos:
        p['dias'] = dias_hasta(p['fecha'])
        p['semaforo'] = semaforo(p['dias'])
        p['fecha_fmt'] = datetime.strptime(p['fecha'], "%Y-%m-%d").strftime("%d/%m/%Y")
    return plazos

def enviar_email(urgentes):
    if not urgentes or EMAIL_ORIGEN == "tufirma@gmail.com":
        print("Email no configurado o sin urgencias."); return
    rojos = [p for p in urgentes if p['semaforo']=='rojo']
    amarillos = [p for p in urgentes if p['semaforo']=='amarillo']
    html = f"""<html><body style="font-family:Arial;background:#111;color:#eee;padding:30px">
    <h2 style="color:#c9a96e">Lex Tracker — Alerta de Vencimientos {date.today().strftime('%d/%m/%Y')}</h2>
    {"<h3 style='color:#e05c5c'>URGENTE ("+str(len(rojos))+")</h3>"+"".join(f"<p style='color:#e05c5c'>🔴 {p['causa']} — {p['expediente']} — {'HOY' if p['dias']==0 else 'VENCIDO' if p['dias']<0 else str(p['dias'])+' dias'} — {p['responsable']}</p>" for p in rojos) if rojos else ""}
    {"<h3 style='color:#d4a82a'>ATENCION ("+str(len(amarillos))+")</h3>"+"".join(f"<p style='color:#d4a82a'>🟡 {p['causa']} — {p['expediente']} — {p['dias']} dias — {p['responsable']}</p>" for p in amarillos) if amarillos else ""}
    </body></html>"""
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"Lex Tracker — {len(rojos)} urgente(s) — {date.today().strftime('%d/%m/%Y')}"
    msg['From'] = EMAIL_ORIGEN; msg['To'] = ", ".join(EMAILS_DESTINO)
    msg.attach(MIMEText(html, 'html'))
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
            s.login(EMAIL_ORIGEN, EMAIL_PASSWORD)
            s.sendmail(EMAIL_ORIGEN, EMAILS_DESTINO, msg.as_string())
        print("Email enviado!")
    except Exception as e:
        print(f"Error email: {e}")

def loop_alertas():
    enviado_hoy = None
    while True:
        if datetime.now().strftime("%H:%M") == HORA_ALERTA and enviado_hoy != date.today():
            urgentes = [p for p in enriquecer(get_all()) if p['semaforo'] in ('rojo','amarillo')]
            enviar_email(urgentes); enviado_hoy = date.today()
        time.sleep(60)

@app.route("/api/plazos", methods=["GET"])
def api_get(): return jsonify(enriquecer(get_all()))

@app.route("/api/plazos", methods=["POST"])
def api_post():
    data = request.json
    if not data.get('causa') or not data.get('fecha'):
        return jsonify({"error": "faltan campos"}), 400
    return jsonify({"ok": True, "id": insert(data)}), 201

@app.route("/api/plazos/<int:id>", methods=["PUT"])
def api_put(id): update(id, request.json); return jsonify({"ok": True})

@app.route("/api/plazos/<int:id>", methods=["DELETE"])
def api_delete(id): delete(id); return jsonify({"ok": True})

@app.route("/api/test-email", methods=["POST"])
def api_test():
    threading.Thread(target=enviar_email, args=([p for p in enriquecer(get_all()) if p['semaforo'] in ('rojo','amarillo')],), daemon=True).start()
    return jsonify({"ok": True})

HTML = r"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Lex Tracker</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Mono:wght@400;500&family=Lato:wght@300;400;700&display=swap" rel="stylesheet">
<style>
:root{--bg:#0f0f11;--surface:#17171a;--card:#1e1e23;--border:#2a2a32;--text:#e8e6e0;--muted:#6b6880;--accent:#c9a96e;--red:#e05c5c;--yellow:#d4a82a;--green:#5ab88a;--red-bg:rgba(224,92,92,.10);--yellow-bg:rgba(212,168,42,.10);--green-bg:rgba(90,184,138,.10)}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font-family:'Lato',sans-serif;min-height:100vh;display:flex}
.sidebar{width:230px;flex-shrink:0;background:var(--surface);border-right:1px solid var(--border);padding:32px 20px;display:flex;flex-direction:column;position:sticky;top:0;height:100vh;overflow-y:auto}
.logo{font-family:'DM Serif Display',serif;font-size:22px;color:var(--accent);margin-bottom:2px}
.logo-sub{font-family:'DM Mono',monospace;font-size:10px;color:var(--muted);letter-spacing:2px;text-transform:uppercase;margin-bottom:32px}
.legend{background:rgba(255,255,255,.02);border:1px solid var(--border);border-radius:10px;padding:14px;margin-bottom:16px}
.legend-title{font-family:'DM Mono',monospace;font-size:9px;letter-spacing:2px;text-transform:uppercase;color:var(--muted);margin-bottom:10px}
.legend-item{display:flex;align-items:center;gap:8px;font-size:12px;margin-bottom:7px}
.dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}
.sidebar-footer{margin-top:auto;font-size:11px;color:var(--muted);line-height:1.8;border-top:1px solid var(--border);padding-top:16px}
.main{flex:1;padding:36px 40px;min-width:0}
.topbar{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:28px}
.page-title{font-family:'DM Serif Display',serif;font-size:30px}
.page-sub{font-size:13px;color:var(--muted);margin-top:4px}
.btn{padding:10px 20px;border-radius:8px;border:none;cursor:pointer;font-family:'Lato',sans-serif;font-size:14px;font-weight:700;transition:all .2s}
.btn-primary{background:var(--accent);color:#0f0f11}.btn-primary:hover{background:#d4b07a;transform:translateY(-1px)}
.btn-ghost{background:transparent;color:var(--muted);border:1px solid var(--border)}.btn-ghost:hover{border-color:var(--accent);color:var(--accent)}
.btn-sm{padding:6px 14px;font-size:12px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:22px}
.stat{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px;position:relative;overflow:hidden;transition:transform .2s}
.stat:hover{transform:translateY(-2px)}.stat::before{content:'';position:absolute;top:0;left:0;right:0;height:3px}
.stat.red::before{background:var(--red)}.stat.yellow::before{background:var(--yellow)}.stat.green::before{background:var(--green)}.stat.acc::before{background:var(--accent)}
.stat-label{font-family:'DM Mono',monospace;font-size:10px;text-transform:uppercase;letter-spacing:2px;color:var(--muted);margin-bottom:6px}
.stat-num{font-family:'DM Serif Display',serif;font-size:36px;line-height:1}
.stat.red .stat-num{color:var(--red)}.stat.yellow .stat-num{color:var(--yellow)}.stat.green .stat-num{color:var(--green)}.stat.acc .stat-num{color:var(--accent)}
.stat-desc{font-size:12px;color:var(--muted);margin-top:4px}
.filters{display:flex;gap:8px;align-items:center;margin-bottom:14px;flex-wrap:wrap}
.fbtn{padding:5px 14px;border-radius:20px;border:1px solid var(--border);background:transparent;color:var(--muted);font-size:13px;cursor:pointer;transition:all .2s;font-family:'Lato',sans-serif}
.fbtn:hover,.fbtn.active{border-color:var(--accent);color:var(--accent);background:rgba(201,169,110,.06)}
.search{margin-left:auto;background:var(--card);border:1px solid var(--border);border-radius:8px;padding:7px 14px;color:var(--text);font-family:'Lato',sans-serif;font-size:13px;outline:none;width:200px;transition:border-color .2s}
.search:focus{border-color:var(--accent)}.search::placeholder{color:var(--muted)}
.tbl-wrap{background:var(--card);border:1px solid var(--border);border-radius:14px;overflow:hidden}
table{width:100%;border-collapse:collapse}
thead tr{background:var(--surface);border-bottom:1px solid var(--border)}
th{font-family:'DM Mono',monospace;font-size:10px;text-transform:uppercase;letter-spacing:2px;color:var(--muted);padding:13px 16px;text-align:left;font-weight:500;cursor:pointer;user-select:none;white-space:nowrap}
th:hover{color:var(--accent)}
tbody tr{border-bottom:1px solid rgba(42,42,50,.6);transition:background .15s;animation:rowIn .3s ease both}
tbody tr:last-child{border-bottom:none}tbody tr:hover{background:rgba(255,255,255,.025)}
@keyframes rowIn{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:translateY(0)}}
td{padding:12px 16px;font-size:14px;vertical-align:middle}
.causa-n{font-weight:700;color:var(--text);margin-bottom:2px}
.exped{font-family:'DM Mono',monospace;font-size:11px;color:var(--muted)}
.sem-cell{display:flex;align-items:center;gap:9px}
.sem-dot{width:13px;height:13px;border-radius:50%;flex-shrink:0}
.dot-red{background:var(--red);box-shadow:0 0 8px var(--red);animation:blink .9s ease-in-out infinite}
.dot-yellow{background:var(--yellow);box-shadow:0 0 8px var(--yellow);animation:blink 1.5s ease-in-out infinite}
.dot-green{background:var(--green);box-shadow:0 0 6px var(--green)}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.25}}
.days-red{color:var(--red);font-family:'DM Mono',monospace;font-size:13px;font-weight:700}
.days-yellow{color:var(--yellow);font-family:'DM Mono',monospace;font-size:13px;font-weight:700}
.days-green{color:var(--green);font-family:'DM Mono',monospace;font-size:13px}
.tipo-tag{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;background:rgba(124,106,247,.1);color:#a99df7;border:1px solid rgba(124,106,247,.2)}
.abt{background:none;border:none;color:var(--muted);cursor:pointer;padding:5px 7px;border-radius:6px;transition:all .2s;font-size:15px}
.abt:hover{color:var(--accent);background:rgba(201,169,110,.08)}.abt.del:hover{color:var(--red);background:var(--red-bg)}
.empty{text-align:center;padding:60px;color:var(--muted)}.empty-icon{font-size:36px;margin-bottom:10px}
.overlay{position:fixed;inset:0;background:rgba(0,0,0,.8);backdrop-filter:blur(4px);z-index:200;display:flex;align-items:center;justify-content:center;opacity:0;pointer-events:none;transition:opacity .2s}
.overlay.open{opacity:1;pointer-events:all}
.modal{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:36px;width:540px;max-width:95vw;transform:translateY(20px);transition:transform .25s}
.overlay.open .modal{transform:translateY(0)}
.modal-title{font-family:'DM Serif Display',serif;font-size:24px;margin-bottom:22px;color:var(--accent)}
.fgrid{display:grid;grid-template-columns:1fr 1fr;gap:13px}
.fg{display:flex;flex-direction:column;gap:5px}.fg.full{grid-column:1/-1}
.flabel{font-family:'DM Mono',monospace;font-size:10px;text-transform:uppercase;letter-spacing:1.5px;color:var(--muted)}
.finput,.fselect{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:10px 14px;color:var(--text);font-family:'Lato',sans-serif;font-size:14px;outline:none;transition:border-color .2s}
.finput:focus,.fselect:focus{border-color:var(--accent)}.fselect option{background:var(--card)}
.mactions{display:flex;gap:10px;justify-content:flex-end;margin-top:24px}
.banner{background:var(--red-bg);border:1px solid rgba(224,92,92,.3);border-radius:10px;padding:12px 18px;display:none;align-items:center;gap:12px;margin-bottom:18px;font-size:13px;color:var(--red)}
.banner.show{display:flex}
.toast{position:fixed;bottom:24px;right:24px;padding:12px 20px;border-radius:10px;font-size:13px;font-weight:700;transform:translateY(60px);opacity:0;transition:all .3s;z-index:999;pointer-events:none}
.toast.ok{background:var(--green);color:#0f0f11}.toast.err{background:var(--red);color:#fff}.toast.show{transform:translateY(0);opacity:1}
</style></head><body>
<div class="sidebar">
  <div class="logo">Lex Tracker</div>
  <div class="logo-sub">Vencimientos</div>
  <div class="legend">
    <div class="legend-title">Semaforo</div>
    <div class="legend-item"><div class="dot" style="background:var(--green);box-shadow:0 0 6px var(--green)"></div><span style="color:var(--green);font-weight:700">Verde</span><span style="color:var(--muted);margin-left:4px">+5 dias</span></div>
    <div class="legend-item"><div class="dot" style="background:var(--yellow);box-shadow:0 0 6px var(--yellow)"></div><span style="color:var(--yellow);font-weight:700">Amarillo</span><span style="color:var(--muted);margin-left:4px">3-5 dias</span></div>
    <div class="legend-item"><div class="dot" style="background:var(--red);box-shadow:0 0 6px var(--red)"></div><span style="color:var(--red);font-weight:700">Rojo</span><span style="color:var(--muted);margin-left:4px">2 dias o menos</span></div>
  </div>
  <button class="btn btn-ghost btn-sm" onclick="testEmail()" style="margin-bottom:12px">Probar email</button>
  <div class="sidebar-footer">Lex Tracker v1.0<br>Alertas: {{ hora }}<br>2026</div>
</div>
<div class="main">
  <div class="topbar">
    <div><div class="page-title">Vencimientos</div><div class="page-sub" id="fecha-hoy"></div></div>
    <button class="btn btn-primary" onclick="abrirModal()">+ Nuevo plazo</button>
  </div>
  <div class="banner" id="banner">🚨 <span id="banner-txt"></span></div>
  <div class="stats">
    <div class="stat red"><div class="stat-label">Urgente</div><div class="stat-num" id="st-r">0</div><div class="stat-desc">2 dias o menos</div></div>
    <div class="stat yellow"><div class="stat-label">Atencion</div><div class="stat-num" id="st-y">0</div><div class="stat-desc">3 a 5 dias</div></div>
    <div class="stat green"><div class="stat-label">En tiempo</div><div class="stat-num" id="st-g">0</div><div class="stat-desc">Mas de 5 dias</div></div>
    <div class="stat acc"><div class="stat-label">Total</div><div class="stat-num" id="st-t">0</div><div class="stat-desc">plazos activos</div></div>
  </div>
  <div class="filters">
    <button class="fbtn active" onclick="setF('todos',this)">Todos</button>
    <button class="fbtn" onclick="setF('rojo',this)">Urgentes</button>
    <button class="fbtn" onclick="setF('amarillo',this)">Atencion</button>
    <button class="fbtn" onclick="setF('verde',this)">En tiempo</button>
    <input class="search" type="text" placeholder="Buscar causa..." oninput="buscar(this.value)">
  </div>
  <div class="tbl-wrap">
    <table>
      <thead><tr>
        <th onclick="sort('causa')">Causa / Expediente</th>
        <th onclick="sort('tipo')">Tipo</th>
        <th onclick="sort('fecha')">Vencimiento</th>
        <th>Estado</th>
        <th onclick="sort('dias')">Dias</th>
        <th>Responsable</th>
        <th></th>
      </tr></thead>
      <tbody id="tbody"></tbody>
    </table>
    <div class="empty" id="empty" style="display:none"><div class="empty-icon">📂</div><div>No hay plazos</div></div>
  </div>
</div>
<div class="overlay" id="overlay">
  <div class="modal">
    <div class="modal-title" id="modal-title">Nuevo Plazo</div>
    <div class="fgrid">
      <div class="fg full"><label class="flabel">Causa *</label><input class="finput" id="f-causa" placeholder="Ej: Garcia c/ Municipalidad"></div>
      <div class="fg"><label class="flabel">Expediente</label><input class="finput" id="f-exped" placeholder="Ej: 12.345/2026"></div>
      <div class="fg"><label class="flabel">Tipo</label>
        <select class="fselect" id="f-tipo">
          <option>Prorroga</option><option>Contestacion de demanda</option><option>Recurso</option>
          <option>Pericia</option><option>Audiencia</option><option>Presentacion</option><option>Otro</option>
        </select>
      </div>
      <div class="fg"><label class="flabel">Vencimiento *</label><input class="finput" id="f-fecha" type="date"></div>
      <div class="fg"><label class="flabel">Responsable</label><input class="finput" id="f-resp" placeholder="Ej: Dr. Rodriguez"></div>
      <div class="fg full"><label class="flabel">Notas</label><input class="finput" id="f-notas" placeholder="Observaciones..."></div>
    </div>
    <div class="mactions">
      <button class="btn btn-ghost" onclick="cerrarModal()">Cancelar</button>
      <button class="btn btn-primary" onclick="guardar()">Guardar</button>
    </div>
  </div>
</div>
<div class="toast" id="toast"></div>
<script>
let datos=[],filtro='todos',busq='',sortCol='dias',sortDir=1,editId=null;
async function cargar(){const r=await fetch('/api/plazos');datos=await r.json();render();}
function render(){
  let lista=[...datos];
  if(filtro!=='todos')lista=lista.filter(p=>p.semaforo===filtro);
  if(busq)lista=lista.filter(p=>(p.causa+p.expediente+p.responsable+p.tipo).toLowerCase().includes(busq.toLowerCase()));
  lista.sort((a,b)=>{let va=a[sortCol]??'',vb=b[sortCol]??'';return typeof va==='number'?(va-vb)*sortDir:va.localeCompare(vb)*sortDir;});
  document.getElementById('st-r').textContent=datos.filter(p=>p.semaforo==='rojo').length;
  document.getElementById('st-y').textContent=datos.filter(p=>p.semaforo==='amarillo').length;
  document.getElementById('st-g').textContent=datos.filter(p=>p.semaforo==='verde').length;
  document.getElementById('st-t').textContent=datos.length;
  const urg=datos.filter(p=>p.semaforo==='rojo');
  const banner=document.getElementById('banner');
  if(urg.length){document.getElementById('banner-txt').textContent=`${urg.length} plazo(s) vencen en 2 dias o menos: ${urg.map(p=>p.causa).join(' - ')}`;banner.classList.add('show');}
  else banner.classList.remove('show');
  document.getElementById('fecha-hoy').textContent=new Date().toLocaleDateString('es-AR',{weekday:'long',year:'numeric',month:'long',day:'numeric'});
  const tbody=document.getElementById('tbody'),empty=document.getElementById('empty');
  if(!lista.length){tbody.innerHTML='';empty.style.display='block';return;}
  empty.style.display='none';
  tbody.innerHTML=lista.map((p,i)=>{
    const dc=p.semaforo==='rojo'?'dot-red':p.semaforo==='amarillo'?'dot-yellow':'dot-green';
    const lc=p.semaforo==='rojo'?'days-red':p.semaforo==='amarillo'?'days-yellow':'days-green';
    const label=p.dias<0?'VENCIDO':p.dias===0?'HOY':`${p.dias}d`;
    const est=p.semaforo==='rojo'?'URGENTE':p.semaforo==='amarillo'?'ATENCION':'En tiempo';
    return `<tr style="animation-delay:${i*0.04}s">
      <td><div class="causa-n">${p.causa}</div><div class="exped">${p.expediente||'—'}</div></td>
      <td><span class="tipo-tag">${p.tipo||'—'}</span></td>
      <td style="color:var(--muted)">${p.fecha_fmt}</td>
      <td><div class="sem-cell"><div class="sem-dot ${dc}"></div><span style="font-size:12px;color:var(--muted)">${est}</span></div></td>
      <td><span class="${lc}">${label}</span></td>
      <td style="color:var(--muted);font-size:13px">${p.responsable||'—'}</td>
      <td><button class="abt" onclick="editar(${p.id})">✏️</button><button class="abt del" onclick="eliminar(${p.id},'${p.causa.replace(/'/g,"\\'")}')">🗑️</button></td>
    </tr>`;
  }).join('');
}
function setF(f,el){filtro=f;document.querySelectorAll('.fbtn').forEach(b=>b.classList.remove('active'));el.classList.add('active');render();}
function buscar(v){busq=v;render();}
function sort(col){sortDir=(sortCol===col)?-sortDir:1;sortCol=col;render();}
function abrirModal(id=null){
  editId=id;const p=id?datos.find(x=>x.id===id):null;
  document.getElementById('modal-title').textContent=id?'Editar Plazo':'Nuevo Plazo';
  document.getElementById('f-causa').value=p?.causa||'';
  document.getElementById('f-exped').value=p?.expediente||'';
  document.getElementById('f-tipo').value=p?.tipo||'Prorroga';
  document.getElementById('f-fecha').value=p?.fecha||'';
  document.getElementById('f-resp').value=p?.responsable||'';
  document.getElementById('f-notas').value=p?.notas||'';
  document.getElementById('overlay').classList.add('open');
}
function cerrarModal(){document.getElementById('overlay').classList.remove('open');editId=null;}
async function guardar(){
  const causa=document.getElementById('f-causa').value.trim(),fecha=document.getElementById('f-fecha').value;
  if(!causa||!fecha){toast('Causa y fecha son obligatorios','err');return;}
  const body={causa,expediente:document.getElementById('f-exped').value,tipo:document.getElementById('f-tipo').value,fecha,responsable:document.getElementById('f-resp').value,notas:document.getElementById('f-notas').value};
  if(editId){await fetch(`/api/plazos/${editId}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});toast('Actualizado','ok');}
  else{await fetch('/api/plazos',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});toast('Guardado','ok');}
  cerrarModal();cargar();
}
function editar(id){abrirModal(id);}
async function eliminar(id,causa){if(!confirm(`Eliminar "${causa}"?`))return;await fetch(`/api/plazos/${id}`,{method:'DELETE'});toast('Eliminado','ok');cargar();}
async function testEmail(){toast('Enviando prueba...','ok');await fetch('/api/test-email',{method:'POST'});}
function toast(msg,type){const el=document.getElementById('toast');el.textContent=msg;el.className=`toast ${type} show`;setTimeout(()=>el.classList.remove('show'),3000);}
document.getElementById('overlay').addEventListener('click',e=>{if(e.target===e.currentTarget)cerrarModal();});
cargar();setInterval(cargar,60000);
</script>
</body></html>"""

@app.route("/")
def index(): return render_template_string(HTML, hora=HORA_ALERTA)

if __name__ == "__main__":
    init_db()
    print("\n  LEX TRACKER — Listo!")
    print("  Abri en tu navegador: http://localhost:5000")
    print("  Ctrl+C para detener\n")
    threading.Thread(target=loop_alertas, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=False)
flask

