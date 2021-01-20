#Modified by smartbuilds.io
#Date: 27.06.20
#Desc: This script is running a face recongition of a live webcam stream. This is a modifed
#code of the orginal Ageitgey (GitHub) face recognition demo to include multiple faces.
#Simply add the your desired 'passport-style' face to the 'profiles' folder.

import face_recognition
import cv2
import os
import facerec

class VideoCamera(object):
    def __init__(self, livestream=True):
        self.video = cv2.VideoCapture(0)
        self.livestream = livestream
        self.success, self.image = self.video.read()

    def __del__(self):
        self.video.release()
    
    def set_raw_frame(self):
        self.success, self.image = self.video.read()

    def get_raw_frame(self):
        self.success, self.image = self.video.read()
        return self.success, self.image

    def detected_face(self):
        face_locations = []
        image = self.image
        
        # Resize frame of video to 1/4 size for faster face recognition processing
        small_frame = cv2.resize(image, (0, 0), fx=0.25, fy=0.25)
        
        # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
        rgb_small_frame = small_frame[:, :, ::-1]
        
        # Find all the faces and face encodings in the current frame of video
        face_locations = face_recognition.face_locations(rgb_small_frame)

        # # Display the results
        # for top, right, bottom, left in face_locations:
        #     # Scale back up face locations since the frame we detected in was scaled to 1/4 size
        #     top *= 4
        #     right *= 4
        #     bottom *= 4
        #     left *= 4

        #     # Draw a box around the face
        #     cv2.rectangle(image, (left, top), (right, bottom), (255, 255, 255), 2)

        if len(face_locations) > 0:
            return True
         
        return False

    def get_frame(self):
        self.set_raw_frame()

        image = facerec.process_img_with_face_rec(self.image)

        ret, jpeg = cv2.imencode('.jpg', image)
        
        return jpeg.tobytes()
