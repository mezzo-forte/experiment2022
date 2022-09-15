# import json 
# import os 
# from PIL import Image


# for i in range(20): 
#     path_to_images=os.path.join(os.getcwd(), f'static/assets/m{i}.jpg')
#     with Image.open(path_to_images) as img:
#         print(img.size)
#         obj=img.resize((640,640))
#         print(obj.size)
#         obj.save(path_to_images)
 

# def load_data(path):
#     with open(path, 'r', encoding="utf-8") as f:
#         return json.loads(f.read())

# def save_json(path, data):
#     with open(path, "w") as f:
#         f.write(json.dumps(data, indent=2))


# path_to_load =  from PIL import Image
# path_to_save = os.path.join(os.getcwd(), 'countrylist.json')

# path_to_load = os.path.join(os.getcwd(), 'high_income_list.json')
# path_to_save = os.path.join(os.getcwd(), 'high_income.json')

# countries = load_data(path_to_load)
# countries_list = []

# for _ in range(len(countries)):
#     countries_list.append(countries[_])

# save_json(path_to_save, countries_list)

# class Tasks():
#     id = -1
#     content = ""
#     correct_answer = ""
#     submitted_answer = ""
#     amount_for_a_part = 10
#     attempt = 0
#     income = 0
    
# task = Tasks()

# task.correct_answer = 5
# dict = {}
# dict['Income']=vars(task)

# dict['Income']['id'] += 1
# print (dict)

