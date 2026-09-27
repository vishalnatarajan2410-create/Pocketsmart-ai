import os
import json
import re
import urllib.parse
from typing import Optional, Dict, Any, List
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

genai_available = False
genai_model = None

try:
    import google.generativeai as genai
    if GEMINI_API_KEY and GEMINI_API_KEY.strip() and GEMINI_API_KEY != "your_api_key_here":
        genai.configure(api_key=GEMINI_API_KEY.strip())
        genai_available = True
        try:
            genai_model = genai.GenerativeModel("gemini-1.5-flash")
        except Exception:
            try:
                genai_model = genai.GenerativeModel("gemini-pro")
            except Exception:
                genai_model = None
except Exception as e:
    print(f"Warning: Gemini AI initialization error: {e}")
    genai_available = False


def extract_json_from_response(text: str) -> dict:
    """Extract and parse JSON safely from LLM output."""
    if not text:
        return {}
    
    # Try direct parse
    text_clean = text.strip()
    try:
        return json.loads(text_clean)
    except Exception:
        pass

    # Try finding markdown JSON block
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text_clean, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except Exception:
            pass

    # Try finding outermost {}
    first_brace = text_clean.find('{')
    last_brace = text_clean.rfind('}')
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        json_str = text_clean[first_brace:last_brace+1]
        try:
            return json.loads(json_str)
        except Exception:
            pass

    return {}


def usd_to_inr(amount_usd: float, exchange_rate: float = 83.0) -> float:
    """Convert USD amount to INR using the specified exchange rate."""
    return amount_usd * exchange_rate


def build_shopping_links(category: str, search_terms: str) -> Dict[str, str]:
    """Build platform shopping links for items."""
    encoded_terms = urllib.parse.quote_plus(search_terms)
    encoded_query = urllib.parse.quote(search_terms)
    cat_lower = category.lower()

    links = {}
    
    # Generic e-commerce
    links["amazon"] = f"https://www.amazon.in/s?k={encoded_terms}"
    links["flipkart"] = f"https://www.flipkart.com/search?q={encoded_terms}"

    if any(k in cat_lower for k in ["furniture", "decor", "lighting", "fan", "home", "fixture", "table", "chair"]):
        links["ikea"] = f"https://www.ikea.com/in/en/search/?q={encoded_terms}"
        links["myntra"] = f"https://www.myntra.com/{encoded_terms}"
        links["ajio"] = f"https://www.ajio.com/search/?text={encoded_terms}"
    elif any(k in cat_lower for k in ["catering", "food", "cake", "snack", "meal", "dinner", "lunch", "beverage", "drinks"]):
        links["swiggy"] = f"https://www.swiggy.com/search?query={encoded_terms}"
        links["zomato"] = f"https://www.zomato.com/search?q={encoded_terms}"
        links["bigbasket"] = f"https://www.bigbasket.com/ps/?q={encoded_terms}"
    elif any(k in cat_lower for k in ["venue", "stay", "resort", "hall", "hotel", "room"]):
        links["google"] = f"https://www.google.com/search?q={encoded_terms}"
        links["booking"] = f"https://www.booking.com/search.html?ss={encoded_terms}"
        links["makemytrip"] = f"https://www.makemytrip.com/hotels/hotel-listing/?searchtext={encoded_terms}"
        links["oyorooms"] = f"https://www.oyorooms.com/search/?location={encoded_terms}"
        links["nobroker"] = f"https://www.nobroker.in/property/search/searchterm={encoded_terms}"
    elif any(k in cat_lower for k in ["entertainment", "music", "dj", "game", "show", "artist"]):
        links["bookmyshow"] = f"https://in.bookmyshow.com/search?q={encoded_terms}"
        links["meesho"] = f"https://www.meesho.com/search?q={encoded_terms}"
    elif any(k in cat_lower for k in ["jewelry", "jewellery", "earring", "ring", "necklace", "bracelet", "watch", "gold", "silver"]):
        links["bluestone"] = f"https://www.bluestone.com/search.html?query={encoded_terms}"
        links["tanishq"] = f"https://www.tanishq.co.in/search?q={encoded_terms}"
        links["caratlane"] = f"https://www.caratlane.com/search?q={encoded_terms}"
        links["melorra"] = f"https://www.melorra.com/search?q={encoded_terms}"
        links["meesho"] = f"https://www.meesho.com/search?q={encoded_terms}"
    else:
        links["meesho"] = f"https://www.meesho.com/search?q={encoded_terms}"
        links["myntra"] = f"https://www.myntra.com/{encoded_terms}"

    return links


# ==========================================
# 1. HOME INTERIOR PLANNER LOGIC
# ==========================================

def get_fallback_home_recommendations(budget_input: Any) -> dict:
    """Intelligent fallback for Home Interior Planner when Gemini API is unavailable."""
    budget = float(budget_input.total_budget)
    num_lights = int(budget_input.num_lights or 4)
    num_fans = int(budget_input.num_fans or 2)
    num_furniture = int(budget_input.num_furniture or 2)
    num_dining = int(budget_input.num_dining_tables or 1)
    
    rooms = []
    if getattr(budget_input, "has_living_room", True):
        rooms.append("Living Room")
    if getattr(budget_input, "has_kitchen", True):
        rooms.append("Kitchen")
    if getattr(budget_input, "has_bedroom", True):
        rooms.append("Bedroom")
    if not rooms:
        rooms = ["Living Room", "Bedroom"]

    # Proportional allocation
    lighting_alloc = round(budget * 0.22, 2)
    fans_alloc = round(budget * 0.28, 2)
    furniture_alloc = round(budget * 0.35, 2)
    dining_alloc = round(budget * 0.10, 2)
    
    light_price = round(lighting_alloc / max(1, num_lights), 2)
    fan_price = round(fans_alloc / max(1, num_fans), 2)
    furn_price = round(furniture_alloc / max(1, num_furniture), 2)
    table_price = round(dining_alloc / max(1, num_dining), 2)

    total_cost = (light_price * num_lights) + (fan_price * num_fans) + (furn_price * num_furniture) + (table_price * num_dining)
    remaining_budget = max(0.0, round(budget - total_cost, 2))

    breakdown = [
        {
            "category": "Lighting",
            "allocation": lighting_alloc,
            "items": [
                {
                    "name": "Smart / Warm-White LED Ceiling Fixture & Bulbs",
                    "description": f"Energy-efficient ambient and task lighting suitable for {', '.join(rooms)}.",
                    "estimated_price": light_price,
                    "quantity": num_lights,
                    "search_terms": "LED warm ceiling lights Philips Crompton",
                    "shopping_links": build_shopping_links("Lighting", "LED warm ceiling lights Philips Crompton")
                }
            ]
        },
        {
            "category": "Ceiling Fans",
            "allocation": fans_alloc,
            "items": [
                {
                    "name": "High-Airflow BLDC Energy Saver Ceiling Fan",
                    "description": "Silent, remote-controlled 1200mm decorative ceiling fan with low power consumption.",
                    "estimated_price": fan_price,
                    "quantity": num_fans,
                    "search_terms": "BLDC Ceiling Fan Atomberg Havells 1200mm",
                    "shopping_links": build_shopping_links("Ceiling Fans", "BLDC Ceiling Fan Atomberg Havells 1200mm")
                }
            ]
        },
        {
            "category": "Furniture",
            "allocation": furniture_alloc,
            "items": [
                {
                    "name": "Ergonomic Accent Chairs / Modular Sofa Unit",
                    "description": "Comfortable, contemporary wood/fabric furniture pieces designed for durability and style.",
                    "estimated_price": furn_price,
                    "quantity": num_furniture,
                    "search_terms": "Modern accent chair sofa set IKEA Amazon",
                    "shopping_links": build_shopping_links("Furniture", "Modern accent chair sofa set IKEA Amazon")
                }
            ]
        },
        {
            "category": "Dining & Tables",
            "allocation": dining_alloc,
            "items": [
                {
                    "name": "Compact Engineered Wood Dining Table",
                    "description": "Space-saving sturdy dining or coffee table matching contemporary decor.",
                    "estimated_price": table_price,
                    "quantity": num_dining,
                    "search_terms": "Engineered wood dining table compact IKEA",
                    "shopping_links": build_shopping_links("Dining & Tables", "Engineered wood dining table compact IKEA")
                }
            ]
        }
    ]

    calc_table = [
        {
            "category": "Lighting",
            "items_count": num_lights,
            "total_cost": round(light_price * num_lights, 2),
            "percentage_of_budget": round(((light_price * num_lights) / budget) * 100, 1)
        },
        {
            "category": "Ceiling Fans",
            "items_count": num_fans,
            "total_cost": round(fan_price * num_fans, 2),
            "percentage_of_budget": round(((fan_price * num_fans) / budget) * 100, 1)
        },
        {
            "category": "Furniture",
            "items_count": num_furniture,
            "total_cost": round(furn_price * num_furniture, 2),
            "percentage_of_budget": round(((furn_price * num_furniture) / budget) * 100, 1)
        },
        {
            "category": "Dining & Tables",
            "items_count": num_dining,
            "total_cost": round(table_price * num_dining, 2),
            "percentage_of_budget": round(((table_price * num_dining) / budget) * 100, 1)
        }
    ]

    return {
        "total_budget": budget,
        "budget_breakdown": breakdown,
        "calculation_table": calc_table,
        "remaining_budget": remaining_budget,
        "additional_suggestions": [
            "Opt for 5-star BEE rated BLDC fans to save up to 65% on electricity bills.",
            "Consider modular flat-pack furniture from IKEA for easy DIY assembly and budget savings.",
            "Look for festive discounts, bank cashback offers on Amazon and Flipkart during big sale events.",
            "Incorporate potted indoor plants (Areca Palm, Snake Plant) as cost-effective aesthetic enhancements."
        ]
    }


def get_home_recommendations(budget_input: Any) -> dict:
    """Generate home interior recommendations within budget in INR for Indian market."""
    try:
        if not genai_available or not genai_model:
            return get_fallback_home_recommendations(budget_input)

        rooms_desc = []
        if getattr(budget_input, "has_living_room", False):
            rooms_desc.append("Living Room")
        if getattr(budget_input, "has_kitchen", False):
            rooms_desc.append("Kitchen")
        if getattr(budget_input, "has_bedroom", False):
            rooms_desc.append("Bedroom")
        rooms_str = ", ".join(rooms_desc) if rooms_desc else "General Home Interior"

        prompt = f"""
You are an expert AI Home Decor and Interior Budget Advisor for Indian households.
I need interior design product recommendations for a home in India with a total budget of ₹{float(budget_input.total_budget):.2f}.

Requirements:
- {budget_input.num_lights} lights/lighting fixtures
- {budget_input.num_fans} ceiling fans
- {budget_input.num_furniture} furniture pieces
- {budget_input.num_dining_tables} dining tables

Target Rooms: {rooms_str}
Additional Requirements: {getattr(budget_input, 'additional_requirements', None) or 'None'}

Please provide a detailed budget breakdown with product recommendations available in India.
Use Indian brands and realistic INR pricing. Include search terms suitable for Indian shopping platforms (IKEA, Amazon, Flipkart, Myntra, Ajio).

Format your response strictly as JSON with this schema:
{{
  "total_budget": {float(budget_input.total_budget):.2f},
  "budget_breakdown": [
    {{
      "category": "Lighting",
      "allocation": 0.0,
      "items": [
        {{
          "name": "...",
          "description": "...",
          "estimated_price": 0.0,
          "quantity": 1,
          "search_terms": "..."
        }}
      ]
    }}
  ],
  "calculation_table": [
    {{
      "category": "Lighting",
      "items_count": 0,
      "total_cost": 0.0,
      "percentage_of_budget": 0.0
    }}
  ],
  "remaining_budget": 0.0,
  "additional_suggestions": [
    "Tip 1...",
    "Tip 2..."
  ]
}}

Ensure all costs are in INR and total estimated cost does NOT exceed total_budget. Return ONLY raw JSON.
"""
        response = genai_model.generate_content(prompt)
        result = extract_json_from_response(response.text)

        if not result or "budget_breakdown" not in result:
            return get_fallback_home_recommendations(budget_input)

        # Attach shopping links
        for category in result.get("budget_breakdown", []):
            cat_name = category.get("category", "Home")
            for item in category.get("items", []):
                search_terms = item.get("search_terms") or item.get("name", "")
                item["shopping_links"] = build_shopping_links(cat_name, search_terms)

        return result

    except Exception as e:
        print(f"Error in get_home_recommendations: {e}. Falling back to default generator.")
        return get_fallback_home_recommendations(budget_input)


# ==========================================
# 2. PARTY BUDGET PLANNER LOGIC
# ==========================================

def get_fallback_party_recommendations(budget_input: Any) -> dict:
    """Intelligent fallback for Party Budget Planner when Gemini API is unavailable."""
    budget = float(budget_input.total_budget)
    guests = int(budget_input.num_guests or 10)
    party_type = budget_input.party_type or "Celebration Party"
    venue_type = budget_input.venue_type or "Home / Banquet"

    needs_catering = getattr(budget_input, "needs_catering", True)
    needs_decor = getattr(budget_input, "needs_decoration", True)
    needs_ent = getattr(budget_input, "needs_entertainment", True)

    # Budget distribution
    catering_alloc = round(budget * 0.45, 2) if needs_catering else 0.0
    decor_alloc = round(budget * 0.20, 2) if needs_decor else 0.0
    ent_alloc = round(budget * 0.20, 2) if needs_ent else 0.0
    venue_alloc = round(budget * 0.05, 2) if "home" in venue_type.lower() else round(budget * 0.15, 2)
    contingency = max(0.0, round(budget - (catering_alloc + decor_alloc + ent_alloc + venue_alloc), 2))

    breakdown = []
    calc_table = []

    if venue_alloc > 0 or "home" in venue_type.lower():
        cost = 0.0 if "home" in venue_type.lower() else venue_alloc
        breakdown.append({
            "category": "Venue",
            "allocation": venue_alloc,
            "items": [
                {
                    "name": f"{venue_type} Space Booking / Setup",
                    "description": f"Comfortable venue arrangement suitable for {guests} guests with seating and lighting.",
                    "estimated_price": cost,
                    "quantity": 1,
                    "search_terms": f"party banquet hall {venue_type} booking",
                    "shopping_links": build_shopping_links("venue", f"party venue {venue_type} for {guests} guests")
                }
            ]
        })
        calc_table.append({
            "category": "Venue",
            "items_count": 1,
            "total_cost": cost,
            "percentage_of_budget": round((cost / budget) * 100, 1)
        })

    if needs_catering:
        per_head = round(catering_alloc / max(1, guests), 2)
        breakdown.append({
            "category": "Catering & Refreshments",
            "allocation": catering_alloc,
            "items": [
                {
                    "name": f"Buffet & Finger Foods Platter for {guests} guests",
                    "description": f"Curated appetizers, main course, and beverages (~₹{per_head}/person) ordered via Swiggy/Zomato or local caterers.",
                    "estimated_price": catering_alloc,
                    "quantity": 1,
                    "search_terms": f"{party_type} catering bulk food boxes Swiggy Zomato",
                    "shopping_links": build_shopping_links("catering", f"party snacks catering {party_type}")
                }
            ]
        })
        calc_table.append({
            "category": "Catering",
            "items_count": 1,
            "total_cost": catering_alloc,
            "percentage_of_budget": round((catering_alloc / budget) * 100, 1)
        })

    if needs_decor:
        breakdown.append({
            "category": "Decoration & Ambiance",
            "allocation": decor_alloc,
            "items": [
                {
                    "name": f"{party_type} Theme Balloons, Banners & Fairy Lights Kit",
                    "description": "Complete DIY festive decoration kit including backdrop curtain, balloons arch, and LED fairy lights.",
                    "estimated_price": decor_alloc,
                    "quantity": 1,
                    "search_terms": f"{party_type} decoration kit banner balloon arch Amazon",
                    "shopping_links": build_shopping_links("decoration", f"{party_type} party decoration kit")
                }
            ]
        })
        calc_table.append({
            "category": "Decoration",
            "items_count": 1,
            "total_cost": decor_alloc,
            "percentage_of_budget": round((decor_alloc / budget) * 100, 1)
        })

    if needs_ent:
        breakdown.append({
            "category": "Entertainment & Music",
            "allocation": ent_alloc,
            "items": [
                {
                    "name": "Party Speaker / Games & Music Playlist Pass",
                    "description": "Bluetooth portable party speaker rental or interactive party board games & streaming music.",
                    "estimated_price": ent_alloc,
                    "quantity": 1,
                    "search_terms": "Party board games Bluetooth speaker rental Amazon",
                    "shopping_links": build_shopping_links("entertainment", "Party board games bluetooth speaker")
                }
            ]
        })
        calc_table.append({
            "category": "Entertainment",
            "items_count": 1,
            "total_cost": ent_alloc,
            "percentage_of_budget": round((ent_alloc / budget) * 100, 1)
        })

    if contingency > 0:
        breakdown.append({
            "category": "Contingency & Return Gifts",
            "allocation": contingency,
            "items": [
                {
                    "name": "Emergency Buffer & Custom Return Gifts",
                    "description": f"Reserved buffer for last-minute supplies, extra ice/beverages, or token souvenirs for {guests} guests.",
                    "estimated_price": contingency,
                    "quantity": 1,
                    "search_terms": "party return gifts bulk pack Amazon",
                    "shopping_links": build_shopping_links("gifts", "party return gifts bulk pack")
                }
            ]
        })
        calc_table.append({
            "category": "Contingency",
            "items_count": 1,
            "total_cost": contingency,
            "percentage_of_budget": round((contingency / budget) * 100, 1)
        })

    total_spent = sum(c["total_cost"] for c in calc_table)
    remaining = max(0.0, round(budget - total_spent, 2))

    venue_suggestions = [
        {
            "name": f"Selected {venue_type}",
            "type": venue_type,
            "capacity": f"Up to {guests + 10} guests",
            "estimated_cost": venue_alloc if "home" not in venue_type.lower() else 0.0,
            "search_terms": f"party halls and venues for {guests} guests",
            "shopping_links": build_shopping_links("venue", f"{venue_type} venues for {guests} guests")
        }
    ]

    return {
        "total_budget": budget,
        "budget_breakdown": breakdown,
        "calculation_table_inr": calc_table,
        "venue_suggestions": venue_suggestions,
        "remaining_budget": remaining,
        "additional_suggestions": [
            "Order group meal platters on Swiggy Gourmet or Zomato Pro for 15-20% party discounts.",
            "Create a collaborative Spotify / Apple Music party playlist so guests can queue their favorite tracks.",
            "DIY balloon arrangements using manual balloon pumps save over ₹2,000 compared to event decorator agencies.",
            "Utilize digital e-invites (Canva) rather than printed cards to save money and stay eco-friendly."
        ]
    }


def get_party_recommendations(budget_input: Any) -> dict:
    """Generate party planning recommendations within budget in INR for Indian market."""
    try:
        if not genai_available or not genai_model:
            return get_fallback_party_recommendations(budget_input)

        catering_str = "Yes" if getattr(budget_input, 'needs_catering', True) else "No"
        decor_str = "Yes" if getattr(budget_input, 'needs_decoration', True) else "No"
        ent_str = "Yes" if getattr(budget_input, 'needs_entertainment', True) else "No"

        prompt = f"""
You are an expert AI Party Planner and Budget Consultant for Indian events.
I need party planning recommendations for India with a total budget of ₹{float(budget_input.total_budget):.2f}.

Party details:
- Type: {budget_input.party_type}
- Number of guests: {budget_input.num_guests}
- Venue type: {budget_input.venue_type or 'Not specified'}
- Catering needed: {catering_str}
- Decoration needed: {decor_str}
- Entertainment needed: {ent_str}
- Additional requirements: {getattr(budget_input, 'additional_requirements', None) or 'None'}

Please provide a detailed budget breakdown with specific recommendations available in India using INR prices.
Use Indian brands, services (Swiggy, Zomato, BigBasket, BookMyShow, Amazon, OYO), and typical cost expectations.

Format your response strictly as JSON with this schema:
{{
  "total_budget": {float(budget_input.total_budget):.2f},
  "budget_breakdown": [
    {{
      "category": "Catering",
      "allocation": 0.0,
      "items": [
        {{
          "name": "...",
          "description": "...",
          "estimated_price": 0.0,
          "quantity": 1,
          "search_terms": "..."
        }}
      ]
    }}
  ],
  "venue_suggestions": [
    {{
      "name": "...",
      "type": "...",
      "capacity": 0,
      "estimated_cost": 0.0,
      "search_terms": "..."
    }}
  ],
  "calculation_table_inr": [
    {{
      "category": "Catering",
      "items_count": 1,
      "total_cost": 0.0,
      "percentage_of_budget": 0.0
    }}
  ],
  "remaining_budget": 0.0,
  "additional_suggestions": [
    "Tip 1...",
    "Tip 2..."
  ]
}}

Ensure all costs are in INR and total does not exceed total_budget. Return ONLY raw JSON.
"""
        response = genai_model.generate_content(prompt)
        result = extract_json_from_response(response.text)

        if not result or "budget_breakdown" not in result:
            return get_fallback_party_recommendations(budget_input)

        # Attach shopping links
        for category in result.get("budget_breakdown", []):
            cat_name = category.get("category", "Party")
            for item in category.get("items", []):
                search_terms = item.get("search_terms") or item.get("name", "")
                item["shopping_links"] = build_shopping_links(cat_name, search_terms)

        for venue in result.get("venue_suggestions", []):
            search_terms = venue.get("search_terms") or venue.get("name", "")
            venue["shopping_links"] = build_shopping_links("venue", search_terms)

        return result

    except Exception as e:
        print(f"Error in get_party_recommendations: {e}. Falling back to default generator.")
        return get_fallback_party_recommendations(budget_input)


# ==========================================
# 3. JEWELRY BUDGET PLANNER LOGIC
# ==========================================

def get_fallback_jewelry_recommendations(budget_input: Any, image_path: Optional[str] = None) -> dict:
    """Intelligent fallback for Jewelry Planner when Gemini API is unavailable."""
    budget = float(budget_input.total_budget)
    occasion = budget_input.occasion or "Special Occasion / Party"
    prefs = budget_input.preferences or "Elegant, modern Indian aesthetics"

    has_image = image_path is not None and os.path.exists(image_path)
    
    outfit_analysis = {
        "colors": ["Royal Blue", "Golden Zari", "Ivory White"] if has_image else ["Classic Traditional / Modern Palette"],
        "style": "Contemporary Ethnic Elegance" if "wedding" in occasion.lower() or "traditional" in occasion.lower() else "Modern Chic",
        "formality": "Festive / Formal" if "wedding" in occasion.lower() or "party" in occasion.lower() else "Semi-Formal"
    }

    earring_price = round(budget * 0.35, 2)
    necklace_price = round(budget * 0.40, 2)
    bracelet_price = round(budget * 0.20, 2)
    
    total_cost = earring_price + necklace_price + bracelet_price
    remaining = max(0.0, round(budget - total_cost, 2))

    recs = [
        {
            "item_type": "Statement Jhumkas / Drop Earrings",
            "description": f"Intricately crafted drop earrings with pearl and gemstone accents tailored for {occasion}.",
            "style": "Kundan & Polki / Modern Minimalist",
            "estimated_price": earring_price,
            "search_terms": f"{occasion} Kundan pearl drop earrings for women",
            "shopping_links": build_shopping_links("jewelry", f"{occasion} Kundan earrings Tanishq Caratlane")
        },
        {
            "item_type": "Choker / Layered Pendant Necklace",
            "description": f"Graceful neckpiece designed to complement the neckline and colors of your {occasion} outfit.",
            "style": "Rose Gold / Antique Gold Finish",
            "estimated_price": necklace_price,
            "search_terms": f"{occasion} rose gold pendant necklace CaratLane Bluestone",
            "shopping_links": build_shopping_links("jewelry", f"{occasion} pendant necklace CaratLane Bluestone")
        },
        {
            "item_type": "Sleek Cuff Bracelet / Delicate Kada",
            "description": "Subtle, adjustable hand accessory featuring embedded cubic zirconia crystals.",
            "style": "Contemporary Sleek",
            "estimated_price": bracelet_price,
            "search_terms": "adjustable silver zircon bracelet cuff women",
            "shopping_links": build_shopping_links("jewelry", "adjustable silver zircon bracelet cuff women")
        }
    ]

    return {
        "total_budget": budget,
        "outfit_analysis": outfit_analysis,
        "jewelry_recommendations": recs,
        "remaining_budget": remaining,
        "styling_tips": [
            "Balance the focal point: If wearing heavy statement earrings, keep the necklace subtle and delicate.",
            "Match metal undertones: Warm toned outfits (red, marigold, emerald) pair brilliantly with yellow/antique gold, while pastel/cool shades look great with silver and rose gold.",
            "Check certified 925 sterling silver or 14K/18K BIS-hallmarked options on CaratLane, Bluestone, and Tanishq for lasting value.",
            "Store jewelry in airtight zip pouches to avoid oxidation and moisture damage."
        ]
    }


def get_jewelry_recommendations(budget_input: Any, image_path: Optional[str] = None) -> dict:
    """Generate jewelry recommendations based on uploaded dress/outfit image and budget in INR."""
    try:
        if not genai_available or not genai_model:
            return get_fallback_jewelry_recommendations(budget_input, image_path)

        base_prompt = f"""
You are an expert AI Fashion Stylist and Jewelry Consultant for Indian markets.
I need jewelry recommendations for India with a total budget of ₹{float(budget_input.total_budget):.2f}.

Occasion: {budget_input.occasion}
Preferences: {getattr(budget_input, 'preferences', None) or 'Not specified'}
Provide only India-relevant styles, availability, and price ranges in INR.
"""

        img = None
        if image_path and os.path.exists(image_path):
            try:
                img = Image.open(image_path)
            except Exception as e:
                print(f"Failed to open outfit image: {e}")
                img = None

        if img:
            prompt = base_prompt + """
An image of the outfit is uploaded. Analyze the outfit's colors, patterns, neckline, and style, then suggest complementary jewelry considering color harmony, metal choice, design, and occasion appropriateness.

Format the output strictly as JSON with this schema:
{
  "total_budget": 0.0,
  "outfit_analysis": {
    "colors": ["Primary Color", "Secondary Color"],
    "style": "Traditional/Western/Indo-Western",
    "formality": "Casual/Festive/Bridal/Formal"
  },
  "jewelry_recommendations": [
    {
      "item_type": "Earrings / Necklace / Ring / Bracelet / Watch",
      "description": "...",
      "style": "...",
      "estimated_price": 0.0,
      "search_terms": "..."
    }
  ],
  "remaining_budget": 0.0,
  "styling_tips": [
    "Tip 1...",
    "Tip 2..."
  ]
}

Make sure prices are in INR and total does not exceed total_budget. Return ONLY raw JSON.
"""
            response = genai_model.generate_content([prompt, img])
        else:
            prompt = base_prompt + """
Format the output strictly as JSON with this schema:
{
  "total_budget": 0.0,
  "outfit_analysis": {
    "colors": ["Suggested coordinating colors"],
    "style": "Occasion matching style",
    "formality": "Festive/Formal"
  },
  "jewelry_recommendations": [
    {
      "item_type": "Earrings / Necklace / Ring / Bracelet / Watch",
      "description": "...",
      "style": "...",
      "estimated_price": 0.0,
      "search_terms": "..."
    }
  ],
  "remaining_budget": 0.0,
  "styling_tips": [
    "Tip 1...",
    "Tip 2..."
  ]
}

Keep prices in INR and relevant to Indian brands (Tanishq, CaratLane, Bluestone, Melorra, Meesho, Amazon, Flipkart). Return ONLY raw JSON.
"""
            response = genai_model.generate_content(prompt)

        result = extract_json_from_response(response.text)

        if not result or "jewelry_recommendations" not in result:
            return get_fallback_jewelry_recommendations(budget_input, image_path)

        # Attach shopping links
        for item in result.get("jewelry_recommendations", []):
            search_terms = item.get("search_terms") or item.get("item_type", "")
            item["shopping_links"] = build_shopping_links("jewelry", search_terms)

        return result

    except Exception as e:
        print(f"Error in get_jewelry_recommendations: {e}. Falling back to default generator.")
        return get_fallback_jewelry_recommendations(budget_input, image_path)
