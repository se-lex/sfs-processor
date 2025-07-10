"""
Styling constants for HTML exporters.

Contains all color variables and common styles used across HTML generation.
"""

# Configuration constants
LIGHTER_PERCENT_ON_HOVER = 20


def lighten_color(hex_color, percent=20):
    """
    Lighten a hex color by a given percentage.
    
    Args:
        hex_color: Hex color string (e.g., '#002147' or '#fff')
        percent: Percentage to lighten (0-100)
        
    Returns:
        str: Lightened hex color
    """
    # Remove # if present
    hex_color = hex_color.lstrip('#')
    
    # Handle 3-character hex codes by expanding them
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    
    # Convert to RGB
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    
    # Calculate lighten amount
    lighten_amount = percent / 100
    
    # Lighten each component
    r = min(255, int(r + (255 - r) * lighten_amount))
    g = min(255, int(g + (255 - g) * lighten_amount))
    b = min(255, int(b + (255 - b) * lighten_amount))
    
    # Convert back to hex
    return f'#{r:02x}{g:02x}{b:02x}'


# Primary color palette
COLORS = {
    # Selex brand colors
    'selex_dark_blue': '#002147',
    'selex_middle_blue': '#0056a0',
    'selex_light_blue': '#0072c6',
    'selex_yellow': '#f1c40f',
    'selex_white': '#fff',
    'selex_light_grey': '#f5f5f5',
    'selex_dark_grey': '#bdc3c7',
    
    # Semantic colors
    'success_green': '#28a745',
    'success_green_bg': '#d4edda',
    'danger_red': '#dc3545',
    'danger_red_bg': '#f8d7da',
    'warning_yellow': '#ffc107',
    'warning_yellow_bg': '#fff3cd',
    
    # Greys and neutrals
    'text_primary': '#333',
    'text_secondary': '#666',
    'text_muted': '#555',
    'border_grey': '#ddd',
    'border_light_grey': '#dee2e6',
    'bg_light_grey': '#f8f9fa',
    'white': '#fff',
}

# Automatically generate hover variants for all selex colors
selex_hover_variants = {
    f'{color_name}_hover': lighten_color(color_value, LIGHTER_PERCENT_ON_HOVER)
    for color_name, color_value in COLORS.items()
    if color_name.startswith('selex_')
}
COLORS.update(selex_hover_variants)


def get_css_variables():
    """
    Returns CSS custom properties (variables) definition string.
    
    Returns:
        str: CSS :root block with all color variables
    """
    css_vars = [":root {"]
    
    # Add Selex brand colors
    css_vars.append("    /* Selex brand colors */")
    css_vars.append(f"    --selex-dark-blue: {COLORS['selex_dark_blue']};")
    css_vars.append(f"    --selex-middle-blue: {COLORS['selex_middle_blue']};")
    css_vars.append(f"    --selex-light-blue: {COLORS['selex_light_blue']};")
    css_vars.append(f"    --selex-yellow: {COLORS['selex_yellow']};")
    css_vars.append(f"    --selex-white: {COLORS['selex_white']};")
    css_vars.append(f"    --selex-light-grey: {COLORS['selex_light_grey']};")
    css_vars.append(f"    --selex-dark-grey: {COLORS['selex_dark_grey']};")
    
    # Add Selex hover variants (automatically generated)
    css_vars.append(f"\n    /* Selex hover variants ({LIGHTER_PERCENT_ON_HOVER}% lighter) */")
    selex_hover_colors = {k: v for k, v in COLORS.items() if k.startswith('selex_') and k.endswith('_hover')}
    for color_name in sorted(selex_hover_colors.keys()):
        css_var_name = color_name.replace('_', '-')
        css_vars.append(f"    --{css_var_name}: {COLORS[color_name]};")
    
    # Add navbar aliases
    css_vars.append("\n    /* Navbar color aliases */")
    css_vars.append("    --navbar-dark-blue: var(--selex-dark-blue);")
    css_vars.append("    --navbar-middle-blue: var(--selex-middle-blue);")
    css_vars.append("    --navbar-light-blue: var(--selex-light-blue);")
    css_vars.append("    --navbar-yellow: var(--selex-yellow);")
    css_vars.append("    --navbar-white: var(--selex-white);")
    
    # Add semantic colors
    css_vars.append("\n    /* Semantic colors */")
    css_vars.append(f"    --success-green: {COLORS['success_green']};")
    css_vars.append(f"    --success-green-bg: {COLORS['success_green_bg']};")
    css_vars.append(f"    --danger-red: {COLORS['danger_red']};")
    css_vars.append(f"    --danger-red-bg: {COLORS['danger_red_bg']};")
    css_vars.append(f"    --warning-yellow: {COLORS['warning_yellow']};")
    css_vars.append(f"    --warning-yellow-bg: {COLORS['warning_yellow_bg']};")
    
    # Add text and neutral colors
    css_vars.append("\n    /* Text and neutral colors */")
    css_vars.append(f"    --text-primary: {COLORS['text_primary']};")
    css_vars.append(f"    --text-secondary: {COLORS['text_secondary']};")
    css_vars.append(f"    --text-muted: {COLORS['text_muted']};")
    css_vars.append(f"    --border-grey: {COLORS['border_grey']};")
    css_vars.append(f"    --border-light-grey: {COLORS['border_light_grey']};")
    css_vars.append(f"    --bg-light-grey: {COLORS['bg_light_grey']};")
    
    # Add other utility variables
    css_vars.append("\n    /* Utility variables */")
    css_vars.append("    --base-font-size: 14px;")
    
    css_vars.append("}")
    
    return "\n".join(css_vars)


def get_css_variables_escaped():
    """
    Returns CSS custom properties definition string with double braces for Python f-strings.
    
    Returns:
        str: CSS :root block with all color variables (brace-escaped)
    """
    return get_css_variables().replace("{", "{{").replace("}", "}}")