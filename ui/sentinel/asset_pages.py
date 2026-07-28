from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QTableWidget, QTableWidgetItem, QProgressBar, QLineEdit, QPushButton, QComboBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor

class MiniChart(QWidget):
    """Lightweight dependency-free live chart for Raspberry Pi deployments."""
    def __init__(self, parent=None):
        super().__init__(parent); self.values=[18,24,20,35,28,46,40,58,51,66]; self.setMinimumHeight(120)
    def set_values(self, values): self.values=list(values[-30:]) or [0]; self.update()
    def paintEvent(self, event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); r=self.rect().adjusted(8,8,-8,-12)
        p.setPen(QPen(QColor('#1F3A50'),1)); p.drawLine(r.left(),r.bottom(),r.right(),r.bottom()); p.drawLine(r.left(),r.top(),r.left(),r.bottom())
        if len(self.values)<2:return
        hi=max(self.values) or 1; step=r.width()/(len(self.values)-1); pts=[]
        for i,v in enumerate(self.values): pts.append((r.left()+i*step,r.bottom()-float(v)/hi*r.height()))
        p.setPen(QPen(QColor('#25B7F3'),2));
        for a,b in zip(pts,pts[1:]): p.drawLine(int(a[0]),int(a[1]),int(b[0]),int(b[1]))

class DataPage(QWidget):
    def __init__(self, title, subtitle):
        super().__init__(); self.rows = []
        lay = QVBoxLayout(self); lay.setContentsMargins(20,20,20,20); lay.setSpacing(14)
        h=QLabel(title); h.setStyleSheet('font-size:24px;font-weight:700;color:#F5F7FA'); lay.addWidget(h)
        s=QLabel(subtitle); s.setStyleSheet('color:#8FA4B8;font-size:13px'); lay.addWidget(s)
        self.kpis=QHBoxLayout(); lay.addLayout(self.kpis)
        self.search=QLineEdit(); self.search.setPlaceholderText('Search...'); self.search.textChanged.connect(self._filter); lay.addWidget(self.search)
        self.table=QTableWidget(0,5); self.table.setSortingEnabled(True); self.table.setAlternatingRowColors(True); self.table.setMinimumHeight(300)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setStyleSheet('QTableWidget{background:#0D1B2A;color:#E8F0F7;border:1px solid #1F3A50;gridline-color:#1F3A50} QHeaderView::section{background:#12283A;color:#8FD8FF;padding:8px;border:0}')
        lay.addWidget(self.table)
        controls=QHBoxLayout(); self.prev=QPushButton('Previous'); self.next=QPushButton('Next'); self.page_size=QComboBox(); self.page_size.addItems(['10','25','50']); self.page=QLabel('Page 1'); self.status=QLabel('No data available'); self.status.setStyleSheet('color:#8FA4B8'); controls.addWidget(self.status); controls.addStretch(); controls.addWidget(QLabel('Rows:')); controls.addWidget(self.page_size); controls.addWidget(self.prev); controls.addWidget(self.page); controls.addWidget(self.next); lay.addLayout(controls)
        self._all_rows=[]
        self._page_index=0; self.prev.clicked.connect(lambda: self._turn(-1)); self.next.clicked.connect(lambda: self._turn(1)); self.page_size.currentTextChanged.connect(lambda _: self._render_page())
        self.setMinimumWidth(520)
    def add_kpi(self,label,value,color='#25B7F3'):
        f=QFrame(); f.setStyleSheet('QFrame{background:#0D1B2A;border:1px solid #1F3A50;border-radius:8px}')
        l=QVBoxLayout(f); a=QLabel(label); a.setStyleSheet('color:#8FA4B8;font-size:12px'); b=QLabel(value); b.setStyleSheet(f'color:{color};font-size:24px;font-weight:700'); l.addWidget(a); l.addWidget(b); self.kpis.addWidget(f)
    def set_rows(self, rows, headers):
        self._all_rows=list(rows)
        self.table.setColumnCount(len(headers)); self.table.setHorizontalHeaderLabels(headers)
        self.table.resizeColumnsToContents()
        self._render_page()
    def _filter(self, text):
        q=text.lower().strip(); rows=[r for r in self._all_rows if not q or q in ' '.join(map(str,r)).lower()]
        headers=[self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
        self._all_rows=rows; self._page_index=0; self._render_page()
    def _render_page(self):
        rows=self._all_rows; size=int(self.page_size.currentText()); pages=max(1,(len(rows)+size-1)//size); self._page_index=max(0,min(self._page_index,pages-1)); visible=rows[self._page_index*size:(self._page_index+1)*size]
        self.table.setRowCount(len(visible))
        for r,row in enumerate(visible):
            for c,val in enumerate(row): self.table.setItem(r,c,QTableWidgetItem(str(val)))
        self.page.setText(f'Page {self._page_index+1}/{pages}'); self.prev.setEnabled(self._page_index>0); self.next.setEnabled(self._page_index<pages-1); self.status.setText(f'{len(rows)} records' if rows else 'No matching records')
    def _turn(self, direction): self._page_index += direction; self._render_page()

class DevicesPage(DataPage):
    def __init__(self):
        super().__init__('Devices','Detected and scanned USB devices with identity and verdict state')
        self.add_kpi('Devices scanned','0'); self.add_kpi('Connected now','0','#35D07F'); self.add_kpi('Blocked','0','#FF5C5C')
        self.chart=MiniChart(); self.layout().insertWidget(3,self.chart)
        self.set_rows([],['Device','Status','Verdict','Fingerprint','Last scan'])
    def apply_backend_device(self,d):
        self.set_rows([[d.get('name','Unknown'), 'Connected', d.get('verdict','Pending'), d.get('fingerprint','Unavailable'), d.get('last_scan','Live')]], ['Device','Status','Verdict','Fingerprint','Last scan'])

class QuarantinePage(DataPage):
    restore_requested=pyqtSignal(int); delete_requested=pyqtSignal(int); details_requested=pyqtSignal(int)
    def __init__(self):
        super().__init__('Quarantine','Isolated files and remediation actions')
        self.add_kpi('Quarantined files','0','#FFB020'); self.add_kpi('Storage used','0 B'); self.add_kpi('Integrity','Verified','#35D07F')
        self.chart=MiniChart(); self.layout().insertWidget(3,self.chart)
        self.set_rows([],['Filename','Threat type','Original path','Added','State'])
        self.empty=QPushButton('Empty quarantine'); self.empty.setStyleSheet('QPushButton{background:#7D2027;color:white;padding:8px;border-radius:6px}'); self.layout().insertWidget(4,self.empty)
        self.table.cellDoubleClicked.connect(lambda row,col: self.restore_requested.emit(row))
    def apply_backend_report(self,d):
        q=d.get('quarantine') or {}; items=q.get('items') or []; self.chart.set_values([max(1,len(items)-i*2) for i in range(10)])
        self.set_rows([[x.get('name','Unknown'),x.get('threat_type','Unknown'),x.get('original_path','-'),x.get('timestamp','-'),'Intact',''] for x in items],['Filename','Threat type','Original path','Added','State','Actions'])
        for row in range(self.table.rowCount()):
            box=QHBoxLayout(); host=QWidget(); box.setContentsMargins(2,0,2,0)
            b=QPushButton('Restore'); b.clicked.connect(lambda _,r=row:self.restore_requested.emit(r)); d=QPushButton('Delete'); d.clicked.connect(lambda _,r=row:self.delete_requested.emit(r)); v=QPushButton('View'); v.clicked.connect(lambda _,r=row:self.details_requested.emit(r))
            for x in (b,d,v): x.setStyleSheet('QPushButton{color:#25B7F3;background:#12283A;border:1px solid #25B7F3;padding:3px}') ; box.addWidget(x)
            host.setLayout(box); self.table.setCellWidget(row,5,host)

class DeviceDetailsPage(DataPage):
    def __init__(self):
        super().__init__('Device details','Identity, storage health, and threat telemetry for the selected USB device')
        self.add_kpi('Capacity','Unavailable'); self.add_kpi('Used','Unavailable'); self.add_kpi('Available','Unavailable','#35D07F'); self.add_kpi('Health','Unknown','#FFB020')
        self.set_rows([],['Property','Value','Property','Value','Status'])
    def apply_backend_device(self,d):
        fields=[('Manufacturer',d.get('manufacturer','Unknown')),('Vendor ID',d.get('vid','Unknown')),('Product ID',d.get('pid','Unknown')),('Serial number',d.get('serial','Missing')),('Filesystem',d.get('file_system','Unavailable')),('Mount point',d.get('mount_point','Unavailable')),('USB port',d.get('usb_port','Unavailable')),('Fingerprint',d.get('fingerprint','Unavailable'))]
        self.set_rows([[a,b,c,e,'Available'] for (a,b),(c,e) in zip(fields[::2],fields[1::2])],['Property','Value','Property','Value','Status'])
