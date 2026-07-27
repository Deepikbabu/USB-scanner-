from PyQt6.QtGui import QPixmap, QPainter
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtSvg import QSvgRenderer

# Premium Liquid Glass SVG Templates
# These use dynamic variables to integrate seamlessly with the ThemeManager
SVG_TEMPLATES = {
    "dashboard": """
    <svg width="64" height="64" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="glassGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="{accent}" stop-opacity="{glass_op1}" />
                <stop offset="100%" stop-color="{accent}" stop-opacity="{glass_op2}" />
            </linearGradient>
            <linearGradient id="strokeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="{primary}" stop-opacity="0.9" />
                <stop offset="100%" stop-color="{primary}" stop-opacity="0.3" />
            </linearGradient>
            <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
        </defs>
        <!-- Background Glass Elements -->
        <rect x="12" y="12" width="16" height="16" rx="6" fill="url(#glassGrad)" stroke="url(#strokeGrad)" stroke-width="2" filter="{glow_filter}"/>
        <rect x="36" y="12" width="16" height="16" rx="6" fill="url(#glassGrad)" stroke="url(#strokeGrad)" stroke-width="2" filter="{glow_filter}"/>
        <rect x="12" y="36" width="16" height="16" rx="6" fill="url(#glassGrad)" stroke="url(#strokeGrad)" stroke-width="2" filter="{glow_filter}"/>
        <rect x="36" y="36" width="16" height="16" rx="6" fill="url(#glassGrad)" stroke="url(#strokeGrad)" stroke-width="2" filter="{glow_filter}"/>
        
        <!-- Glossy Reflection -->
        <path d="M12 18 Q 20 12 28 12 L 12 28 Z" fill="#FFFFFF" opacity="{reflect_op}" />
        <path d="M36 18 Q 44 12 52 12 L 36 28 Z" fill="#FFFFFF" opacity="{reflect_op}" />
    </svg>
    """,
    "scan": """
    <svg width="64" height="64" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="glassGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="{accent}" stop-opacity="{glass_op1}" />
                <stop offset="100%" stop-color="{accent}" stop-opacity="{glass_op2}" />
            </linearGradient>
            <linearGradient id="strokeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="{primary}" stop-opacity="0.9" />
                <stop offset="100%" stop-color="{primary}" stop-opacity="0.3" />
            </linearGradient>
            <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
        </defs>
        <circle cx="28" cy="28" r="16" fill="url(#glassGrad)" stroke="url(#strokeGrad)" stroke-width="3" filter="{glow_filter}"/>
        <!-- Scanner handle -->
        <line x1="40" y1="40" x2="52" y2="52" stroke="url(#strokeGrad)" stroke-width="4" stroke-linecap="round" filter="{glow_filter}"/>
        
        <!-- Laser line -->
        <path d="M16 28 L 40 28" stroke="{accent}" stroke-width="2" opacity="0.8"/>
        <!-- Glossy Reflection -->
        <path d="M16 22 A 16 16 0 0 1 34 16 A 16 16 0 0 0 16 34 Z" fill="#FFFFFF" opacity="{reflect_op}" />
    </svg>
    """,
    "history": """
    <svg width="64" height="64" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="glassGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="{accent}" stop-opacity="{glass_op1}" />
                <stop offset="100%" stop-color="{accent}" stop-opacity="{glass_op2}" />
            </linearGradient>
            <linearGradient id="strokeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="{primary}" stop-opacity="0.9" />
                <stop offset="100%" stop-color="{primary}" stop-opacity="0.3" />
            </linearGradient>
            <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
        </defs>
        <!-- Clock Face -->
        <circle cx="32" cy="32" r="20" fill="url(#glassGrad)" stroke="url(#strokeGrad)" stroke-width="2.5" filter="{glow_filter}"/>
        <!-- Clock Hands -->
        <polyline points="32,20 32,32 40,38" fill="none" stroke="url(#strokeGrad)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" filter="{glow_filter}"/>
        
        <!-- Arc element -->
        <path d="M 20 16 A 24 24 0 0 1 44 16" fill="none" stroke="{accent}" stroke-width="2" stroke-linecap="round" opacity="0.6" filter="{glow_filter}"/>
        <polygon points="41,13 46,15 44,20" fill="{accent}" opacity="0.6" />
        
        <!-- Glossy Reflection -->
        <path d="M16 24 A 20 20 0 0 1 40 14 A 20 20 0 0 0 16 38 Z" fill="#FFFFFF" opacity="{reflect_op}" />
    </svg>
    """,
    "settings": """
    <svg width="64" height="64" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="glassGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="{accent}" stop-opacity="{glass_op1}" />
                <stop offset="100%" stop-color="{accent}" stop-opacity="{glass_op2}" />
            </linearGradient>
            <linearGradient id="strokeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="{primary}" stop-opacity="0.9" />
                <stop offset="100%" stop-color="{primary}" stop-opacity="0.3" />
            </linearGradient>
            <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
        </defs>
        <!-- Gear body -->
        <path d="M32 20 A 12 12 0 1 0 32 44 A 12 12 0 1 0 32 20 Z" fill="url(#glassGrad)" stroke="url(#strokeGrad)" stroke-width="2.5" filter="{glow_filter}"/>
        <path d="M30 14 L34 14 L35 18 L29 18 Z" fill="url(#strokeGrad)" opacity="0.8"/>
        <path d="M30 50 L34 50 L35 46 L29 46 Z" fill="url(#strokeGrad)" opacity="0.8"/>
        <path d="M14 30 L14 34 L18 35 L18 29 Z" fill="url(#strokeGrad)" opacity="0.8"/>
        <path d="M50 30 L50 34 L46 35 L46 29 Z" fill="url(#strokeGrad)" opacity="0.8"/>
        <path d="M20 20 L23 23 L25 19 L19 17 Z" fill="url(#strokeGrad)" opacity="0.8"/>
        <path d="M44 44 L41 41 L39 45 L45 47 Z" fill="url(#strokeGrad)" opacity="0.8"/>
        <path d="M44 20 L41 23 L39 19 L45 17 Z" fill="url(#strokeGrad)" opacity="0.8"/>
        <path d="M20 44 L23 41 L25 45 L19 47 Z" fill="url(#strokeGrad)" opacity="0.8"/>
        <circle cx="32" cy="32" r="5" fill="{bg}" stroke="url(#strokeGrad)" stroke-width="2" />
        <path d="M24 24 A 12 12 0 0 1 36 22 A 12 12 0 0 0 22 36 Z" fill="#FFFFFF" opacity="{reflect_op}" />
    </svg>
    """,
    "usb": """
    <svg width="64" height="64" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
        <path d="M32 12 L32 48" stroke="{primary}" stroke-width="2" stroke-linecap="round" fill="none"/>
        <path d="M32 32 L22 22 L22 18" stroke="{primary}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        <path d="M32 32 L42 22 L42 18" stroke="{primary}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        <polygon points="32,8 36,16 28,16" fill="none" stroke="{primary}" stroke-width="2" stroke-linejoin="round"/>
        <circle cx="22" cy="16" r="2.5" fill="none" stroke="{accent}" stroke-width="2"/>
        <rect x="40" y="14" width="4" height="4" rx="0.5" fill="none" stroke="{accent}" stroke-width="2"/>
        <circle cx="32" cy="50" r="3.5" fill="none" stroke="{accent}" stroke-width="2"/>
    </svg>
    """,
    "pendrive": """
    <svg width="64" height="64" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
        <rect x="24" y="24" width="16" height="26" rx="3" fill="none" stroke="{primary}" stroke-width="2"/>
        <rect x="27" y="14" width="10" height="10" rx="1" fill="none" stroke="{primary}" stroke-width="2"/>
        <rect x="30" y="17" width="1.5" height="4" rx="0.5" fill="{accent}"/>
        <rect x="33" y="17" width="1.5" height="4" rx="0.5" fill="{accent}"/>
        <line x1="27" y1="30" x2="37" y2="30" stroke="{accent}" stroke-width="1.5" stroke-linecap="round"/>
    </svg>
    """,
    "type-c": """
    <svg width="64" height="64" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
        <rect x="24" y="20" width="16" height="10" rx="5" fill="none" stroke="{primary}" stroke-width="2"/>
        <rect x="22" y="32" width="20" height="16" rx="3" fill="none" stroke="{primary}" stroke-width="2"/>
        <line x1="32" y1="48" x2="32" y2="54" stroke="{primary}" stroke-width="2" stroke-linecap="round"/>
        <circle cx="29" cy="25" r="1" fill="{accent}"/>
        <circle cx="35" cy="25" r="1" fill="{accent}"/>
    </svg>
    """,
    "hdmi": """
    <svg width="64" height="64" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
        <polygon points="20,18 44,18 48,28 48,46 16,46 16,28" fill="none" stroke="{primary}" stroke-width="2" stroke-linejoin="round"/>
        <line x1="24" y1="26" x2="24" y2="36" stroke="{accent}" stroke-width="1.5" stroke-linecap="round"/>
        <line x1="30" y1="26" x2="30" y2="36" stroke="{primary}" stroke-width="1.5" stroke-linecap="round"/>
        <line x1="34" y1="26" x2="34" y2="36" stroke="{primary}" stroke-width="1.5" stroke-linecap="round"/>
        <line x1="40" y1="26" x2="40" y2="36" stroke="{accent}" stroke-width="1.5" stroke-linecap="round"/>
    </svg>
    """,
    "jack": """
    <svg width="64" height="64" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
        <rect x="29" y="30" width="6" height="22" rx="2" fill="none" stroke="{primary}" stroke-width="2"/>
        <rect x="30" y="14" width="4" height="16" rx="1" fill="none" stroke="{primary}" stroke-width="2"/>
        <path d="M30 14 L32 10 L34 14" fill="none" stroke="{accent}" stroke-width="2" stroke-linejoin="round"/>
        <line x1="28" y1="22" x2="36" y2="22" stroke="{accent}" stroke-width="1.5" stroke-linecap="round"/>
        <line x1="28" y1="26" x2="36" y2="26" stroke="{primary}" stroke-width="1.5" stroke-linecap="round"/>
    </svg>
    """,
    "mouse": """
    <svg width="64" height="64" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
        <rect x="22" y="14" width="20" height="36" rx="10" fill="none" stroke="{primary}" stroke-width="2"/>
        <line x1="32" y1="14" x2="32" y2="28" stroke="{primary}" stroke-width="1.5"/>
        <rect x="31" y="18" width="2" height="6" rx="1" fill="{accent}"/>
    </svg>
    """,
    "keyboard": """
    <svg width="64" height="64" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
        <rect x="10" y="20" width="44" height="24" rx="4" fill="none" stroke="{primary}" stroke-width="2"/>
        <rect x="14" y="24" width="4" height="4" rx="1" fill="{accent}"/>
        <rect x="22" y="24" width="4" height="4" rx="1" fill="none" stroke="{primary}" stroke-width="1.5"/>
        <rect x="30" y="24" width="4" height="4" rx="1" fill="none" stroke="{primary}" stroke-width="1.5"/>
        <rect x="38" y="24" width="4" height="4" rx="1" fill="none" stroke="{primary}" stroke-width="1.5"/>
        <rect x="46" y="24" width="4" height="4" rx="1" fill="none" stroke="{primary}" stroke-width="1.5"/>
        <rect x="14" y="32" width="4" height="4" rx="1" fill="none" stroke="{primary}" stroke-width="1.5"/>
        <rect x="22" y="32" width="20" height="4" rx="1" fill="none" stroke="{accent}" stroke-width="1.5"/>
        <rect x="46" y="32" width="4" height="4" rx="1" fill="none" stroke="{primary}" stroke-width="1.5"/>
    </svg>
    """,
    "hdd": """
    <svg width="64" height="64" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
        <rect x="16" y="16" width="32" height="32" rx="4" fill="none" stroke="{primary}" stroke-width="2"/>
        <circle cx="32" cy="30" r="8" fill="none" stroke="{primary}" stroke-width="1.5"/>
        <circle cx="32" cy="30" r="2" fill="{accent}"/>
        <line x1="22" y1="42" x2="42" y2="42" stroke="{accent}" stroke-width="1.5" stroke-linecap="round"/>
    </svg>
    """,
    "sd-card": """
    <svg width="64" height="64" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
        <polygon points="24,14 42,14 46,18 46,50 18,50 18,22" fill="none" stroke="{primary}" stroke-width="2" stroke-linejoin="round"/>
        <line x1="24" y1="20" x2="24" y2="28" stroke="{primary}" stroke-width="1.5" stroke-linecap="round"/>
        <line x1="28" y1="20" x2="28" y2="28" stroke="{accent}" stroke-width="1.5" stroke-linecap="round"/>
        <line x1="32" y1="20" x2="32" y2="28" stroke="{primary}" stroke-width="1.5" stroke-linecap="round"/>
        <line x1="36" y1="20" x2="36" y2="28" stroke="{primary}" stroke-width="1.5" stroke-linecap="round"/>
    </svg>
    """,
    "smartphone": """
    <svg width="64" height="64" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
        <rect x="22" y="12" width="20" height="40" rx="3" fill="none" stroke="{primary}" stroke-width="2"/>
        <line x1="28" y1="16" x2="36" y2="16" stroke="{primary}" stroke-width="1.5" stroke-linecap="round"/>
        <circle cx="32" cy="46" r="2" fill="none" stroke="{accent}" stroke-width="1.5"/>
    </svg>
    """,
    "webcam": """
    <svg width="64" height="64" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
        <circle cx="32" cy="26" r="14" fill="none" stroke="{primary}" stroke-width="2"/>
        <circle cx="32" cy="26" r="6" fill="none" stroke="{primary}" stroke-width="1.5"/>
        <circle cx="32" cy="26" r="2" fill="{accent}"/>
        <path d="M24 44 L32 38 L40 44 L36 50 L28 50 Z" fill="none" stroke="{primary}" stroke-width="2" stroke-linejoin="round"/>
    </svg>
    """,
    "microphone": """
    <svg width="64" height="64" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
        <rect x="26" y="12" width="12" height="22" rx="6" fill="none" stroke="{primary}" stroke-width="2"/>
        <path d="M20 28 A 12 12 0 0 0 44 28" fill="none" stroke="{primary}" stroke-width="2" stroke-linecap="round"/>
        <line x1="32" y1="40" x2="32" y2="48" stroke="{primary}" stroke-width="2" stroke-linecap="round"/>
        <line x1="26" y1="48" x2="38" y2="48" stroke="{accent}" stroke-width="2" stroke-linecap="round"/>
    </svg>
    """,
    "printer": """
    <svg width="64" height="64" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
        <rect x="14" y="24" width="36" height="18" rx="3" fill="none" stroke="{primary}" stroke-width="2"/>
        <rect x="22" y="14" width="20" height="10" rx="1" fill="none" stroke="{primary}" stroke-width="2"/>
        <rect x="20" y="42" width="24" height="10" rx="1" fill="none" stroke="{primary}" stroke-width="2"/>
        <line x1="24" y1="46" x2="40" y2="46" stroke="{accent}" stroke-width="1.5" stroke-linecap="round"/>
        <line x1="24" y1="49" x2="34" y2="49" stroke="{primary}" stroke-width="1" stroke-linecap="round"/>
        <circle cx="18" cy="30" r="1.5" fill="{accent}"/>
    </svg>
    """
}

def get_glass_icon(name, theme_manager, is_hover=False, is_active=False, accent_override=None):
    """
    Renders an SVG string into a QPixmap dynamically based on the current theme and state.
    """
    template = SVG_TEMPLATES.get(name.lower(), SVG_TEMPLATES["dashboard"])
    
    # Extract colors from theme
    accent = accent_override if accent_override else theme_manager.get_color("accent")
    primary = theme_manager.get_color("text_primary")
    bg = theme_manager.get_color("bg")
    
    # State modifiers
    glow_filter = "url(#glow)" if (is_hover or is_active) else "none"
    glass_op1 = "0.7" if is_active else ("0.5" if is_hover else "0.3")
    glass_op2 = "0.2" if is_active else ("0.1" if is_hover else "0.05")
    reflect_op = "0.3" if theme_manager.current_theme == "light" else "0.15"
    
    # Inject variables
    svg_str = template.format(
        accent=accent,
        primary=primary,
        bg=bg,
        glow_filter=glow_filter,
        glass_op1=glass_op1,
        glass_op2=glass_op2,
        reflect_op=reflect_op
    )
    
    # Convert to bytes
    svg_bytes = bytearray(svg_str, encoding='utf-8')
    
    # Render
    renderer = QSvgRenderer(svg_bytes)
    pixmap = QPixmap(QSize(64, 64))
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter)
    painter.end()
    
    return pixmap

