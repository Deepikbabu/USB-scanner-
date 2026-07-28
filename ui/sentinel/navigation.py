"""Animated production sidebar with resolution-independent vector icons."""
import math
from PyQt6.QtCore import (
    QEasingCurve, QPointF, QParallelAnimationGroup, QPropertyAnimation,
    QRectF, Qt, pyqtSignal,
)
from PyQt6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
from theme import theme_manager


class NavIcon(QWidget):
    def __init__(self, name, parent=None):
        super().__init__(parent); self.name=name; self.active=False; self.setFixedSize(24,24)
    def set_active(self, active):
        self.active=active; self.update()
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color=theme_manager.get_qcolor("accent" if self.active else "text_secondary")
        p.setPen(QPen(color,1.7,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush); c=12
        if self.name=="dashboard":
            for x,y in ((4,4),(13,4),(4,13),(13,13)): p.drawRoundedRect(QRectF(x,y,7,7),1.5,1.5)
        elif self.name=="scan":
            p.drawEllipse(QRectF(4,4,13,13)); p.drawLine(QPointF(15.8,15.8),QPointF(21,21))
            p.drawLine(QPointF(8,10.5),QPointF(13,10.5))
        elif self.name=="devices":
            p.drawRoundedRect(QRectF(7,3,10,14),2,2); p.drawLine(10,7,14,7)
            p.drawLine(12,17,12,21); p.drawLine(9,21,15,21)
        elif self.name=="quarantine":
            path=QPainterPath(); path.moveTo(12,3); path.lineTo(19,6); path.lineTo(18,14)
            path.cubicTo(17,18,12,21,12,21); path.cubicTo(12,21,7,18,6,14); path.lineTo(5,6); path.closeSubpath()
            p.drawPath(path); p.drawLine(9,11,15,11); p.drawLine(12,8,12,14)
        elif self.name=="history":
            p.drawArc(QRectF(4,4,16,16),-45*16,300*16); p.drawLine(12,7,12,12); p.drawLine(12,12,16,14)
            path=QPainterPath(); path.moveTo(4,5); path.lineTo(4,10); path.lineTo(9,7); p.drawPath(path)
        elif self.name=="settings":
            p.drawEllipse(QRectF(8,8,8,8))
            for i in range(8):
                a=i*math.pi/4; p.drawLine(QPointF(c+5*math.cos(a),c+5*math.sin(a)),QPointF(c+9*math.cos(a),c+9*math.sin(a)))


class NavButton(QPushButton):
    def __init__(self,label,icon_name,page_index,parent=None):
        super().__init__(parent); self.page_index=page_index; self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor); self.setToolTip(label); self.setProperty("nav",True)
        layout=QHBoxLayout(self); layout.setContentsMargins(14,0,12,0); layout.setSpacing(12)
        self.icon=NavIcon(icon_name,self); self.text_label=QLabel(label); self.text_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self.icon); layout.addWidget(self.text_label); layout.addStretch()
        self.toggled.connect(self.icon.set_active)
    def set_collapsed(self,collapsed):
        self.text_label.setVisible(not collapsed)


class BottomNavigationBar(QFrame):
    """Compatibility name retained while the implementation is a sidebar."""
    tab_changed=pyqtSignal(int); page_changed=tab_changed
    EXPANDED_WIDTH=204; COLLAPSED_WIDTH=68
    def __init__(self,parent=None):
        super().__init__(parent); self.setObjectName("sideNavigation"); self._collapsed=False
        self.setMinimumWidth(self.EXPANDED_WIDTH); self.setMaximumWidth(self.EXPANDED_WIDTH)
        layout=QVBoxLayout(self); layout.setContentsMargins(10,18,10,14); layout.setSpacing(5)
        self.brand=QLabel("USB  SECURITY"); self.brand.setObjectName("brandLabel"); layout.addWidget(self.brand)
        self.brand_sub=QLabel("SCANNER  CONSOLE"); self.brand_sub.setObjectName("brandSubLabel"); layout.addWidget(self.brand_sub); layout.addSpacing(22)
        items=(("Dashboard","dashboard",0),("Live Scan","scan",1),("Devices","devices",2),("Quarantine","quarantine",3),("History","history",4),("Settings","settings",6))
        self.buttons=[]
        for text,icon,index in items:
            button=NavButton(text,icon,index,self); button.clicked.connect(lambda checked=False,value=index:self.set_active_tab(value))
            self.buttons.append(button); layout.addWidget(button)
        layout.addStretch()
        self.security_state=QLabel("●  PROTECTED"); self.security_state.setObjectName("securityState"); layout.addWidget(self.security_state)
        self.version=QLabel("Sentinel Engine  •  v1"); self.version.setObjectName("navFooter"); layout.addWidget(self.version)
        self._animation=QParallelAnimationGroup(self); self.set_active_tab(0,emit=False); self._apply_theme(); theme_manager.theme_changed.connect(self._apply_theme)
    @property
    def collapsed(self): return self._collapsed
    def toggle_collapsed(self):
        self._collapsed=not self._collapsed; start=self.width(); end=self.COLLAPSED_WIDTH if self._collapsed else self.EXPANDED_WIDTH
        self._animation.stop(); self._animation=QParallelAnimationGroup(self)
        for prop in (b"minimumWidth",b"maximumWidth"):
            anim=QPropertyAnimation(self,prop,self); anim.setDuration(260); anim.setStartValue(start); anim.setEndValue(end); anim.setEasingCurve(QEasingCurve.Type.OutCubic); self._animation.addAnimation(anim)
        self.brand.setText("US" if self._collapsed else "USB  SECURITY")
        self.brand_sub.setVisible(not self._collapsed); self.security_state.setText("●" if self._collapsed else "●  PROTECTED")
        self.version.setVisible(not self._collapsed)
        for button in self.buttons: button.set_collapsed(self._collapsed)
        self._animation.start()
    def handle_click(self,index): self.set_active_tab(index)
    def set_active_tab(self,page_index,emit=True):
        for button in self.buttons: button.setChecked(button.page_index==page_index)
        if emit:self.tab_changed.emit(page_index)
    def _apply_theme(self):
        c=theme_manager.colors
        self.setStyleSheet(f"""
        QFrame#sideNavigation{{background:{c['surface']};border:0;border-right:1px solid {c['border']};}}
        QLabel#brandLabel{{color:{c['text_primary']};font-size:13px;font-weight:800;letter-spacing:1px;padding-left:7px;}}
        QLabel#brandSubLabel{{color:{c['accent']};font-size:8px;font-weight:800;letter-spacing:2px;padding-left:7px;}}
        QLabel#securityState{{color:{c['success']};font-size:9px;font-weight:800;padding:8px;}}
        QLabel#navFooter{{color:{c['text_muted']};font-size:8px;padding-left:8px;}}
        QPushButton[nav="true"]{{min-height:44px;text-align:left;color:{c['text_secondary']};background:transparent;border:1px solid transparent;border-radius:8px;font-weight:600;}}
        QPushButton[nav="true"] QLabel{{color:{c['text_secondary']};background:transparent;font-size:11px;font-weight:600;}}
        QPushButton[nav="true"]:hover{{background:{c['surface_hover']};}}
        QPushButton[nav="true"]:checked{{background:{c['accent_soft']};border-color:{c['accent']};}}
        QPushButton[nav="true"]:checked QLabel{{color:{c['text_primary']};font-weight:700;}}
        """)
