import requests

URL = 'http://127.0.0.1:5000'

#       Пользователи
# response = requests.post(
#     f"{URL}/user/",
#     json={
#         "email": "a1@b.c",
#         "password": "ajdgouhiweuhr"
#     }
# )

# response = requests.post(
#     f"{URL}/login/",
#     json={
#         "email": "a1@b.c",
#         "password": "ajdgouhiweuhr"
#     }
# )

# response = requests.get(f"{URL}/user/1")

#      Объявления
# headers = {
#     "email": "a1@b.c",
#     "token": "9cb5ce94-cf5e-4284-beaf-42627c8ef2bc"
# }
# response = requests.post(
#     f'{URL}/',
#     headers=headers,
#     json={"title": "some title",
#           "description": "some desc"
#           }
# )

# response = requests.get(f'{URL}/2/')

# response = requests.get(f'{URL}/')

# response = requests.patch(
#     f'{URL}/2/',
#     headers=headers,
#     json={
#         "description": "new desc 1"
#     }
# )

# response = requests.delete(f'{URL}/2/')


print(response.status_code)
print(response.json())
