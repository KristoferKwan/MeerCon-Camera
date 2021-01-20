import database
import storage
import os
from os import path
import pickle
import shutil
import cv2

def resize_images(folder_path, desired_width):
    for filename in os.listdir(folder_path):
        img = cv2.imread(f"{folder_path}/{filename}")
        width = img.shape[1]
        height = img.shape[0]
        if width > 1000:
            conversionFactor = desired_width/float(width)
            newWidth = desired_width
            newHeight = int(height * conversionFactor)
            dim = (newWidth, newHeight)
            img = cv2.resize(img, dim, interpolation=cv2.INTER_AREA)
            cv2.imwrite(f"{folder_path}/{filename}", img)

if path.exists("./known_faces2"):
    shutil.rmtree("./known_faces2")

people = database.get_people_for_device()
people_dict = dict()
for person in people:
    person_id, fullname, image_url = person
    f, ext = os.path.splitext(image_url)
    fpath = f.split("/")
    filename=fpath[-1]
    folder=f"./known_faces2/{fullname}"
    filepath = f"{folder}/{filename}{ext}"
    if not path.exists(folder):
        os.makedirs(folder)
    storage.download_image_to_s3(filepath, image_url)
    people_dict[fullname] = person_id
    with open("./config.pickle", "wb") as outfile:
        pickle.dump(people_dict, outfile)
  
for person in people_dict:
  filepath = f"./known_faces2/{person}"
  resize_images(filepath, 400)

