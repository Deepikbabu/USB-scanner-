"""Persisted incident history and security analytics."""
import csv
from collections import Counter
from pathlib import Path
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QPainter, QPen
from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QLineEdit, QComboBox, QTableWidgetItem, QVBoxLayout, QWidget
from theme import theme_manager
from widgets import AppButton, AppCard, AppTableWidget, EmptyState
from asset_pages import KpiCard, PageHeader, label


class HistoryChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self.values=[]; self.setMinimumHeight(130)
    def set_values(self, values):
        self.values=list(values[-14:]); self.update()
    def paintEvent(self, event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r=self.rect().adjusted(12,12,-12,-18); p.setPen(QPen(theme_manager.get_qcolor("border"),1))
        for step in range(4):
            y=int(r.top()+r.height()*step/3); p.drawLine(r.left(),y,r.right(),y)
        if not self.values: return
        high=max(max(self.values),1); gap=r.width()/max(len(self.values),1); width=max(5,int(gap*.55))
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(theme_manager.get_qcolor("accent"))
        for index,value in enumerate(self.values):
            height=r.height()*float(value)/high; x=r.left()+index*gap+(gap-width)/2
            p.drawRoundedRect(int(x),int(r.bottom()-height),width,int(height),3,3)


class HistoryPage(QWidget):
    HEADERS=("Timestamp","Device","Final verdict","State","Risk","Incident ID","Report")
    def __init__(self,parent=None):
        super().__init__(parent); self._incidents=[]; self._visible=[]; self._reports={}; self._build_ui()
    def _build_ui(self):
        root=QVBoxLayout(self); root.setContentsMargins(2,0,2,2); root.setSpacing(11)
        root.addWidget(PageHeader("Incident history","Persisted USB decisions, final verdicts, risk, and consolidated evidence."))
        metrics=QHBoxLayout(); metrics.setSpacing(10)
        self.kpi_scans=KpiCard("TOTAL INCIDENTS"); self.kpi_threats=KpiCard("THREAT INCIDENTS",tone="danger")
        self.kpi_clean=KpiCard("CLEAN / TRUSTED",tone="success"); self.kpi_incomplete=KpiCard("INCOMPLETE",tone="warning")
        for card in (self.kpi_scans,self.kpi_threats,self.kpi_clean,self.kpi_incomplete): metrics.addWidget(card)
        root.addLayout(metrics)
        chart_card=AppCard(); chart_layout=QVBoxLayout(chart_card); chart_layout.setContentsMargins(16,12,16,10)
        head=QHBoxLayout(); head.addWidget(label("INCIDENT RISK OVER TIME",muted=True,size=10,weight=800)); head.addStretch()
        self.verdict_breakdown=label("No persisted incidents",muted=True,size=9); head.addWidget(self.verdict_breakdown)
        chart_layout.addLayout(head); self.chart=HistoryChart(); chart_layout.addWidget(self.chart); root.addWidget(chart_card)
        controls=QHBoxLayout(); self.search=QLineEdit(); self.search.setPlaceholderText("Search incident, device, verdict or state…")
        self.search.textChanged.connect(self._apply_filters); controls.addWidget(self.search,1)
        self.verdict_filter=QComboBox(); self.verdict_filter.addItems(("All verdicts","CLEAN","TRUSTED","SUSPICIOUS","DANGEROUS","INCOMPLETE"))
        self.verdict_filter.currentTextChanged.connect(self._apply_filters); controls.addWidget(self.verdict_filter)
        self.btn_export=AppButton("Export filtered CSV"); self.btn_export.clicked.connect(self.export_csv); controls.addWidget(self.btn_export); root.addLayout(controls)
        self.table=AppTableWidget(0,len(self.HEADERS)); self.table.setHorizontalHeaderLabels(self.HEADERS); self.table.setSortingEnabled(True)
        self.table.cellDoubleClicked.connect(self._open_row_report); root.addWidget(self.table,1)
        self.empty_state=EmptyState("No incident history","Completed backend incidents will appear after evidence is persisted.","◷"); root.addWidget(self.empty_state)
        self.lbl_status=label("0 incidents",muted=True,size=10); root.addWidget(self.lbl_status); self._render()
    @staticmethod
    def _normalize(incident):
        raw=dict(incident or {}); device=raw.get("device")
        name=(device.get("name") or device.get("product") or device.get("serial")) if isinstance(device,dict) else device
        return {**raw,"incident_id":str(raw.get("incident_id") or "Unavailable"),"device_name":str(name or raw.get("device_name") or "Unknown USB device"),
                "verdict":str(raw.get("verdict") or "INCOMPLETE").upper(),"state":str(raw.get("state") or "COMPLETED").upper(),
                "risk":int(raw.get("risk",raw.get("risk_score",0)) or 0),"updated":str(raw.get("updated") or raw.get("timestamp") or "Unknown")}
    def add_log_entry(self,device,timestamp,status):
        data=dict(device or {}) if isinstance(device,dict) else {"name":str(device)}
        self._incidents.insert(0,self._normalize({"incident_id":data.get("incident_id") or f"live-{timestamp}","device":data,
            "updated":timestamp,"state":"COMPLETED","verdict":status,"risk":data.get("risk",0)})); self._apply_filters()
    def apply_backend_incidents(self,incidents):
        self._incidents=[self._normalize(item) for item in incidents or []]; self._apply_filters()
    def apply_backend_resources(self,resources):
        self._reports={str(r.get("incident_id")):dict(r) for r in (resources.get("reports",[]) if isinstance(resources,dict) else [])}
        # Evidence reports carry the complete device identity and final metrics;
        # merge them over the intentionally small incident database projection.
        by_id={item["incident_id"]:item for item in self._incidents}
        for incident_id,report in self._reports.items():
            device=report.get("device") if isinstance(report.get("device"),dict) else {}
            enriched=self._normalize({
                **by_id.get(incident_id,{}), **report,
                "incident_id":incident_id,
                "device":device or by_id.get(incident_id,{}).get("device_name"),
                "updated":report.get("timestamp") or by_id.get(incident_id,{}).get("updated"),
            })
            by_id[incident_id]=enriched
        self._incidents=list(by_id.values()); self._apply_filters()
    def _apply_filters(self,*_):
        query=self.search.text().strip().casefold(); verdict=self.verdict_filter.currentText()
        self._visible=[item for item in self._incidents if (not query or query in " ".join(str(v) for v in item.values()).casefold())
                       and (verdict=="All verdicts" or item["verdict"]==verdict)]; self._render()
    def _render(self):
        rows=self._visible; self.table.setSortingEnabled(False); self.table.setRowCount(len(rows))
        for row,item in enumerate(rows):
            report=self._reports.get(item["incident_id"],{}); report_state="Available" if report.get("pdf_path") or report.get("json_path") else "Unavailable"
            for col,value in enumerate((item["updated"],item["device_name"],item["verdict"],item["state"],f"{item['risk']}/100",item["incident_id"],report_state)):
                cell=QTableWidgetItem(str(value)); cell.setData(Qt.ItemDataRole.UserRole,item["incident_id"]); self.table.setItem(row,col,cell)
        self.table.setSortingEnabled(True); self.table.resizeColumnsToContents(); self.table.setVisible(bool(rows)); self.empty_state.setVisible(not rows)
        counts=Counter(i["verdict"] for i in self._incidents); threats=counts["DANGEROUS"]+counts["SUSPICIOUS"]; safe=counts["CLEAN"]+counts["TRUSTED"]
        self.kpi_scans.value.setText(str(len(self._incidents))); self.kpi_threats.value.setText(str(threats)); self.kpi_clean.value.setText(str(safe)); self.kpi_incomplete.value.setText(str(counts["INCOMPLETE"]))
        self.chart.set_values([i["risk"] for i in reversed(self._incidents)])
        self.verdict_breakdown.setText(f"Safe {safe}  •  Threat {threats}  •  Incomplete {counts['INCOMPLETE']}")
        self.lbl_status.setText(f"{len(rows)} of {len(self._incidents)} incidents"); self.btn_export.setEnabled(bool(rows))
    def export_csv(self):
        if not self._visible:return
        path,_=QFileDialog.getSaveFileName(self,"Export filtered incident history","usb-scan-history.csv","CSV files (*.csv)")
        if not path:return
        with Path(path).open("w",encoding="utf-8",newline="") as stream:
            writer=csv.writer(stream); writer.writerow(self.HEADERS[:-1])
            for i in self._visible: writer.writerow((i["updated"],i["device_name"],i["verdict"],i["state"],i["risk"],i["incident_id"]))
    def _open_row_report(self,row,column):
        cell=self.table.item(row,0)
        if cell:self.view_report(str(cell.data(Qt.ItemDataRole.UserRole)))
    def view_report(self,incident_id):
        report=self._reports.get(str(incident_id),{}); path=report.get("pdf_path") or report.get("json_path")
        if path and Path(path).exists():QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(path).resolve())))
    def view_latest_report(self):
        if self._incidents:self.view_report(self._incidents[0]["incident_id"])
    def update_styles(self):self.update()
