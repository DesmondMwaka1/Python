import requests
from bs4 import BeautifulSoup

key="9632499936921768aac8162a7205cd84"
# url=f"https://api.sportmonks.com/v3/football/schedules/teams/{id}?api_token={token}"
# response = requests.get(url)

url = "https://v3.football.api-sports.io/leagues"

payload={}
headers = {
  'x-apisports-key': f'{key}',
}

response = requests.request("GET", url, headers=headers, data=payload)

print(response.text)