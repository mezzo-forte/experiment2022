import os
import json
import re
from collections import Counter

def load_data(path):
    with open(path, 'r', encoding="utf-8") as f:
        return json.loads(f.read())

def save_json(path, data):
    with open(path, "w") as f:
        f.write(json.dumps(data, indent=2))


def data_fetcher(path_to_folder):
    fetched = {}
    dir_listed = os.listdir(path_to_folder)
    for path in dir_listed:
        dummy = load_data(os.path.join(path_to_folder, path))
        fetched[dummy['Subject_number_overall']]=dummy
    # pass
    save_json(path_fetched, fetched)
  
    # fetched[subject_file_data['Subject_overall_number']]=subject_file_data
    # pass
    return fetched

def parameter_counter(parameter, fetched_data):
    counter = 0
    for i in fetched_data:
        if parameter in fetched_data[i]:
            counter += 1

    
    return counter

def quality_parameter_counter(key, parameter, fetched_data):
    counter = 0
    for i in fetched_data:
        if fetched_data[i][key]==parameter:
            counter += 1

    return counter


def full_group_counter(group_size):
    dummy = load_data(path_groups_content_dict)
    counter = 0
    for group in dummy:
        if len(dummy[group]) == group_size:
            counter += 1
    return counter

def model_group_distribution_counter(group_size):
    data = load_data(path_voting_dict)
    data_list = list(data.keys())    
    models = {"UBI":0, "WS":0, "UBIWS":0}
    for group in data:
        if len(data[group]) != group_size:
            data_list.remove(group)
        else:
            print(group)
            print(type(group))
            print(data_list)
            number = ""
            for s in group:
                if s.isdigit():
                    number += s
                    print(number)
                    print(type(number))
            number=int(number)
            print(type(number))
            if (number + 2) % 3 == 0:
                models['UBI']+= 1
            elif (number+ 1) % 3 == 0:
                models['WS'] += 1
            else: 
                models['UBIWS'] += 1  
            # number = re.findall(r'\d+', group)

    return models

def model_counter(fetched_data):
    
    counter=[0,0,0]
    for i in fetched_data:
        if fetched_data[i]['Model']=="UBI":
            counter[0] += 1
        elif fetched_data[i]['Model']=="WS":
            counter[1] += 1
        elif fetched_data[i]['Model'] == "UBIWS":
            counter[2] += 1
    return counter

def average_income(fetched_data, income_type, period):
    sum_income = [0,0,0]
    average_income=[0,0,0]
    model_count = model_counter(fetched_data)
    for entry in fetched_data:
        if fetched_data[entry]['Model']=='UBI':
            sum_income[0] += fetched_data[entry][f'{income_type}{period}']
        elif fetched_data[entry]['Model'] == 'WS':
            sum_income[1] += fetched_data[entry][f'{income_type}{period}']
        elif fetched_data[entry]['Model'] == 'UBIWS':
            sum_income[2] += fetched_data[entry][f'{income_type}{period}']
    for k in range(len(sum_income)):
        try:
            average_income[k]=int(round(sum_income[k]/model_count[k],0))
        except ZeroDivisionError:
            pass

       
    return average_income

def taxation_chosen_by_model_counter(group_size):
       
    data = load_data(path_voting_dict)
    data_list = list(data.keys())    
    
    models_groups = {"UBI": [], "WS": [], "UBIWS":[]}
    taxation_chosen = {"UBI":{"Income_tax":0, "Endowment_tax":0},"WS":{"Income_tax":0, "Endowment_tax":0}, "UBIWS":{"Income_tax":0, "Endowment_tax":0}}
    for group in data:
        if len(data[group]) != group_size:
            data_list.remove(group)
        else:
            
            number = ""
            for s in group:
                if s.isdigit():
                    number += s
                    
            number=int(number)
            print(type(number))
            if (number + 2) % 3 == 0:
                 models_groups["UBI"].append(group)
                 
            elif (number+ 1) % 3 == 0:
                 models_groups["WS"].append(group)
                 
            else: 
                 models_groups["UBIWS"].append(group)
                 
    for i in models_groups:
        for gr in models_groups[i]:
            taxation_chosen = Counter(data[gr]).most_common()
            # number = re.findall(r'\d+', group)

    return  taxation_chosen

# def taxation_chosen_by_model_counter(fetched_data):
#     counter={"UBI":{"Income_tax":0, "Endowment_tax":0},"WS":{"Income_tax":0, "Endowment_tax":0}, "UBIWS":{"Income_tax":0, "Endowment_tax":0}}
#     for i in fetched_data:
#         if fetched_data[i]['Model']=="UBI":
#             if fetched_data[i]['Taxation_system']=="Income_tax":
#                 counter["UBI"]['Income_tax'] += 1
#             else:
#                 counter["UBI"]['Endowment_tax'] += 1
#         elif fetched_data[i]['Model']=="WS":
#             if fetched_data[i]['Taxation_system']=="Income_tax":
#                 counter["WS"]['Income_tax'] += 1
#             else:
#                 counter["WS"]['Endowment_tax'] += 1
#         elif fetched_data[i]['Model']=="UBIWS":
#             if fetched_data[i]['Taxation_system']=="Income_tax":
#                 counter["UBIWS"]['Income_tax'] += 1
#             else:
#                 counter["UBIWS"]['Endowment_tax'] += 1
#     print (counter)
#     return counter

# def average_income_counter(fetched_data, modelCounter):
#     # dummyDictAdmin = load_data(pathAdmin)
#     sumIncome = [0,0,0]
#     averageIncome = [0,0,0]
#     for i in fetched_data:
#         if dummyDictAdmin[i]['Model']=="UBI":
#             sumIncome[0] += dummyDictAdmin[i]['Income']
#         elif dummyDictAdmin[i]['Model']=="UBIWS":
#             sumIncome[1] += dummyDictAdmin[i]['Income']
#         elif dummyDictAdmin[i]['Model']=="MIGWS":
#             sumIncome[2] += dummyDictAdmin[i]['Income']        
#     for k in range(len(sumIncome)):
#         try:
#             averageIncome[k]=int(round(sumIncome[k]/modelCounter[k],0))
#         except ZeroDivisionError:
#             pass
#     return averageIncome

path_data_folder = os.path.join(os.getcwd(), 'data')
path_fetched = os.path.join(path_data_folder, 'fetched.json')
path_subjects_folder = os.path.join(os.getcwd(), 'data/subjects')
path_subjects_recovered_folder = os.path.join(os.getcwd(), 'data/subjects_recovered')
path_maths = os.path.join(os.getcwd(), 'maths.json')
path_maths2 = os.path.join(os.getcwd(), 'maths2.json')
path_main_dict = os.path.join(path_data_folder, 'info.json')
path_groups_content_dict = os.path.join(path_data_folder, 'group_content.json')
path_groups_folder = os.path.join(path_data_folder, 'groups')
path_voting_dict = os.path.join(path_data_folder, 'voting.json')
path_trivia_content = os.path.join(os.getcwd(), 'trivia.json')
path_trivia_answers = os.path.join(os.getcwd(), 'trivia_answers.json')