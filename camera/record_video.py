import numpy as np
import os
import cv2
import camera
import time
import facerec
import collections
import threading
import storage
import database
from dotenv import load_dotenv
import pickle

load_dotenv("user.env")

# Set resolution for the video capture
# Function adapted from https://kirr.co/0l6qmh
def change_res(cap, width, height):
    cap.set(3, width)
    cap.set(4, height)

# Standard Video Dimensions Sizes
STD_DIMENSIONS =  {
    "480p": (640, 480),
    "720p": (1280, 720),
    "1080p": (1920, 1080),
    "4k": (3840, 2160),
}

with open("config.pickle", "rb") as f:
    people_dict = pickle.loads(f.read(), encoding="latin-1")

# grab resolution dimensions and set video capture to it.
def get_dims(cap, res='1080p'):
    width, height = STD_DIMENSIONS["480p"]
    if res in STD_DIMENSIONS:
        width,height = STD_DIMENSIONS[res]
    ## change the current caputre device
    ## to the resulting resolution
    change_res(cap, width, height)
    return width, height

# Video Encoding, might require additional installs
# Types of Codes: http://www.fourcc.org/codecs.php
VIDEO_TYPE = {
    '.avi': cv2.VideoWriter_fourcc(*'XVID'),
    '.mp4': cv2.VideoWriter_fourcc(*'mp4v'),
    '.h264': cv2.VideoWriter_fourcc(*'H264'),
}

def get_video_type(filename):
    filename, ext = os.path.splitext(filename)
    print(ext)
    if ext in VIDEO_TYPE:
      return  VIDEO_TYPE[ext]
    return VIDEO_TYPE['avi']


def process_recording(filepath="video.mp4", frames_per_second=10.0, res="480p"):
    facesDetectedList = list()
    
    f, ext = os.path.splitext(filepath)
    fpath = f.split("/")
    path = ("/").join(fpath[0:-1])
    filename=fpath[-1]
    print(filepath)
    processed_filename=f"{path}/processed-{filename}{ext}"

    cap = cv2.VideoCapture(filepath)
    out = cv2.VideoWriter(processed_filename, get_video_type(filepath), frames_per_second, get_dims(cap, res))
    # Loop until the end of the video 
    while (cap.isOpened()): 
        try:
            # Capture frame-by-frame 
            ret, frame = cap.read() 
            if(type(frame) is not None):
                # cv2.imshow('frame',frame)
                # k = cv2.waitKey(1) & 0xFF
                # if k == ord('q'):
                #     break
                #process image to add facial recognition
                _, faceLocations, faceNames = facerec.process_img_with_face_rec(frame, livestream=False)
                if faceNames:
                  facerec.getSameFaces(faceLocations, faceNames, facesDetectedList)
                out.write(frame)
        except Exception as e:
            print(e)
            break
  
    faceIdList = list()
    print(facesDetectedList)
    if len(facesDetectedList) > 0:
      for face in facesDetectedList:
            matchList = face[1]
            matchesCount = collections.Counter(matchList)
            match = matchesCount.most_common(1)[0][0].replace(" ", "_")
            print(f"Individual is {match}")
            if(match == "Unknown"):
                faceIdList.append(-1)
            else:
                faceIdList.append(people_dict[match])
    # release the video capture object 
    cap.release()
    # release the output object
    out.release() 
    # Closes all the windows currently opened. 
    cv2.destroyAllWindows() 

    compressed_filename=f"{path}/result-{filename}{ext}"
    os.system(f"sudo ffmpeg -y -i {processed_filename} -vcodec libx264 {compressed_filename}")
    USER = os.getenv('EMAIL')
    videoRecordingUrl = f"/users/{USER}/devicerecordings/{filename}{ext}"
    storage.upload_file_to_s3(compressed_filename, videoRecordingUrl)
    database.add_device_recording(filename.replace("_", " "), faceIdList, videoRecordingUrl)

def start_recording(filename="video.mp4", frames_per_second=10.0, res="480p"):
    vidCam = camera.VideoCamera(livestream=False)
    cap = vidCam.video
    detectedFaceInit = False 
    out = None
    timeSinceFaceDetected = 0
    startTime = time.time()
    while timeSinceFaceDetected < 3:
        ret, frame = vidCam.get_raw_frame()
        detectedFace = vidCam.detected_face()
        if detectedFace and not detectedFaceInit:
            out = cv2.VideoWriter(filename, get_video_type(filename), frames_per_second, get_dims(cap, res))
            detectedFaceInit = True
            timeSinceFaceDetected = 0
        elif detectedFaceInit and type(out) is cv2.VideoWriter:
            out.write(frame)
        
        if detectedFace:
            startTime = time.time()
        else:
            timeSinceFaceDetected = time.time() - startTime
        # cv2.imshow('frame',frame)
        # k = cv2.waitKey(1) & 0xFF
        # if k == ord('q'):
        #     break
 
    cap.release()
    if type(out) is cv2.VideoWriter:
        out.release()
        clientThread = threading.Thread(target=process_recording, args=(filename, 10.0, "480p", ))
        clientThread.start()
        
    cv2.destroyAllWindows()