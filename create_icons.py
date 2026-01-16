# -*- coding: utf-8 -*-
"""
Generate simple icons for pyRevit buttons
"""
import os
from PIL import Image, ImageDraw, ImageFont

# Icon configuration
ICON_SIZE = 64
ICONS = [
    {
        'name': 'Diagnostics.pushbutton',
        'symbol': '🔧',
        'bg_color': '#4A90E2',
        'text': 'D',
        'text_color': '#FFFFFF'
    },
    {
        'name': 'Place_Lights_RoomCenters.pushbutton',
        'symbol': '💡',
        'bg_color': '#F5A623',
        'text': 'L',
        'text_color': '#FFFFFF'
    },
    {
        'name': 'Place_Panel_ShK_AboveApartmentDoor.pushbutton',
        'symbol': '📦',
        'bg_color': '#7ED321',
        'text': 'ШК',
        'text_color': '#FFFFFF'
    },
    {
        'name': 'Place_Sockets_Perimeter_3m.pushbutton',
        'symbol': '🔌',
        'bg_color': '#D0021B',
        'text': 'S',
        'text_color': '#FFFFFF'
    },
    {
        'name': 'Place_Switches_ByDoors.pushbutton',
        'symbol': '🎚️',
        'bg_color': '#50E3C2',
        'text': 'SW',
        'text_color': '#000000'
    },
    {
        'name': 'PlaceLightsFromRooms.pushbutton',
        'symbol': '💡',
        'bg_color': '#F8E71C',
        'text': 'LR',
        'text_color': '#000000'
    }
]

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def create_icon(bg_color, text, text_color, size=ICON_SIZE):
    """Create a simple icon with text"""
    # Create image with background color
    img = Image.new('RGB', (size, size), hex_to_rgb(bg_color))
    draw = ImageDraw.Draw(img)

    # Try to use a nice font, fall back to default if not available
    try:
        font = ImageFont.truetype("arial.ttf", int(size * 0.4))
    except:
        try:
            font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", int(size * 0.4))
        except:
            font = ImageFont.load_default()

    # Draw text in center
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    position = ((size - text_width) // 2, (size - text_height) // 2 - 4)

    draw.text(position, text, fill=hex_to_rgb(text_color), font=font)

    return img

def main():
    base_path = os.path.dirname(os.path.abspath(__file__))
    panel_path = os.path.join(base_path, 'EOMTemplateTools.extension', 'EOM.tab', 'Setup.panel')

    for icon_config in ICONS:
        button_path = os.path.join(panel_path, icon_config['name'])
        icon_path = os.path.join(button_path, 'icon.png')

        print(f"Creating icon for {icon_config['name']}...")

        # Create icon
        img = create_icon(
            icon_config['bg_color'],
            icon_config['text'],
            icon_config['text_color']
        )

        # Save icon
        img.save(icon_path, 'PNG')
        print(f"  Saved to {icon_path}")

    print("\nAll icons created successfully!")

if __name__ == '__main__':
    main()
