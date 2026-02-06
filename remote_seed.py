import requests

BASE_URL = "https://interactive-story-api-dylv.onrender.com"


def seed_remote_db():
    print(f"Connecting to {BASE_URL}...")

    # 1. Create a Story
    story_data = {
        "title": "The Cloud Deployment",
        "description": "You successfully deployed to Render. Now, can you survive the latency?",
        "status": "published"
    }
    r = requests.post(f"{BASE_URL}/stories", json=story_data)
    if r.status_code != 201:
        print("Failed to create story:", r.text)
        return
    story = r.json()
    print(f"Created Story: {story['title']} (ID: {story['id']})")

    # 2. Create Pages
    p1_data = {"text": "You open your browser to check the live site. It loads...", "is_ending": False}
    p1 = requests.post(f"{BASE_URL}/stories/{story['id']}/pages", json=p1_data).json()

    p2_data = {"text": "It works! The JSON loads perfectly.", "is_ending": True, "ending_label": "Success"}
    p2 = requests.post(f"{BASE_URL}/stories/{story['id']}/pages", json=p2_data).json()

    p3_data = {"text": "500 Internal Server Error. You forgot to set the environment variable.", "is_ending": True,
               "ending_label": "Fail"}
    p3 = requests.post(f"{BASE_URL}/stories/{story['id']}/pages", json=p3_data).json()

    # 3. Create Choices
    requests.post(f"{BASE_URL}/pages/{p1['id']}/choices", json={
        "text": "Check the logs", "next_page_id": p2['id']
    })
    requests.post(f"{BASE_URL}/pages/{p1['id']}/choices", json={
        "text": "Panic and redeploy", "next_page_id": p3['id']
    })

    # 4. Update Story Start Page
    requests.put(f"{BASE_URL}/stories/{story['id']}", json={"start_page_id": p1['id']})

    print("Cloud database seeded successfully!")


if __name__ == "__main__":
    seed_remote_db()