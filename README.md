# Thai Election Analytics Dashboard

Streamlit dashboard สำหรับวิเคราะห์ข้อมูลหน่วยเลือกตั้งจาก OCR, ตรวจ anomaly และดูคะแนน integrity ตามอำเภอ/ตำบล

โปรเจกต์นี้เป็น scaffold เริ่มต้นสำหรับทำ dashboard ต่อ โดยแต่ละแท็บมี placeholder `Coming soon` ให้ทีมพัฒนากราฟจริงต่อได้

## โครงสร้างโปรเจกต์

```text
Phatthalung-District2-Election-Visualization/
├── app.py
├── requirements.txt
├── data/
│   └── วางไฟล์ CSV ที่นี่
├── utils/
│   ├── __init__.py
│   └── loader.py
└── tabs/
    ├── __init__.py
    ├── tab_overview.py
    ├── tab_anomaly.py
    ├── tab_map.py
    ├── tab_heatmap.py
    ├── tab_station.py
    └── tab_votephase.py
```

## ไฟล์ข้อมูลที่ต้องมี

วางไฟล์ CSV ทั้งหมดไว้ในโฟลเดอร์ `data/`

```text
data/constituency_clean.csv
data/anomaly_summary.csv
data/subdistrict_summary.csv
data/phase_summary.csv
```

ถ้ายังไม่มีไฟล์ CSV แอปยังรันได้ แต่ข้อมูลใน dashboard จะว่าง เพราะ `utils/loader.py` เตรียม empty DataFrame ไว้ให้แล้ว

แนะนำให้ save CSV เป็น encoding แบบ `UTF-8` เพื่อรองรับภาษาไทย

## วิธีรันบน Windows PowerShell

เข้าโฟลเดอร์โปรเจกต์:

```powershell
cd "C:\Y3T2\DSDE\Final\Phatthalung-District2-Election-Visualization"
```

สร้าง virtual environment:

```powershell
python -m venv .venv
```

เปิดใช้งาน environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

ติดตั้ง dependencies:

```powershell
pip install -r requirements.txt
```

รันแอป:

```powershell
streamlit run app.py
```

จากนั้นเปิดเว็บ:

```text
http://localhost:8501
```

## ถ้า Activate.ps1 โดน Windows block

ถ้า PowerShell ขึ้น error ประมาณว่า running scripts is disabled ให้รันแบบไม่ต้อง activate:

```powershell
cd "C:\Y3T2\DSDE\Final\Phatthalung-District2-Election-Visualization"
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## ถ้า port 8501 ถูกใช้อยู่

ให้เปลี่ยน port เช่น:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8502
```

แล้วเปิด:

```text
http://localhost:8502
```

## คำสั่งหยุดแอป

กด `Ctrl + C` ใน terminal ที่รัน Streamlit อยู่

ถ้าเปิดใช้งาน virtual environment อยู่ และต้องการออก:

```powershell
deactivate
```

## Dependencies หลัก

โปรเจกต์ใช้ package ต่อไปนี้จาก `requirements.txt`

```text
streamlit
pandas
plotly
folium
streamlit-folium
numpy
```

## หมายเหตุสำหรับทีมพัฒนา

- จุดโหลดข้อมูลอยู่ที่ `utils/loader.py`
- หน้า dashboard หลักอยู่ที่ `app.py`
- แต่ละแท็บแยกอยู่ในโฟลเดอร์ `tabs/`
- ทุกแท็บมี `render(...)` function สำหรับให้ `app.py` เรียกใช้งาน
- ตอนนี้กราฟหลายส่วนยังเป็น stub พร้อม comment `# TODO:` สำหรับ implement ต่อ
- sidebar filter เลือก `district` แล้วส่ง DataFrame ที่กรองแล้วเข้าแต่ละแท็บ

## Troubleshooting

ถ้าขึ้น `No module named streamlit`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

ถ้าข้อมูลไม่ขึ้น:

- เช็คว่าไฟล์ CSV อยู่ใน `data/`
- เช็คชื่อไฟล์ให้ตรงกับที่กำหนด
- เช็คชื่อ columns ให้ตรงกับ data schema
- เช็คว่า CSV เป็น `UTF-8`

ถ้าเปิดเว็บแล้วหน้าว่าง:

- ดู error ใน terminal ที่รัน Streamlit
- กด refresh ที่ browser
- ลองหยุดด้วย `Ctrl + C` แล้วรันใหม่
