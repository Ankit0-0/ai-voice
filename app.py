import cv2 # type: ignore
import numpy as np # type: ignore
import torch
import pyttsx3 # type: ignore
import google.generativeai as genai

# Initialize YOLOv5 model as per your code
model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)

# Configure Gemini API
genai.configure(api_key="AIzaSyApSgyv-eadSkXNdJXKFuC9WTnjzExsBtU")  # Your API key
generation_config = {"temperature": 1, "top_p": 0.95, "top_k": 40, "max_output_tokens": 8192}
gemini_model = genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config=generation_config)
chat_session = gemini_model.start_chat(history=[
    {"role": "user", "parts": ["You are BeetleGuard.ai, a conversational AI for drivers, providing rephrased and helpful responses."]},
])

# Initialize text-to-speech engine
tts_engine = pyttsx3.init()
tts_engine.setProperty('rate', 150)

# Voice alert function
def voice_alert(text):
    tts_engine.say(text)
    tts_engine.runAndWait()

# Detect objects and send detected messages to Gemini for rephrasing
# Detect objects and provide alerts based on proximity and position, with Gemini integration


import time

# Define classes that will trigger alerts
alert_classes = ["person", "dog", "car"]

# Dictionary to track the last alert time for each alert class and position
alerted_objects = {}

def detect_objects_and_alert(frame, lane_midpoint):
    results = model(frame)
    frame_height, frame_width = frame.shape[:2]
    detected_classes = []  # Track detected classes for pet alert
    current_time = time.time()

    for *box, conf, cls in results.xyxy[0]:
        x1, y1, x2, y2 = map(int, box)
        class_name = results.names[int(cls)]
        box_width = x2 - x1
        box_height = y2 - y1
        midpoint = (x1 + x2) // 2

        # Check if object is close based on bounding box size
        if (box_width * box_height) >= 5000:
            # Determine object position relative to lane midpoint
            position = "left" if midpoint < lane_midpoint else "right"
            detected_key = f"{class_name}_{position}"

           
            if class_name in alert_classes:
                if detected_key not in alerted_objects or (current_time - alerted_objects[detected_key] > 120):  # 2 minutes
                   
                    if class_name == "person":
                        detected_message = f"Notice: A pedestrian is noticed on the {position}."
                    elif class_name == "dog":
                        detected_message = f"Notice: Animal detected on the {position}."
                    elif class_name == "car":
                        detected_message = f"Please be cautious: A vehicle is spotted on the {position}."
                    else:
                        detected_message = f"Attention: {class_name} spotted on your {position}."

                    print(detected_message)  #debug

                    # Send the message to Gemini and track the time for this alert
                    alerted_objects[detected_key] = current_time  # Update last alert time
                    try:
                        response = chat_session.send_message(detected_message)
                        gemini_response = response.text
                        print(gemini_response)  # For debugging
                        voice_alert(gemini_response)
                    except Exception as e:
                        print(f"Error with Gemini response: {e}")

    
    if ("person", "left") in detected_classes and ("dog", "left") in detected_classes:
        pet_alert_message = "Note: A person and a dog are nearby, possibly together as a pet and owner."
        print(pet_alert_message)  # Debugging
        try:
            response = chat_session.send_message(pet_alert_message)
            gemini_response = response.text
            print(gemini_response)  # For debugging
            voice_alert(gemini_response)
        except Exception as e:
            print(f"Error with Gemini response: {e}")

    # Render detections on the frame
    results.render()
    return results.ims[0]

 

# Main function as per your original logic
# Lane detection
def detect_lanes(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)
    
    height, width = frame.shape[:2]
    mask = np.zeros_like(edges)
    polygon = np.array([[
        (0, int(height * 0.7)),
        (width, int(height * 0.7)),
        (width, height),
        (0, height)
    ]], np.int32)
    cv2.fillPoly(mask, polygon, 255)
    cropped_edges = cv2.bitwise_and(edges, mask)

    lines = cv2.HoughLinesP(cropped_edges, rho=1, theta=np.pi/180, threshold=50, minLineLength=100, maxLineGap=50)
    line_image = np.zeros_like(frame)
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            cv2.line(line_image, (x1, y1), (x2, y2), (0, 255, 0), 5)
    
    lanes = cv2.addWeighted(frame, 0.8, line_image, 1, 1)
    return lanes

def main():
    cap = cv2.VideoCapture(0)  # Use appropriate index for camera

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to grab frame.")
            break

        # Lane detection and calculating lane midpoint
        lanes_frame = detect_lanes(frame)
        lane_midpoint = lanes_frame.shape[1] // 2

        # Object detection and alerts based on proximity and position
        output_frame = detect_objects_and_alert(lanes_frame, lane_midpoint)

        # Display frame with lane and object detections
        cv2.imshow("Lane and Object Detection with Alerts", output_frame)

        # Quit on 'q' key press
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release resources
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
