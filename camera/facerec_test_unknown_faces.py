import face_recognition
import cv2
import numpy as np
import os
face_cascade=cv2.CascadeClassifier("haarcascade_frontalface_alt2.xml")
ds_factor=0.3

KNOWN_FACES_DIR = "known_faces"
UNKNOWN_FACES_DIR = "unknown_faces"
#Store objects in array
known_person=[] #Name of person string
known_image=[] #Image object
known_face_encodings=[] #Encoding object

# Initialize some variables
face_locations = []
face_encodings = []
face_names = []
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

for filename in os.listdir(UNKNOWN_FACES_DIR):
    # Grab a single frame of video
    frame = face_recognition.load_image_file(f'{UNKNOWN_FACES_DIR}/{filename}')
    print(f'{UNKNOWN_FACES_DIR}/{filename}')
    # Resize frame of video to 1/4 size for faster face recognition processing

    # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
    rgb_small_frame = frame

    face_locations = face_recognition.face_locations(rgb_small_frame)
    face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

    global name_gui;
    #face_names = []
    for face_encoding in face_encodings:
        # See if the face is a match for the known face(s)
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=ds_factor)
        name = "Unknown"
        
        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
        face_distances_sum = np.sum(face_distances, dtype=np.float32, axis=1)
        
        best_match_index = np.argmin(face_distances_sum)
        print(len(face_distances[0]), face_distances_sum)
        if matches[best_match_index].all() and face_distances_sum[best_match_index] < 3.5:
            name = known_person[best_match_index].replace("_", " ")

        face_names.append(name)

        name_gui = name

    # Display the results
    print("face_locations", face_locations)
    for (top, right, bottom, left), name in zip(face_locations, face_names):
        # Scale back up face locations since the frame we detected in was scaled to 1/4 size
        # top *= 4
        # right *= 4
        # bottom *= 4
        # left *= 4

        # Draw a box around the face
        cv2.rectangle(frame, (left, top), (right, bottom), (255, 255, 255), 2)

        # Draw a label with a name below the face
        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (255, 255, 255), cv2.FILLED)
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(frame, name_gui, (left + 10, bottom - 10), font, 1.0, (0, 0, 0), 1)

    # Display the resulting image
    cv2.imshow(filename, frame)
    cv2.waitKey(0)