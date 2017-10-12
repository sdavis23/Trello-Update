import requests
import json
import pprint
import datetime

import dateutil.parser

#globals that defines the keys, etc.
api_key = "e1dbefc801c245737f11408ff28187fb"

base_url = "https://api.trello.com/1/"

#Just some contants
CREATE_CARD_TYPE = "createCard"
UPDATE_CARD_TYPE = "updateCard"

done_synonyms = ["Done"]
started_synonyms = ["ToDo"]

def makeURL(resource, api_token):
	return base_url + resource + "&key=" + api_key + "&token=" + api_token 


def member_url(member_username, api_token):
	return makeURL("/members/" + member_username + 
				"?fields=id,username&boards=all&board_fields=id,name,date&board_lists=all&board_actions=createBoard", api_token)


def card_url(board_id, api_token):
	return  makeURL("/boards/" + board_id + "/cards?fields=id,name,idList,desc,idMembers&actions=updateCard:idList,createCard", api_token)


def trelloCardDictToObject(card_dict):
	return Card(card_dict['id'], card_dict['name'])

def trelloCardsDictToObjects(card_list):
	return map(trelloCardDictToObject, card_list )

#

def trelloListToObject(list):
	id = list['id']
	
	return TrelloList(id, list['name'] )


class Member:
	def __init__(self, username, api_token):
		
		self.username = username
		self.api_token = api_token

class Board:

	def __init__(self, member, id, name, lists, date):
		self.id = id
		self.name = name
		self.member = member
		self.date = date
		self.done_dict = {}
		self.doing_dict = {}


		# first, just get the lists that we need, and seperate into dictionaries.
		for l in lists :
		
			if l.name in done_synonyms :
				
				self.done_dict[l.id] = l

			elif l.name in started_synonyms :
				
				self.doing_dict[l.id] = l

			
	# takes in the card dictionaries, that come straight from the 
	# 	assumes the cards belong to the board, that this method is called on
	# also assumes that the cards: contains a group called actions and:
	# 	actions can fall into one of two categories: 
	#		a) New card
	#		b) updateCard:idList
	# returns a dict of tasks.
	def cardsToTasks(self, cards):

		tasks = []

		p = pprint.PrettyPrinter(indent=4)
		
		
		for card in cards:

			

			#print("Getting card: " + card['name'] + ", " + card['idList'])
			#print(self.done_dict)
			#print(self.doing_dict)

			list_id = card['idList']

			list = None
			is_done = False

			if list_id in self.done_dict :
				list = self.done_dict[list_id]
				is_done = True

			elif list_id in self.doing_dict :
				list = self.doing_dict[list_id]

			if list != None:

				actions = card['actions']

				#find the created date and the updated date
				created_date = dateutil.parser.parse(filter(lambda action: action['type'] == CREATE_CARD_TYPE, actions)[0]['date'])

				updated_actions = sorted(filter(lambda action: action['type'] == UPDATE_CARD_TYPE, actions), 
												key = lambda action: dateutil.parser.parse(action['date'] )  )
				actual_time = None
				updated_date = None

				#so long as an updated action exists,
				if len(updated_actions) > 0 :
					last_updated_action = updated_actions[len(updated_actions) - 1]
					updated_date = dateutil.parser.parse(last_updated_action['date'])
					actual_time  = (updated_date - created_date).total_seconds()


				#check if there is a member attached
				employee_trello_id = 0

				if len(card['idMembers']) > 0 :
					employee_trello_id= card['idMembers'][0]

				new_task = { 	"board_id": self.id, 
								"card_id": card['id'],
								"name": card['name'] ,
								"updated_date" : updated_date,
								"employee_trello_id": employee_trello_id,
								"actual_time": actual_time,
								"description": card['desc'],
								"done": is_done
					  		}

				tasks.append(new_task)

		return tasks
			

	def isProject(self):
		return len(self.done_dict) > 0 and len(self.doing_dict) > 0


	def printLists(self):
		for l in self.lists:
			l.prettyPrint()


def trelloBoardToObject(board, member):
	return Board(	member,
					board['id'], 
					board['name'], 
					map(trelloListToObject, board['lists'] ), 
					dateutil.parser.parse(board['actions'][0]['date']) )


def trelloListsDictToObjects(list):
	return map(trelloListToObject, list)

def trelloJSON(url):
	#requesting some of the data
	response = requests.request("GET", url)
	
	#p = pprint.PrettyPrinter(indent=4)
	#p.pprint(json.loads(response.text))
	return json.loads(response.text)


# Takes the Trello JSON defined by url, and applied func to it
def trelloJSONToObject(url, func):
	return func( trelloJSON(url) )


class Card:
	def __init__(self, id, name, created_date):
		self.id = id
		self.name = name


class TrelloList:

	def __init__(self, id, name):
		self.id = id
 		self.name = name
 		

 	def prettyPrint(self):
 		print("List Name: " + self.name)
 		

 	def printCards(self):
 		str = ""

 		for c in self.cards:
 			str = "	" + c.id + ", " + c.name + "\n"

 		return str




# filters a set of boards and returns a set the fulfills:
# 	the boards that have lists with at least one of done synynomns and start synonomns 
#	as a name.
def filterBoards(boards):
	for b in boards:
		print("Name Filter:")
		print(" 	" + b.name)
	return filter(lambda board: board.isProject(), boards)	


def grabMemberBoards(member):
	return filterBoards(trelloJSONToObject(member_url(member.username, member.api_token), 
						lambda member_json:  map(lambda b_json: trelloBoardToObject(b_json, member), member_json['boards'] ) ) ) 

# Takes in: a two dimensional array where the first
#	dimension corresponds to a member
# 	and the second dimension corresponds to a board
def flatten(list):
	return [item for sublist in list for item in sublist]

# takes a list of boards and returns a dictionary of UNIQUE boards.
#	the dictionary is indexed by board ids
# Two boards are said to be the same if: they have the same id
def uniqueBoards(boards):
	board_dict = {}

	for b in boards:
		if not (b.id in board_dict) :
			board_dict[b.id] = b

	return board_dict.values()



def boardToProject(board):
	return {
				"name": board.name,
				"location": board.name,
				"date_start": str(board.date),
				"board_id" : board.id }

# takes in a list of unique boards,
#	and returns a list of dictionaries that are ready to send
#	as JSON to the main server
def boardsToProjects(boards):
	return map(boardToProject  , boards)


def groupTasksByEmployee(tasks):
	task_dict = {}

	for t in tasks:

		if not (t['employee_trello_id'] in task_dict) : 
			task_dict[t['employee_trello_id']] = []

		task_dict[t['employee_trello_id']].append(t)


	return task_dict


def mapTaskToJSON(task):

	json_task = {

		 	"board_id": task['board_id'], 
			"card_id": task['card_id'],
			"name": task['name'] ,
			"employee_trello_id": task['employee_trello_id'],
			"actual_time": task['actual_time'],
			"description": task['description'],
			"done": task['done'] }

	return json_task


# Maps a dictionary of tasks into a json-ready dictionary
def mapTasksToJSON(tasks) :

	return map(mapTaskToJSON, tasks)



# takes in a dictionary indexed by employee_trello_ids 
# and returns an array of tasks where the actual_time is calculated properly 
def calculateTaskTime(employee_tasks) :

	ret_tasks = []

	for employee_task in employee_tasks.values() :

		done_tasks = filter(lambda task: task['updated_date'] != None, employee_task )
		not_done_tasks = filter(lambda task: task['updated_date'] == None, employee_task )

		print(done_tasks)

		
		ret_tasks.extend(calculateActualTime(done_tasks))

		ret_tasks.extend(not_done_tasks)

	return ret_tasks


# Given a list of tasks,
# calculates the time spent on each one.
def calculateActualTime(tasks):

	prev_task = None;

	

	sorted_tasks = sorted(tasks, key = lambda task: task['updated_date'])

	prev_task = sorted_tasks[0]


	date = prev_task["updated_date"]

	prev_task['actual_time'] = ( prev_task['updated_date'] - datetime.datetime(date.year, date.month, date.day, 9).replace(tzinfo=date.tzinfo) ).total_seconds()

	itertasks = iter(tasks)
	next(itertasks)

	for t in itertasks:


		if date.day == t['updated_date'].day :

			t['actual_time'] = abs(t['actual_time'] - prev_task['actual_time']) 
				
			prev_task = t

		else :

			date = t["updated_date"]
			prev_task = t

			prev_task['actual_time'] = ( prev_task['updated_date'] - datetime.datetime(date.year, date.month, date.day, 9).replace(tzinfo=date.tzinfo)).total_seconds()

	return sorted_tasks


	
# takes a list of members and finds all of
# the tasks and boards on trello,
# 	and converts it into two dictionary containing two arrays
# projects - is the list of ready to convert to JSON projects
# tasks - the list of associated tasks
def membersToProjectTaskDictionary(members) :
	board_array = uniqueBoards(flatten(map(grabMemberBoards, members)))
	
	p = pprint.PrettyPrinter(indent=4)
	json_members = []

	flat_boards = flatten(map(lambda board: board.cardsToTasks(trelloJSON(card_url(board.id, board.member.api_token))), board_array))

	employee_tasks = groupTasksByEmployee(flat_boards)

	tasks = mapTasksToJSON(calculateTaskTime(employee_tasks))

	

	project_list = boardsToProjects(board_array)
	project_dict = {}

	for p in project_list:
		project_dict[p['board_id']] = p


	for m in members :
		
		json_m = trelloJSON(member_url(m.username, m.api_token))
		
		json_members.append({"username": m.username, "id": json_m['id']})

	return { 
		"members" : json_members,
		"projects": project_dict ,
		"tasks": filter( lambda task: len(task) > 0 , tasks)}



p = pprint.PrettyPrinter(indent=4)

members = map(	lambda emp: Member( emp['trello_username'], emp['trello_token']), 

				filter(	lambda emp: len(emp['trello_username']) > 0 and len(emp['trello_token']) > 0, 
						trelloJSON("http://timetickets.onsite3d.com/employee_trello")  ) )


#member_objects = [0] * len(members)

#member_index = 0
#token_index = 0

#while member_index < len(members) :
#	member_objects[member_index] = Member(members[member_index], tokens[token_index])
#	member_index = member_index + 1
#	token_index = token_index + 1


# grab all of the boards that correspond to a project

json_dict = membersToProjectTaskDictionary(members) 

print("***Employee Receiving")
p.pprint(trelloJSON("http://timetickets.onsite3d.com/employee_trello"))

print("****Sending: ")
p.pprint(json_dict)

print("***Receiving: ")
response = requests.post("http://www.timetickets.onsite3d-internal.com/project_trello_update", json=json_dict)
p.pprint(response.text)
p.pprint(json.loads(response.text))

#boards = map(lambda board: trelloBoardToObject(board), boards)


