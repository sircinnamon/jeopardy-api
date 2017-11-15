import pymongo
from pymongo import MongoClient
from bs4 import BeautifulSoup
import json
import requests
import dateparser
import re
import sys

def get_page(url):
	r = requests.get(url)
	data = r.text
	return BeautifulSoup(data, "html.parser")

def build_dict(soup, season_id):
	page_dict = {}
	#print(soup)
	page_dict["_id"], page_dict["date"] = parse_game_title(parse_text(soup.find(id="game_title")), season_id)
	page_dict["comments"] = soup.find(id="game_comments").string or ''
	page_dict["contestants"] = parse_contestants(soup.find_all(class_="contestants"))
	page_dict["rounds"] = parse_rounds(soup.find_all(id=["jeopardy_round","double_jeopardy_round"]), page_dict["_id"])
	page_dict["final_round"] = parse_final_round(soup.find(id="final_jeopardy_round"), page_dict["_id"])
	return page_dict

def parse_game_title(game_title, season_id):
	#print(game_title)
	if "Super Jeopardy" in game_title:
		season_id = "SJ"
	elif "pilot" in game_title:
		season_id = "P"
	show_num = game_title.split()[1].replace('#','')
	show_date = dateparser.parse(game_title.split('-')[1], languages=['en'])
	return season_id+show_num, show_date.isoformat()

def parse_contestants(contestant_list):
	contestants = list()
	for contestant in contestant_list:
		cont_dict = {}
		#print(contestant)
		cont_dict["_id"] = contestant.a["href"].split('player_id=')[1]
		cont_dict["name"] = contestant.a.string
		cont_dict["bio"] = contestant.contents[1].replace(", ", "", 1)
		contestants.append(cont_dict)
	return contestants

def parse_rounds(rounds_list, game_id):
	rounds = list()
	for j_round in rounds_list:
		#print(j_round)
		# print("^^^^")
		r_dict = {}
		isDoubleJeopardy = j_round["id"] == "double_jeopardy_round"
		r_dict["double_jeopardy"] = isDoubleJeopardy
		r_dict["end_scores"] = parse_score_table(j_round.find_all("table")[-1])
		r_dict["board"] = parse_board(j_round.find("table"), isDoubleJeopardy, game_id)

		rounds.append(r_dict)
	return rounds

def parse_score_table(score_table):
	scores_list = list()
	# print(score_table)
	# print("###########")
	for x, y in zip(score_table.contents[1].find_all("td"),
					score_table.contents[3].find_all("td")):
		scores_list.append({"player":x.string.strip(), "score":y.string.strip()})
	return scores_list

def parse_board(board, isDoubleJeopardy, game_id):
	#print(board)
	columns = list()
	counter = 0
	column_ids = "A B C D E F".split() if not isDoubleJeopardy else "G H I J K L".split()
	for category in board.find("tr").contents:
		if(category.name == "td"):
			#print(category)
			column_dict = {"_id":game_id+'.'+column_ids[counter], "category":{}} 
			column_dict["category"]["category_name"] = parse_text(category.find(class_="category_name"))
			column_dict["category"]["category_comments"] = category.find(class_="category_comments").string
			questions = list()
			column_dict["questions"] = questions
			columns.append(column_dict)
			counter = counter+1
	y = 0
	for row in board.find("tr").next_siblings:
		if(row.name=="tr"):
			x = 0
			for clue in row.find_all(class_="clue"):
				clue_obj = parse_clue(clue,game_id+'.'+column_ids[x],y)
				if(clue_obj != None): columns[x]["questions"].append(clue_obj)
				x=x+1
			y=y+1
	return columns

def parse_clue(clue, column, row):
	clue_dict = {}
	clue_dict["_id"] = column+str(row)
	if(len(clue.find_all(class_="clue_text")) == 0):
		return None;
	clue_dict["is_daily_double"] = (len(clue.find_all(class_="clue_value_daily_double"))!=0)
	clue_dict["value"] = clue.find(class_=["clue_value","clue_value_daily_double"]).string.replace("DD: ","")
	clue_dict["order"] = clue.find(class_="clue_order_number").string
	clue_dict["clue_text"] = parse_text(clue.find(class_="clue_text"))
	answer = BeautifulSoup(clue.find("div")["onmouseover"].split("_stuck', '")[1][:-2].replace("\\",""),"html.parser")
	clue_dict["answer"] = parse_text(answer.find(class_="correct_response"))
	clue_dict["triple_stumper"] = (len(answer.find_all(class_="wrong")) != 0 and answer.find_all(class_="wrong")[-1].string=="Triple Stumper")
	clue_dict["right"], clue_dict["wrong"] = parse_right_wrong(answer.find("table"))
	clue_dict["comments"] = parse_answer_comments(answer)
	external_info = clue.find(class_="clue_text").find_all("a")
	clue_dict["external_info"] = list()
	for link in external_info:
		clue_dict["external_info"].append({"text":parse_text(link), "link":link["href"]})
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
		if(str(element).startswith("<em") or str(element).startswith("<table>")):
			#print(comments)
			return comments
		if(element.string != None):
			comments = comments+element.string
		else:
			comments = comments+parse_text(element)

def parse_final_round(final_round, game_id):
	r_dict = {}
	category_name = parse_text(final_round.find(class_="category_name"))
	category_comments = final_round.find(class_="category_comments").string
	r_dict["end_scores"] = parse_final_score_table(final_round.find(class_="score_player_nickname").parent.parent)
	r_dict["category"] = 	{"category_name":category_name,
							"category_comments":category_comments,
							"_id":game_id+".M"}
	answer = str(final_round.find("div")["onmouseover"]).split("_stuck', '")[1][:-2].replace("\\","")
	r_dict["clue"] = parse_final_clue(final_round.find(class_="clue"), answer, r_dict["category"]["_id"])

	return r_dict

def parse_final_score_table(table):
	scores_list = list()
	if(len(table.contents) < 6):
		#there is no comments table
		#insert a blank one
		table.insert(5, BeautifulSoup("<tr><td></td><td></td><td></td></tr>", "html.parser"))
	for x, y, z in zip(table.contents[1].find_all("td"),
					table.contents[3].find_all("td"),
					table.contents[5].find_all("td")):
		#print(str(x.string)+" "+str(y.string)+" "+str(z.string))
		x = x.string
		y = y.string
		z = z.string
		if z == None:
			z = " "
		scores_list.append({"player":x.strip(), "score":y.strip(),"comments":z.strip()})
	#print(scores_list)
	return scores_list

def parse_final_clue(clue, answer, category_id):
	#print(clue)
	clue_dict = {}
	clue_dict["_id"] = category_id+"1"
	clue_dict["clue_text"] = parse_text(clue.find(class_="clue_text"))
	answer = BeautifulSoup(answer, "html.parser")
	#print(answer)
	clue_dict["answer"] = parse_text(answer.find(class_="correct_response"))
	clue_dict["responses"] = parse_final_clue_responses(answer)
	clue_dict["comments"] = parse_answer_comments(answer)
	return clue_dict

def parse_final_clue_responses(answer):
	response_list = list()
	response_count = int(len(answer.find("table").find_all("tr"))/2)
	for i in range(0,response_count):
		resp_dict = {}
		resp_dict["player"] = answer.find("table").find_all("tr")[2*i].contents[0].string
		resp_dict["response"] = parse_text(answer.find("table").find_all("tr")[2*i].contents[1])
		resp_dict["wager"] = answer.find("table").find_all("tr")[(2*i)+1].contents[0].string
		resp_dict["correct"] = ("right" in answer.find("table").find_all("tr")[2*i].contents[0]["class"])
		response_list.append(resp_dict)
		#print(resp_dict)
	return response_list

def parse_text(tag):
	full_string = ""
	for string in tag.strings:
		full_string = full_string+string
	return full_string

def validate_game_data(game):
	if game["_id"] == None: return "game _id"
	if game["date"] == None: return "game date"
	for contestant in game["contestants"]:
		if contestant["_id"] == None: return "contestant _id"
		if contestant["name"] == None: return "contestant name"
		if contestant["bio"] == None: return "contestant bio"
	for round_ in game["rounds"]:
		for end_score in round_["end_scores"]:
			if end_score["player"] == None: return "round end_score player"
			if end_score["score"] == None: return "round end_score score"
		for column in round_["board"]:
			if column["category"]["category_name"] == None: return "round column category_name"
			if column["_id"] == None: return "round column _id"
			for question in column["questions"]:
				if question["_id"] == None: return "round column question _id"
				if question["clue_text"] == None: return "round column question clue_text"
				if question["value"] == None: return "round column question value"
				if question["order"] == None: return "round column question order"
				for link in question["external_info"]:
					if link["text"] == None: return "round column question external_info text"
					if link["link"] == None: return "round column question external_info link"
	for score in game["final_round"]["end_scores"]:
		if score["player"] == None: return "final_round end_scores player"
		if score["score"] == None: return "final_round end_scores player"
	if game["final_round"]["category"]["_id"] == None: return "final_round category _id"
	if game["final_round"]["category"]["category_name"] == None: return "final_round category category_name"
	if game["final_round"]["clue"]["_id"] == None: return "final_round clue _id"
	if game["final_round"]["clue"]["clue_text"] == None: return "final_round clue clue_text"
	if game["final_round"]["clue"]["answer"] == None: return "final_round clue answer"
	for response in game["final_round"]["clue"]["responses"]:
		if response["player"] == None: return "final_round clue response player"
		if response["response"] == None: return "final_round clue response response"
		if response["wager"] == None: return "final_round clue response wager"
		if response["correct"] == None: return "final_round clue response correct"
	return ""

client = MongoClient()
db = client.jeopardy
docs = db.games
#gameset = [940]
gameset = range(1000,2000)
broken_pages = [30,60,705,327,320]
super_jeopardy = [1347, 1933, 1348, 948, 940, 1936, 1349, 1212, 1940, 1970, 1982, 1985, 1022]
pilots = [1309,1317] 
for i in gameset:
	if i not in broken_pages and i not in super_jeopardy and i not in pilots:
		print("#########################")
		print(i)
		try:
			page = get_page("http://www.j-archive.com/showgame.php?game_id="+str(i))
			game = build_dict(page, '')
			#print(game)
			test = validate_game_data(game)
		except:
			print(sys.exc_info()[0])
			print("VVVV")
			print(page)
			print("^^^^")
			test = "ERROR"
			# raise
		if(test != ""):
			print(i)
			print(test)
			print(game)
		else:
			#print("success")
			print(docs.insert_one(game).inserted_id)
		#print(str(game))
		# for category in game["rounds"][0]["board"]:
			# for clue in category["questions"]:
			# 	print(clue["_id"])
			# 	print(clue["value"])
			# 	print(clue["clue_text"])
			# 	print(clue["answer"])
			# 	print("Comment: "+clue["comments"])
			# 	print(clue["external_info"])
			# 	print("-------------------")
			# print(category["_id"])
			# print(category["category"]["category_name"])
			# print(category["category"]["category_comments"])
			# print("###################\n\n")
		# for category in game["rounds"][1]["board"]:
			# for clue in category["questions"]:
			# 	print(clue["_id"])
			# 	print(clue["value"])
			# 	print(clue["clue_text"])
			# 	print(clue["answer"])
			# 	print("Comment: "+clue["comments"])
			# 	print(clue["external_info"])
			# 	print("-------------------\n\n")
			# print(category["_id"])
			# print(category["category"]["category_name"])
			# print(category["category"]["category_comments"])
			# print("###################\n\n")
		# print(game["final_round"]["category"]["category_name"])
		# print(game["final_round"]["clue"]["_id"])
		# print(game["final_round"]["clue"]["clue_text"])
		# print(game["final_round"]["clue"]["answer"])
		# print(game["final_round"]["clue"]["responses"])
		# print("-------------------")
