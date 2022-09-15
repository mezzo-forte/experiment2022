
import re
from flask import Flask, redirect, url_for, render_template, session, request
from flask_socketio import SocketIO, send, join_room, leave_room
import random
import eventlet
import logging 
import string
import json
from dotenv import load_dotenv
from datetime import date, datetime
import os
import asyncio
from collections import Counter
import random
import admin

  
def id_generator():
    return "".join([random.choice(string.ascii_letters
            + string.digits) for n in range(10)])

def load_data(path):
    with open(path, 'r', encoding="utf-8") as f:
        return json.loads(f.read())

def save_json(path, data):
    with open(path, "w") as f:
        f.write(json.dumps(data, indent=2))

def create_dir_if_not_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)

def create_if_not_exists(path, default_content):
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(json.dumps(default_content))
            f.close()

def group_assigner(group_counter, current_group_number, group_size):
    if group_counter == 0:
        group_counter = 1
        current_group_number = 1
            
    elif group_counter < group_size:
        group_counter += 1

    elif group_counter == group_size:
        group_counter = 1
        current_group_number += 1
    return group_counter, current_group_number

# income without endowment and taxes but subcidies added
def gross_income_calculator(model, correct_tasks, period):
    if model == "UBI":
        income = amount_UBI*period + correct_tasks * wage_rate  
    elif model == "WS":
        income = correct_tasks * wage_rate * (1 + subsidy_rate_WS)
    elif model == "UBIWS":
        income = amount_UBIWS * period + correct_tasks * wage_rate * (1 + subsidy_rate_UBIWS)
    return income

def income_after_taxes_calculator(model, taxation_system, paid_hours, endowment, period):
    if taxation_system == "Income":
        tax_income = 0.25
        tax_endowment = 0
    elif taxation_system == "Endowment":
        tax_income = 0
        tax_endowment = 0.25

    if model == "UBI":
# Income which is taxed and not taxed
        if (paid_hours * wage_rate + endowment) < (amount_UBI * total_work_units + total_work_units * wage_rate)*poverty_threshold:
            income = amount_UBI * period + endowment + paid_hours * wage_rate 
        else: 
            income = amount_UBI * period + endowment * (1 - tax_endowment) + paid_hours * wage_rate * (1 - tax_income)
    elif model == "WS":
        if (endowment + paid_hours * wage_rate * (1 + subsidy_rate_WS)) < (total_work_units * wage_rate * (1 + subsidy_rate_WS)) * poverty_threshold:
            income = endowment + paid_hours * wage_rate * (1 + subsidy_rate_WS)
        else: 
            income = endowment * (1 - tax_endowment) + paid_hours * wage_rate * (1 + subsidy_rate_WS - tax_income)
    elif model == "UBIWS":
        if (amount_UBIWS * period + endowment + paid_hours * wage_rate * (1 + subsidy_rate_UBIWS)) < (amount_UBIWS * total_work_units + total_work_units * wage_rate)*poverty_threshold:
            income = amount_UBIWS * period + endowment + paid_hours * wage_rate * (1 + subsidy_rate_UBIWS)
        else: 
            income = amount_UBIWS * period + endowment*(1-tax_endowment) + paid_hours * wage_rate * (1 + subsidy_rate_UBIWS - tax_income) 

    return income


def endowment_distributor():
    endowment = random.randrange(endowment_minimum, endowment_maximum, 100)
    return endowment    

# Chat functions

# def handle_message(message):
#     print("Received message: " + message)
#     if message != 'User connected!':
#         send(message, broadcast = True)


# def add_user (username, roomname, sid):
#     user = {'name': username.upper(), 'room': roomname.upper(), 'sid': sid}
#     join_room(roomname)
#     users[sid] = user


# def get_user_by_sid(sid):
#     if sid in users:
#         return users[sid]
#     return None


# def get_user_by_name(name):
#     for key, value in users.items():
#         if value['name'] == name.upper():
#             return value
#     return None


# def get_all_users(roomname):
#     all_users = []
#     for key, value in users.items():
#         if value['room'] == roomname.upper():
#             all_users.append(value['name'])
#     return all_users 


async def voting_calculator(group_size, *group_id):
    while True: 
        voting_dict=load_data(path_voting_dict)
        if len(voting_dict[session['Group']]) < group_size:
            print(f"{session['Subject']} has voted. Entries in voting_dict: {voting_dict[session['Group']]}")
            await asyncio.sleep(2)
        else: 
            votes = Counter(voting_dict[session['Group']]).most_common()
            print (votes)
            group_voted_for = votes[0][0]
            break 
    return group_voted_for


async def voting_unanimity(group_size, path_dict, *group_id):
    while True: 
        voting_dict=load_data(path_dict)
        if len(voting_dict[session['Group']]) < group_size:
            print(f"{session['Subject']} has voted. Entries in voting_dict: {voting_dict[session['Group']]}")
            await asyncio.sleep(2)
        else: 
            votes = Counter(voting_dict[session['Group']]).most_common()
            print (votes)
            if len(votes) == 1:
                group_voted_for = votes[0][0]
                break
            else:
                group_voted_for = "Revote"
                voting_dict.pop(session['Group'])
                save_json(path_dict, voting_dict)
                break 
    return group_voted_for

async def voting_majority(group_size,path_dict, *group_id):
    while True: 
        voting_dict=load_data(path_dict)
        if len(voting_dict[session['Group']]) < group_size:
            print(f"{session['Subject']} has voted. Entries in voting_dict: {voting_dict[session['Group']]}")
            await asyncio.sleep(2)
        else: 
            votes = Counter(voting_dict[session['Group']]).most_common()
            print (votes)
            group_voted_for = votes[0][0]
            break 
    return group_voted_for

# eventlet.monkey_patch()
app = Flask(__name__)
load_dotenv()
app.secret_key=os.getenv('TOKEN')
socketio = SocketIO(app, logger=True, engineio_logger=True)
# socketio = SocketIO(app, cors_allowed_origins="*")
# socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")
users = {}

number_of_questions_1_stage = 12
number_of_questions_2_stage = 12
estimated_time_for_1_stage = 5
estimated_time_for_2_stage = 5 
estimated_time_for_voting = 2
estimated_time_for_voting_ind = 1
estimated_time_questionnaire = 5
amount_UBI = 100
amount_UBIWS = 50
subsidy_rate_UBIWS = 0.25
subsidy_rate_WS = 0.50
# wage_rate = salary per month (1 working period/each task) 
wage_rate = 200
poverty_threshold = 0.15
work_unit_multiplicator = 40
working_time = 1 
cutoff_income = 153
tax_rate = 0.25
group_size = 1
switching_attempts = 3
total_work_units = 12
amount_tasks_per_stage = 12
lower_range = 0
# ENDOWMENT calculated twice
upper_range = 300
endowment_minimum = 0
endowment_maximum = int(wage_rate * total_work_units) 

path_data_folder = os.path.join(os.getcwd(), 'data')
path_subjects_folder = os.path.join(os.getcwd(), 'data/subjects')
path_subjects_recovered_folder = os.path.join(os.getcwd(), 'data/subjects_recovered')
path_chat_folder=os.path.join(os.getcwd(), 'data/chat')
path_maths = os.path.join(os.getcwd(), 'maths.json')
path_maths2 = os.path.join(os.getcwd(), 'maths2.json')
path_main_dict = os.path.join(path_data_folder, 'info.json')
path_groups_content_dict = os.path.join(path_data_folder, 'group_content.json')
path_voting_dict = os.path.join(path_data_folder, 'voting.json')
path_voting_taxation_dict = os.path.join(path_data_folder, 'voting_taxation.json')
path_trivia_content = os.path.join(os.getcwd(), 'trivia.json')
path_trivia_answers = os.path.join(os.getcwd(), 'trivia_answers.json')

create_dir_if_not_exists(path_subjects_folder)

# current_task=Tasks()

tasks_database = load_data(path_maths)
tasks_content = list(tasks_database.keys())
tasks_answers = list(tasks_database.values())
trivia_content_dict = load_data(path_trivia_content)
trivia_content = list(trivia_content_dict.keys())
trivia_content_options = list(trivia_content_dict.values())
trivia_answers_list=load_data(path_trivia_answers)

countries = load_data(os.path.join(os.getcwd(), 'countrylist.json'))

group_dict = {}
group_full = 0
group_full_same_type_counter = {}
voting_dict = {}
voting_taxation_dict = {}
low_group_counter = 0
high_group_counter = 0
current_low_group_number = 0
current_high_group_number = 0
current_group = 0





@app.route("/")
def home():
    create_if_not_exists(path_main_dict,{"Subjects":[]})
    data_dict=load_data(path_main_dict)
    if 'Subject' not in session:
        
        session['Subject'] = id_generator()
        path_subject_file=os.path.join(path_subjects_folder, f'{session["Subject"]}.json')
        create_if_not_exists(path_subject_file, {})
        dummy_dict = load_data(path_subject_file)
        data_dict['Subjects'].append(session['Subject'])
        dummy_dict['Subject']=session['Subject']
        save_json(path_subject_file, dummy_dict)
        save_json(path_main_dict,data_dict)
        # session['Model'] = model_distributor()
    elif 'Subject' in session and 'Subject' not in data_dict['Subjects']:
        path_subject_file=os.path.join(path_subjects_folder, f'{session["Subject"]}.json')
        create_if_not_exists(path_subject_file, {})
        dummy_dict = load_data(path_subject_file)
        data_dict['Subjects'].append(session['Subject'])
        dummy_dict['Subject']=session['Subject']
        save_json(path_subject_file, dummy_dict)
        save_json(path_main_dict,data_dict)
        
    return render_template("index.html")

@app.route("/description/")
def description():
    return render_template("description.html", amount1 = number_of_questions_1_stage, amount2 = number_of_questions_2_stage, time0 = estimated_time_for_voting, time1 = estimated_time_for_1_stage, time2 = estimated_time_for_2_stage, time3 = estimated_time_for_voting_ind, time4 = estimated_time_questionnaire)

# Add one text of app.route for each page 
# after def the name should be unique for each page

@app.route("/land/", methods = ['POST', 'GET'])
def land_choice():
    if request.method == 'POST':
        if 'Country' not in session:
            dummy_dict = load_data(path_main_dict)
            session['Country']=request.form['country']
            
            if 'Tier_count' not in dummy_dict:
                dummy_dict['Tier_count']={"High":0, "Low":0}

            if 'Subjects_amount' not in dummy_dict:
                dummy_dict['Subjects_amount'] = 1
            else: 
                dummy_dict['Subjects_amount'] += 1
            
            session['Subject_number_overall']=dummy_dict['Subjects_amount']
            high_income_countries=load_data(os.path.join(os.getcwd(), 'high_income.json'))
            if session['Country'] in high_income_countries:
                session['Land_income_tier']="high"
                dummy_dict['Tier_count']['High'] += 1
                session['Subject_number_tier'] = dummy_dict['Tier_count']['High']
            else: 
                session['Land_income_tier']="low"
                dummy_dict['Tier_count']['Low'] += 1
                session['Subject_number_tier'] = dummy_dict['Tier_count']['Low']
            
            save_json(path_main_dict, dummy_dict)
            return redirect('/model1')
        else:
            return render_template ('landchosen.html', country=session['Country'])
    elif 'Country' in session:
        return redirect('/model1')
    else:
        # to-do? hide the block "select" and inform that country has been chosen?
        return render_template('landincome.html', countries=countries)


@app.route("/model1/")
def model_distributor():
    if 'Model' not in session:
        session['Stage']="Constitutional"
        path_subject_file=os.path.join(path_subjects_folder, f'{session["Subject"]}.json')       
        subject_dict=load_data(path_subject_file)
        subject_dict['Country']=session['Country']
        subject_dict['Land_income_tier']=session['Land_income_tier']
        subject_dict['Subject_number_tier']=session['Subject_number_tier']
        
        # session['ModelTime']=datetime.utcnow().isoformat()
        # session['ModelReturn'] = 0
        create_if_not_exists(path_groups_content_dict,{})
        groups_content_dict=load_data(path_groups_content_dict)
        dummy_dict = load_data(path_main_dict)

# ASSIGNING THE GROUP
        if subject_dict['Land_income_tier'] == "high":
            if 'High_group_counter' not in dummy_dict:
                dummy_dict['High_group_counter']=0
            if 'Current_high_group_number' not in dummy_dict:
                dummy_dict['Current_high_group_number']=0
            high_group_counter=dummy_dict['High_group_counter']
            current_high_group_number=dummy_dict['Current_high_group_number']
            
            # global high_group_counter, current_high_group_number
            print (f"Tier High, before assigner: high_group_counter = {high_group_counter}, current_high_group_number = {current_high_group_number}")
            
            high_group_counter, current_high_group_number = group_assigner(high_group_counter, current_high_group_number, group_size)
            
            print (f"Tier High, after assigner: high_group_counter = {high_group_counter}, current_high_group_number = {current_high_group_number}")

            dummy_dict['High_group_counter']=high_group_counter
            dummy_dict['Current_high_group_number']=current_high_group_number
            
            session['Number_in_group']= high_group_counter
            print(f"user {session['Subject']} number in gtoup {session['Number_in_group']}")
            session['Group_number_for_model']=current_high_group_number
            session['Group']=session['Land_income_tier']+str(current_high_group_number)
                
        else:
            # global low_group_counter, current_low_group_number
            
            if 'Low_group_counter' not in dummy_dict:
                dummy_dict['Low_group_counter']=0
            if 'Current_low_group_number' not in dummy_dict:
                dummy_dict['Current_low_group_number']=0
            low_group_counter=dummy_dict['Low_group_counter']
            current_low_group_number=dummy_dict['Current_low_group_number']

            print (f"Tier Low, before assigner: low_group_counter = {low_group_counter}, current_low_group_number = {current_low_group_number}")

            low_group_counter, current_low_group_number = group_assigner(low_group_counter, current_low_group_number, group_size)
            
            print (f"Tier Low, after assigner: low_group_counter = {low_group_counter}, current_low_group_number = {current_low_group_number}")
            dummy_dict['Low_group_counter']=low_group_counter
            dummy_dict['Current_low_group_number']=current_low_group_number
            
            session['Number_in_group']= low_group_counter
            session['Group_number_for_model']=current_low_group_number
            session['Group']=session['Land_income_tier']+str(current_low_group_number)



# Saving group info
        if session['Group'] not in groups_content_dict:
            groups_content_dict[session['Group']]=[session['Subject']]
        else:
            groups_content_dict[session['Group']].append(session['Subject'])

        save_json(path_main_dict,dummy_dict)
        save_json(path_groups_content_dict, groups_content_dict)

# Loading subject datafile and writing
        subject_dict['Group_number_for_model']=session['Group_number_for_model']
        subject_dict['Group']=session['Group'] 

# Setting endowment, income, active part, current_task_id 
        if 'Endowment' not in session:
            session['Endowment']=endowment_distributor()
        if 'Income_current' not in session:
            session['Income_current'] = 0
        if 'Active_part' not in session:
            session['Active_part'] = 1
        if 'Current_task_id' not in session:
            session['Current_task_id']=-1

# Assigning model based on group
        if (session['Group_number_for_model'] + 2) % 3 == 0:
            session['Model']="UBI"
        elif (session['Group_number_for_model']+ 1) % 3 == 0:
            session['Model']="WS"
        else: 
            session['Model']="UBIWS"
# Saving to subject's file
        subject_dict['Endowment']=session['Endowment']
        subject_dict['Model']=session['Model']
        subject_dict['Active_part'] = session['Active_part']
        save_json(path_subject_file, subject_dict)



# Redirecting to task if came by clicking 'Back' from tasks
    if 'Task_type' in session: 
        return redirect (f"/{session['Task_type'].lower()}")

# Redirecting back to voting if came from voting 
    if 'Voted' in session: 
        return render_template ('wait.html')

# Opening the correspondent model page
    if session['Model'] == "UBI":
        return render_template("ubiPart1.html", group_size=group_size, lower_range=lower_range, upper_range=upper_range, amount_UBI=amount_UBI, wage_rate=wage_rate, working_time=working_time, cutoff_income=cutoff_income, tax_rate=tax_rate)
    elif session['Model'] == "UBIWS":
        return render_template("ubiwsPart1.html", group_size=group_size, lower_range=lower_range, upper_range=upper_range, amount_UBIWS=amount_UBIWS, subsidy_rate_UBIWS=subsidy_rate_UBIWS, wage_rate=wage_rate, working_time=working_time, cutoff_income=cutoff_income, tax_rate=tax_rate)
    elif session['Model'] == "WS":
        return render_template("wsPart1.html", group_size=group_size, lower_range=lower_range, upper_range=upper_range, subsidy_rate_WS=subsidy_rate_WS, wage_rate=wage_rate, working_time=working_time, cutoff_income=cutoff_income, tax_rate=tax_rate)    


@app.route('/voting', methods=['POST','GET'])
def voting():
    if request.method == "POST":
        if 'Constitutional' in request.form:
            session['Voted_for_constitution'] = request.form['Constitutional']
            # Loading voting dict            
            path_voting_in_group = os.path.join(path_data_folder, f"groups/{session['Group']}_constitution.json")
            create_if_not_exists(path_voting_in_group,{})
            create_if_not_exists(path_voting_dict,{})
            voting_dict=load_data(path_voting_dict)
            voting_in_group_dict=load_data(path_voting_in_group)
# Registering votes            
            if session['Group'] not in voting_dict:
                voting_dict[session['Group']]=[session['Voted_for_constitution']]
            else:
                voting_dict[session['Group']].append(session['Voted_for_constitution'])
# Updating files and saving 
            voting_in_group_dict[session['Subject']]=session['Voted_for_constitution']
            save_json(path_voting_dict, voting_dict)
            save_json(path_voting_in_group, voting_in_group_dict)
            return render_template('waiting.html')
        
        elif "Taxation" in request.form:
            session['Voted_for_taxation'] = request.form['Taxation']
            # Loading voting dict            
            path_voting_in_group = os.path.join(path_data_folder, f"groups/{session['Group']}_taxation.json")
            create_if_not_exists(path_voting_in_group,{})
            create_if_not_exists(path_voting_taxation_dict,{})
            voting_taxation_dict=load_data(path_voting_taxation_dict)
            voting_in_group_dict=load_data(path_voting_in_group)
# Registering votes            
            if session['Group'] not in voting_taxation_dict:
                voting_taxation_dict[session['Group']]=[session['Voted_for_taxation']]
            else:
                voting_taxation_dict[session['Group']].append(session['Voted_for_taxation'])
# Updating files and saving 
            voting_in_group_dict[session['Subject']]=session['Voted_for_taxation']
            save_json(path_voting_taxation_dict, voting_taxation_dict)
            save_json(path_voting_in_group, voting_in_group_dict)
            return render_template('waiting.html')

    else:
        if (session['Stage']=="Constitutional"):
            return render_template('vote_constitutional.html')
        elif (session['Stage'] == "Taxation"):
            return render_template('vote_taxation.html')

@app.route('/tax')
def tax():
    session['Stage']='Taxation'
    session['Revote']="False"
    if session['Constitution'] == "Unanimity":
        return redirect ('/chat')
    elif session['Constitution'] == "Majority":
        return redirect('/voting')

@app.route('/vote_counter', methods=['POST', 'GET'])
async def vote_counter():
    # voting function waiting for inputs
    if 'Constitution' not in session:
        try:
            group_voted_for= await voting_unanimity(group_size, path_voting_dict)
        except:
            group_voted_for="Revote"
            session['Revote']="True"
            return redirect('/chat')

        # updating files and saving
        if group_voted_for == "Revote":
            # voting_dict=load_data(path_voting_dict)
            # voting_dict.pop(session['Group'])
            # save_json(path_voting_dict, voting_dict)
            session['Revote']="True"
            path_voting_in_group = os.path.join(path_data_folder, f"groups/{session['Group']}_constitution.json")
            save_json(path_voting_in_group, {})
            return redirect('/chat')

        elif group_voted_for == "Unanimity" or group_voted_for == "Majority":
            path_subject_file=os.path.join(path_subjects_folder, f'{session["Subject"]}.json')
            session['Constitution']=group_voted_for
            subject_dict=load_data(path_subject_file)
            subject_dict['Constitution']=session['Constitution']
            save_json(path_subject_file,subject_dict)
            stage=session['Stage']
            
            
            return render_template('voting_results.html', stage=stage, voted=group_voted_for)
            
    elif "Taxation_system" not in session:
        if session['Constitution']=="Unanimity":
            try:
                group_voted_for= await voting_unanimity(group_size, path_voting_taxation_dict)
            except:
                group_voted_for="Revote"
                session['Revote']="True"
                return redirect('/chat')
        
        elif session['Constitution']=="Majority":
            try:
                group_voted_for= await voting_majority(group_size, path_voting_taxation_dict)
            except:
                return redirect('/taskchoice')

        if group_voted_for == "Revote":
            # voting_dict=load_data(path_voting_dict)
            # voting_dict.pop(session['Group'])
            # save_json(path_voting_dict, voting_dict)
            session['Revote']="True"
            path_voting_in_group = os.path.join(path_data_folder, f"groups/{session['Group']}_taxation.json")
            save_json(path_voting_in_group, {})
            return redirect('/chat')

        elif group_voted_for == "Income" or group_voted_for == "Endowment":
            session['Taxation_system'] = group_voted_for  
            path_subject_file=os.path.join(path_subjects_folder, f'{session["Subject"]}.json')   
            subject_dict=load_data(path_subject_file)
            subject_dict['Taxation_system']=session['Taxation_system']
            save_json(path_subject_file,subject_dict)
            stage=session['Stage']
            print(f"Group {session['Group']} voted for {group_voted_for}")
            return render_template('voting_results.html', stage=stage, voted=group_voted_for)
        else: 
            
            return redirect('/taskchoice')
    
    
    
    


# @app.route('/results_voting')
# async def results_voting():
# # voting function waiting for inputs
#     if 'Taxation_system' not in session:
#         try:
#             group_voted_for= await voting_calculator(group_size)
#         except:
#             return redirect('/taskchoice')
    
# # updating files and saving
#         if group_voted_for == "1":
#             session['Taxation_system'] = "Income_tax"
#         elif group_voted_for == "2":
#             session['Taxation_system'] = "Endowment_tax"    
#         path_subject_file=os.path.join(path_subjects_folder, f'{session["Subject"]}.json')       
#         subject_dict=load_data(path_subject_file)
#         subject_dict['Voted_for']=session['Voted_for']
#         subject_dict['Taxation_system']=session['Taxation_system']
#         save_json(path_subject_file, subject_dict)
#         print(f"Group {session['Group']} voted for {group_voted_for}")
#         return render_template('results_voting.html', voted=group_voted_for)
#     else: 
#         return redirect('/taskchoice')

# @app.route('/vote', methods=['POST', 'GET'])
# def vote():
# # Processin clicked voting button    
#     if request.method == 'POST':
#         if 'Voted' not in session:
#             session['Voted_for']=request.form['answer']
#             session['Voted']="True"
# # Loading voting dict            
#             path_voting_in_group = os.path.join(path_data_folder, f"groups/{session['Group']}.json")
#             create_if_not_exists(path_voting_in_group,{})
#             create_if_not_exists(path_voting_dict,{})
#             voting_dict=load_data(path_voting_dict)
#             voting_in_group_dict=load_data(path_voting_in_group)
# # Registering votes            
#             if session['Group'] not in voting_dict:
#                 voting_dict[session['Group']]=[session['Voted_for']]
#             else:
#                 voting_dict[session['Group']].append(session['Voted_for'])
# # Updating files and saving 
#             voting_in_group_dict[session['Subject']]=session['Voted_for']
#             save_json(path_voting_dict, voting_dict)
#             save_json(path_voting_in_group, voting_in_group_dict)
            
#             return render_template('wait.html')
#     elif 'Voted' not in session: 
# # Entering voting for the 1 time
#         return render_template('vote.html', part_started=session['Active_part'], income=session['Income_current'], endowment=session['Endowment']) 
# # If voting entered by clicking back 
#     elif "Voted" in session:
#         return render_template('wait.html')



@app.route("/taskchoice/", methods=['POST', 'GET'])
def taskchoice():
    if request.method == "POST":
# if tried to submit request after clicking back from task
        if 'Task_loaded' in session: 
            return render_template('taskchosen.html', task=session['Task_type'].lower())

# Registering that task was loaded, loading subject file
        path_subject_file=os.path.join(path_subjects_folder, f'{session["Subject"]}.json')
        session['Task_type']=list(request.form.keys())[0]
        session['Task_loaded'] = "True"
        session['Last_task']=""
        # session[f'Correct_part{session["Active_part"]}'] = 0
        session[f'Work_units_part{session["Active_part"]}'] += 1
        session['Current_task_id'] += 1
        subject_dict=load_data(path_subject_file)
# Resistration of task type            
        if 'Tasks' not in session:
            subject_dict['Tasks']={}
        subject_dict['Tasks'][session["Current_task_id"]]=[session['Task_type']]
        save_json(path_subject_file, subject_dict)
# Processing form from post request, creating entries in session file        
        if 'Paid' in request.form:
            session[f'Paid_work_part{session["Active_part"]}'] += 1
            return redirect('/paid')

        elif 'Unpaid' in request.form:
            session[f'Unpaid_work_part{session["Active_part"]}'] += 1
            return redirect('/unpaid')
        
        elif 'Nowork' in request.form:
            session[f'No_work_part{session["Active_part"]}'] += 1
            return redirect('/nowork')

# Actions by entering the page for the first time 
    elif "First_time_entering" not in session:
        if 'Task_loaded' not in session:
            session['First_time_entering']="True"
            session[f'Work_units_part{session["Active_part"]}']= 0
            session[f'Correct_part{session["Active_part"]}'] = 0
            session[f'Paid_work_part{session["Active_part"]}'] = 0
            session[f'Unpaid_work_part{session["Active_part"]}'] = 0
            session[f'No_work_part{session["Active_part"]}'] = 0
         
        return render_template("taskchoice.html", work_units=total_work_units, endowment=session['Endowment'], part_started=session['Active_part'])
   
    elif 'Task_loaded' in session: 
        return redirect(f"/{session['Task_type'].lower()}")
    
    # elif session['Active_part']==2:
    #     return render_template("taskchoice.html", work_units=total_work_units, endowment=session['Endowment'], part_started=session['Active_part'])
    else: 
        return "Unexpected outcome :) Please tell us about it"
        # return render_template("taskchoice.html", work_units=total_work_units, endowment=session['Endowment'], part_started=session['Active_part'])




@app.route("/unpaid", methods=['POST', 'GET'])
def unpaid():
    if request.method=="POST":
# Registering contents of the form
        if "Task_loaded" in session:
            trivia_answer = request.form['trivia_answer']
            if chr(int(trivia_answer)+97) == trivia_answers_list[session['Current_task_id']]:
                session['Last_task']="Correct"
            else: 
                session['Last_task']="Incorrect"
# Saving answer for task             
            path_subject_file=os.path.join(path_subjects_folder, f'{session["Subject"]}.json')
            subject_dict=load_data(path_subject_file)
            subject_dict['Tasks'][str(session['Current_task_id'])].append(session['Last_task'])
            save_json(path_subject_file, subject_dict)
            session.pop('Task_loaded')
            return redirect ('/taskswitch')

        elif 'Task_loaded' not in session:
            return render_template('tasksubmitted.html')

# Entering the page
    elif 'Task_loaded' in session:
        

# Loading trivia data        
        session['Current_task_content']=trivia_content[session['Current_task_id']]
        session['Current_task_options']=trivia_content_options[session['Current_task_id']]
    
        return render_template('trivia.html', current_work_units=session[f'Work_units_part{session["Active_part"]}'], total_work_units=total_work_units, task_content=session['Current_task_content'], task_content_options=session['Current_task_options'])
    
    elif 'Task_loaded' not in session:
        return redirect('/taskswitch')

    else: 
        "We did not expect this. Please let us know!"


@app.route("/paid/", methods=['POST', 'GET'])
def paid():
    if request.method=="POST":
        if "Task_loaded" in session:
            session['Answer_given']=request.form['answerGiven']
            
            session.pop('Task_loaded')

# Numeration 0-23
            return redirect(f'/check/{session["Current_task_id"]}')

        
        elif "Task_loaded" not in session:
            return render_template('tasksubmitted.html')

# Entering the page     
    elif "Task_loaded" in session:
        session['Current_task_content']=tasks_content[session['Current_task_id']]
        session['Current_task_correct_answer']=tasks_answers[session['Current_task_id']]

        return render_template("maths.html", current_work_units=session[f'Work_units_part{session["Active_part"]}'], total_work_units=total_work_units, task_content=session['Current_task_content'])
    else: 
        return redirect('/taskswitch')
    

@app.route('/nowork', methods = ['POST', 'GET'])
def nowork():
    if request.method== 'POST':
        if 'Task_loaded' in session:
            session.pop('Task_loaded')
            return redirect('/taskswitch')
            
        else:
            return render_template('tasksubmitted.html')
   
    elif 'Task_loaded' in session:

        return render_template('nowork.html', current_work_units=session[f'Work_units_part{session["Active_part"]}'], total_work_units=total_work_units, task_id=str(session['Current_task_id']))
    elif 'Task_loaded' not in session:
        return redirect ('/taskswitch')
    else:
        "Error not expected! Please let us know!"    


@app.route('/check/<int:id>')
def check(id):
    task_for_check = session['Answer_given']
    path_subject_file=os.path.join(path_subjects_folder, f'{session["Subject"]}.json')
    subject_dict=load_data(path_subject_file)
    print(subject_dict['Tasks'])
    subject_dict['Tasks'][str(session['Current_task_id'])].append(session['Answer_given'])

# CHecking answer    
    if task_for_check == tasks_answers[id]:
        session[f'Correct_part{session["Active_part"]}'] += 1
        session['Last_task']="Correct"
    else: 
        session['Last_task']="Incorrect"
# Saving answer and correctness for maths task    
    subject_dict['Tasks'][str(session['Current_task_id'])].append(session['Last_task'])
    save_json(path_subject_file, subject_dict)
 
    
    return redirect ('/taskswitch')



@app.route("/taskswitch", methods = ['POST','GET'])
def taskswitch():
    if request.method == 'POST':
        
        if 'Task_loaded' in session: 
            return render_template('taskchosen.html', task=session['Task_type'].lower())
        
        
# Registering chosen task
        session['Task_type']=list(request.form.keys())[0]
        session['Task_loaded']="True"
        session['Current_task_id'] += 1
        session[f'Work_units_part{session["Active_part"]}'] += 1
        path_subject_file=os.path.join(path_subjects_folder, f'{session["Subject"]}.json')
        subject_dict=load_data(path_subject_file)
# Resistration of task type            
        subject_dict['Tasks'][session["Current_task_id"]]=[session['Task_type']]
        save_json(path_subject_file, subject_dict)
        
        if 'Paid' in request.form:
            session[f'Paid_work_part{session["Active_part"]}'] += 1
            return redirect('/paid')

        elif 'Unpaid' in request.form:
            session[f'Unpaid_work_part{session["Active_part"]}'] += 1
            return redirect('/unpaid')
                
        elif 'Nowork' in request.form:
            session[f'No_work_part{session["Active_part"]}'] += 1
            return redirect('/nowork')

       

    elif session[f'Work_units_part{session["Active_part"]}'] < total_work_units:

        session['Income_current']=gross_income_calculator(session['Model'], session[f'Correct_part{session["Active_part"]}'],session[f'Work_units_part{session["Active_part"]}'])

        session[f'Income_after_taxation_part{session["Active_part"]}']=income_after_taxes_calculator(session['Model'], session['Taxation_system'], session[f'Correct_part{session["Active_part"]}'], session['Endowment'], session[f'Work_units_part{session["Active_part"]}'])


        
        return render_template("taskswitch.html", switching_attempts=switching_attempts, task_type=session['Task_type'], last_task=session['Last_task'], total_work_units=total_work_units, current_work_units=session[f'Work_units_part{session["Active_part"]}'], income=session['Income_current'], endowment=session['Endowment'], part_started=session['Active_part'], income_after_tax = session[f'Income_after_taxation_part{session["Active_part"]}'])
    
    elif session[f'Work_units_part{session["Active_part"]}'] >= total_work_units:
        session[f'Income_part{session["Active_part"]}']=session["Income_current"]
        session[f'Income_after_taxation_part{session["Active_part"]}']=income_after_taxes_calculator(session['Model'], session['Taxation_system'], session[f'Correct_part{session["Active_part"]}'], session['Endowment'], session[f'Work_units_part{session["Active_part"]}'])

        path_subject_file=os.path.join(path_subjects_folder, f'{session["Subject"]}.json')
        subject_dict=load_data(path_subject_file)
        subject_dict[f'Income_part{session["Active_part"]}']=session["Income_current"]
        subject_dict[f'Income_after_taxation_part{session["Active_part"]}']=session[f'Income_after_taxation_part{session["Active_part"]}']
        save_json(path_subject_file, subject_dict)
        if session['Active_part']==1:
            return redirect('/preliminary_results')
        else:
            return redirect('/final_results')
        
@app.route('/preliminary_results', methods=['POST', 'GET'])
def preliminary_results():
    if request.method == 'POST':
        # if session['Active_part'] == 1:
        session['Active_part'] = 2
        session.pop('First_time_entering')
        return redirect('/model2')

    else: 
        return render_template('prelim_results.html', income=session[f'Income_part{session["Active_part"]}'], endowment=session['Endowment'], income_after_tax=session[f'Income_after_taxation_part{session["Active_part"]}'], tax_system = session['Taxation_system'])


@app.route("/model2")
def model2():
    if session["Active_part"] == 2:
        if session['Model'] == "UBI":
            return render_template("ubiPart2.html", group_size=group_size, lower_range=lower_range, upper_range=upper_range, amount_UBI=amount_UBI, wage_rate=wage_rate, working_time=working_time, cutoff_income=cutoff_income, tax_rate=tax_rate)
        elif session['Model'] == "UBIWS":
            return render_template("ubiwsPart2.html", group_size=group_size, lower_range=lower_range, upper_range=upper_range, amount_UBIWS=amount_UBIWS, subsidy_rate_UBIWS=subsidy_rate_UBIWS, wage_rate=wage_rate, working_time=working_time, cutoff_income=cutoff_income, tax_rate=tax_rate)
        elif session['Model'] == "WS":
            return render_template("wsPart2.html", group_size=group_size, lower_range=lower_range, upper_range=upper_range, subsidy_rate_WS=subsidy_rate_WS, wage_rate=wage_rate, working_time=working_time, cutoff_income=cutoff_income, tax_rate=tax_rate) 
    else:
        return redirect('/preliminary_results')


@app.route('/final_results', methods=['POST', 'GET'])
def final_results():
    if request.method == 'POST':
        if 'Finished' not in session and session['Active_part'] == 2:
                session['Finished'] = "True"
        return redirect('/system_choice')

    elif "Finished" not in session: 
        path_subject_file=os.path.join(path_subjects_folder, f'{session["Subject"]}.json')
        subject_dict=load_data(path_subject_file)
        total_income = session["Income_after_taxation_part1"]+session["Income_after_taxation_part2"]
        session['Total_income']=total_income
        subject_dict['Total_income']=session['Total_income']
        save_json(path_subject_file, subject_dict)

        return render_template('final_results.html', income=session[f'Income_part{session["Active_part"]}'], endowment=session['Endowment'], income_after_tax=session[f'Income_after_taxation_part{session["Active_part"]}'], tax_system = session['Taxation_system'], income_after_tax_part1 = session['Income_after_taxation_part1'], total_income=total_income)
        

@app.route('/system_choice', methods=['POST', 'GET'])
def system_choice():
    if request.method == 'POST':
        if 'System_choice' not in session:
            session['System_choice']="True"
            session['System_chosen'] = request.form['answer']
            path_subject_file=os.path.join(path_subjects_folder, f'{session["Subject"]}.json')
            subject_dict=load_data(path_subject_file)
            subject_dict['System_chosen']=session['System_chosen']
            save_json(path_subject_file, subject_dict)
        return redirect ('/questionnaire')
    else:
        return render_template('choice_system.html', income=session[f'Income_part{session["Active_part"]}'], endowment=session['Endowment'], income_after_tax=session[f'Income_after_taxation_part{session["Active_part"]}'], tax_system = session['Taxation_system'])
   


@app.route('/questionnaire/', methods=['POST', 'GET'])
def questionnaire():
        if request.method == "POST":
            # path_subject_file=os.path.join(path_subjects_folder, f'{session["Subject"]}.json')
            # subject_dict=load_data(path_subject_file)
            session['Questionnaire']=request.form
            session['Questionnaire_list']={"":""}
            session['Questionnaire_list']['Q6']=request.form.getlist('Q6')
            session['Questionnaire_list']['Q8']=request.form.getlist('Q8')
            session['Questionnaire_list']['Q9']=request.form.getlist('Q9')
            session['Questionnaire_list']['Q18']=request.form.getlist('Q18')
            session['Questionnaire_list']['Q20']=request.form.getlist('Q20')
            # subject_dict['Questionnaire']=session['Questionnaire']
            # save_json(path_subject_file, path_subject_file)
            
            path_subject_file=os.path.join(path_subjects_folder, f'{session["Subject"]}.json')
            subject_dict=load_data(path_subject_file)
            # pathData=os.path.join(path_subjects_folder, f"{session['Subject']}_recovered.json")
            questionnaireQuestions = list(request.form.keys())
            questionnaireAnswers = list(request.form.values())
            questionnaireDict = dict(zip(questionnaireQuestions, questionnaireAnswers))
            
            questionnaireDict['Q6'] = request.form.getlist('Q6')
            questionnaireDict['Q8'] = request.form.getlist('Q8')
            questionnaireDict['Q9'] = request.form.getlist('Q9')
            questionnaireDict['Q18'] = request.form.getlist('Q18')
            questionnaireDict['Q20'] = request.form.getlist('Q20')
            subject_dict = load_data(path_subject_file)
            # dummyDict['Questionnaire_answers']={}
            subject_dict.update(questionnaireDict)
            save_json(path_subject_file,subject_dict)
            
            return redirect('/final')
        else:
            return render_template('questionnaire.html')


@app.route('/final')
def final():
    path_recovery_file=os.path.join(path_subjects_recovered_folder, f'{session["Subject"]}_recovered.json')
    create_if_not_exists(path_recovery_file, {})
    subject_dict={}
    # print(session)
    for k in session:
        subject_dict[f'{k}']=session[f'{k}']
    save_json(path_recovery_file, subject_dict)
    return render_template('final.html', code=session['Subject'])

# @app.route("/expRulesStage2/")
# def exptRulesStage2():
#     return render_template("expRulesStage2.html")


@app.route('/controlpanel')
def control_panel():
    subjects_count = load_data(path_main_dict)['Subjects_amount']
      
    fetched_data = admin.data_fetcher(path_subjects_recovered_folder)

    subjects_finished = admin.parameter_counter("Finished", fetched_data)
    full_groups = admin.full_group_counter(group_size)
    ubi_count=admin.quality_parameter_counter("Model", "UBI", fetched_data)
    ws_count=admin.quality_parameter_counter("Model", "WS", fetched_data)
    ubiws_count=admin.quality_parameter_counter("Model", "UBIWS", fetched_data)
    models_list = admin.model_group_distribution_counter(group_size)
    ubi_group_count = models_list['UBI']
    ws_group_count = models_list['WS']
    ubiws_group_count = models_list['UBIWS']
    average_income_earned_part1 = admin.average_income(fetched_data,"Income_part", 1)
    average_income_earned_part2 = admin.average_income(fetched_data,"Income_part", 2)
    average_income_after_taxation_part1 = admin.average_income(fetched_data,"Income_after_taxation_part", 1)
    average_income_after_taxation_part2 = admin.average_income(fetched_data,"Income_after_taxation_part", 2)

    average_paid_hours_part1 = admin.average_income(fetched_data, "Paid_work_part", 1)
    average_paid_hours_part2 = admin.average_income(fetched_data, "Paid_work_part", 2)
    average_unpaid_hours_part1 = admin.average_income(fetched_data, "Unpaid_work_part", 1)
    average_unpaid_hours_part2 = admin.average_income(fetched_data, "Unpaid_work_part", 2)
    average_nowork_hours_part1 = admin.average_income(fetched_data, "No_work_part", 1)
    average_nowork_hours_part2 = admin.average_income(fetched_data, "No_work_part", 2)

    taxation_chosen=admin.taxation_chosen_by_model_counter(group_size)
    
    return render_template('controlpanel.html', subjects_count=subjects_count, subjects_finished=subjects_finished, full_groups=full_groups, ubi_count=ubi_count, ws_count=ws_count, ubiws_count=ubiws_count, group_size=group_size, ubi_group_count=ubi_group_count, ws_group_count=ws_group_count, ubiws_group_count=ubiws_group_count, average_income_earned_part1=average_income_earned_part1, average_income_earned_part2=average_income_earned_part2, average_income_after_taxation_part1=average_income_after_taxation_part1,average_income_after_taxation_part2 = average_income_after_taxation_part2, average_paid_hours_part1=average_paid_hours_part1, average_paid_hours_part2 = average_paid_hours_part2, average_unpaid_hours_part1 = average_unpaid_hours_part1, average_unpaid_hours_part2 = average_unpaid_hours_part2, average_nowork_hours_part1 = average_nowork_hours_part1, 
    average_nowork_hours_part2 =average_nowork_hours_part2, taxation_chosen=taxation_chosen)


@app.route('/save')
def save_save():
    path_recovery_file=os.path.join(path_subjects_recovered_folder, f'{session["Subject"]}_recovered.json')
    create_if_not_exists(path_recovery_file, {})
    subject_dict={}
    # print(session)
    for k in session:
        subject_dict[f'{k}']=session[f'{k}']
    save_json(path_recovery_file, subject_dict)
    return '''saved.. i hope
    
    '''


@app.route('/clear', methods=['POST', 'GET'])
def clear():
    if request.method == "GET":
        return render_template('clear.html')
    elif request.method == "POST":
        session.clear()
        return redirect('/')    
    # return '''session cleared
    # <br> 
    # <a href="http://experiment.socolab.online">http://experiment.socolab.online</a>
    
    # '''


# @app.route('/chatmech')
# def chatintro():
#     return render_template('chatmech.html')

@app.route('/chat')    
def chat():
    create_dir_if_not_exists(path_chat_folder)
    username = f"Player {session['Number_in_group']}"
    room = session['Group']
    path_chat = os.path.join(path_chat_folder, f"{room}.json")
    create_if_not_exists(path_chat, [])
    chat_history = load_data(path_chat)
    stage=session['Stage']
    if "Constitution" in session:
        voting_type=session['Constitution']
    else: 
        voting_type=['Unanimity']
    if "Revote" in session:
        revote=session['Revote']
    else: 
        revote="NA"
  #  username = request.args.get('username')
  #  room = request.args.get('room')
    if username and room:    

        return render_template('chat.html', username=username, room=room, user=session['Subject'], chat_history=chat_history, stage=stage, voting_type=voting_type, revote=revote)
    else:
        return redirect (url_for('home'))


@socketio.on('join_room')
def handle_join_room_event(data):
    # create_dir_if_not_exists(path_chat_folder)
    # path_chat = os.path.join(path_chat_folder, f"{session['Group']}.json")
    # create_if_not_exists(path_chat, [])
    app.logger.info(f"{data['username']} has joined the room {data['room']}")
    join_room(data['room'])
    # chat_history = load_data(path_chat)
    # data['chat_history']=chat_history
    # socketio.emit('join_room_announcement', data, room=data['room'])

@socketio.on('send_message')
def handle_send_message_event(data):
    message_time=datetime.now()
    data['message_time']=message_time.strftime("%H:%M:%S")
    app.logger.info(f"{data['username']} has sent message to the room {data['room']}: {data['message']} at {data['message_time']}")
    path_chat = os.path.join(path_chat_folder, f"{session['Group']}.json")
    chat_history = load_data(path_chat)
    chat_history.append({"Subject" : session['Subject'], "Username": data['username'], "Room": data['room'], "Message_time": data['message_time'], "Message": data['message'], "Stage" : session['Stage']})
    save_json(path_chat, chat_history)
    # if data['message']=="/vote":
    #     socketio.emit('redirect', url_for('voting'), room=data['room'])
    # else:
    socketio.emit('receive_message', data, room=data['room'])

# @socketio.on('voting_stage')
# def voting_preparation(data):
#     data['Subject']=session['Subject']
#     socketio.emit('connected_voting', data, room=data['room'])

# @socketio.on('voting_register')
# def register_votes(data):
#     path_voting_in_group = os.path.join(path_data_folder, f"groups/{session['Group']}.json")
#     session['Voted']=data['voted']
#     create_if_not_exists(path_voting_in_group,{})
#     voting_in_group_dict=load_data(path_voting_in_group)
#     voting_in_group_dict[session['Subject']]=session['Voted']
#     if len(voting_in_group_dict) == group_size:
#         votes_counter = Counter(voting_in_group_dict.values())
#         if session['Stage']== "Constitutional":
#             if len(votes_counter) > 1:
#                 voting_in_group_dict = {}
#                 socketio.emit('redirect_to_chat', data, room=data['room'], include_self=True)
                
#             elif len(votes_counter) >= 1:
#                 session['Group_constitution']=session['Voted']
#                 data['voted'] = session['Voted']
#                 socketio.emit('redirect_to_next', data, room=data['room'],include_self=True)
                
                
#         elif session['Stage'] == "Taxation":
#             if session['Group_constitution']=="Unanimity":
#                 pass
#     save_json(path_voting_in_group, voting_in_group_dict)
                

# @socketio.on('setting_voting_var')
# def setting_voting_variable(data):
#     session['Group_constitution']=data['voted']

# @app.route('/voting_results', methods=['POST', 'GET'])
# def voting_results():
#     if request.method== "GET":
#         stage=session['Stage']
#         username = f"Player {session['Number_in_group']}"
#         room = session['Group']
#         if "Group_taxation" and "Group_constitution" in session:
#             voted=session['Group_taxation']
#         elif "Group_constitution" in session:
#             voted=session['Group_constitution']


#         return render_template('voting_results.html', stage=stage, user=session['Subject'], username=username, room=room, voted=voted)
#     elif request.method== "POST":
#         session['Stage']="Taxation"
#         return redirect('/taskchoice')

# @app.route('/voting')
# def voting():
#     stage=session['Stage']
#     username = f"Player {session['Number_in_group']}"
#     room = session['Group']
#     return render_template('voting.html', stage=stage, user=session['Subject'], username=username, room=room)


if __name__=="__main__":
    app.config['ENV'] = "development"
    socketio.run(app, debug=True, host="0.0.0.0")
    # app.run(debug=True, host="0.0.0.0")

