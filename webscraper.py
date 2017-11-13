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
			column_dict = {"id":column_ids[counter], "category":{}} 
			column_dict["category"]["category_name"] = category.find_all(class_="category_name")[0].string
			column_dict["category"]["category_comments"] = category.find_all(class_="category_comments")[0].string
			questions = list()
			column_dict["questions"] = questions
			columns.append(column_dict)
			counter = counter+1
	y = 0
	for row in board.find("tr").next_siblings:
		if(row.name=="tr"):
			x = 0
			for clue in row.find_all(class_="clue"):
				clue_obj = parse_clue(clue,column_ids[x],y)
				if(clue_obj != None): columns[x]["questions"].append(clue_obj)
				x=x+1
			y=y+1
	return columns

def parse_clue(clue, column, row):
	clue_dict = {}
	clue_dict["id"] = column+str(row)
	if(len(clue.find_all(class_="clue_text")) == 0):
		return None;
	clue_dict["is_daily_double"] = (len(clue.find_all(class_="clue_value_daily_double"))!=0)
	clue_dict["value"] = clue.find_all(class_=["clue_value","clue_value_daily_double"])[0].string
	clue_dict["order"] = clue.find_all(class_="clue_order_number")[0].string
	clue_dict["clue_text"] = clue.find_all(class_="clue_text")[0].string
	answer = BeautifulSoup(clue.find("div")["onmouseover"].split("_stuck', '")[1][:-2].replace("\\",""),"html.parser")
	clue_dict["answer"] = answer.find(class_="correct_response").string
	clue_dict["triple_stumper"] = (len(answer.find_all(class_="wrong")) != 0 and answer.find_all(class_="wrong")[-1].string=="Triple Stumper")
	clue_dict["right"], clue_dict["wrong"] = parse_right_wrong(answer.find("table"))
	clue_dict["comments"] = parse_answer_comments(answer)
	#print(answer)
	#print(clue_dict)
	#print("\n")
	return clue_dict

def parse_right_wrong(table):
	wrong = list()
	right = None
	for answer in table.find_all("td"):
		#print(answer)
		if "wrong" in answer["class"] and answer.string != "Triple Stumper":
			wrong.append(answer.string)
		elif "right" in answer["class"]:
			right = answer.string
	return right, wrong

def parse_answer_comments(answer):
	comments = ""
	for element in answer.contents:
		if(str(element).startswith("<em")):
			#print(comments)
			return comments
		comments = comments+str(element).replace("<br/>","")
	return comments
	#curr = answer.find_all(class_="correct_response")
	#while

for i in range(1,2):
	page = get_page("http://www.j-archive.com/showgame.php?game_id="+str(i))
	game = build_dict(page)
	print(str(game))
