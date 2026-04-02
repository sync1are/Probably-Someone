from tool_handlers import execute_tool
import json

# Test the screenshot tool
print("Testing screenshot tool...")
print("Taking screenshot in 3 seconds...")

import time
time.sleep(3)

result = execute_tool("take_screenshot", {"mode": "full"})

if result["success"]:
    print(f"✓ Screenshot captured successfully!")
    print(f"  Size: {result['width']}x{result['height']}")
    print(f"  Format: {result['format']}")
    print(f"  Base64 length: {len(result['image_base64'])} characters")
    
    # Optionally save to file for verification
    import base64
    from PIL import Image
    from io import BytesIO
    
    img_data = base64.b64decode(result['image_base64'])
    img = Image.open(BytesIO(img_data))
    img.save("test_screenshot.png")
    print("  Saved as: test_screenshot.png")
else:
    print(f"✗ Screenshot failed: {result.get('error')}")
