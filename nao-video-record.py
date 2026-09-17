
import sys
import time
from naoqi import ALProxy
import paramiko

# --- CONFIGURATION ---
ROBOT_IP = "192.168.200.74"  # Replace with your NAO's IP address
PORT = 9559
ROBOT_USER = "nao"
ROBOT_PASS = "nao"           # Default NAO password is 'nao'

# Paths
REMOTE_VIDEO_PATH = "/home/nao/recordings/my_video"  # Note: Do not append extension (.avi), NAO adds it automatically
LOCAL_OUTPUT_PATH = "downloaded_video_3_hell.avi"           # Where to save it on your computer

RECORD_DURATION = 30  # Duration in seconds

def record_and_download():
    # 1. Initialize NAOqi Proxy for Video Recording
    print("Connecting to NAO...")
    try:
        video_recorder = ALProxy("ALVideoRecorder", ROBOT_IP, PORT)
    except Exception as e:
        print("Could not connect to ALVideoRecorder: ", e)
        sys.exit(1)

    # Configure recording specifications
    video_recorder.setResolution(1)  # 1 = kQVGA (320x240), 2 = kVGA (640x480)
    video_recorder.setFrameRate(10)   # Frames per second (Min 3 fps for MJPG)
    video_recorder.setVideoFormat("MJPG")

    # 2. Start Recording on the Robot
    print("Recording video on NAO for {} seconds...".format(RECORD_DURATION))
    # Path inside the robot. NAO automatically turns 'my_video' into 'my_video.avi'
    video_recorder.startRecording("/home/nao/recordings", "my_video")

    time.sleep(RECORD_DURATION)

    # Stop Recording
    video_info = video_recorder.stopRecording()
    print("Recording stopped. File stored on NAO at: {}".format(video_info[0]))

    # 3. Download the File to Computer via SFTP
    print("Establishing SSH/SFTP connection to pull file...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(ROBOT_IP, username=ROBOT_USER, password=ROBOT_PASS)
        sftp = ssh.open_sftp()

        # Note: The remote extension is explicitly stated here (.avi)
        remote_file_full = REMOTE_VIDEO_PATH + ".avi"
        print("Downloading {} to {}...".format(remote_file_full, LOCAL_OUTPUT_PATH))

        sftp.get(remote_file_full, LOCAL_OUTPUT_PATH)
        print("Transfer complete! Video successfully saved to your PC.")

        sftp.close()
        ssh.close()
    except Exception as e:
        print("Failed to transfer file: ", e)

if __name__ == "__main__":
    record_and_download()
