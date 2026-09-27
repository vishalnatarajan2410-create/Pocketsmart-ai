import asyncio
import io
from fastapi.testclient import TestClient
from app import app, users_db

client = TestClient(app)

def test_all_routes():
    print("1. Testing GET Landing page...")
    res = client.get("/")
    assert res.status_code == 200, f"Landing failed: {res.status_code}"
    print("Landing OK!")

    print("2. Testing Login page & Authentication...")
    res = client.get("/login")
    assert res.status_code == 200
    
    # Login as demo user 'sai'
    login_res = client.post("/login", data={"username": "sai", "password": "password123"}, follow_redirects=False)
    assert login_res.status_code == 302, f"Login failed: {login_res.status_code}"
    cookies = login_res.cookies
    print("Login OK! Cookie obtained.")

    print("3. Testing Dashboard...")
    res = client.get("/dashboard", cookies=cookies)
    assert res.status_code == 200
    print("Dashboard OK!")

    print("4. Testing Home Planner GET & POST...")
    res = client.get("/home-planner", cookies=cookies)
    assert res.status_code == 200
    
    post_home = client.post("/generate-home", json={
        "total_budget": 60000,
        "num_lights": 6,
        "num_fans": 3,
        "num_furniture": 3,
        "num_dining_tables": 1,
        "has_living_room": True,
        "has_kitchen": True,
        "has_bedroom": True,
        "additional_requirements": "Warm lighting"
    }, cookies=cookies)
    assert post_home.status_code == 200, f"Home POST failed: {post_home.text}"
    home_json = post_home.json()
    assert "budget_breakdown" in home_json
    print(f"Home Planner OK! Categories: {len(home_json['budget_breakdown'])}, Remaining: INR {home_json['remaining_budget']}")

    print("5. Testing Party Planner GET & POST...")
    res = client.get("/party-planner", cookies=cookies)
    assert res.status_code == 200
    
    post_party = client.post("/generate-party", json={
        "total_budget": 30000,
        "num_guests": 20,
        "party_type": "Birthday",
        "venue_type": "Banquet Hall",
        "needs_catering": True,
        "needs_decoration": True,
        "needs_entertainment": True,
        "additional_requirements": "Vegetarian buffet"
    }, cookies=cookies)
    assert post_party.status_code == 200, f"Party POST failed: {post_party.text}"
    party_json = post_party.json()
    assert "budget_breakdown" in party_json
    print(f"Party Planner OK! Allocations: {len(party_json['budget_breakdown'])}, Remaining: INR {party_json['remaining_budget']}")

    print("6. Testing Jewelry Planner GET & POST...")
    res = client.get("/jewelry-planner", cookies=cookies)
    assert res.status_code == 200
    
    post_jewelry = client.post("/generate-jewelry", data={
        "total_budget": 20000,
        "occasion": "Wedding Reception",
        "preferences": "Traditional gold and pearl"
    }, cookies=cookies)
    assert post_jewelry.status_code == 200, f"Jewelry POST failed: {post_jewelry.text}"
    jewelry_json = post_jewelry.json()
    assert "jewelry_recommendations" in jewelry_json
    print(f"Jewelry Planner OK! Items: {len(jewelry_json['jewelry_recommendations'])}")

    print("7. Testing History GET & Details API...")
    res = client.get("/history", cookies=cookies)
    assert res.status_code == 200

    hist_api = client.get("/recommendation-history", cookies=cookies)
    assert hist_api.status_code == 200
    hist_json = hist_api.json()
    assert len(hist_json["history"]) > 0
    first_id = hist_json["history"][0]["id"]
    
    detail_res = client.get(f"/recommendation-details/{first_id}", cookies=cookies)
    assert detail_res.status_code == 200
    print(f"History API OK! Total history records: {len(hist_json['history'])}")

    print("8. Testing Session Info...")
    sess_res = client.get("/session-info", cookies=cookies)
    assert sess_res.status_code == 200
    print(f"Session info OK! Username: {sess_res.json()['username']}")

    print("\nALL BACKEND & FRONTEND TESTS PASSED SUCCESSFULLY! [OK]")

if __name__ == "__main__":
    test_all_routes()
