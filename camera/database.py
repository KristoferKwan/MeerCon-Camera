import psycopg2
import os
from dotenv import load_dotenv

# OR, explicitly providing path to '.env'
from pathlib import Path  # Python 3.6+ only
env_path = Path('.') / 'storage.env'
load_dotenv(dotenv_path=env_path)

#Establishing the connection
DATABASE=os.getenv("PGDATABASE")
USER=os.getenv("PGUSER")
PASSWORD=os.getenv("PGPASSWORD")
HOST=os.getenv("PGHOST")
PORT=os.getenv("PGPORT")

load_dotenv("./user.env")
EMAIL=os.getenv("EMAIL")
DEVICE_ID=os.getenv("DEVICE_ID")


def open_connection():
    conn = psycopg2.connect(
        database=DATABASE, user=USER, password=PASSWORD, host=HOST, port=PORT
    )
    #Setting auto commit false
    conn.autocommit = True

    #Creating a cursor object using the cursor() method
    cursor = conn.cursor()
    return conn, cursor

def close_connection(conn):
    conn.close()

def get_people_for_device():
    conn, cursor = open_connection()
    print(DEVICE_ID)
    getPeopleQuery="""SELECT
        p.person_id,
        CONCAT(p.first_name, '_', p.last_name) as fullname,
        ph.image_url
    FROM
        devices d
        INNER JOIN devicesgroup dg
        ON dg.device_id = d.device_id
        INNER JOIN groups g
        ON dg.group_id = g.id
        INNER JOIN grouppeople gp
        ON g.id = gp.group_id
        INNER JOIN people p
        ON gp.person_id = p.person_id
        INNER JOIN photos ph
        ON p.person_id = ph.person_id
    WHERE
        d.device_id=%s
    ORDER BY
        p.last_name ASC,
        p.first_name ASC;"""

    cursor.execute(getPeopleQuery, (DEVICE_ID))
    
    people = cursor.fetchall()
    print(people)
    close_connection(conn)
    return people


def add_device_recording(recordTimestamp, facesDetected, videoRecordingUrl):
    conn, cursor = open_connection()
    numUnknownFaces = facesDetected.count(-1)
    if numUnknownFaces > 0:
        threatLevel = 1
    else:
        threatLevel = 0
    deviceRecordingQuery='''INSERT INTO devicerecords(device_id, created_by, 
    record_timestamp, num_unknown_faces, video_recording_url, threat_level)
    VALUES (%s, %s, timestamp %s, %s, %s, %s)
    returning *'''

    # Preparing SQL queries to INSERT a record into the database.
    peopleDeviceRecordingQuery='''INSERT INTO persondevicerecords(person_id, device_record_id, created_by)
    VALUES (%s, %s, %s)'''
    cursor.execute(deviceRecordingQuery, (DEVICE_ID, EMAIL, recordTimestamp, numUnknownFaces, videoRecordingUrl, threatLevel))
    
    deviceRecord = cursor.fetchone()
    deviceRecordId = deviceRecord[0] 
    for faceId in facesDetected:
        if faceId != -1:
            cursor.execute(peopleDeviceRecordingQuery, (faceId, deviceRecordId, EMAIL))

    print("Records inserted........")
    close_connection(conn)

