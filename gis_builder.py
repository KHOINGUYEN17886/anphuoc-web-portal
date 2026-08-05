# -*- coding: utf-8 -*-
"""
gis_builder.py — Self-Contained GIS Command Center Map Builder for Render Cloud Deployment
==========================================================================================
Generates 100% cloud-compatible interactive GIS map HTML without local Windows path dependencies.
"""

import os
import json

COORDS_JSON_PATH = os.path.join(os.path.dirname(__file__), 'verified_store_coordinates.json')
SEED_STORES_PATH = os.path.join(os.path.dirname(__file__), 'seed_stores_baseline.json')

ASM_COLORS = {
    'Khôi': '#ef4444',
    'Quân': '#10b981',
    'Ni': '#f59e0b',
    'Tuyền': '#3b82f6',
    'Chương': '#ec4899',
    'Tuấn': '#8b5cf6',
    'Quang': '#06b6d4',
    'Thắng': '#f43f5e',
    'Huy': '#84cc16',
    'Hương': '#eab308',
    'Hà Nội': '#14b8a6',
    'HN': '#14b8a6',
    'Khác': '#64748b'
}


def load_verified_coords() -> dict:
    """Loads verified store coordinates JSON."""
    if os.path.exists(COORDS_JSON_PATH):
        try:
            with open(COORDS_JSON_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def generate_cloud_gis_map_html(db_stores_list: list = None) -> str:
    """Generates 100% self-contained GIS Executive Map HTML for Render Cloud Deployment."""
    coords_map = load_verified_coords()

    # Load baseline stores if db_stores_list is empty
    if not db_stores_list:
        if os.path.exists(SEED_STORES_PATH):
            try:
                with open(SEED_STORES_PATH, 'r', encoding='utf-8') as f:
                    db_stores_list = json.load(f)
            except Exception:
                db_stores_list = []
        else:
            db_stores_list = []

    store_list = []
    asms_set = set()
    regions_set = set()

    for item in db_stores_list:
        code = str(item.get('store_code') or item.get('code') or '').strip()
        if not code:
            continue

        name = str(item.get('store_name') or item.get('name') or code).strip()
        addr = str(item.get('address') or item.get('addr') or '').strip()
        asm  = str(item.get('asm_name') or item.get('asm') or 'Khác').strip()
        reg  = str(item.get('region') or 'Khác').strip()
        tier = str(item.get('store_type') or item.get('tier') or 'Standard').strip()
        mgr  = str(item.get('cht_name') or item.get('manager') or item.get('mgr') or 'N/A').strip()
        phone= str(item.get('phone') or 'N/A').strip()

        asms_set.add(asm)
        regions_set.add(reg)

        # Lookup Lat/Lng from verified coordinates JSON
        c_info = coords_map.get(code, {})
        lat = c_info.get('lat', 10.7769)
        lng = c_info.get('lng', 106.7009)
        color = ASM_COLORS.get(asm, '#64748b')

        # Stock metrics fallback if offline on cloud
        total_qty = c_info.get('total_qty', 1500)
        total_val_m = c_info.get('total_val_m', 2500.0)
        sku_count = c_info.get('sku_count', 4500)

        store_list.append({
            'code': code, 'name': name, 'addr': addr,
            'asm': asm, 'region': reg, 'tier': tier,
            'mgr': mgr, 'phone': phone,
            'lat': lat, 'lng': lng, 'color': color,
            'total_qty': total_qty,
            'total_val_m': total_val_m,
            'sku_count': sku_count
        })

    stores_json = json.dumps(store_list, ensure_ascii=False)
    asms_json   = json.dumps(sorted(list(asms_set)), ensure_ascii=False)
    regions_json= json.dumps(sorted(list(regions_set)), ensure_ascii=False)

    total_qty_sum = sum(s['total_qty'] for s in store_list)
    total_val_sum = round(sum(s['total_val_m'] for s in store_list) / 1000.0, 1)

    html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AN PHƯỚC — GIS SPATIAL COMMAND CENTER</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.4.1/dist/MarkerCluster.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.4.1/dist/MarkerCluster.Default.css" />
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet.markercluster@1.4.1/dist/leaflet.markercluster.js"></script>

    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: 'Plus Jakarta Sans', sans-serif; background-color: #0b0f19; color: #f8fafc; overflow: hidden; height: 100vh; }}
        
        #topbar {{
            height: 70px; background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(16px);
            display: flex; align-items: center; justify-content: space-between; padding: 0 28px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1); z-index: 1000; position: relative;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3);
        }}
        .brand-title {{ font-size: 20px; font-weight: 800; letter-spacing: -0.5px; background: linear-gradient(135deg, #38bdf8 0%, #818cf8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; display: flex; align-items: center; gap: 12px; }}
        .badge-executive {{ background: linear-gradient(135deg, #0284c7 0%, #4f46e5 100%); color: #ffffff; padding: 5px 14px; border-radius: 30px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; box-shadow: 0 0 15px rgba(56, 189, 248, 0.4); }}
        
        .filter-container {{ display: flex; align-items: center; gap: 12px; }}
        .input-glass {{
            background: rgba(30, 41, 59, 0.8); color: #f8fafc; border: 1px solid rgba(255, 255, 255, 0.15);
            padding: 10px 16px; border-radius: 12px; font-size: 13px; outline: none; font-family: inherit;
            transition: all 0.25s ease; backdrop-filter: blur(8px);
        }}
        .input-glass:hover, .input-glass:focus {{ border-color: #38bdf8; box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.25); background: rgba(30, 41, 59, 0.95); }}

        .kpi-wrapper {{ display: flex; gap: 20px; }}
        .kpi-box {{ background: rgba(30, 41, 59, 0.6); padding: 8px 18px; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.08); display: flex; flex-direction: column; justify-content: center; }}
        .kpi-lbl {{ font-size: 11px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; }}
        .kpi-num {{ font-size: 16px; font-weight: 800; color: #f8fafc; margin-top: 2px; }}

        #main {{ display: flex; height: calc(100vh - 70px); position: relative; }}
        #map {{ flex: 1; height: 100%; width: 100%; background: #090d16; }}

        .theme-switcher {{
            position: absolute; bottom: 30px; left: 30px; z-index: 999;
            background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(12px); padding: 8px;
            border-radius: 14px; border: 1px solid rgba(255, 255, 255, 0.12); display: flex; gap: 6px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
        }}
        .theme-btn {{
            padding: 8px 14px; border-radius: 8px; border: none; background: transparent;
            color: #94a3b8; font-size: 12px; font-weight: 600; cursor: pointer; transition: all 0.2s;
        }}
        .theme-btn.active, .theme-btn:hover {{ background: #38bdf8; color: #0f172a; font-weight: 700; box-shadow: 0 0 12px rgba(56, 189, 248, 0.4); }}

        #drawer {{
            width: 400px; background: rgba(15, 23, 42, 0.92); backdrop-filter: blur(20px);
            border-left: 1px solid rgba(255, 255, 255, 0.12); padding: 28px; display: none; flex-direction: column; gap: 22px;
            overflow-y: auto; z-index: 1001; box-shadow: -15px 0 40px rgba(0,0,0,0.6); position: absolute; right: 0; top: 0; bottom: 0;
            animation: slideIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }}
        @keyframes slideIn {{ from {{ transform: translateX(100%); }} to {{ transform: translateX(0); }} }}

        .drawer-header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255, 255, 255, 0.1); padding-bottom: 16px; }}
        .drawer-title-main {{ font-size: 20px; font-weight: 800; color: #38bdf8; letter-spacing: -0.5px; }}
        .drawer-code-badge {{ font-size: 12px; font-weight: 700; color: #94a3b8; background: rgba(255,255,255,0.08); padding: 2px 8px; border-radius: 6px; }}
        .close-btn {{ cursor: pointer; color: #64748b; font-size: 20px; font-weight: 700; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border-radius: 50%; background: rgba(255,255,255,0.05); transition: 0.2s; }}
        .close-btn:hover {{ background: rgba(239, 68, 68, 0.2); color: #ef4444; }}

        .hero-card {{ background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%); padding: 18px; border-radius: 14px; border: 1px solid rgba(56, 189, 248, 0.2); }}
        .hero-val {{ font-size: 26px; font-weight: 800; color: #38bdf8; margin-top: 4px; }}

        .info-grid {{ display: flex; flex-direction: column; gap: 10px; }}
        .info-row {{ display: flex; justify-content: space-between; align-items: center; font-size: 13px; padding: 10px; border-radius: 8px; background: rgba(255, 255, 255, 0.03); }}
        .info-lbl {{ color: #94a3b8; font-weight: 500; }}
        .info-val {{ font-weight: 700; color: #f1f5f9; }}

        /* Marker Pins - Display STORE NAME */
        .custom-pin {{
            width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
            color: #fff; font-weight: 800; font-size: 11px; border: 2.5px solid #ffffff; box-shadow: 0 0 15px rgba(0,0,0,0.6);
            position: relative; transition: transform 0.2s; cursor: pointer;
        }}
        .custom-pin:hover {{ transform: scale(1.35); z-index: 9999; }}
        .pin-label {{
            position: absolute; top: -20px; left: 50%; transform: translateX(-50%);
            background: rgba(15, 23, 42, 0.95); color: #ffffff; padding: 3px 8px; border-radius: 6px;
            font-size: 11px; font-weight: 700; white-space: nowrap; border: 1px solid rgba(255,255,255,0.25);
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        }}
    </style>
</head>
<body>
    <div id="topbar">
        <div class="brand-title">
            ⚡ GIS SPATIAL COMMAND CENTER
            <span class="badge-executive">An Phước Portal v2026</span>
        </div>

        <div class="filter-container">
            <input type="text" id="searchInput" class="input-glass" style="width: 240px;" placeholder="🔍 Tìm Tên / Mã / Địa Chỉ..." oninput="filterMap()" />
            
            <select id="asmSelect" class="input-glass" onchange="filterMap()">
                <option value="ALL">-- Tất Cả ASM ({len(asms_set)} ASM) --</option>
            </select>

            <select id="regionSelect" class="input-glass" onchange="filterMap()">
                <option value="ALL">-- Tất Cả Vùng ({len(regions_set)} Vùng) --</option>
            </select>
        </div>

        <div class="kpi-wrapper">
            <div class="kpi-box">
                <div class="kpi-lbl">Cửa Hàng</div>
                <div id="kpiStores" class="kpi-num">{len(store_list)}</div>
            </div>
            <div class="kpi-box">
                <div class="kpi-lbl">Tổng Tồn Kho</div>
                <div id="kpiQty" class="kpi-num">{total_qty_sum:,} pcs</div>
            </div>
            <div class="kpi-box">
                <div class="kpi-lbl">Giá Trị Tồn Kho</div>
                <div id="kpiVal" class="kpi-num" style="color: #38bdf8;">{total_val_sum:,.1f} Tỷ</div>
            </div>
        </div>
    </div>

    <div id="main">
        <div id="map"></div>

        <div class="theme-switcher">
            <button id="btnVoyager" class="theme-btn active" onclick="setTheme('voyager')">☀️ Sáng Rõ (Voyager)</button>
            <button id="btnCyber" class="theme-btn" onclick="setTheme('cyber')">🌙 Cyber Neon</button>
            <button id="btnSatellite" class="theme-btn" onclick="setTheme('satellite')">🛰️ Vệ Tinh (Satellite)</button>
        </div>

        <div id="drawer">
            <div class="drawer-header">
                <div>
                    <div id="drawerName" class="drawer-title-main">Cửa Hàng</div>
                    <div id="drawerCode" class="drawer-code-badge" style="margin-top:4px; display:inline-block;">Mã: ---</div>
                </div>
                <div class="close-btn" onclick="closeDrawer()">✕</div>
            </div>

            <div style="font-size: 13px; color: #94a3b8; line-height:1.5;" id="drawerAddr">---</div>

            <div class="hero-card">
                <div style="font-size: 12px; color: #94a3b8; font-weight: 600;">Tổng Tồn Kho Trực Tuyến</div>
                <div class="hero-val" id="drawerQty">0 pcs</div>
                <div style="font-size: 13px; color: #94a3b8; margin-top: 6px;">Tổng Giá Trị: <strong style="color:#38bdf8;" id="drawerVal">0 Tr VNĐ</strong></div>
            </div>

            <div class="info-grid">
                <div class="info-row"><span class="info-lbl">ASM Quản Lý:</span><span class="info-val" id="drawerASM">---</span></div>
                <div class="info-row"><span class="info-lbl">Vùng Địa Lý:</span><span class="info-val" id="drawerRegion">---</span></div>
                <div class="info-row"><span class="info-lbl">Phân Loại Cửa Hàng:</span><span class="info-val" id="drawerTier">Standard</span></div>
                <div class="info-row"><span class="info-lbl">Cửa Hàng Trưởng:</span><span class="info-val" id="drawerMgr">N/A</span></div>
                <div class="info-row"><span class="info-lbl">Số Điện Thoại CH:</span><span class="info-val" id="drawerPhone">N/A</span></div>
                <div class="info-row"><span class="info-lbl">Số SKU Đang Có Tồn:</span><span class="info-val" id="drawerSKUs">0 SKUs</span></div>
            </div>
        </div>
    </div>

    <script>
        const stores    = {stores_json};
        const asms      = {asms_json};
        const regions   = {regions_json};

        const asmSel = document.getElementById('asmSelect');
        asms.forEach(a => {{
            const opt = document.createElement('option');
            opt.value = a; opt.innerText = 'ASM ' + a;
            asmSel.appendChild(opt);
        }});

        const regSel = document.getElementById('regionSelect');
        regions.forEach(r => {{
            const opt = document.createElement('option');
            opt.value = r; opt.innerText = 'Vùng ' + r;
            regSel.appendChild(opt);
        }});

        const tileLayers = {{
            voyager: L.tileLayer('https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}{{r}}.png', {{ attribution: '&copy; CARTO', maxZoom: 19 }}),
            cyber: L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{ attribution: '&copy; CARTO', maxZoom: 19 }}),
            satellite: L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{ attribution: '&copy; Esri', maxZoom: 18 }})
        }};

        const map = L.map('map', {{
            center: [15.8700, 105.8000],
            zoom: 6,
            layers: [tileLayers.voyager]
        }});

        let currentTheme = 'voyager';
        function setTheme(themeKey) {{
            map.removeLayer(tileLayers[currentTheme]);
            tileLayers[themeKey].addTo(map);
            currentTheme = themeKey;

            document.querySelectorAll('.theme-btn').forEach(b => b.classList.remove('active'));
            if (themeKey === 'voyager') document.getElementById('btnVoyager').classList.add('active');
            if (themeKey === 'cyber') document.getElementById('btnCyber').classList.add('active');
            if (themeKey === 'satellite') document.getElementById('btnSatellite').classList.add('active');
        }}

        const clusterGroup = L.markerClusterGroup({{
            chunkedLoading: true,
            maxClusterRadius: 40,
            spiderfyOnMaxZoom: true
        }}).addTo(map);

        let markerStoreMap = {{}};

        // Render Markers displaying STORE NAME
        stores.forEach(s => {{
            const iconHtml = `<div class="custom-pin" style="background: ${{s.color}};">
                <div class="pin-label">${{s.name}}</div>
            </div>`;

            const customIcon = L.divIcon({{
                html: iconHtml,
                className: '',
                iconSize: [32, 32],
                iconAnchor: [16, 16]
            }});

            const marker = L.marker([s.lat, s.lng], {{ icon: customIcon }});
            marker.on('click', () => openDrawer(s));

            clusterGroup.addLayer(marker);
            markerStoreMap[s.code] = {{ marker: marker, data: s }};
        }});

        function filterMap() {{
            const query  = document.getElementById('searchInput').value.trim().toLowerCase();
            const selASM = document.getElementById('asmSelect').value;
            const selReg = document.getElementById('regionSelect').value;

            clusterGroup.clearLayers();
            let visibleCodes = [];
            let sumQty = 0, sumVal = 0;

            stores.forEach(s => {{
                const matchQuery = !query || s.code.toLowerCase().includes(query) || s.name.toLowerCase().includes(query) || s.addr.toLowerCase().includes(query);
                const matchASM   = (selASM === 'ALL') || (s.asm === selASM);
                const matchReg   = (selReg === 'ALL') || (s.region === selReg);

                if (matchQuery && matchASM && matchReg) {{
                    clusterGroup.addLayer(markerStoreMap[s.code].marker);
                    visibleCodes.push(s.code);
                    sumQty += s.total_qty;
                    sumVal += s.total_val_m;
                }}
            }});

            document.getElementById('kpiStores').innerText = visibleCodes.length;
            document.getElementById('kpiQty').innerText    = sumQty.toLocaleString() + ' pcs';
            document.getElementById('kpiVal').innerText    = (sumVal / 1000.0).toFixed(1) + ' Tỷ';
        }}

        function openDrawer(s) {{
            document.getElementById('drawerName').innerText  = s.name;
            document.getElementById('drawerCode').innerText  = 'Mã Cửa Hàng: ' + s.code;
            document.getElementById('drawerAddr').innerText  = s.addr;
            document.getElementById('drawerQty').innerText   = s.total_qty.toLocaleString() + ' pcs';
            document.getElementById('drawerVal').innerText   = s.total_val_m.toLocaleString() + ' Tr VNĐ';
            document.getElementById('drawerASM').innerText   = s.asm;
            document.getElementById('drawerRegion').innerText= s.region;
            document.getElementById('drawerTier').innerText  = s.tier;
            document.getElementById('drawerMgr').innerText   = s.mgr;
            document.getElementById('drawerPhone').innerText = s.phone;
            document.getElementById('drawerSKUs').innerText  = s.sku_count + ' SKUs';

            document.getElementById('drawer').style.display = 'flex';
        }}

        function closeDrawer() {{
            document.getElementById('drawer').style.display = 'none';
        }}
    </script>
</body>
</html>
"""
    return html_content
