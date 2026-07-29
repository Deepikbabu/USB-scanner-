"""Security settings, service health, and protected resource overview."""
from pathlib import Path
from PyQt6.QtCore import QSettings, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QGridLayout, QHBoxLayout, QScrollArea, QVBoxLayout,
    QWidget,
)
from asset_pages import PageHeader, label
from theme import theme_manager
from widgets import AppButton, AppCard


class StatusRow(AppCard):
    def __init__(self,title,description="",parent=None):
        super().__init__(parent); layout=QHBoxLayout(self); layout.setContentsMargins(14,10,14,10)
        text=QVBoxLayout(); text.addWidget(label(title,size=11,weight=700))
        if description:text.addWidget(label(description,muted=True,size=9))
        layout.addLayout(text,1); self.lbl_val=label("UNKNOWN",muted=True,size=10,weight=800); layout.addWidget(self.lbl_val)
    def set_status(self,value,tone="neutral"):
        self.lbl_val.setText(str(value).upper()); token=tone if tone in theme_manager.colors else "text_secondary"
        self.lbl_val.setStyleSheet(f"color:{theme_manager.get_color(token)};font-size:10px;font-weight:800")


class ResourceRow(AppCard):
    def __init__(self,title,value,detail="",parent=None):
        super().__init__(parent); layout=QVBoxLayout(self); layout.setContentsMargins(13,9,13,9)
        head=QHBoxLayout(); head.addWidget(label(title,size=10,weight=700)); head.addStretch(); head.addWidget(label(value,size=10,weight=700)); layout.addLayout(head)
        if detail:
            desc=label(detail,muted=True,size=9); desc.setWordWrap(True); layout.addWidget(desc)


class SettingsPage(QWidget):
    recover_hid_requested=pyqtSignal()
    diagnostics_requested=pyqtSignal()
    trust_management_requested=pyqtSignal()
    dashboard_preferences_changed=pyqtSignal(bool,bool)
    quarantine_restore_requested=pyqtSignal(int)
    quarantine_delete_requested=pyqtSignal(int)
    def __init__(self,parent=None):
        super().__init__(parent); self.latest_report_path=None; self.trusted_dynamic=[]; self.quarantine_dynamic=[]; self._build_ui()
    def _build_ui(self):
        outer=QVBoxLayout(self); outer.setContentsMargins(2,0,2,2); outer.setSpacing(10)
        outer.addWidget(PageHeader("Settings and diagnostics","Scanner health, notifications, protected resources, and local appearance."))
        self.lbl_status=label("Waiting for backend status",muted=True,size=10); outer.addWidget(self.lbl_status)
        scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; border: none; }")
        content=QWidget(); content.setStyleSheet("background: transparent;")
        root=QVBoxLayout(content); root.setContentsMargins(0,0,6,0); root.setSpacing(12)
        root.addWidget(label("SCANNER HEALTH",muted=True,size=10,weight=800)); health=QGridLayout(); health.setSpacing(8); self.health_rows={}
        definitions=(("usbguard","USBGuard","Pre-driver device isolation"),("clamav","ClamAV","Antivirus signature engine"),
                     ("yara","YARA","Static malware rules"),("root","Enforcement privileges","Mount and device authorization"))
        for i,(key,title,desc) in enumerate(definitions):
            row=StatusRow(title,desc); self.health_rows[key]=row; health.addWidget(row,i//2,i%2)
        root.addLayout(health)
        diagnostics=AppCard(); diagnostics_layout=QHBoxLayout(diagnostics)
        diagnostics_text=QVBoxLayout()
        diagnostics_text.addWidget(label("System readiness check",size=11,weight=700))
        diagnostic_help=label(
            "Refresh engine health, trust stores, quarantine integrity, and report availability.",
            muted=True,size=9,
        )
        diagnostic_help.setWordWrap(True); diagnostics_text.addWidget(diagnostic_help)
        diagnostics_layout.addLayout(diagnostics_text,1)
        self.btn_diagnostics=AppButton("Run diagnostics","primary")
        self.btn_diagnostics.clicked.connect(self._request_diagnostics)
        diagnostics_layout.addWidget(self.btn_diagnostics); root.addWidget(diagnostics)
        root.addWidget(label("NOTIFICATIONS AND EVIDENCE",muted=True,size=10,weight=800)); notice=QGridLayout(); notice.setSpacing(8)
        self.email_status_row=StatusRow("Email delivery","Alerts for suspicious, dangerous, and incomplete incidents.")
        report_host=AppCard(); report_layout=QHBoxLayout(report_host)
        self.report_status_row=StatusRow("Latest report","Consolidated backend PDF/JSON evidence."); report_layout.addWidget(self.report_status_row,1)
        self.btn_open_report=AppButton("Open latest report"); self.btn_open_report.setEnabled(False); self.btn_open_report.clicked.connect(self.open_latest_report); report_layout.addWidget(self.btn_open_report)
        notice.addWidget(self.email_status_row,0,0); notice.addWidget(report_host,0,1); root.addLayout(notice)
        root.addWidget(label("TRUST MANAGEMENT",muted=True,size=10,weight=800)); trust_head=AppCard(); trust_layout=QHBoxLayout(trust_head)
        trust_text=QVBoxLayout(); self.lbl_trust_title=label("0 TRUSTED HID RECORDS",size=11,weight=800)
        self.lbl_hid_recovery=label("Hardware fingerprints are verified before authorization.",muted=True,size=9); self.lbl_hid_recovery.setWordWrap(True)
        trust_text.addWidget(self.lbl_trust_title); trust_text.addWidget(self.lbl_hid_recovery); trust_layout.addLayout(trust_text,1)
        self.btn_recover=AppButton("Verify and recover HID","primary"); self.btn_recover.clicked.connect(self.recover_hid_requested); trust_layout.addWidget(self.btn_recover); root.addWidget(trust_head)
        self.btn_manage_trust=AppButton("Open trust inventory")
        self.btn_manage_trust.clicked.connect(self.trust_management_requested)
        trust_layout.addWidget(self.btn_manage_trust)
        self.trusted_container=QWidget(); self.trusted_layout=QVBoxLayout(self.trusted_container); self.trusted_layout.setContentsMargins(0,0,0,0); self.trusted_layout.setSpacing(6); root.addWidget(self.trusted_container)
        root.addWidget(label("QUARANTINE RESOURCE",muted=True,size=10,weight=800)); qhead=AppCard(); qlayout=QVBoxLayout(qhead)
        self.lbl_quarantine_title=label("0 FILES IN QUARANTINE",size=11,weight=800); qlayout.addWidget(self.lbl_quarantine_title)
        qlayout.addWidget(label("Use the Quarantine page for integrity details, restore, and deletion.",muted=True,size=9)); root.addWidget(qhead)
        self.quarantine_container=QWidget(); self.quarantine_layout=QVBoxLayout(self.quarantine_container); self.quarantine_layout.setContentsMargins(0,0,0,0); self.quarantine_layout.setSpacing(6); root.addWidget(self.quarantine_container)
        root.addWidget(label("APPEARANCE",muted=True,size=10,weight=800)); appearance=AppCard(); alayout=QHBoxLayout(appearance)
        atext=QVBoxLayout(); atext.addWidget(label("Interface theme",size=11,weight=700)); atext.addWidget(label("Applied to every shared component.",muted=True,size=9)); alayout.addLayout(atext,1)
        self.btn_dark=AppButton("Dark","primary"); self.btn_light=AppButton("Light"); self.btn_dark.clicked.connect(lambda:theme_manager.set_theme("dark")); self.btn_light.clicked.connect(lambda:theme_manager.set_theme("light"))
        alayout.addWidget(self.btn_dark); alayout.addWidget(self.btn_light); root.addWidget(appearance)
        motion=AppCard(); mlayout=QHBoxLayout(motion)
        mtext=QVBoxLayout(); mtext.addWidget(label("Reduce interface motion",size=11,weight=700))
        mdesc=label("Disables page fades, sidebar transitions, and notification fades.",muted=True,size=9)
        mdesc.setWordWrap(True); mtext.addWidget(mdesc); mlayout.addLayout(mtext,1)
        self.chk_reduced_motion=QCheckBox("Reduced motion")
        self.chk_reduced_motion.setChecked(theme_manager.reduced_motion)
        self.chk_reduced_motion.setAccessibleName("Reduce interface animation")
        self.chk_reduced_motion.toggled.connect(theme_manager.set_reduced_motion)
        mlayout.addWidget(self.chk_reduced_motion); root.addWidget(motion)
        access=AppCard(); access_layout=QGridLayout(access)
        access_layout.addWidget(label("Accessibility and display",size=11,weight=700),0,0,1,2)
        self.chk_high_contrast=QCheckBox("High contrast")
        self.chk_high_contrast.setChecked(theme_manager.high_contrast)
        self.chk_high_contrast.toggled.connect(theme_manager.set_high_contrast)
        self.chk_touch=QCheckBox("Touchscreen controls")
        self.chk_touch.setChecked(theme_manager.touch_mode)
        self.chk_touch.toggled.connect(theme_manager.set_touch_mode)
        self.text_scale=QComboBox()
        self.text_scale.addItem("90% text",0.9); self.text_scale.addItem("100% text",1.0)
        self.text_scale.addItem("115% text",1.15); self.text_scale.addItem("130% text",1.3)
        closest=min(range(self.text_scale.count()),key=lambda i:abs(self.text_scale.itemData(i)-theme_manager.text_scale))
        self.text_scale.setCurrentIndex(closest)
        self.text_scale.currentIndexChanged.connect(
            lambda index:theme_manager.set_text_scale(self.text_scale.itemData(index))
        )
        access_layout.addWidget(self.chk_high_contrast,1,0)
        access_layout.addWidget(self.chk_touch,1,1)
        access_layout.addWidget(label("Interface text size",muted=True,size=9),2,0)
        access_layout.addWidget(self.text_scale,2,1)
        root.addWidget(access)
        dashboard=AppCard(); dashboard_layout=QVBoxLayout(dashboard)
        dashboard_layout.addWidget(label("Dashboard modules",size=11,weight=700))
        dashboard_help=label("Hide optional modules to prioritize the information your operators use.",muted=True,size=9)
        dashboard_help.setWordWrap(True); dashboard_layout.addWidget(dashboard_help)
        prefs=QSettings("BBBS","USB Security Scanner")
        self.chk_dashboard_risk=QCheckBox("Show risk trend")
        self.chk_dashboard_activity=QCheckBox("Show recent activity")
        self.chk_dashboard_risk.setChecked(str(prefs.value("dashboard/show_risk","true")).lower()=="true")
        self.chk_dashboard_activity.setChecked(str(prefs.value("dashboard/show_activity","true")).lower()=="true")
        self.chk_dashboard_risk.toggled.connect(self._emit_dashboard_preferences)
        self.chk_dashboard_activity.toggled.connect(self._emit_dashboard_preferences)
        dashboard_layout.addWidget(self.chk_dashboard_risk)
        dashboard_layout.addWidget(self.chk_dashboard_activity)
        root.addWidget(dashboard)
        root.addStretch(); scroll.setWidget(content); outer.addWidget(scroll,1)
    @staticmethod
    def _clear(layout,rows):
        for row in rows:layout.removeWidget(row); row.deleteLater()
        rows.clear()
    @staticmethod
    def _ready(value):
        return value is True or str(value).upper() in {"READY","ONLINE","OK","ACTIVE","TRUE","ENABLED"}
    def apply_backend_status(self,system_status,resources):
        status=dict(system_status or {}); aliases={"usbguard":("usbguard","USBGuard"),"clamav":("clamav","ClamAV"),"yara":("yara","YARA"),"root":("root","Linux")}; ready_count=0
        for key,names in aliases.items():
            value=next((status[name] for name in names if name in status),None); ready=self._ready(value); ready_count+=int(ready)
            self.health_rows[key].set_status("Ready" if ready else "Unavailable","success" if ready else "warning")
        self.lbl_status.setText(f"{ready_count}/4 scanner capabilities reported ready")
        self.btn_diagnostics.setEnabled(True)
        self.btn_diagnostics.setText("Run diagnostics")
        if resources:self.apply_backend_resources(resources)
    def apply_backend_resources(self,resources):
        resources=dict(resources or {}); trusted=resources.get("signed_trust") or resources.get("trusted_hid") or {}
        trusted_items=[{"identity":k,"record":v} for k,v in trusted.items()] if isinstance(trusted,dict) else list(trusted)
        self._clear(self.trusted_layout,self.trusted_dynamic)
        for item in trusted_items:
            record=item.get("record") if isinstance(item.get("record"),dict) else {}; identity=item.get("identity") or record.get("identity") or "Unknown identity"
            name=record.get("name") or record.get("product") or str(item.get("status") or "Trusted HID"); row=ResourceRow(str(name),"TRUSTED",str(identity))
            self.trusted_layout.addWidget(row); self.trusted_dynamic.append(row)
        self.lbl_trust_title.setText(f"{len(trusted_items)} TRUSTED HID RECORDS")
        quarantine=list(resources.get("quarantine") or []); self._clear(self.quarantine_layout,self.quarantine_dynamic)
        for item in quarantine[:5]:
            row=ResourceRow(str(item.get("original_name") or item.get("name") or "Unknown file"),"ISOLATED",str(item.get("reason") or item.get("threat_type") or "Security finding"))
            self.quarantine_layout.addWidget(row); self.quarantine_dynamic.append(row)
        count=len(quarantine); self.lbl_quarantine_title.setText(f"{count} {'FILE' if count==1 else 'FILES'} IN QUARANTINE")
        email=dict(resources.get("email_status") or {}); ready=bool(email.get("enabled") and email.get("ready")); self.email_status_row.set_status("Ready" if ready else "Disabled","success" if ready else "warning")
        reports=list(resources.get("reports") or []); latest=reports[0] if reports else {}; self.latest_report_path=latest.get("pdf_path") or latest.get("json_path")
        self.report_status_row.set_status("Available" if self.latest_report_path else "None","success" if self.latest_report_path else "neutral"); self.btn_open_report.setEnabled(bool(self.latest_report_path))
    def apply_resource_event(self,event,data):
        if event=="email_delivery_updated":
            status=str(data.get("status") or "UNKNOWN").upper(); self.email_status_row.set_status(status,"success" if status=="SENT" else "warning")
        elif event=="quarantine_updated":self.lbl_quarantine_title.setText("QUARANTINE UPDATED — REFRESHING")
        elif event=="trust_updated":self.lbl_hid_recovery.setText(str(data.get("reason") or "Trust records updated."))
    def open_latest_report(self):
        if self.latest_report_path and Path(self.latest_report_path).exists():QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(self.latest_report_path).resolve())))
    def start_update_check(self):self.lbl_status.setText("Backend capabilities are refreshed through the live connection.")
    def _request_diagnostics(self):
        self.btn_diagnostics.setEnabled(False)
        self.btn_diagnostics.setText("Checking…")
        self.lbl_status.setText("Running authoritative backend readiness check…")
        self.diagnostics_requested.emit()
    def _emit_dashboard_preferences(self):
        self.dashboard_preferences_changed.emit(
            self.chk_dashboard_risk.isChecked(),
            self.chk_dashboard_activity.isChecked(),
        )
    def update_styles(self):self.update()
