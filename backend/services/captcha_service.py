import random
import uuid
import base64
from io import BytesIO
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
from backend.database.db import get_db
from backend import config

def generate_math_captcha() -> tuple[str, str, str]:
    """
    Generate a mathematical CAPTCHA.
    Returns:
        captcha_key (str): A unique key/id.
        captcha_equation (str): The equation text (e.g. '8 + 5 =').
        captcha_value (str): The correct answer.
    """
    num1 = random.randint(1, 20)
    num2 = random.randint(1, 20)
    operator = random.choice(['+', '-', '*'])
    
    # Ensure no negative results for simplicity
    if operator == '-' and num1 < num2:
        num1, num2 = num2, num1
        
    equation = f"{num1} {operator} {num2}"
    
    if operator == '+':
        answer = num1 + num2
    elif operator == '-':
        answer = num1 - num2
    else:
        answer = num1 * num2
        
    captcha_key = str(uuid.uuid4())
    return captcha_key, f"{equation} = ?", str(answer)

def generate_captcha_image(text: str) -> str:
    """
    Generate an image with distorted text and lines, representing the CAPTCHA.
    Returns a base64 encoded data-URI.
    """
    # Create image canvas
    width, height = 220, 70
    image = Image.new('RGB', (width, height), color=(240, 245, 255))
    draw = ImageDraw.Draw(image)
    
    # Add random background noise (lines)
    for _ in range(8):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=(random.randint(100, 200), random.randint(100, 200), random.randint(150, 230)), width=random.randint(1, 2))
        
    # Draw simple math text (character by character with slight distortion)
    # If font is not available, Pillow falls back to default
    try:
        # Try to use a standard system font, if not, fallback
        font = ImageFont.truetype("arial.ttf", 32)
    except IOError:
        font = ImageFont.load_default()
        
    # Draw characters with random displacement
    start_x = 20
    for char in text:
        y_pos = random.randint(15, 25)
        # Choose a nice deep blue color for text
        draw.text((start_x, y_pos), char, fill=(0, 71, 171), font=font)
        # Advance character position
        start_x += random.randint(20, 28)
        
    # Add minor pixel noise
    for _ in range(150):
        draw.point((random.randint(0, width), random.randint(0, height)), fill=(0, 71, 171))
        
    # Save image to buffer and encode
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{img_str}"

def create_captcha_challenge() -> dict:
    """
    Generate a math equation, make it an image, store it in db, and return the key and base64 image.
    """
    key, equation, value = generate_math_captcha()
    img_base64 = generate_captcha_image(equation)
    
    expires_at = datetime.now() + timedelta(minutes=config.CAPTCHA_EXPIRE_MINUTES)
    
    with get_db() as conn:
        with conn.cursor() as cursor:
            # Delete expired entries to keep database clean
            cursor.execute("DELETE FROM captcha_verifications WHERE expires_at < NOW()")
            # Insert the new captcha challenge
            cursor.execute(
                "INSERT INTO captcha_verifications (captcha_key, captcha_value, expires_at) VALUES (%s, %s, %s)",
                (key, value, expires_at)
            )
            
    return {
        "captcha_key": key,
        "captcha_image": img_base64
    }

def validate_captcha(key: str, user_value: str) -> bool:
    """
    Validate and delete CAPTCHA key to prevent replay attacks.
    """
    if not key or not user_value:
        return False
        
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT captcha_value, expires_at FROM captcha_verifications WHERE captcha_key = %s",
                (key,)
            )
            row = cursor.fetchone()
            
            # Delete challenge immediately
            cursor.execute("DELETE FROM captcha_verifications WHERE captcha_key = %s", (key,))
            
            if not row:
                return False
                
            expires_at = row["expires_at"]
            correct_value = row["captcha_value"]
            
            # Check if expired
            if datetime.now() > expires_at:
                return False
                
            return user_value.strip() == correct_value.strip()
