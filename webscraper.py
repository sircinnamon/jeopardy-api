import pymongo
from bs4 import BeautifulSoup
import json
import requests
import dateparser
import re

def get_page(url):
	r = requests.get(url)
	data = r.text
	return BeautifulSoup(data, "html.parser")

def build_dict(soup):
	page_dict = {}
	page_dict["id"], page_dict["date"] = parse_game_title(soup.find(id="game_title").string)
	page_dict["comments"] = soup.find(id="game_comments").string or ''
	page_dict["contestants"] = parse_contestants(soup.find_all(class_="contestants"))
	page_dict["rounds"] = parse_rounds(soup.find_all(id=["jeopardy_round","double_jeopardy_round"]))
	return page_dict

def parse_game_title(game_title):
	#print(game_title)
	show_num = int(game_title.split()[1].replace('#',''))
	show_date = dateparser.parse(game_title.split('-')[1], languages=['en'])
	return show_num, show_date.isoformat()

def parse_contestants(contestant_list):
	contestants = list()
	for contestant in contestant_list:
		cont_dict = {}
		#print(contestant)
		cont_dict["id"] = contestant.a["href"].split('player_id=')[1]
		cont_dict["name"] = contestant.a.string
		cont_dict["bio"] = contestant.contents[1].replace(", ", "", 1)
		contestants.append(cont_dict)
	return contestants

def parse_rounds(rounds_list):
	rounds = list()
	for j_round in rounds_list:
		#print(j_round)
		r_dict = {}
		isDoubleJeopardy = j_round["id"] == "double_jeopardy_round"
		r_dict["double_jeopardy"] = isDoubleJeopardy
		r_dict["end_scores"] = parse_score_table(j_round.find_all("table")[-1])
		r_dict["board"] = parse_board(j_round.find("table"), isDoubleJeopardy)

		rounds.append(r_dict)
	return rounds

def parse_score_table(score_table):
	scores_list = list()
	for x, y in zip(score_table.contents[1].find_all("td"),
					score_table.contents[3].find_all("td")):
		scores_list.append({"player":x.string.strip(), "score":y.string.strip()})
	return scores_list

def parse_board(board, isDoubleJeopardy):
	#print(board)
	columns = list()
	counter = 0
	column_ids = "A B C D E F".split() if not isDoubleJeopardy else "G H I J K L".split()
	for category in board.find("tr").contents:
		if(category.name == "td"):
			#print(category)
			print(category.find_all(class_="category_name")[0].string)
			print(category.find_all(class_="category_comments")[0].string)

	return ""

for i in range(1,2):
	page = get_page("http://www.j-archive.com/showgame.php?game_id="+str(i))
	game = build_dict(page)
	print(str(game))
