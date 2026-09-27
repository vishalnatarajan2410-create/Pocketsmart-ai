# PocketSmart AI: Your Smart Budget & Recommendation Assistant

**PocketSmart AI** is a GenAI-powered cross-platform budget allocation and recommendation system designed to optimize personal spending across **Home Interior Planning**, **Party & Event Planning**, and **Jewelry Matching**.

Built with **FastAPI**, **Google Gemini AI**, and **Jinja2 Templates**, it transforms lifestyle budgeting into an intelligent experience by generating realistic item breakdowns, cost calculations, styling insights, and direct shopping links (Amazon, Flipkart, IKEA, Swiggy, Zomato, BookMyShow, Tanishq, CaratLane, Bluestone, OYO, and more).

---

## 🌟 Key Features & Scenarios

### 1. 🏠 Home Interior Budget Planner
- **Intelligent Budget Breakdown:** Allocates total budget into Lighting, Ceiling Fans, Furniture Pieces, Dining Tables, and Decor.
- **Room Selection:** Supports custom preferences for Living Room, Kitchen, Bedroom, and open areas.
- **Dynamic Platform Links:** Generates direct purchase links on Amazon India, Flipkart, IKEA, Myntra, and Ajio.
- **Summary & Allocation Table:** Shows item counts, estimated costs in ₹ INR, budget percentage shares, and cost-saving tips.

### 2. 🥳 AI-Based Party Budget Planner
- **Guest & Event Driven:** Allocates funds proportionally for Birthdays, Weddings, Anniversaries, Dinners, and Corporate Events based on guest count and venue type.
- **Multicategory Sourcing:** Integrates recommendations with catering & food delivery (Swiggy, Zomato, BigBasket), entertainment (BookMyShow), and venues (OYO, MakeMyTrip, NoBroker).
- **Buffer & Contingency:** Allocates emergency buffers and souvenir return gift packages.

### 3. 💎 Jewelry Recommendation & Multimodal Outfit Matching
- **Multimodal AI Analysis:** Accepts optional dress/outfit image uploads. Gemini AI analyzes colors, neckline, style (traditional, western, Indo-western), and formality level.
- **Curated Suggestions:** Recommends earrings, necklaces, rings, bracelets, and watches matching your budget and occasion.
- **Branded Links:** Generates one-click search links to Tanishq, CaratLane, Bluestone, Melorra, Meesho, Amazon, and Flipkart.

### 4. 📊 Dashboard & Recommendation History
- **Session Tracking:** Tracks user sessions, durations, and preferences.
- **Comprehensive History:** Stores all past recommendations with instant filter tabs and interactive details modals.
- **Print & Export:** One-click print / PDF export capability for all budget plans.

---

## 🏗️ Architecture & Technology Stack

- **Backend Framework:** FastAPI (Python 3.10+)
- **AI Foundation Model:** Google Gemini (Gemini 1.5 Flash / Gemini Pro) with robust fallback generator
- **Authentication & Security:** OAuth2 Password Bearer, JWT tokens (HS256), BCrypt password hashing, session expiration worker
- **Multimodal Image Processing:** Pillow (PIL)
- **Frontend:** Responsive HTML5, CSS3 Glassmorphic Design System, FontAwesome 6, Jinja2 Templates

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10 or higher
- (Optional) Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/)

### 2. Installation
```bash
# Clone or navigate to the repository
cd "pocketsmart ai"

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Edit `.env` to configure your environment:
```env
GEMINI_API_KEY=your_gemini_api_key_here
SECRET_KEY=pocketsmart_super_secret_jwt_key_2025_secure_random_string_99
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
PORT=8000
HOST=0.0.0.0
```
> *Note: If `GEMINI_API_KEY` is not provided, PocketSmart automatically runs in smart fallback mode with realistic Indian market allocations.*

### 4. Run the Application
```bash
python app.py
```
Or with Uvicorn:
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Open your browser and visit: **`http://localhost:8000`**

---

## 🔑 Demo User Credentials

| Username | Password | Role |
| :--- | :--- | :--- |
| `sai` | `password123` | Demo User (with seeded history) |
| `admin` | `admin123` | Administrator |

*You can also register a new account anytime via `/register`.*

---

## 📡 API Endpoints Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Landing page |
| `GET` / `POST` | `/login` | User login (form & cookie session) |
| `POST` | `/token` | OAuth2 Bearer token generation |
| `GET` / `POST` | `/register` | New user account creation |
| `GET` / `POST` | `/logout` | Session termination & cookie invalidation |
| `GET` | `/dashboard` | User dashboard |
| `GET` / `POST` | `/generate-home` or `/home-budget` | Generate Home Interior budget recommendations |
| `GET` / `POST` | `/generate-party` or `/party-budget` | Generate Party & Event budget recommendations |
| `GET` / `POST` | `/generate-jewelry` or `/jewelry-budget` | Multimodal Jewelry recommendations (supports image upload) |
| `GET` | `/history` | Recommendation history page |
| `GET` | `/recommendation-history` | JSON history API |
| `GET` | `/recommendation-details/{id}` | Full JSON details of a specific past recommendation |
| `GET` | `/session-info` | Active session metadata |

---

## 🧪 Testing

Run the automated integration test suite:
```bash
python test_app.py
```

---

## 📝 License
Developed as part of the SmartBridge / SmartInternz GenAI Program.
