from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import cv2
import numpy as np
import torch
import pyttsx3
import google.generativeai as genai
import asyncio
import json
from typing import Set, Dict
import time

# Initialize FastAPI app
app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize YOLOv5 model
model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)

# Configure Gemini API
genai.configure(api_key="AIzaSyApSgyv-eadSkXNdJXKFuC9WTnjzExsBtU")  # Replace with your API key
generation_config = {"temperature": 1, "top_p": 0.95, "top_k": 40, "max_output_tokens": 8192}
gemini_model = genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config=generation_config)
chat_session = gemini_model.start_chat(history=[
    {"role": "user", "parts": ["You are BeetleGuard.ai, a conversational AI for drivers, providing rephrased and helpful responses."]},
])

# Initialize text-to-speech engine
tts_engine = pyttsx3.init()
tts_engine.setProperty('rate', 150)

# Store active WebSocket connections and tracked objects
active_connections: Set[WebSocket] = set()
alerted_objects: Dict[str, float] = {}

# Define alert classes
alert_classes = ["person", "dog", "car"]

# WebSocket connection manager
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except:
        active_connections.remove(websocket)

# Broadcast alert to all connected clients
async def broadcast_alert(alert_data: dict):
    for connection in active_connections:
        try:
            await connection.send_json(alert_data)
        except:
            active_connections.remove(connection)

# Voice alert function
# def voice_alert(text):
#     tts_engine.say(text)
#     tts_engine.runAndWait()

# Lane detection function
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

    lines = cv2.HoughLinesP(cropped_edges, rho=1, theta=np.pi/180, threshold=50, 
                           minLineLength=100, maxLineGap=50)
    line_image = np.zeros_like(frame)
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            cv2.line(line_image, (x1, y1), (x2, y2), (0, 255, 0), 5)
    
    lanes = cv2.addWeighted(frame, 0.8, line_image, 1, 1)
    return lanes

# Object detection and alert function
async def detect_objects_and_alert(frame, lane_midpoint):
    results = model(frame)
    frame_height, frame_width = frame.shape[:2]
    detected_classes = []
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
                    # Generate alert message
                    if class_name == "person":
                        detected_message = f"Notice: A pedestrian is noticed on the {position}."
                    elif class_name == "dog":
                        detected_message = f"Notice: Animal detected on the {position}."
                    elif class_name == "car":
                        detected_message = f"Please be cautious: A vehicle is spotted on the {position}."
                    else:
                        detected_message = f"Attention: {class_name} spotted on your {position}."

                    try:
                        # Get Gemini response
                        response = chat_session.send_message(detected_message)
                        gemini_response = response.text

                        # Create alert data
                        alert_data = {
                            "type": class_name,
                            "position": position,
                            "timestamp": current_time,
                            "message": gemini_response
                        }
                        
                        # Broadcast alert and update tracking
                        await broadcast_alert(alert_data)
                        alerted_objects[detected_key] = current_time
                        
                        # Optional: Voice alert
                        voice_alert(gemini_response)
                    except Exception as e:
                        print(f"Error with alert processing: {e}")

            detected_classes.append((class_name, position))

    # Check for pet-owner combinations
    if ("person", "left") in detected_classes and ("dog", "left") in detected_classes:
        pet_alert_message = "Note: A person and a dog are nearby, possibly together as a pet and owner."
        try:
            response = chat_session.send_message(pet_alert_message)
            gemini_response = response.text
            
            alert_data = {
                "type": "pet_owner",
                "position": "left",
                "timestamp": current_time,
                "message": gemini_response
            }
            
            await broadcast_alert(alert_data)
            voice_alert(gemini_response)
        except Exception as e:
            print(f"Error with pet-owner alert: {e}")

    return results.ims[0]

# Main video processing loop
async def process_video():
    cap = cv2.VideoCapture(0)  # Use appropriate camera index

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                print("Error: Failed to grab frame.")
                break

            # Process frame
            lanes_frame = detect_lanes(frame)
            lane_midpoint = lanes_frame.shape[1] // 2
            output_frame = await detect_objects_and_alert(lanes_frame, lane_midpoint)

            # Optional: Display frame locally
            cv2.imshow("Lane and Object Detection", output_frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            # Add a small delay to prevent overwhelming the system
            await asyncio.sleep(0.033)  # Approximately 30 FPS

    finally:
        cap.release()
        cv2.destroyAllWindows()

# Startup event to begin video processing
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(process_video())

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)