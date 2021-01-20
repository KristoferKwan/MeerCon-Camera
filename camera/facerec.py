#Modified by smartbuilds.io
#Date: 27.06.20
#Desc: This script is running a face recongition of a live webcam stream. This is a modifed
#code of the orginal Ageitgey (GitHub) face recognition demo to include multiple faces.
#Simply add the your desired 'passport-style' face to the 'profiles' folder.

import face_recognition
import cv2
import numpy as np
import os
face_cascade=cv2.CascadeClassifier("haarcascade_frontalface_alt2.xml")
ds_factor=0.6

KNOWN_FACES_DIR = "known_faces"

#Store objects in array
known_person=[] #Name of person string
known_image=[] #Image object
known_face_encodings=[] #Encoding object

# Initialize some variables
process_this_frame = True


for name in os.listdir(KNOWN_FACES_DIR):
    for filename in os.listdir(f"{KNOWN_FACES_DIR}/{name}"):
        try:
            print(f"./{KNOWN_FACES_DIR}/{name}/{filename}")
            image = face_recognition.load_image_file(f"./{KNOWN_FACES_DIR}/{name}/{filename}")
            encoding = face_recognition.face_encodings(image)
            if len(encoding) > 0:
                known_face_encodings.append(encoding)
                known_person.append(name)
                known_image.append(image)
            else:
                print(f"no face found in image at ./{KNOWN_FACES_DIR}/{name}/{filename}")
        except Exception as e:
            print("err encoding image", e)

# returns if a face is the same if the location is somewhere in the vicinity
def isSameFace(location, prevLocation):
    if abs(location[1] - prevLocation[1]) <= 50 and abs(location[0] - prevLocation[0]) <= 50:
        return True
    return False


# takes in the current locations list, corresponding names, and the prevlocations dictionary of faces detected with their corresponding id
def getSameFaces(faceLocations, faceMatches, facesIdentified):
    print(faceLocations)
    print(faceMatches)
    for i in range(len(faceLocations)):
        currLocationPoint = (faceLocations[i][3], faceLocations[i][0]) #gets the left corner of the detection box
        foundFace = None
        # loops through all the faces seens so far in the video stream [location, [list of names]]
        for j in range(len(facesIdentified)):
            faceLocation = facesIdentified[j][0] 
            if isSameFace(currLocationPoint, faceLocation):
                foundFace = j
                facesIdentified[j][1].append(faceMatches[i])
                facesIdentified[j][0] = currLocationPoint
        if foundFace is None:
            print("In not foundFace",foundFace)
            facesIdentified.append([currLocationPoint, [faceMatches[i]]])

def process_img_with_face_rec(image, livestream=True):
    process_this_frame = True
    face_locations = []
    face_encodings = []
    face_names = []
        # Resize frame of video to 1/4 size for faster face recognition processing
    small_frame = cv2.resize(image, (0, 0), fx=0.25, fy=0.25)

    # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
    rgb_small_frame = small_frame[:, :, ::-1]
    
    # Only process every other frame of video to save time
    if process_this_frame:
        # Find all the faces and face encodings in the current frame of video
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

        global name_gui;
        for face_encoding in face_encodings:
            # See if the face is a match for the known face(s)
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
            name = "Unknown"
            
            #print(face_encoding)
            #print(matches)

            face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
            face_distances_sum = np.sum(face_distances, dtype=np.float32, axis=1)

            best_match_index = np.argmin(face_distances_sum)
            if matches[best_match_index].all() and face_distances_sum[best_match_index] < 3.5:
                name = known_person[best_match_index].replace("_", " ")

            print(name + "\n")
            face_names.append(name)
    
            name_gui = name

    process_this_frame = not process_this_frame
        
    # Display the results
    for (top, right, bottom, left), name in zip(face_locations, face_names):
        # Scale back up face locations since the frame we detected in was scaled to 1/4 size
        top *= 4
        right *= 4
        bottom *= 4
        left *= 4

        # Draw a box around the face
        cv2.rectangle(image, (left, top), (right, bottom), (255, 255, 255), 2)

        # Draw a label with a name below the face
        cv2.rectangle(image, (left, bottom - 35), (right, bottom), (255, 255, 255), cv2.FILLED)
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(image, name_gui, (left + 10, bottom - 10), font, 1.0, (0, 0, 0), 1)

    if livestream:
      return image
    elif not process_this_frame: # if the frame was processed this iteration, process_this_frame would have been set to false
      return image, face_locations, face_names
    else:
      return image, None, None