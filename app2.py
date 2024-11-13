import cv2  # type: ignore
import numpy as np  # type: ignore
import torch
import pyttsx3  # type: ignore
import google.generativeai as genai
import time
import asyncio
import websockets

# Load YOLOv5 Model
model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)

# Configure Gemini API
genai.configure(api_key="YOUR_GEMINI_API_KEY")
generation_config = {"temperature": 1, "top_p": 0.95, "top_k": 40, "max_output_tokens": 8192}
gemini_model = genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config=generation_config)
chat_session = gemini_model.start_chat(history=[
    {"role": "user", "parts": ["You are BeetleGuard.ai, a conversational AI for drivers, providing rephrased and helpful responses."]},
])

# Initialize Text-to-Speech Engine
tts_engine = pyttsx3.init()
tts_engine.setProperty('rate', 150)

# Set up WebSocket Clients Set to keep track of connected clients
clients = set()

# WebSocket Handler for Sending Messages
async def websocket_handler(websocket, path):
    # Register client
    clients.add(websocket)
    try:
        await websocket.wait_closed()  # Wait until connection is closed
    finally:
        clients.remove(websocket)  # Remove client on disconnect

# Function to Send Message to All WebSocket Clients
async def send_websocket_message(message):
    if clients:  # Only send if clients are connected
        await asyncio.wait([client.send(message) for client in clients])

# Voice Alert Function
def voice_alert(text):
    tts_engine.say(text)
    tts_engine.runAndWait()

# Detect Objects, Rephrase Alerts, and Send to Frontend via WebSocket
alert_classes = ["person", "dog", "car"]
alerted_objects = {}

async def detect_objects_and_alert(frame, lane_midpoint):
    results = model(frame)
    frame_height, frame_width = frame.shape[:2]
    current_time = time.time()

    for *box, conf, cls in results.xyxy[0]:
        x1, y1, x2, y2 = map(int, box)
        class_name = results.names[int(cls)]
        box_width = x2 - x1
        box_height = y2 - y1
        midpoint = (x1 + x2) // 2

        if (box_width * box_height) >= 5000:
            position = "left" if midpoint < lane_midpoint else "right"
            detected_key = f"{class_name}_{position}"

            if class_name in alert_classes:
                if detected_key not in alerted_objects or (current_time - alerted_objects[detected_key] > 120):
                    if class_name == "person":
                        detected_message = f"Notice: A pedestrian is noticed on the {position}."
                    elif class_name == "dog":
                        detected_message = f"Notice: Animal detected on the {position}."
                    elif class_name == "car":
                        detected_message = f"Please be cautious: A vehicle is spotted on the {position}."
                    else:
                        detected_message = f"Attention: {class_name} spotted on your {position}."

                    print(detected_message)
                    alerted_objects[detected_key] = current_time
                    
                    try:
                        response = chat_session.send_message(detected_message)
                        gemini_response = response.text
                        print(gemini_response)
                        voice_alert(gemini_response)
                        # Send the rephrased message via WebSocket
                        await send_websocket_message(gemini_response)
                    except Exception as e:
                        print(f"Error with Gemini response: {e}")

    results.render()
    return results.ims[0]

# Lane Detection Function
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

# Main Function with WebSocket Integration
async def main():
    cap = cv2.VideoCapture(0)
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to grab frame.")
            break

        lanes_frame = detect_lanes(frame)
        lane_midpoint = lanes_frame.shape[1] // 2

        # Call async function and await it
        output_frame = await detect_objects_and_alert(lanes_frame, lane_midpoint)

        cv2.imshow("Lane and Object Detection with Alerts", output_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

# Start WebSocket Server and Main Loop
if __name__ == "__main__":
    # Start the WebSocket server
    websocket_server = websockets.serve(websocket_handler, "localhost", 6789)

    # Run the main function and the WebSocket server together
    asyncio.get_event_loop().run_until_complete(websocket_server)
    asyncio.get_event_loop().run_until_complete(main())
    asyncio.get_event_loop().run_forever()
