import requests

URL = 'http://127.0.0.1:5000'

# response = requests.post(
#     f'{URL}/adv/',
#     json={"title": "some title",
#           "description": "some desc",
#           "owner": "smbd"
#           })

# response = requests.get(f'{URL}/adv/2/')

# response = requests.get(f'{URL}/adv/')

response = requests.delete(f'{URL}/adv/10/')

print(response.status_code)
print(response.json())
