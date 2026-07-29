from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QPoint

def setup_fade_in_animation(target_widget, duration=450):
    from theme import theme_manager
    from PyQt6.QtWidgets import QGraphicsOpacityEffect
    opacity_effect = QGraphicsOpacityEffect(target_widget)
    target_widget.setGraphicsEffect(opacity_effect)
    
    anim = QPropertyAnimation(opacity_effect, b"opacity")
    anim.setDuration(0 if theme_manager.reduced_motion else duration)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
    return anim, opacity_effect

def setup_slide_animation(target_widget, start_pos, end_pos, duration=500):
    from theme import theme_manager
    anim = QPropertyAnimation(target_widget, b"pos")
    anim.setDuration(0 if theme_manager.reduced_motion else duration)
    anim.setStartValue(start_pos)
    anim.setEndValue(end_pos)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    return anim
